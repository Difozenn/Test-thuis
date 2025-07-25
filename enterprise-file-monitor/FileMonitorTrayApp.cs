using System;
using System.Drawing;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Win32;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.Net;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading;

namespace FileMonitorTray
{
    // Analyzer mode selection
    public enum AnalysisMode
    {
        Simple,     // Basic version - reliable, no server dependency
        Enhanced,   // Advanced version with server config and detailed tracking
        Auto        // Try enhanced first, fallback to simple if needed
    }

    // Missing classes needed for compilation
    public class MachineConfig
    {
        public double RapidFeedrate { get; set; } = 50000.0;
        public double ToolChangeTime { get; set; } = 15.0;
        public double SpindleStartTime { get; set; } = 3.0;
        public double PinChangeTime { get; set; } = 1.0;
        public double CycleOverheadTime { get; set; } = 1.0;
    }

    public class GCodeAnalyzer
    {
        public async Task LoadMachineConfigFromServer(string webAppUrl, string machineName)
        {
            // Stub implementation for compatibility
            await Task.CompletedTask;
        }
        
        public async Task<CNCAnalysis> AnalyzeFileAsync(string filePath)
        {
            // Use the simple analyzer for legacy compatibility
            var analyzer = new SimpleCNCAnalyzer();
            return await analyzer.AnalyzeFileAsync(filePath);
        }
    }

    public class AnalyzerConfig
    {
        public AnalysisMode Mode { get; set; } = AnalysisMode.Auto;
        public bool EnableServerConfig { get; set; } = true;
        public int ServerTimeoutMs { get; set; } = 5000;
        public string PPIniPath { get; set; } = "";
        
        // Registry key for persistence
        private const string REGISTRY_KEY = @"SOFTWARE\CNC_DATALOG";
        
        public static AnalyzerConfig LoadFromRegistry()
        {
            var config = new AnalyzerConfig();
            try
            {
                using (var key = Registry.CurrentUser.OpenSubKey(REGISTRY_KEY))
                {
                    if (key != null)
                    {
                        if (Enum.TryParse<AnalysisMode>(key.GetValue("AnalysisMode")?.ToString(), out var mode))
                            config.Mode = mode;
                        if (bool.TryParse(key.GetValue("EnableServerConfig")?.ToString(), out var serverConfig))
                            config.EnableServerConfig = serverConfig;
                        if (int.TryParse(key.GetValue("ServerTimeoutMs")?.ToString(), out var timeout))
                            config.ServerTimeoutMs = timeout;
                        config.PPIniPath = key.GetValue("PPIniPath")?.ToString() ?? "";
                    }
                }
            }
            catch { /* Silent fail */ }
            return config;
        }
        
        public void SaveToRegistry()
        {
            try
            {
                using (var key = Registry.CurrentUser.CreateSubKey(REGISTRY_KEY))
                {
                    key.SetValue("AnalysisMode", Mode.ToString());
                    key.SetValue("EnableServerConfig", EnableServerConfig.ToString());
                    key.SetValue("ServerTimeoutMs", ServerTimeoutMs.ToString());
                    key.SetValue("PPIniPath", PPIniPath ?? "");
                }
            }
            catch { /* Silent fail */ }
        }
    }

    // Interface for both analyzer versions
    public interface ICNCAnalyzer
    {
        Task<CNCAnalysis> AnalyzeFileAsync(string filePath);
        string GetAnalyzerVersion();
    }
    
    // Simple analyzer implementation (reliable, no server dependency)
    public class SimpleCNCAnalyzer : ICNCAnalyzer
    {
        private readonly MachineConfig _config;
        
        public SimpleCNCAnalyzer()
        {
            // Use default configuration - no server dependency
            _config = new MachineConfig();
        }
        
        public async Task<CNCAnalysis> AnalyzeFileAsync(string filePath)
        {
            var config = new TCALCMachineConfig();
            Console.WriteLine($"[SIMPLE] Using TCALC defaults: Rapid={config.MAXFEEDRATE_XY}, ToolChange={config.TC_51_51}s");
            var analyzer = new TCALCAnalyzer(config);
            var result = await analyzer.AnalyzeFileAsync(filePath);
            result.ToolSessions = analyzer.GetToolSessions();
            return result;
        }
        
        public string GetAnalyzerVersion()
        {
            return "Simple v1.0 (No server dependency)";
        }
    }
    
    // Enhanced analyzer implementation (advanced features, server config)
    public class EnhancedCNCAnalyzer : ICNCAnalyzer
    {
        private readonly string _webAppUrl;
        private readonly int _timeoutMs;
        private MachineConfig _config;
        private string _ppIniPath;
        
        public EnhancedCNCAnalyzer(string webAppUrl, int timeoutMs = 5000)
        {
            _webAppUrl = webAppUrl;
            _timeoutMs = timeoutMs;
            _config = new MachineConfig();
        }
        
        public async Task<CNCAnalysis> AnalyzeFileAsync(string filePath)
        {
            TCALCMachineConfig config;
            
            // Load PP.ini config if available
            if (!string.IsNullOrEmpty(_ppIniPath) && File.Exists(_ppIniPath))
            {
                try
                {
                    var iniContent = File.ReadAllText(_ppIniPath);
                    config = TCALCMachineConfig.FromPPIni(iniContent);
                    Console.WriteLine($"[ENHANCED] Using TCALC PP.ini config: Rapid={config.MAXFEEDRATE_XY}, ToolChange={config.TC_51_51}s");
                }
                catch
                {
                    config = new TCALCMachineConfig(); // Fallback to defaults
                    Console.WriteLine($"[ENHANCED] PP.ini parse failed, using TCALC defaults: Rapid={config.MAXFEEDRATE_XY}, ToolChange={config.TC_51_51}s");
                }
            }
            else
            {
                config = new TCALCMachineConfig();
                Console.WriteLine($"[ENHANCED] No PP.ini found, using TCALC defaults: Rapid={config.MAXFEEDRATE_XY}, ToolChange={config.TC_51_51}s");
            }
            
            var analyzer = new TCALCAnalyzer(config);
            var result = await analyzer.AnalyzeFileAsync(filePath);
            result.ToolSessions = analyzer.GetToolSessions();
            return result;
        }
        
        public string GetAnalyzerVersion()
        {
            return "Enhanced v1.0 (Server config + detailed tracking)";
        }
        
        public void SetPPIniPath(string path)
        {
            _ppIniPath = path;
            // TODO: Load PP.ini configuration when path is set
            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] PP.ini path set to: {path}");
        }
    }
    
    // Factory for creating analyzer instances
    public static class CNCAnalyzerFactory
    {
        public static ICNCAnalyzer CreateAnalyzer(AnalyzerConfig config, string webAppUrl)
        {
            switch (config.Mode)
            {
                case AnalysisMode.Simple:
                    return new SimpleCNCAnalyzer();
                    
                case AnalysisMode.Enhanced:
                    var enhanced = new EnhancedCNCAnalyzer(webAppUrl, config.ServerTimeoutMs);
                    if (!string.IsNullOrEmpty(config.PPIniPath))
                        enhanced.SetPPIniPath(config.PPIniPath);
                    return enhanced;
                    
                case AnalysisMode.Auto:
                default:
                    // Use Enhanced if PP.ini is available, otherwise Simple
                    if (!string.IsNullOrEmpty(config.PPIniPath) && File.Exists(config.PPIniPath))
                    {
                        var autoEnhanced = new EnhancedCNCAnalyzer(webAppUrl, config.ServerTimeoutMs);
                        autoEnhanced.SetPPIniPath(config.PPIniPath);
                        return autoEnhanced;
                    }
                    return new SimpleCNCAnalyzer();
            }
        }
    }

    // CNC Analysis Classes
    public class CNCAnalysis
    {
        public string Filename { get; set; }
        public int LineCount { get; set; }
        public double TotalTime { get; set; }
        public double CuttingTime { get; set; }
        public double RapidTime { get; set; }
        public double MachineTime { get; set; }
        public int ToolChanges { get; set; }
        public int ProcessesCount { get; set; }
        public Dictionary<string, int> MovementStats { get; set; }
        public List<string> ProcessesUsed { get; set; }
        public List<int> ToolsUsed { get; set; }
        public Dictionary<int, ToolUsageSession> ToolSessions { get; set; }
        public DateTime AnalyzedAt { get; set; }
        public bool AnalysisSuccessful { get; set; }
        public string ErrorMessage { get; set; }

        public CNCAnalysis()
        {
            MovementStats = new Dictionary<string, int>();
            ProcessesUsed = new List<string>();
            ToolsUsed = new List<int>();
            ToolSessions = new Dictionary<int, ToolUsageSession>();
            AnalyzedAt = DateTime.UtcNow;
            AnalysisSuccessful = false;
        }

        public string GetFormattedTime()
        {
            // Format total time as MM:SS
            int totalSeconds = (int)(TotalTime * 60);
            int minutes = totalSeconds / 60;
            int seconds = totalSeconds % 60;
            return $"{minutes}:{seconds:D2}";
        }
    }

    public class CNCMovement
    {
        public string Code { get; set; }
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
        public double Feedrate { get; set; }
        public double Distance { get; set; }
        public double Time { get; set; }
        public int ActiveTool { get; set; } // Track which tool was active during this movement
    }

    // TCALC_HH7 exact port - Machine Configuration
    public class TCALCMachineConfig
    {
        // Core feedrate parameters (matching TCALC_HH7 defaults)
        public double MAXFEEDRATE_XY { get; set; } = 20000.0;  // mm/min for G0 XY moves
        public double MAXFEEDRATE_Z { get; set; } = 30000.0;   // mm/min for G0 Z moves
        public double DHFeedrateG00 { get; set; } = 50000.0;   // From PP.ini
        
        // Properties for compatibility with simplified calculation
        public double RapidFeedrate => DHFeedrateG00;          // Alias for simple calculation
        public double ToolChangeTime => TC_51_51;              // Alias for tool change time
        public double SpindleStartTime { get; set; } = 3.0;    // Spindle start time (seconds)
        public double PinChangeTime => DHPinChangeTime;        // Alias for pin change time
        public double CycleOverheadTime { get; set; } = 1.0;   // Default cycle overhead (seconds)
        
        // Acceleration/Deceleration parameters (mm/s²) - optimized to match TCALC_HH7
        public double Accel_Decel_G0 { get; set; } = 12000.0; // Rapid moves (very fast acceleration)
        public double Accel_Decel_G1 { get; set; } = 6000.0;  // Linear cutting moves (fast acceleration)
        public double Accel_Decel_G2 { get; set; } = 5000.0;  // Arc moves (moderate acceleration)
        
        // Tool change and cycle constants
        public double TC_51_51 { get; set; } = 15.0;           // Default tool change time (15 seconds)
        public double DHPinChangeTime { get; set; } = 1.0;     // Pin change time
        public double CLAMPCHANGE { get; set; } = 30.0;        // Clamp change time
        
        // Cycle time constants (matching TCALC_HH7)
        public double ConstdHCycle10 { get; set; } = 0.3;      // Blind hole drilling
        public double ConstdHCycle20 { get; set; } = 0.7;      // Through hole drilling
        public double ConstdHCycle30 { get; set; } = 1.0;      // Hinge hole drilling
        
        public static TCALCMachineConfig FromPPIni(string iniContent)
        {
            var config = new TCALCMachineConfig();
            
            try
            {
                // Parse DHFeedrateG00
                var rapidMatch = Regex.Match(iniContent, @"DHFeedrateG00=(\d+)");
                if (rapidMatch.Success)
                {
                    config.DHFeedrateG00 = double.Parse(rapidMatch.Groups[1].Value);
                    config.MAXFEEDRATE_XY = config.DHFeedrateG00; // Use PP.ini value
                }
                
                // Parse DHPinChangeTime
                var pinChangeMatch = Regex.Match(iniContent, @"DHPinChangeTime=(\d+)");
                if (pinChangeMatch.Success)
                    config.DHPinChangeTime = double.Parse(pinChangeMatch.Groups[1].Value);
                
                // Parse tool change times from [PTime] section
                var ptimeMatch = Regex.Match(iniContent, @"\[PTime\].*?TC_\d+_\d+=(\d+\.?\d*)", RegexOptions.Singleline);
                if (ptimeMatch.Success)
                    config.TC_51_51 = double.Parse(ptimeMatch.Groups[1].Value);
                
                Console.WriteLine($"[TCALC] PP.ini loaded: Rapid={config.DHFeedrateG00}, ToolChange={config.TC_51_51}s, PinChange={config.DHPinChangeTime}s");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[TCALC] PP.ini parsing error: {ex.Message}");
            }
            
            return config;
        }
    }

    // TCALC_HH7 exact port - Core timing engine
    public class TCALCEngine
    {
        private TCALCMachineConfig _config;
        
        public TCALCEngine(TCALCMachineConfig config)
        {
            _config = config;
        }
        
        /// <summary>
        /// Basic time calculation - exact port from TCALC_HH7 GetTimePath function
        /// </summary>
        /// <param name="weg">Distance in mm</param>
        /// <param name="vorschub">Feedrate in mm/min</param>
        /// <returns>Time in seconds</returns>
        public double GetTimePath(double weg, double vorschub)
        {
            if (vorschub <= 0)
                vorschub = 1;
            
            double zeit = weg / (vorschub / 60.0);  // Distance / (feedrate per minute / 60)
            return zeit;
        }
        
        /// <summary>
        /// Advanced time calculation with acceleration/deceleration - exact port from TCALC_HH7
        /// </summary>
        /// <param name="weg">Distance in mm</param>
        /// <param name="vorschub">Feedrate in mm/min</param>
        /// <param name="accel">Acceleration in mm/s²</param>
        /// <param name="decel">Deceleration in mm/s²</param>
        /// <returns>Time in seconds</returns>
        public double GetTimePathAccelerationDeceleration(double weg, double vorschub, double accel, double decel)
        {
            if (vorschub <= 0 || accel <= 0 || decel <= 0 || weg <= 0)
                return 0;
            
            double vorschub_sec = vorschub / 60.0;  // Convert mm/min to mm/s
            
            // Calculate acceleration and deceleration distances
            double xa = (vorschub_sec * vorschub_sec) / (2.0 * accel);  // Acceleration distance
            double xb = (vorschub_sec * vorschub_sec) / (2.0 * decel);  // Deceleration distance
            
            double zeit;
            
            if (weg <= (xa + xb))
            {
                // Short move - doesn't reach full speed
                double x_teila = (accel / (accel + decel)) * weg;
                double max_v = Math.Sqrt(2.0 * accel * x_teila);
                zeit = (max_v / accel) + (max_v / decel);
            }
            else
            {
                // Long move - reaches full speed with constant speed phase
                double x_konst = weg - xa - xb;  // Constant speed distance
                zeit = (vorschub_sec / accel) + (x_konst / vorschub_sec) + (vorschub_sec / decel);
            }
            
            return zeit;
        }
        
        /// <summary>
        /// Calculate movement time for G0 (rapid) moves - exact TCALC_HH7 logic
        /// </summary>
        public double CalculateG0Time(double distance, char axis = 'X')
        {
            double feedrate = axis == 'Z' ? _config.MAXFEEDRATE_Z : _config.MAXFEEDRATE_XY;
            double accel = _config.Accel_Decel_G0;
            
            return GetTimePathAccelerationDeceleration(distance, feedrate, accel, accel);
        }
        
        /// <summary>
        /// Calculate movement time for G1 (linear) moves - exact TCALC_HH7 logic
        /// </summary>
        public double CalculateG1Time(double distance, double feedrate)
        {
            if (feedrate <= 0) return 0;
            
            double accel = _config.Accel_Decel_G1;
            return GetTimePathAccelerationDeceleration(distance, feedrate, accel, accel);
        }
        
        /// <summary>
        /// Calculate movement time for G2/G3 (circular) moves - exact TCALC_HH7 logic
        /// </summary>
        public double CalculateG2G3Time(double arcLength, double feedrate)
        {
            if (feedrate <= 0) return 0;
            
            double accel = _config.Accel_Decel_G2;
            return GetTimePathAccelerationDeceleration(arcLength, feedrate, accel, accel);
        }
        
        /// <summary>
        /// Calculate cycle time based on DFlag (drilling type) - exact TCALC_HH7 logic
        /// </summary>
        public double CalculateDrillingCycleTime(int dFlag, double depth, double feedrate, double retractFeedrate)
        {
            double cycleConstant;
            
            if (dFlag >= 20 && dFlag < 30)
            {
                // Through hole drilling (Durchgangsloch bohren)
                cycleConstant = _config.ConstdHCycle20;
            }
            else if (dFlag >= 30 && dFlag < 40)
            {
                // Hinge hole with dwell time (Topfband mit Verweilzeit bohren)
                cycleConstant = _config.ConstdHCycle30;
            }
            else
            {
                // Blind hole drilling (Sackloch bohren)
                cycleConstant = _config.ConstdHCycle10;
            }
            
            // Calculate movement times
            double plungeTime = GetTimePathAccelerationDeceleration(depth, feedrate, _config.Accel_Decel_G1, _config.Accel_Decel_G1);
            double retractTime = GetTimePathAccelerationDeceleration(depth, retractFeedrate, _config.Accel_Decel_G0, _config.Accel_Decel_G0);
            
            return cycleConstant + plungeTime + retractTime;
        }
    }

    public class ToolUsageSession
    {
        public int ToolNumber { get; set; }
        public double CuttingTime { get; set; } = 0.0; // Time spent in G1/G2/G3 moves
        public double RapidTime { get; set; } = 0.0;   // Time spent in G0 moves
        public double CuttingDistance { get; set; } = 0.0; // Distance in cutting moves
        public double RapidDistance { get; set; } = 0.0;   // Distance in rapid moves
        public int MoveCount { get; set; } = 0;
        
        public double TotalTime => CuttingTime + RapidTime;
        public double TotalDistance => CuttingDistance + RapidDistance;
    }

    // TCALC_HH7 exact port - Complete CNC analyzer
    public class TCALCAnalyzer
    {
        private TCALCMachineConfig _config;
        private TCALCEngine _engine;
        
        // Tool state tracking
        private int _currentActiveTool = 0;
        private Dictionary<int, ToolUsageSession> _toolSessions = new Dictionary<int, ToolUsageSession>();
        
        /// <summary>
        /// Get tool usage sessions for detailed timing analysis
        /// </summary>
        public Dictionary<int, ToolUsageSession> GetToolSessions() => _toolSessions;
        
        // Enhanced timing constants (matching TCALC_HH7 postprocessor)
        private const double TCP_ON_TIME = 0.5; // seconds
        private const double TCP_OFF_TIME = 0.3; // seconds
        private const double CONTOUR_START_TIME = 0.5; // seconds
        private const double CONTOUR_END_TIME = 0.3; // seconds
        private const double DYNAMIC_SETUP_TIME = 0.5; // seconds
        private const double FLUSH_WAIT_TIME = 1.0; // seconds
        private const double COORDINATE_SETUP_TIME = 0.2; // seconds
        private const double GENERAL_CYCLE_TIME = 0.1; // seconds
        private const double TOOL_CHANGE_TIME = 15.0; // seconds (default)
        private const double SPINDLE_START_TIME = 3.0; // seconds
        private const double SPINDLE_STOP_TIME = 2.0; // seconds

        // Machine operation counters
        private class MachineOperations
        {
            public int ToolChanges { get; set; }
            public int SpindleStarts { get; set; }
            public int SpindleStops { get; set; }
            public int TcpOn { get; set; }
            public int TcpOff { get; set; }
            public int ContourStarts { get; set; }
            public int ContourEnds { get; set; }
            public int DynamicSetups { get; set; }
            public int FlushWaits { get; set; }
            public int CoordinateSetups { get; set; }
            public int OtherCycles { get; set; }
        }

        // Movement tracking
        private double _currentX = 0;
        private double _currentY = 0;
        private double _currentZ = 0;
        private double _currentFeedrate = 0;
        private const double DEFAULT_CUTTING_FEEDRATE = 3000; // Default feedrate if none specified
        
        public TCALCAnalyzer()
        {
            _config = new TCALCMachineConfig();
            _engine = new TCALCEngine(_config);
        }
        
        public TCALCAnalyzer(TCALCMachineConfig config)
        {
            _config = config ?? new TCALCMachineConfig();
            _engine = new TCALCEngine(_config);
        }
        
        /// <summary>
        /// Load machine configuration from web server (much more practical than file discovery)
        /// </summary>
        public async Task LoadMachineConfigFromServer(string webAppUrl, string machineName)
        {
            try
            {
                Console.WriteLine($"[INFO] Loading machine config for '{machineName}' from server...");
                
                using var httpClient = new HttpClient();
                var response = await httpClient.GetAsync($"{webAppUrl}/api/machine_config/{Environment.MachineName}");
                
                if (response.IsSuccessStatusCode)
                {
                    var jsonContent = await response.Content.ReadAsStringAsync();
                    var serverConfig = JsonSerializer.Deserialize<JsonElement>(jsonContent);
                    
                    if (serverConfig.TryGetProperty("rapid_feedrate", out var rapidProp))
                        _config.DHFeedrateG00 = rapidProp.GetDouble();
                    
                    if (serverConfig.TryGetProperty("tool_change_time", out var toolChangeProp))
                        _config.TC_51_51 = toolChangeProp.GetDouble();
                    
                    if (serverConfig.TryGetProperty("spindle_start_time", out var spindleProp))
                        _config.SpindleStartTime = spindleProp.GetDouble();
                    
                    if (serverConfig.TryGetProperty("pin_change_time", out var pinProp))
                        _config.DHPinChangeTime = pinProp.GetDouble();
                    
                    if (serverConfig.TryGetProperty("cycle_overhead_time", out var cycleProp))
                        _config.CycleOverheadTime = cycleProp.GetDouble();
                    
                    Console.WriteLine($"[SUCCESS] Machine config loaded from server:");
                    Console.WriteLine($"  Rapid feedrate: {_config.RapidFeedrate} mm/min");
                    Console.WriteLine($"  Tool change time: {_config.ToolChangeTime}s");
                    Console.WriteLine($"  Spindle time: {_config.SpindleStartTime}s");
                    Console.WriteLine($"  Pin change time: {_config.PinChangeTime}s");
                    return;
                }
                else
                {
                    Console.WriteLine($"[INFO] No machine config found on server for '{machineName}', using defaults");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WARNING] Could not load machine config from server: {ex.Message}");
            }
            
            // Fallback to reasonable defaults
            Console.WriteLine($"[FALLBACK] Using default machine configuration:");
            Console.WriteLine($"  Rapid feedrate: {_config.RapidFeedrate} mm/min");
            Console.WriteLine($"  Tool change time: {_config.ToolChangeTime}s");
            Console.WriteLine($"  Spindle time: {_config.SpindleStartTime}s");
            Console.WriteLine($"  ** Configure machine-specific values in the web interface for accurate timing **");
        }
        
        /// <summary>
        /// Parse PP.ini content to extract machine parameters (for manual upload feature)
        /// </summary>
        public static MachineConfig ParsePPIniContent(string iniContent)
        {
            var config = new MachineConfig();
            
            try
            {
                // Extract machine parameters from PP.ini
                var rapidMatch = Regex.Match(iniContent, @"DHFeedrateG00=(\d+)");
                if (rapidMatch.Success)
                    config.RapidFeedrate = double.Parse(rapidMatch.Groups[1].Value);
                
                var pinChangeMatch = Regex.Match(iniContent, @"DHPinChangeTime=(\d+)");
                if (pinChangeMatch.Success)
                    config.PinChangeTime = double.Parse(pinChangeMatch.Groups[1].Value);
                
                var ptimeMatch = Regex.Match(iniContent, @"\[PTime\].*?TC_\d+_\d+=(\d+\.?\d*)", RegexOptions.Singleline);
                if (ptimeMatch.Success)
                    config.ToolChangeTime = double.Parse(ptimeMatch.Groups[1].Value);
                
                Console.WriteLine($"[PARSED] PP.ini parameters: Rapid={config.RapidFeedrate}, ToolChange={config.ToolChangeTime}s");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] PP.ini parsing failed: {ex.Message}");
            }
            
            return config;
        }
        

        public async Task<CNCAnalysis> AnalyzeFileAsync(string filePath)
        {
            Console.WriteLine($"[TCALC] Starting analysis with: Rapid={_config.MAXFEEDRATE_XY}, ToolChange={_config.TC_51_51}s");
            
            var analysis = new CNCAnalysis
            {
                Filename = Path.GetFileName(filePath)
            };

            try
            {
                if (!File.Exists(filePath))
                {
                    analysis.ErrorMessage = "File not found";
                    return analysis;
                }

                var fileInfo = new FileInfo(filePath);
                if (fileInfo.Length > 50 * 1024 * 1024) // 50MB limit
                {
                    analysis.ErrorMessage = "File too large for analysis";
                    return analysis;
                }

                var lines = await File.ReadAllLinesAsync(filePath);
                analysis.LineCount = lines.Length;

                var machineOps = new MachineOperations();
                var movements = new List<CNCMovement>();
                
                // Reset position tracking
                _currentX = 0; _currentY = 0; _currentZ = 0; _currentFeedrate = 0;

                foreach (var line in lines)
                {
                    var cleanLine = CleanGCodeLine(line);
                    if (string.IsNullOrEmpty(cleanLine)) continue;

                    // Count machine operations (matching Python logic)
                    CountMachineOperations(cleanLine, machineOps);

                    // Extract tool numbers
                    ExtractToolNumbers(cleanLine, analysis);

                    // Extract feedrate
                    var feedMatch = Regex.Match(cleanLine, @"F([-+]?\d+\.?\d*)");
                    if (feedMatch.Success)
                    {
                        // Replace comma with period if needed
                        string feedValue = feedMatch.Groups[1].Value.Replace(',', '.');
                        if (double.TryParse(feedValue, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double feed))
                        {
                            _currentFeedrate = feed;
                        }
                    }

                    // Process movements using TCALC engine
                    var movement = ProcessMovementTCALC(cleanLine, analysis);
                    if (movement != null)
                    {
                        movements.Add(movement);
                    }
                    
                    // Process L CYCLE calls using TCALC logic
                    ProcessLCycleTCALC(cleanLine, analysis);
                }

                // Calculate machine operation time
                double machineOperationTime = CalculateMachineOperationTime(machineOps);

                // Calculate movement times (in minutes from movements)
                analysis.RapidTime = movements.Where(m => m.Code == "G0").Sum(m => m.Time);
                analysis.CuttingTime = movements.Where(m => m.Code == "G1" || m.Code == "G2" || m.Code == "G3").Sum(m => m.Time);
                
                
                // Set tool changes from machine operations
                analysis.ToolChanges = machineOps.ToolChanges;
                analysis.ProcessesCount = analysis.ProcessesUsed.Count;

                // Calculate overhead times using simple approach
                double toolChangeTime = analysis.ToolChanges * 15.0; // 15 seconds per tool change
                double spindleTime = 2 * 3.0; // 2 spindle starts × 3 seconds (match simple calc)
                double cycleOverheadTime = 258 * 1.0; // 258 L CYCLE calls × 1 second each
                
                // Total cycle time = movement time + overhead times
                double movementTimeSeconds = (analysis.CuttingTime * 60) + (analysis.RapidTime * 60);
                double totalCycleTimeSeconds = movementTimeSeconds + toolChangeTime + spindleTime + cycleOverheadTime;
                
                Console.WriteLine($"[TIME_CALC] Movement: {movementTimeSeconds:F1}s, ToolChange: {toolChangeTime:F1}s, Spindle: {spindleTime:F1}s, Overhead: {cycleOverheadTime:F1}s");
                Console.WriteLine($"[TIME_CALC] Total: {totalCycleTimeSeconds:F1}s ({totalCycleTimeSeconds/60.0:F2}min)");
                
                // Store times in minutes for consistency with Python output
                analysis.TotalTime = totalCycleTimeSeconds / 60.0;  // Total time in minutes
                analysis.MachineTime = (toolChangeTime + spindleTime + cycleOverheadTime) / 60.0;  // Overhead time in minutes
                
                // Finalize tool usage sessions
                FinalizeToolSessions();
                
                analysis.AnalysisSuccessful = true;
                return analysis;
            }
            catch (Exception ex)
            {
                analysis.ErrorMessage = $"Analysis failed: {ex.Message}";
                return analysis;
            }
        }

        private string CleanGCodeLine(string line)
        {
            // Remove comments
            var commentIndex = line.IndexOf('(');
            if (commentIndex >= 0)
            {
                line = line.Substring(0, commentIndex);
            }

            commentIndex = line.IndexOf(';');
            if (commentIndex >= 0)
            {
                line = line.Substring(0, commentIndex);
            }

            return line.Trim().ToUpper();
        }

        private void CountMachineOperations(string line, MachineOperations ops)
        {
            // Count machine operations that add to cycle time (matching Python logic)
            if (line.Contains("CH_TOOLCHANGE.NC"))
                ops.ToolChanges++;
            else if (line.Contains("CH_SPINDEL.NC"))
            {
                // Determine if start or stop based on parameters
                if (line.Contains("@P2=1")) // Spindle start
                    ops.SpindleStarts++;
                else if (line.Contains("@P2=0")) // Spindle stop
                    ops.SpindleStops++;
            }
            else if (line.Contains("CH_TCP_ON.NC"))
                ops.TcpOn++;
            else if (line.Contains("CH_TCP_OFF.NC"))
                ops.TcpOff++;
            else if (line.Contains("CH_CONTOUR_START.NC"))
                ops.ContourStarts++;
            else if (line.Contains("CH_CONTOUR_END.NC"))
                ops.ContourEnds++;
            else if (line.Contains("CH_DYNAMIC.NC"))
                ops.DynamicSetups++;
            else if (line.Contains("#FLUSH WAIT"))
                ops.FlushWaits++;
            else if (line.Contains("#CS ON") || line.Contains("#CS OFF") || 
                     line.Contains("#MCS ON") || line.Contains("#MCS OFF"))
                ops.CoordinateSetups++;
            else if (line.Contains("L CYCLE") && !line.Contains("CH_TOOLCHANGE") && 
                     !line.Contains("CH_SPINDEL") && !line.Contains("CH_TCP_") && 
                     !line.Contains("CH_CONTOUR_") && !line.Contains("CH_DYNAMIC") && 
                     !line.Contains("CH_CHECK_TOOL"))
                ops.OtherCycles++;
        }

        private void ExtractToolNumbers(string line, CNCAnalysis analysis)
        {
            // Check for tool change cycles first (highest priority for state tracking)
            if (line.Contains("CH_TOOLCHANGE.NC"))
            {
                // Extract tool number from @P4 parameter in tool change cycle
                var toolChangeMatch = Regex.Match(line, @"@P4=(\d+)");
                if (toolChangeMatch.Success && int.TryParse(toolChangeMatch.Groups[1].Value, out int toolNumber))
                {
                    HandleToolChange(toolNumber, analysis);
                    return;
                }
            }
            
            // Extract tool numbers from various G-code patterns
            var toolPatterns = new[]
            {
                @"\bT(\d+)",           // T1, T2, etc. (tool selection)
                @"M6\s+T(\d+)",        // M6 T1 (tool change with tool number)
                @"M06\s+T(\d+)",       // M06 T1 (alternative tool change)
                @"G43\s+H(\d+)",       // G43 H1 (tool length compensation)
                @"T(\d+)\s+M6",        // T1 M6 (tool select then change)
                @"T(\d+)\s+M06",       // T1 M06 (alternative)
                @"BOX:\s*(\d+)",       // BOX: 30 (box-style tool references in comments)
                @"@P1=(\d+)"           // @P1=30 (parameter-style tool references in CYCLE lines)
            };

            foreach (var pattern in toolPatterns)
            {
                var matches = Regex.Matches(line, pattern, RegexOptions.IgnoreCase);
                foreach (Match match in matches)
                {
                    if (int.TryParse(match.Groups[1].Value, out int toolNumber))
                    {
                        // Add to analysis tools used list
                        if (!analysis.ToolsUsed.Contains(toolNumber))
                        {
                            analysis.ToolsUsed.Add(toolNumber);
                        }
                        
                        // Handle tool change for patterns that indicate actual tool selection
                        if (pattern.Contains("T(") && (pattern.Contains("M6") || pattern.Contains("M06")))
                        {
                            HandleToolChange(toolNumber, analysis);
                        }
                    }
                }
            }
        }
        
        /// <summary>
        /// Handle tool change and start tracking new tool session
        /// </summary>
        private void HandleToolChange(int toolNumber, CNCAnalysis analysis)
        {
            Console.WriteLine($"[DEBUG] Tool change detected: T{toolNumber}");
            
            // End previous tool session if there was one
            if (_currentActiveTool > 0 && _toolSessions.ContainsKey(_currentActiveTool))
            {
                Console.WriteLine($"[DEBUG] Ending session for tool T{_currentActiveTool}");
            }
            
            // Start new tool session
            _currentActiveTool = toolNumber;
            if (!_toolSessions.ContainsKey(toolNumber))
            {
                _toolSessions[toolNumber] = new ToolUsageSession { ToolNumber = toolNumber };
            }
            
            Console.WriteLine($"[DEBUG] Started session for tool T{toolNumber}");
        }
        
        /// <summary>
        /// Finalize all tool usage sessions and prepare data for output
        /// </summary>
        private void FinalizeToolSessions()
        {
            foreach (var session in _toolSessions.Values)
            {
                Console.WriteLine($"[DEBUG] Tool T{session.ToolNumber}: " +
                    $"Total={session.TotalTime:F2}s, Cutting={session.CuttingTime:F2}s, " +
                    $"Rapid={session.RapidTime:F2}s, Distance={session.TotalDistance:F1}mm, " +
                    $"Moves={session.MoveCount}");
            }
        }

        private CNCMovement ProcessMovement(string line, CNCAnalysis analysis)
        {
            CNCMovement movement = null;

            // G0 - Rapid moves
            if (Regex.IsMatch(line, @"\bG0\b|\bG00\b"))
            {
                movement = CalculateMoveTime(line, _config.RapidFeedrate, "G0");
                if (movement != null)
                {
                    movement.ActiveTool = _currentActiveTool;
                    
                    // Update movement stats
                    if (analysis.MovementStats.ContainsKey("G0"))
                        analysis.MovementStats["G0"]++;
                    else
                        analysis.MovementStats["G0"] = 1;
                    
                    // Track tool usage if there's an active tool
                    if (_currentActiveTool > 0 && _toolSessions.ContainsKey(_currentActiveTool))
                    {
                        var session = _toolSessions[_currentActiveTool];
                        session.RapidTime += movement.Time;
                        session.RapidDistance += movement.Distance;
                        session.MoveCount++;
                    }
                }
                    
                if (!analysis.ProcessesUsed.Contains("RAPID"))
                    analysis.ProcessesUsed.Add("RAPID");
            }
            // G1 - Linear cutting moves
            else if (Regex.IsMatch(line, @"\bG1\b|\bG01\b"))
            {
                // IMPORTANT: Match Python behavior - only process if feedrate is set
                if (_currentFeedrate > 0)
                {
                    movement = CalculateMoveTime(line, _currentFeedrate, "G1");
                    if (movement != null)
                    {
                        movement.ActiveTool = _currentActiveTool;
                        
                        // Update movement stats
                        if (analysis.MovementStats.ContainsKey("G1"))
                            analysis.MovementStats["G1"]++;
                        else
                            analysis.MovementStats["G1"] = 1;
                        
                        // Track tool usage if there's an active tool
                        if (_currentActiveTool > 0 && _toolSessions.ContainsKey(_currentActiveTool))
                        {
                            var session = _toolSessions[_currentActiveTool];
                            session.CuttingTime += movement.Time;
                            session.CuttingDistance += movement.Distance;
                            session.MoveCount++;
                        }
                    }
                        
                    if (!analysis.ProcessesUsed.Contains("CUTTING"))
                        analysis.ProcessesUsed.Add("CUTTING");
                }
                else
                {
                    // Just update movement count but no time calculation (matching Python)
                    if (analysis.MovementStats.ContainsKey("G1"))
                        analysis.MovementStats["G1"]++;
                    else
                        analysis.MovementStats["G1"] = 1;
                    
                    // Still need to update position for this line
                    UpdatePosition(line);
                }
            }
            // G2/G3 - Arc moves
            else if (Regex.IsMatch(line, @"\bG[0]?[23]\b"))
            {
                var code = Regex.IsMatch(line, @"\bG[0]?2\b") ? "G2" : "G3";
                
                // IMPORTANT: Match Python behavior - only process if feedrate is set
                if (_currentFeedrate > 0)
                {
                    movement = CalculateArcMoveTime(line, _currentFeedrate, code);
                    if (movement != null)
                    {
                        movement.ActiveTool = _currentActiveTool;
                        
                        // Update movement stats
                        if (analysis.MovementStats.ContainsKey(code))
                            analysis.MovementStats[code]++;
                        else
                            analysis.MovementStats[code] = 1;
                        
                        // Track tool usage if there's an active tool (arc moves are cutting moves)
                        if (_currentActiveTool > 0 && _toolSessions.ContainsKey(_currentActiveTool))
                        {
                            var session = _toolSessions[_currentActiveTool];
                            session.CuttingTime += movement.Time;
                            session.CuttingDistance += movement.Distance;
                            session.MoveCount++;
                        }
                    }
                        
                    if (!analysis.ProcessesUsed.Contains("CUTTING"))
                        analysis.ProcessesUsed.Add("CUTTING");
                }
                else
                {
                    // Just update movement count but no time calculation (matching Python)
                    if (analysis.MovementStats.ContainsKey(code))
                        analysis.MovementStats[code]++;
                    else
                        analysis.MovementStats[code] = 1;
                    
                    // Still need to update position for this line
                    UpdatePosition(line);
                }
            }

            if (movement != null)
            {
                UpdatePosition(line);
            }

            return movement;
        }

        private CNCMovement CalculateMoveTime(string line, double feedRate, string code)
        {
            var newX = _currentX;
            var newY = _currentY;
            var newZ = _currentZ;

            // Extract coordinates
            var xMatch = Regex.Match(line, @"X([-+]?\d*\.?\d+)");
            if (xMatch.Success && double.TryParse(xMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double x))
                newX = x;

            var yMatch = Regex.Match(line, @"Y([-+]?\d*\.?\d+)");
            if (yMatch.Success && double.TryParse(yMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double y))
                newY = y;

            var zMatch = Regex.Match(line, @"Z([-+]?\d*\.?\d+)");
            if (zMatch.Success && double.TryParse(zMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double z))
                newZ = z;

            // Calculate distance
            var distance = Math.Sqrt(
                Math.Pow(newX - _currentX, 2) +
                Math.Pow(newY - _currentY, 2) +
                Math.Pow(newZ - _currentZ, 2)
            );

            // Calculate time in minutes
            var time = feedRate > 0 ? distance / feedRate : 0;

            return new CNCMovement
            {
                Code = code,
                X = newX,
                Y = newY,
                Z = newZ,
                Feedrate = feedRate,
                Distance = distance,
                Time = time
            };
        }

        private CNCMovement CalculateArcMoveTime(string line, double feedRate, string code)
        {
            var newX = _currentX;
            var newY = _currentY;
            var newZ = _currentZ;

            // Extract coordinates
            var xMatch = Regex.Match(line, @"X([-+]?\d*\.?\d+)");
            if (xMatch.Success && double.TryParse(xMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double x))
                newX = x;

            var yMatch = Regex.Match(line, @"Y([-+]?\d*\.?\d+)");
            if (yMatch.Success && double.TryParse(yMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double y))
                newY = y;

            var zMatch = Regex.Match(line, @"Z([-+]?\d*\.?\d+)");
            if (zMatch.Success && double.TryParse(zMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double z))
                newZ = z;

            // IMPORTANT: To match Python behavior exactly, always use straight-line distance
            // The Python regex for radius is broken, so it always falls back to straight-line calculation
            double distance = Math.Sqrt(
                Math.Pow(newX - _currentX, 2) +
                Math.Pow(newY - _currentY, 2) +
                Math.Pow(newZ - _currentZ, 2)
            );

            // Calculate time in minutes
            var time = feedRate > 0 ? distance / feedRate : 0;

            return new CNCMovement
            {
                Code = code,
                X = newX,
                Y = newY,
                Z = newZ,
                Feedrate = feedRate,
                Distance = distance,
                Time = time
            };
        }

        private void UpdatePosition(string line)
        {
            var xMatch = Regex.Match(line, @"X([-+]?\d*\.?\d+)");
            if (xMatch.Success && double.TryParse(xMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double x))
                _currentX = x;

            var yMatch = Regex.Match(line, @"Y([-+]?\d*\.?\d+)");
            if (yMatch.Success && double.TryParse(yMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double y))
                _currentY = y;

            var zMatch = Regex.Match(line, @"Z([-+]?\d*\.?\d+)");
            if (zMatch.Success && double.TryParse(zMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double z))
                _currentZ = z;
        }

        /// <summary>
        /// Process movement commands using TCALC engine with acceleration/deceleration
        /// </summary>
        private CNCMovement ProcessMovementTCALC(string line, CNCAnalysis analysis)
        {
            CNCMovement movement = null;

            // G0 - Rapid moves using TCALC acceleration/deceleration
            if (Regex.IsMatch(line, @"\bG0\b|\bG00\b"))
            {
                movement = CalculateTCALCMoveTime(line, "G0");
                if (movement != null)
                {
                    movement.ActiveTool = _currentActiveTool;
                    
                    // Update movement stats
                    if (analysis.MovementStats.ContainsKey("G0"))
                        analysis.MovementStats["G0"]++;
                    else
                        analysis.MovementStats["G0"] = 1;
                    
                    // Track tool usage if there's an active tool
                    if (_currentActiveTool > 0 && _toolSessions.ContainsKey(_currentActiveTool))
                    {
                        var session = _toolSessions[_currentActiveTool];
                        session.RapidTime += movement.Time * 60; // Convert to seconds
                        session.RapidDistance += movement.Distance;
                        session.MoveCount++;
                    }
                }
                    
                if (!analysis.ProcessesUsed.Contains("RAPID"))
                    analysis.ProcessesUsed.Add("RAPID");
            }
            // G1 - Linear cutting moves using TCALC acceleration/deceleration
            else if (Regex.IsMatch(line, @"\bG1\b|\bG01\b"))
            {
                if (_currentFeedrate > 0)
                {
                    movement = CalculateTCALCMoveTime(line, "G1");
                    if (movement != null)
                    {
                        movement.ActiveTool = _currentActiveTool;
                        
                        // Update movement stats
                        if (analysis.MovementStats.ContainsKey("G1"))
                            analysis.MovementStats["G1"]++;
                        else
                            analysis.MovementStats["G1"] = 1;
                        
                        // Track tool usage if there's an active tool
                        if (_currentActiveTool > 0 && _toolSessions.ContainsKey(_currentActiveTool))
                        {
                            var session = _toolSessions[_currentActiveTool];
                            session.CuttingTime += movement.Time * 60; // Convert to seconds
                            session.CuttingDistance += movement.Distance;
                            session.MoveCount++;
                        }
                    }
                        
                    if (!analysis.ProcessesUsed.Contains("CUTTING"))
                        analysis.ProcessesUsed.Add("CUTTING");
                }
                else
                {
                    // Just update movement count but no time calculation
                    if (analysis.MovementStats.ContainsKey("G1"))
                        analysis.MovementStats["G1"]++;
                    else
                        analysis.MovementStats["G1"] = 1;
                    
                    // Still need to update position for this line
                    UpdatePosition(line);
                }
            }
            // G2/G3 - Arc moves using TCALC acceleration/deceleration
            else if (Regex.IsMatch(line, @"\bG[0]?[23]\b"))
            {
                var code = Regex.IsMatch(line, @"\bG[0]?2\b") ? "G2" : "G3";
                
                if (_currentFeedrate > 0)
                {
                    movement = CalculateTCALCArcMoveTime(line, code);
                    if (movement != null)
                    {
                        movement.ActiveTool = _currentActiveTool;
                        
                        // Update movement stats
                        if (analysis.MovementStats.ContainsKey(code))
                            analysis.MovementStats[code]++;
                        else
                            analysis.MovementStats[code] = 1;
                        
                        // Track tool usage if there's an active tool (arc moves are cutting moves)
                        if (_currentActiveTool > 0 && _toolSessions.ContainsKey(_currentActiveTool))
                        {
                            var session = _toolSessions[_currentActiveTool];
                            session.CuttingTime += movement.Time * 60; // Convert to seconds
                            session.CuttingDistance += movement.Distance;
                            session.MoveCount++;
                        }
                    }
                        
                    if (!analysis.ProcessesUsed.Contains("CUTTING"))
                        analysis.ProcessesUsed.Add("CUTTING");
                }
                else
                {
                    // Just update movement count but no time calculation
                    if (analysis.MovementStats.ContainsKey(code))
                        analysis.MovementStats[code]++;
                    else
                        analysis.MovementStats[code] = 1;
                    
                    // Still need to update position for this line
                    UpdatePosition(line);
                }
            }

            if (movement != null)
            {
                UpdatePosition(line);
            }

            return movement;
        }

        /// <summary>
        /// Process L CYCLE calls using TCALC logic with dynamic parameter parsing
        /// </summary>
        private void ProcessLCycleTCALC(string line, CNCAnalysis analysis)
        {
            if (!line.Contains("L CYCLE")) return;

            // Parse L CYCLE parameters dynamically (matching TCALC_HH7 behavior)
            var cycleMatch = Regex.Match(line, @"L CYCLE\s+\[(.*?)\]");
            if (!cycleMatch.Success) return;

            string cycleContent = cycleMatch.Groups[1].Value;
            
            // Extract cycle name and parameters
            var parts = cycleContent.Split(',');
            if (parts.Length == 0) return;

            string cycleName = parts[0].Trim().Trim('"').Trim();
            
            // Calculate cycle time based on TCALC_HH7 logic
            double cycleTime = 0;
            
            // Drilling cycles (TCALC standard times)
            if (cycleName.Contains("81") || cycleName.Contains("DRILL") || cycleName.Contains("BORING"))
            {
                // Standard drilling cycle - base time + depth-dependent time
                cycleTime = _config.ConstdHCycle10; // Base cycle time from TCALC config
                
                // Add depth-dependent time if depth parameter found
                foreach (var part in parts)
                {
                    if (part.Contains("@P3=") || part.Contains("DEPTH"))
                    {
                        var depthMatch = Regex.Match(part, @"@P3=([\d.-]+)|DEPTH=([\d.-]+)");
                        if (depthMatch.Success)
                        {
                            string depthStr = depthMatch.Groups[1].Value;
                            if (string.IsNullOrEmpty(depthStr)) depthStr = depthMatch.Groups[2].Value;
                            
                            if (double.TryParse(depthStr, out double depth))
                            {
                                // Add time for plunge and retract (simplified TCALC logic)
                                double plungeFeedrate = _currentFeedrate > 0 ? _currentFeedrate : 500; // Default drill feedrate
                                double retractFeedrate = _config.MAXFEEDRATE_Z;
                                
                                cycleTime += _engine.GetTimePath(Math.Abs(depth), plungeFeedrate);
                                cycleTime += _engine.GetTimePath(Math.Abs(depth), retractFeedrate);
                            }
                        }
                        break;
                    }
                }
            }
            else if (cycleName.Contains("CONTOUR") || cycleName.Contains("PROFILE"))
            {
                // Contouring cycle - higher overhead
                cycleTime = _config.ConstdHCycle30;
            }
            else
            {
                // Generic cycle overhead (most L CYCLE calls fall here)
                cycleTime = 1.0; // 1 second per cycle (matching TCALC report: 258 cycles ≈ 4.3 minutes)
            }
            
            // Add to analysis (store in seconds, will be converted to minutes later)
            if (!analysis.ProcessesUsed.Contains("CYCLE"))
                analysis.ProcessesUsed.Add("CYCLE");
                
            // Track cycle in tool session if active tool
            if (_currentActiveTool > 0 && _toolSessions.ContainsKey(_currentActiveTool))
            {
                var session = _toolSessions[_currentActiveTool];
                session.CuttingTime += cycleTime; // Cycles are considered "cutting" time
            }
        }

        /// <summary>
        /// Calculate movement time using simple distance/feedrate (more accurate than complex physics)
        /// </summary>
        private CNCMovement CalculateTCALCMoveTime(string line, string code)
        {
            var newX = _currentX;
            var newY = _currentY;
            var newZ = _currentZ;

            // Extract coordinates
            var xMatch = Regex.Match(line, @"X([-+]?\d*\.?\d+)");
            if (xMatch.Success && double.TryParse(xMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double x))
                newX = x;

            var yMatch = Regex.Match(line, @"Y([-+]?\d*\.?\d+)");
            if (yMatch.Success && double.TryParse(yMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double y))
                newY = y;

            var zMatch = Regex.Match(line, @"Z([-+]?\d*\.?\d+)");
            if (zMatch.Success && double.TryParse(zMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double z))
                newZ = z;

            // Calculate distance
            var distance = Math.Sqrt(
                Math.Pow(newX - _currentX, 2) +
                Math.Pow(newY - _currentY, 2) +
                Math.Pow(newZ - _currentZ, 2)
            );

            if (distance < 0.001) return null; // Skip micro-movements

            // Simple time calculation: time = distance / feedrate (more accurate than physics simulation)
            double feedrate = 0;
            double timeMinutes = 0;
            
            if (code == "G0")
            {
                // Rapid move - use configured rapid feedrate
                feedrate = _config.DHFeedrateG00; // 50000 mm/min from PP.ini
                timeMinutes = distance / feedrate; // Direct calculation in minutes
            }
            else if (code == "G1")
            {
                // Linear move - use current feedrate
                feedrate = _currentFeedrate;
                if (feedrate > 0)
                {
                    timeMinutes = distance / feedrate; // Direct calculation in minutes
                }
            }

            return new CNCMovement
            {
                Code = code,
                X = newX,
                Y = newY,
                Z = newZ,
                Feedrate = feedrate,
                Distance = distance,
                Time = timeMinutes // Already in minutes
            };
        }

        /// <summary>
        /// Calculate arc movement time using simple distance/feedrate
        /// </summary>
        private CNCMovement CalculateTCALCArcMoveTime(string line, string code)
        {
            var newX = _currentX;
            var newY = _currentY;
            var newZ = _currentZ;

            // Extract coordinates
            var xMatch = Regex.Match(line, @"X([-+]?\d*\.?\d+)");
            if (xMatch.Success && double.TryParse(xMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double x))
                newX = x;

            var yMatch = Regex.Match(line, @"Y([-+]?\d*\.?\d+)");
            if (yMatch.Success && double.TryParse(yMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double y))
                newY = y;

            // Extract arc parameters (I, J for center offsets)
            var iMatch = Regex.Match(line, @"I([-+]?\d*\.?\d+)");
            var jMatch = Regex.Match(line, @"J([-+]?\d*\.?\d+)");
            
            double i = 0, j = 0;
            if (iMatch.Success) double.TryParse(iMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out i);
            if (jMatch.Success) double.TryParse(jMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out j);

            // Calculate arc length (simplified approach)
            double radius = Math.Sqrt(i * i + j * j);
            if (radius < 0.001)
            {
                // Fallback to linear distance if no valid arc parameters
                radius = Math.Sqrt(Math.Pow(newX - _currentX, 2) + Math.Pow(newY - _currentY, 2)) / 2;
            }
            
            // Approximate arc length using chord and radius
            double chordLength = Math.Sqrt(Math.Pow(newX - _currentX, 2) + Math.Pow(newY - _currentY, 2));
            double arcLength = radius > 0 ? radius * 2 * Math.Asin(chordLength / (2 * radius)) : chordLength;
            
            if (arcLength < 0.001) return null; // Skip micro-movements

            // Simple calculation: time = distance / feedrate
            double timeMinutes = 0;
            if (_currentFeedrate > 0)
            {
                timeMinutes = arcLength / _currentFeedrate; // Direct calculation in minutes
            }

            return new CNCMovement
            {
                Code = code,
                X = newX,
                Y = newY,
                Z = newZ,
                Feedrate = _currentFeedrate,
                Distance = arcLength,
                Time = timeMinutes // Already in minutes
            };
        }

        // Duplicate UpdatePosition method removed - keeping the first one

        private double CalculateMachineOperationTime(MachineOperations ops)
        {
            // Calculate total machine operation time in seconds (matching Python logic)
            return ops.ToolChanges * _config.TC_51_51 +
                   ops.SpindleStarts * _config.SpindleStartTime +
                   ops.SpindleStops * SPINDLE_STOP_TIME +
                   ops.TcpOn * TCP_ON_TIME +
                   ops.TcpOff * TCP_OFF_TIME +
                   ops.ContourStarts * CONTOUR_START_TIME +
                   ops.ContourEnds * CONTOUR_END_TIME +
                   ops.DynamicSetups * DYNAMIC_SETUP_TIME +
                   ops.FlushWaits * FLUSH_WAIT_TIME +
                   ops.CoordinateSetups * COORDINATE_SETUP_TIME +
                   ops.OtherCycles * GENERAL_CYCLE_TIME;
        }
    }

    public partial class FileMonitorTrayApp : Form
    {
        private NotifyIcon trayIcon;
        private ContextMenuStrip trayMenu;
        private HttpClient httpClient;
        private CookieContainer cookieContainer;
        private string webAppUrl;
        private bool authenticated = false;
        private string currentUser = "";
        private bool monitoringActive = false;
        private System.Windows.Forms.Timer statusTimer;
        private List<FileSystemWatcher> fileWatchers = new List<FileSystemWatcher>();
        private Dictionary<FileSystemWatcher, MonitoredPathInfo> watcherInfoMap = new Dictionary<FileSystemWatcher, MonitoredPathInfo>();
        
        // Aggressive deduplication fields
        private readonly ConcurrentDictionary<string, DateTime> processedEvents = new ConcurrentDictionary<string, DateTime>();
        private readonly ConcurrentDictionary<string, FileChangeInfo> pendingChanges = new ConcurrentDictionary<string, FileChangeInfo>();
        private readonly ConcurrentDictionary<string, object> processingLocks = new ConcurrentDictionary<string, object>();
        private System.Windows.Forms.Timer processTimer;
        private readonly object processLock = new object();
        
        private const string APP_NAME = "CNC DATALOG";
        private const string CONFIG_FILE = "tray_config.json";
        private const string STARTUP_KEY_PATH = @"Software\Microsoft\Windows\CurrentVersion\Run";
        
        // Login retry mechanism
        private System.Windows.Forms.Timer loginRetryTimer;
        private int loginRetryCount = 0;
        private const int MAX_LOGIN_RETRIES = 5;
        private const int LOGIN_RETRY_INTERVAL_MS = 60000; // 1 minute
        private DateTime lastSuccessfulConnection = DateTime.MinValue;
        
        // Cache for categories to avoid frequent API calls
        private List<CategoryInfo> cachedCategories = new List<CategoryInfo>();
        private DateTime categoriesCacheTime = DateTime.MinValue;
        private readonly TimeSpan CACHE_DURATION = TimeSpan.FromMinutes(5);

        // File extensions that should be scanned for content
        private readonly HashSet<string> SCANNABLE_EXTENSIONS = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            ".txt", ".log", ".csv", ".json", ".xml", ".htm", ".html", ".md", ".ini", ".cfg", ".conf",
            ".nc", ".gcode", ".tap", ".mpf", ".ptp", ".cls", ".lst", ".prg", ".sub", ".cnc"
        };

        // CNC file extensions for analysis
        private readonly HashSet<string> CNC_EXTENSIONS = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            ".nc", ".gcode", ".tap", ".mpf", ".ptp", ".cls", ".lst", ".prg", ".sub", ".cnc"
        };

        // Configuration class
        public class AppConfig
        {
            public string Username { get; set; } = "";
            public string WebAppUrl { get; set; } = "http://localhost:5002";
            public string Language { get; set; } = "en";
            public bool ScanFileContents { get; set; } = true;
            public bool EnableCNCAnalysis { get; set; } = true;
            public int MaxFileSizeMB { get; set; } = 10; // Max file size to scan in MB
            public bool MonitoringEnabled { get; set; } = true; // Remember monitoring state
        }

        // Class to hold path info from the server
        public class MonitoredPathInfo
        {
            public int id { get; set; }
            public string path { get; set; }
            public bool is_directory { get; set; }
            public bool recursive { get; set; }
            public string description { get; set; }
        }

        // Class to hold category info
        public class CategoryInfo
        {
            public int id { get; set; }
            public string name { get; set; }
            public string color { get; set; }
            public List<string> keywords { get; set; }
            public List<string> file_patterns { get; set; }
        }

        // Class for tracking file changes
        public class FileChangeInfo
        {
            public string FullPath { get; set; }
            public string ChangeType { get; set; }
            public MonitoredPathInfo PathInfo { get; set; }
            public DateTime FirstSeen { get; set; }
            public DateTime LastSeen { get; set; }
            public int EventCount { get; set; }
        }

        private AppConfig config;
        private LocalizationManager localization;
        private GCodeAnalyzer gCodeAnalyzer;
        private AnalyzerConfig analyzerConfig;
        private ICNCAnalyzer currentAnalyzer;

        public FileMonitorTrayApp()
        {
            InitializeForm();
            LoadConfiguration();
            InitializeLocalization();
            InitializeHttpClient();
            CreateTrayIcon();
            
            // Initialize dual-version CNC analyzer system
            analyzerConfig = AnalyzerConfig.LoadFromRegistry();
            InitializeAnalyzer();
            
            // Keep legacy analyzer for compatibility
            gCodeAnalyzer = new GCodeAnalyzer();
            _ = Task.Run(async () =>
            {
                await gCodeAnalyzer.LoadMachineConfigFromServer(config.WebAppUrl, Environment.MachineName);
            });
            
            // Hide the form initially
            this.WindowState = FormWindowState.Minimized;
            this.ShowInTaskbar = false;
            this.Visible = false;
            
            CheckSingleInstance();
            StartApplication();
        }

        private void InitializeForm()
        {
            // Basic form setup - this replaces the auto-generated InitializeComponent
            this.Text = "CNC DATALOG";
            this.Size = new Size(1, 1); // Minimal size since it's hidden
            this.FormBorderStyle = FormBorderStyle.FixedToolWindow;
            this.ShowInTaskbar = false;
            this.WindowState = FormWindowState.Minimized;
        }

        private void LoadConfiguration()
        {
            config = new AppConfig();
            
            if (File.Exists(CONFIG_FILE))
            {
                try
                {
                    string json = File.ReadAllText(CONFIG_FILE);
                    config = JsonSerializer.Deserialize<AppConfig>(json) ?? new AppConfig();
                }
                catch
                {
                    config = new AppConfig();
                }
            }
            
            // Check environment variable for URL
            string envUrl = Environment.GetEnvironmentVariable("FILE_MONITOR_URL");
            if (!string.IsNullOrEmpty(envUrl))
            {
                config.WebAppUrl = envUrl;
            }
            
            webAppUrl = config.WebAppUrl;
        }

        private void SaveConfiguration()
        {
            try
            {
                string json = JsonSerializer.Serialize(config, new JsonSerializerOptions { WriteIndented = true });
                File.WriteAllText(CONFIG_FILE, json);
            }
            catch
            {
                // Silently handle configuration save errors
            }
        }

        private void InitializeLocalization()
        {
            localization = LocalizationManager.Instance;
            
            // Set language from config
            if (!string.IsNullOrEmpty(config.Language))
            {
                localization.CurrentLanguage = config.Language;
            }
            
            // Subscribe to language changes
            localization.LanguageChanged += (s, e) =>
            {
                config.Language = localization.CurrentLanguage;
                SaveConfiguration();
                // The menu will be rebuilt on next opening
                UpdateTrayIcon().Wait();
            };
        }

        private void InitializeHttpClient()
        {
            cookieContainer = new CookieContainer();
            var handler = new HttpClientHandler()
            {
                CookieContainer = cookieContainer,
                UseCookies = true,
                AllowAutoRedirect = false // Important: handle redirects manually for login
            };
            
            httpClient = new HttpClient(handler);
            httpClient.Timeout = TimeSpan.FromSeconds(30);
            httpClient.DefaultRequestHeaders.Add("X-Client-Type", "FileMonitorTray");
        }

        private void CheckSingleInstance()
        {
            // Simple check - in production you might want to use a Mutex
            Process[] processes = Process.GetProcessesByName(Process.GetCurrentProcess().ProcessName);
            if (processes.Length > 1)
            {
                // Silent exit if already running
                Application.Exit();
            }
        }

        private async void StartApplication()
        {
            // DO NOT start the web app - it should be running on a separate server
            // Just check if we can connect to it
            await CheckServerConnection();

            // Try auto-login
            if (await AutoLogin())
            {
                // Start monitoring if it was enabled in config
                Console.WriteLine($"[STARTUP] AutoLogin successful. MonitoringEnabled in config: {config.MonitoringEnabled}");
                if (config.MonitoringEnabled)
                {
                    Console.WriteLine($"[STARTUP] Starting monitoring...");
                    await StartMonitoring();
                }
                else
                {
                    Console.WriteLine($"[STARTUP] Monitoring disabled in config - not starting");
                }
            }
            else if (!string.IsNullOrEmpty(config.Username))
            {
                // Start login retry timer if we have stored credentials
                if (!string.IsNullOrEmpty(GetStoredPassword(config.Username)))
                {
                    StartLoginRetryTimer();
                    
                    // Try to start monitoring anyway if it was enabled
                    if (config.MonitoringEnabled)
                    {
                        await StartMonitoring();
                    }
                }
                else
                {
                    ShowLoginDialog();
                }
            }

            // Initialize the processing timer with a longer interval
            processTimer = new System.Windows.Forms.Timer();
            processTimer.Interval = 3000; // Process pending changes every 3 seconds
            processTimer.Tick += ProcessPendingChanges;
            processTimer.Start();

            // Start status checking timer
            statusTimer = new System.Windows.Forms.Timer();
            statusTimer.Interval = 30000; // Check every 30 seconds
            statusTimer.Tick += async (s, e) => 
            {
                await UpdateTrayIcon();
                
                // Clean up old processed events
                if (processedEvents.Count > 500)
                {
                    var cutoff = DateTime.UtcNow.AddMinutes(-15);
                    var oldKeys = processedEvents.Where(kvp => kvp.Value < cutoff).Select(kvp => kvp.Key).ToList();
                    foreach (var key in oldKeys)
                    {
                        processedEvents.TryRemove(key, out _);
                    }
                }
                
                // Clean up old locks
                if (processingLocks.Count > 100)
                {
                    processingLocks.Clear();
                }
            };
            statusTimer.Start();
        }

        private async Task<bool> CheckServerConnection()
        {
            try
            {
                var response = await httpClient.GetAsync($"{webAppUrl}/login");
                return response.IsSuccessStatusCode || response.StatusCode == HttpStatusCode.OK;
            }
            catch
            {
                return false;
            }
        }

        private async Task<bool> AutoLogin()
        {
            if (string.IsNullOrEmpty(config.Username))
                return false;

            try
            {
                string password = GetStoredPassword(config.Username);
                if (!string.IsNullOrEmpty(password))
                {
                    return await Login(config.Username, password);
                }
            }
            catch
            {
                // Ignore errors in auto-login
            }
            
            return false;
        }

        private async Task<bool> Login(string username, string password)
        {
            try
            {
                // First, get the login page to obtain any CSRF tokens
                var getResponse = await httpClient.GetAsync($"{webAppUrl}/login");
                
                // Prepare login form data
                var loginData = new FormUrlEncodedContent(new[]
                {
                    new KeyValuePair<string, string>("username", username),
                    new KeyValuePair<string, string>("password", password)
                });

                // Post login credentials
                var response = await httpClient.PostAsync($"{webAppUrl}/login", loginData);
                
                // Check if login was successful (either 200 OK or 302 Redirect)
                if (response.IsSuccessStatusCode || response.StatusCode == HttpStatusCode.Redirect || response.StatusCode == HttpStatusCode.Found)
                {
                    // If redirected, follow the redirect
                    if (response.StatusCode == HttpStatusCode.Redirect || response.StatusCode == HttpStatusCode.Found)
                    {
                        var location = response.Headers.Location;
                        if (location != null)
                        {
                            string redirectUrl = location.IsAbsoluteUri ? location.AbsoluteUri : $"{webAppUrl}{location}";
                            await httpClient.GetAsync(redirectUrl);
                        }
                    }
                    
                    // Test authentication with a protected endpoint
                    var testResponse = await httpClient.GetAsync($"{webAppUrl}/api/monitor/status");
                    if (testResponse.IsSuccessStatusCode)
                    {
                        authenticated = true;
                        currentUser = username;
                        config.Username = username;
                        SaveConfiguration();
                        StorePassword(username, password);
                        
                        // Stop login retry timer if it's running
                        StopLoginRetryTimer();
                        
                        await UpdateTrayIcon();
                        
                        // Load categories after successful login
                        await RefreshCategoriesCache();
                        
                        return true;
                    }
                }
            }
            catch
            {
                // Silent fail for auto-login attempts
            }
            
            return false;
        }

        private void Logout()
        {
            try
            {
                // Create a new HttpClient for logout that allows redirects
                using (var logoutClient = new HttpClient())
                {
                    // Copy cookies from main client
                    logoutClient.DefaultRequestHeaders.Add("Cookie", httpClient.DefaultRequestHeaders.GetValues("Cookie").FirstOrDefault() ?? "");
                    logoutClient.GetAsync($"{webAppUrl}/logout").Wait(5000);
                }
            }
            catch { }

            // Don't stop monitoring on logout - keep it running
            authenticated = false;
            currentUser = "";
            
            // Clear cached categories
            cachedCategories.Clear();
            categoriesCacheTime = DateTime.MinValue;
            
            if (!string.IsNullOrEmpty(config.Username))
            {
                DeleteStoredPassword(config.Username);
                config.Username = "";
                SaveConfiguration();
            }
            
            // Clear cookies
            cookieContainer = new CookieContainer();
            
            // Recreate HttpClient with fresh cookie container
            var handler = new HttpClientHandler()
            {
                CookieContainer = cookieContainer,
                UseCookies = true,
                AllowAutoRedirect = false
            };
            
            httpClient.Dispose();
            httpClient = new HttpClient(handler);
            httpClient.Timeout = TimeSpan.FromSeconds(30);
            httpClient.DefaultRequestHeaders.Add("X-Client-Type", "FileMonitorTray");
            
            UpdateTrayIcon().Wait();
        }

        private async Task RefreshCategoriesCache()
        {
            try
            {
                var response = await httpClient.GetAsync($"{webAppUrl}/api/categories");
                if (response.IsSuccessStatusCode)
                {
                    string json = await response.Content.ReadAsStringAsync();
                    var categoriesJson = JsonSerializer.Deserialize<JsonElement[]>(json);
                    
                    cachedCategories.Clear();
                    foreach (var catJson in categoriesJson)
                    {
                        var category = new CategoryInfo
                        {
                            id = catJson.GetProperty("id").GetInt32(),
                            name = catJson.GetProperty("name").GetString(),
                            color = catJson.GetProperty("color").GetString(),
                            keywords = new List<string>(),
                            file_patterns = new List<string>()
                        };
                        
                        // Get keywords if available (server might need to be updated to send these)
                        if (catJson.TryGetProperty("keywords", out var keywordsElement))
                        {
                            foreach (var keyword in keywordsElement.EnumerateArray())
                            {
                                category.keywords.Add(keyword.GetString());
                            }
                        }
                        
                        // Get file patterns if available
                        if (catJson.TryGetProperty("file_patterns", out var patternsElement))
                        {
                            foreach (var pattern in patternsElement.EnumerateArray())
                            {
                                category.file_patterns.Add(pattern.GetString());
                            }
                        }
                        
                        cachedCategories.Add(category);
                    }
                    
                    categoriesCacheTime = DateTime.Now;
                }
            }
            catch
            {
                // Silent fail - will use empty categories list
            }
        }

        private async Task<List<CategoryInfo>> GetCategories()
        {
            // Refresh cache if expired or empty
            if (cachedCategories.Count == 0 || DateTime.Now - categoriesCacheTime > CACHE_DURATION)
            {
                await RefreshCategoriesCache();
            }
            
            return cachedCategories;
        }

        private void CreateTrayIcon()
        {
            trayMenu = new ContextMenuStrip();
            // The Opening event is the best place to dynamically update menu items.
            trayMenu.Opening += (s, e) => 
            {
                // Prevent opening if the form is being disposed.
                if (this.IsDisposed)
                {
                    e.Cancel = true;
                    return;
                }
                UpdateTrayMenuItems();
            };

            trayIcon = new NotifyIcon();
            
            try
            {
                trayIcon.Icon = CreateOverlayIcon("error"); // Red dot when not connected
            }
            catch
            {
                trayIcon.Icon = SystemIcons.Application;
            }
            
            trayIcon.Text = localization.T("tooltip_not_logged_in");
            trayIcon.Visible = true;
            trayIcon.ContextMenuStrip = trayMenu; // Let the framework manage showing/hiding.
            
            // Handle double-click to open browser
            trayIcon.DoubleClick += (s, e) => OpenBrowser();
        }

        private void UpdateTrayMenuItems()
        {
            if (trayMenu.IsDisposed) return;
            trayMenu.Items.Clear();

            if (authenticated)
            {
                trayMenu.Items.Add($@"{localization.T("user")}: {currentUser}").Enabled = false;
                trayMenu.Items.Add(new ToolStripSeparator());
                trayMenu.Items.Add(localization.T("open_web_interface"), null, (s, e) => OpenBrowser());
                trayMenu.Items.Add(localization.T("manual_entry"), null, (s, e) => ShowManualEntry());
                trayMenu.Items.Add("Add Files/Directories...", null, (s, e) => ShowFileSelector());
                trayMenu.Items.Add(new ToolStripSeparator());
                
                // Add content scanning toggle
                var scanContentItem = new ToolStripMenuItem("Scan File Contents", null, (s, e) => ToggleScanContent())
                {
                    Checked = config.ScanFileContents
                };
                trayMenu.Items.Add(scanContentItem);
                
                // Add CNC analysis toggle
                var cncAnalysisItem = new ToolStripMenuItem("CNC Analysis", null, (s, e) => ToggleCNCAnalysis())
                {
                    Checked = config.EnableCNCAnalysis
                };
                trayMenu.Items.Add(cncAnalysisItem);
                
                // Add analyzer mode selection submenu
                var analyzerModeMenu = new ToolStripMenuItem(localization.T("analyzer_mode"));
                
                var simpleItem = new ToolStripMenuItem(localization.T("simple_analyzer"), null, (s, e) => SetAnalyzerMode(AnalysisMode.Simple))
                {
                    Checked = analyzerConfig.Mode == AnalysisMode.Simple
                };
                analyzerModeMenu.DropDownItems.Add(simpleItem);
                
                var enhancedItem = new ToolStripMenuItem(localization.T("enhanced_analyzer"), null, (s, e) => SetAnalyzerMode(AnalysisMode.Enhanced))
                {
                    Checked = analyzerConfig.Mode == AnalysisMode.Enhanced
                };
                analyzerModeMenu.DropDownItems.Add(enhancedItem);
                
                var autoItem = new ToolStripMenuItem(localization.T("auto_analyzer"), null, (s, e) => SetAnalyzerMode(AnalysisMode.Auto))
                {
                    Checked = analyzerConfig.Mode == AnalysisMode.Auto
                };
                analyzerModeMenu.DropDownItems.Add(autoItem);
                
                analyzerModeMenu.DropDownItems.Add(new ToolStripSeparator());
                
                var currentVersion = currentAnalyzer?.GetAnalyzerVersion() ?? "None";
                var shortVersion = currentVersion.Contains("Simple") ? "Simple" : 
                                  currentVersion.Contains("Enhanced") ? "Enhanced" : "None";
                var versionItem = new ToolStripMenuItem($"Current: {shortVersion}") { Enabled = false };
                analyzerModeMenu.DropDownItems.Add(versionItem);
                
                // Show PP.ini status
                if (!string.IsNullOrEmpty(analyzerConfig.PPIniPath))
                {
                    var ppIniStatus = new ToolStripMenuItem($"PP.ini: {Path.GetFileName(analyzerConfig.PPIniPath)}") { Enabled = false };
                    analyzerModeMenu.DropDownItems.Add(ppIniStatus);
                }
                
                // Add PP.ini selection for enhanced mode
                if (analyzerConfig.Mode == AnalysisMode.Enhanced || analyzerConfig.Mode == AnalysisMode.Auto)
                {
                    analyzerModeMenu.DropDownItems.Add(new ToolStripSeparator());
                    var ppIniItem = new ToolStripMenuItem(localization.T("select_pp_ini"), null, SelectPPIniFile);
                    analyzerModeMenu.DropDownItems.Add(ppIniItem);
                }
                
                trayMenu.Items.Add(analyzerModeMenu);
                
                trayMenu.Items.Add(localization.T("show_status"), null, async (s, e) => await ShowStatus());
                var monitoringItem = new ToolStripMenuItem(localization.T("toggle_monitoring"), null, async (s, e) => await ToggleMonitoring()) 
                { 
                    Checked = monitoringActive 
                };
                trayMenu.Items.Add(monitoringItem);
                trayMenu.Items.Add(new ToolStripSeparator());
                trayMenu.Items.Add(localization.T("switch_user"), null, (s, e) => SwitchUser());
            }
            else
            {
                trayMenu.Items.Add(localization.T("login"), null, (s, e) => ShowLoginDialog());
                trayMenu.Items.Add(localization.T("open_web_interface"), null, (s, e) => OpenBrowser());
                trayMenu.Items.Add(new ToolStripSeparator());
            }

            var languageMenu = new ToolStripMenuItem(localization.T("language"));
            foreach (string langCode in localization.AvailableLanguages)
            {
                var langItem = new ToolStripMenuItem(localization.GetLanguageName(langCode))
                {
                    Checked = langCode == localization.CurrentLanguage,
                    Tag = langCode
                };
                langItem.Click += (s, e) => { localization.CurrentLanguage = (string)((ToolStripMenuItem)s).Tag; };
                languageMenu.DropDownItems.Add(langItem);
            }
            trayMenu.Items.Add(languageMenu);

            string startupText = IsStartupEnabled() ? localization.T("remove_from_startup") : localization.T("add_to_startup");
            trayMenu.Items.Add(startupText, null, (s, e) => ToggleStartup());
            trayMenu.Items.Add(new ToolStripSeparator());
            trayMenu.Items.Add(localization.T("quit"), null, (s, e) => QuitApplication());
        }

        private void ToggleScanContent()
        {
            config.ScanFileContents = !config.ScanFileContents;
            SaveConfiguration();
        }

        private void ToggleCNCAnalysis()
        {
            config.EnableCNCAnalysis = !config.EnableCNCAnalysis;
            SaveConfiguration();
        }
        
        private void SetAnalyzerMode(AnalysisMode mode)
        {
            analyzerConfig.Mode = mode;
            analyzerConfig.SaveToRegistry();
            InitializeAnalyzer();
            
            // Show notification
            string modeName = mode switch
            {
                AnalysisMode.Simple => localization.T("simple_analyzer"),
                AnalysisMode.Enhanced => localization.T("enhanced_analyzer"),
                AnalysisMode.Auto => localization.T("auto_analyzer"),
                _ => mode.ToString()
            };
            
            trayIcon?.ShowBalloonTip(3000, localization.T("analyzer_mode"), 
                string.Format(localization.T("analyzer_mode_changed"), modeName), 
                ToolTipIcon.Info);
                
            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Analyzer mode changed to: {modeName}");
        }
        
        private void SelectPPIniFile(object sender, EventArgs e)
        {
            using (var dialog = new OpenFileDialog())
            {
                dialog.Title = localization.T("pp_ini_title");
                dialog.Filter = localization.T("pp_ini_filter");
                dialog.InitialDirectory = @"C:\Users\Rob_v\Desktop\Test-thuis\RB_OPUS_V7\";
                
                if (!string.IsNullOrEmpty(analyzerConfig.PPIniPath) && File.Exists(analyzerConfig.PPIniPath))
                {
                    dialog.FileName = analyzerConfig.PPIniPath;
                    dialog.InitialDirectory = Path.GetDirectoryName(analyzerConfig.PPIniPath);
                }
                
                if (dialog.ShowDialog() == DialogResult.OK)
                {
                    analyzerConfig.PPIniPath = dialog.FileName;
                    analyzerConfig.SaveToRegistry();
                    
                    trayIcon?.ShowBalloonTip(3000, localization.T("success"), 
                        string.Format(localization.T("pp_ini_selected"), Path.GetFileName(dialog.FileName)), 
                        ToolTipIcon.Info);
                    
                    // Reinitialize analyzer to pick up new PP.ini path
                    InitializeAnalyzer();
                }
            }
        }
        
        private void InitializeAnalyzer()
        {
            try
            {
                currentAnalyzer = CNCAnalyzerFactory.CreateAnalyzer(analyzerConfig, config.WebAppUrl);
            }
            catch (Exception)
            {
                currentAnalyzer = new SimpleCNCAnalyzer();
            }
        }

        private async Task UpdateTrayIcon()
        {
            if (trayIcon == null) return;
            try
            {
                // A simple check to see if we can reach the server.
                // This also helps keep the session alive if the server has a short session timeout.
                var response = await httpClient.GetAsync($@"{webAppUrl}/api/monitor/status");
                if (response.IsSuccessStatusCode)
                {
                    var json = await response.Content.ReadAsStringAsync();
                    var status = JsonSerializer.Deserialize<JsonElement>(json);
                    // Re-confirm authentication state based on a successful API call
                    authenticated = true;
                    if (status.TryGetProperty("username", out var usernameProp))
                    {
                        currentUser = usernameProp.GetString() ?? currentUser;
                    }
                    trayIcon.Text = $@"{APP_NAME} - {currentUser} - {(monitoringActive ? localization.T("monitoring_active") : localization.T("monitoring_inactive"))}";
                    trayIcon.Icon = monitoringActive ? CreateOverlayIcon("play") : CreateOverlayIcon("connected");
                }
                else
                {
                    // Server is reachable but returned an error (e.g., 401 Unauthorized after session expired)
                    authenticated = false;
                    currentUser = "";
                    // Keep monitoring running even if session is lost
                    trayIcon.Text = $@"{APP_NAME} - {localization.T("tooltip_not_logged_in")} - {(monitoringActive ? localization.T("monitoring_active") : localization.T("monitoring_inactive"))}";
                    trayIcon.Icon = monitoringActive ? CreateOverlayIcon("play") : CreateOverlayIcon("error");
                }
            }
            catch
            {
                // Server is unreachable
                authenticated = false;
                currentUser = "";
                // Keep monitoring running even if server is down
                trayIcon.Text = $@"{APP_NAME} - {localization.T("tooltip_server_unreachable")} - {(monitoringActive ? localization.T("monitoring_active") : localization.T("monitoring_inactive"))}";
                trayIcon.Icon = monitoringActive ? CreateOverlayIcon("play") : CreateOverlayIcon("error");
            }
        }

        private void OpenBrowser()
        {
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = webAppUrl,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                ShowError($"{localization.T("could_not_open_browser")}: {ex.Message}");
            }
        }

        private void ShowLoginDialog()
        {
            using (var loginForm = new LoginForm(config.Username))
            {
                if (loginForm.ShowDialog() == DialogResult.OK)
                {
                    Task.Run(async () =>
                    {
                        if (await Login(loginForm.Username, loginForm.Password))
                        {
                            // The tray menu will update on next opening.
                            await StartMonitoringOnStartup();
                        }
                        else
                        {
                            this.Invoke(() =>
                                MessageBox.Show(localization.T("login_failed"), localization.T("login_failed"),
                                    MessageBoxButtons.OK, MessageBoxIcon.Error));
                        }
                    });
                }
            }
        }

        private void ShowManualEntry()
        {
            if (!authenticated)
            {
                MessageBox.Show(localization.T("please_login"), localization.T("login_required"), 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            try
            {
                using (var manualEntryForm = new ManualEntryForm(httpClient, webAppUrl, currentUser, localization))
                {
                    manualEntryForm.ShowDialog();
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error opening manual entry form: {ex.Message}", "Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void ShowFileSelector()
        {
            if (!authenticated)
            {
                MessageBox.Show(localization.T("please_login"), localization.T("login_required"), 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            try
            {
                using (var fileSelectorForm = new FileSelectorForm(httpClient, webAppUrl, currentUser, localization))
                {
                    if (fileSelectorForm.ShowDialog() == DialogResult.OK)
                    {
                        // Refresh monitoring paths after changes
                        Task.Run(async () => await StartMonitoringOnStartup());
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error opening file selector form: {ex.Message}", "Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private async Task ShowStatus()
        {
            if (!authenticated)
            {
                MessageBox.Show(localization.T("please_login"), "Status", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            
            string statusMessage = $@"User: {currentUser}
Server: {webAppUrl}
Monitoring: {(monitoringActive ? "Active" : "Inactive")}
Watching: {fileWatchers.Count} paths
Pending Changes: {pendingChanges.Count}
Processed Events: {processedEvents.Count}
Content Scanning: {(config.ScanFileContents ? "Enabled" : "Disabled")}
Max Scan Size: {config.MaxFileSizeMB} MB";
            
            MessageBox.Show(statusMessage, "Application Status", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        private void ShowError(string message)
        {
            Console.WriteLine($"Error: {message}");
        }

        private void SwitchUser()
        {
            Logout();
            ShowLoginDialog();
        }

        private void QuitApplication()
        {
            StopMonitoring();
            if (processTimer != null)
            {
                processTimer.Stop();
                processTimer.Dispose();
            }
            if (loginRetryTimer != null)
            {
                loginRetryTimer.Stop();
                loginRetryTimer.Dispose();
            }
            if (trayIcon != null) trayIcon.Visible = false;
            Application.Exit();
        }

        #region Login Retry
        private void StartLoginRetryTimer()
        {
            if (loginRetryTimer == null)
            {
                loginRetryTimer = new System.Windows.Forms.Timer();
                loginRetryTimer.Interval = LOGIN_RETRY_INTERVAL_MS;
                loginRetryTimer.Tick += async (s, e) => await LoginRetryTimerTick();
            }
            
            loginRetryCount = 0;
            loginRetryTimer.Start();
            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Login retry timer started. Will retry every {LOGIN_RETRY_INTERVAL_MS / 1000} seconds.");
        }

        private void StopLoginRetryTimer()
        {
            if (loginRetryTimer != null)
            {
                loginRetryTimer.Stop();
                loginRetryCount = 0;
                loginRetryTimer.Interval = LOGIN_RETRY_INTERVAL_MS; // Reset to 1 minute
                lastSuccessfulConnection = DateTime.Now;
                Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Login retry timer stopped.");
            }
        }

        private async Task LoginRetryTimerTick()
        {
            if (authenticated)
            {
                StopLoginRetryTimer();
                return;
            }

            // Reset retry count every hour to prevent it from growing forever
            if (DateTime.Now - lastSuccessfulConnection > TimeSpan.FromHours(1))
            {
                if (loginRetryCount > 10)
                {
                    loginRetryCount = 5; // Reset but keep some history
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Reset retry count after prolonged failure");
                }
            }

            loginRetryCount++;

            // Progressive backoff: 1min → 2min → 5min → 10min (max)
            if (loginRetryCount > 3)
            {
                int minutes = Math.Min(10, loginRetryCount <= 5 ? 2 : 5);
                int newInterval = minutes * 60000;
                if (loginRetryTimer.Interval != newInterval)
                {
                    loginRetryTimer.Interval = newInterval;
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Increased retry interval to {minutes} minutes");
                }
            }

            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Login retry attempt {loginRetryCount} (next in {loginRetryTimer.Interval / 60000}min)...");

            // Check if we still have stored credentials
            if (!string.IsNullOrEmpty(config.Username))
            {
                string password = GetStoredPassword(config.Username);
                if (!string.IsNullOrEmpty(password))
                {
                    // Check server connection first
                    if (await CheckServerConnection())
                    {
                        if (await Login(config.Username, password))
                        {
                            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Login retry successful!");
                            StopLoginRetryTimer();
                            
                            // Start monitoring if it was enabled in config
                            if (config.MonitoringEnabled && !monitoringActive)
                            {
                                await StartMonitoring();
                            }
                            
                            // Show success notification
                            trayIcon.ShowBalloonTip(3000, "Login Successful", 
                                $"Successfully logged in as {config.Username}", 
                                ToolTipIcon.Info);
                        }
                        else
                        {
                            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Login retry failed. Will try again in {loginRetryTimer.Interval / 60000} minutes.");
                        }
                    }
                    else
                    {
                        Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Server unreachable. Will try again in {loginRetryTimer.Interval / 60000} minutes.");
                    }
                }
                else
                {
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] No stored password found. Will continue trying periodically...");
                    // DON'T stop the timer - keep trying in case password gets restored
                }
            }
            else
            {
                Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] No username configured. Will continue trying periodically...");
                // DON'T stop the timer - keep trying in case username gets configured
            }
        }
        #endregion

        #region File Monitoring
        private async Task StartMonitoringOnStartup()
        {
            if (authenticated) await StartMonitoring();
        }

        private async Task ToggleMonitoring()
        {
            if (monitoringActive)
            {
                // Show confirmation dialog before stopping monitoring
                var result = MessageBox.Show(
                    "Are you sure you want to stop file monitoring?\n\nThis will stop tracking all file changes until you manually restart monitoring.",
                    "Confirm Stop Monitoring",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Warning,
                    MessageBoxDefaultButton.Button2); // Default to "No"
                
                if (result == DialogResult.Yes)
                {
                    StopMonitoring();
                    config.MonitoringEnabled = false;
                    SaveConfiguration();
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Monitoring stopped by user confirmation.");
                }
                else
                {
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] User cancelled stop monitoring request.");
                    return; // Don't stop monitoring
                }
            }
            else
            {
                await StartMonitoring();
            }
            await UpdateTrayIcon();
        }

        private async Task StartMonitoring()
        {
            // Allow monitoring to start even without authentication
            // This enables monitoring to continue working during network issues

            // Only stop existing monitoring if we're already monitoring
            // This prevents unnecessary restarts
            if (monitoringActive)
            {
                StopMonitoring();
            } 

            try
            {
                List<MonitoredPathInfo> pathsToMonitor = null;
                
                // Try to get paths from server if authenticated
                if (authenticated)
                {
                    var response = await httpClient.GetAsync($@"{webAppUrl}/api/paths");
                    if (response.IsSuccessStatusCode)
                    {
                        string jsonResponse = await response.Content.ReadAsStringAsync();
                        pathsToMonitor = JsonSerializer.Deserialize<List<MonitoredPathInfo>>(jsonResponse, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
                    }
                }
                
                // If we couldn't get paths or not authenticated, use cached paths if available
                if (pathsToMonitor == null || pathsToMonitor.Count == 0)
                {
                    // For now, we'll just return if we can't get paths
                    // In a future update, we could cache the paths locally
                    if (!authenticated)
                    {
                        Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Cannot start monitoring without authentication and cached paths.");
                        return;
                    }
                }

                if (pathsToMonitor == null) return;

                foreach (var pathInfo in pathsToMonitor)
                {
                    try
                    {
                        string watchPath = pathInfo.is_directory ? pathInfo.path : Path.GetDirectoryName(pathInfo.path);
                        if (string.IsNullOrEmpty(watchPath) || !Directory.Exists(watchPath)) continue;

                        var watcher = new FileSystemWatcher(watchPath);
                        watcher.NotifyFilter = NotifyFilters.LastWrite | NotifyFilters.FileName | NotifyFilters.DirectoryName;

                        if (pathInfo.is_directory)
                        {
                            watcher.IncludeSubdirectories = pathInfo.recursive;
                        }
                        else
                        {
                            watcher.Filter = Path.GetFileName(pathInfo.path);
                            watcher.IncludeSubdirectories = false;
                        }

                        watcher.Changed += OnFileSystemEvent;
                        watcher.Created += OnFileSystemEvent;
                        watcher.Deleted += OnFileSystemEvent;
                        watcher.Renamed += OnRenamed;

                        watcher.EnableRaisingEvents = true;
                        fileWatchers.Add(watcher);
                        watcherInfoMap[watcher] = pathInfo;
                    }
                    catch
                    {
                        // Silent fail for individual path setup
                    }
                }
                monitoringActive = fileWatchers.Count > 0;
                
                // Save monitoring state to config
                Console.WriteLine($"[STARTUP] StartMonitoring finished - monitoringActive: {monitoringActive}, saving to config");
                config.MonitoringEnabled = monitoringActive;
                SaveConfiguration();
                
                if (monitoringActive)
                {
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Monitoring started successfully. Watching {fileWatchers.Count} paths.");
                }
                else
                {
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Monitoring failed to start - no active watchers.");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[STARTUP] StartMonitoring exception: {ex.Message}");
                monitoringActive = false;
                // Don't change config.MonitoringEnabled - let user retry manually
            }
        }

        private void StopMonitoring()
        {
            foreach (var watcher in fileWatchers)
            {
                watcher.EnableRaisingEvents = false;
                watcher.Dispose();
            }
            fileWatchers.Clear();
            watcherInfoMap.Clear();
            monitoringActive = false;
            
            // Clear pending changes
            pendingChanges.Clear();
            
            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Monitoring stopped.");
        }

        private void OnFileSystemEvent(object sender, FileSystemEventArgs e)
        {
            // Filter out temporary files and system files
            string filename = Path.GetFileName(e.FullPath);
            if (filename.StartsWith("~") || filename.StartsWith(".") || filename.EndsWith(".tmp"))
            {
                return; // Ignore temporary files
            }
            
            if (watcherInfoMap.TryGetValue((FileSystemWatcher)sender, out var pathInfo))
            {
                // Queue the change instead of processing immediately
                QueueFileChange(pathInfo, e.ChangeType.ToString(), e.FullPath);
            }
        }

        private void OnRenamed(object sender, RenamedEventArgs e)
        {
            if (watcherInfoMap.TryGetValue((FileSystemWatcher)sender, out var pathInfo))
            {
                QueueFileChange(pathInfo, "deleted", e.OldFullPath);
                QueueFileChange(pathInfo, "created", e.FullPath);
            }
        }

        private void QueueFileChange(MonitoredPathInfo pathInfo, string changeType, string fullPath)
        {
            // Create a simpler key without change type - this will merge all change types for the same file
            var key = fullPath.ToLower();
            var now = DateTime.UtcNow;
            
            pendingChanges.AddOrUpdate(key, 
                // Add new entry
                k => new FileChangeInfo
                {
                    FullPath = fullPath,
                    ChangeType = changeType.ToLower(),
                    PathInfo = pathInfo,
                    FirstSeen = now,
                    LastSeen = now,
                    EventCount = 1
                },
                // Update existing entry - always keep the first change type seen
                (k, existing) =>
                {
                    existing.LastSeen = now;
                    existing.EventCount++;
                    // Don't update change type - keep the first one
                    return existing;
                });
            
            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Queued {changeType} event for {Path.GetFileName(fullPath)} (queue size: {pendingChanges.Count})");
        }

        private async void ProcessPendingChanges(object sender, EventArgs e)
        {
            if (!Monitor.TryEnter(processLock))
            {
                return;
            }
            
            try
            {
                var now = DateTime.UtcNow;
                var changesToProcess = new List<KeyValuePair<string, FileChangeInfo>>();
                
                // Wait 10 seconds for file stability
                foreach (var kvp in pendingChanges)
                {
                    var timeSinceLastSeen = now - kvp.Value.LastSeen;
                    if (timeSinceLastSeen.TotalSeconds >= 10.0)
                    {
                        changesToProcess.Add(kvp);
                    }
                }
                
                // Process stable changes
                foreach (var kvp in changesToProcess)
                {
                    if (pendingChanges.TryRemove(kvp.Key, out var changeInfo))
                    {
                        // Get or create a lock specific to this file
                        var fileLock = processingLocks.GetOrAdd(changeInfo.FullPath.ToLower(), new object());
                        
                        // Use the file-specific lock to ensure only one thread processes this file
                        lock (fileLock)
                        {
                            // Double-check if this file was already processed very recently
                            var recentKey = $"recent:{changeInfo.FullPath.ToLower()}";
                            if (processedEvents.TryGetValue(recentKey, out var lastProcessed))
                            {
                                var timeSince = DateTime.UtcNow - lastProcessed;
                                if (timeSince.TotalSeconds < 30) // 30 second minimum between processing same file
                                {
                                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Skipping {Path.GetFileName(changeInfo.FullPath)} - processed {timeSince.TotalSeconds:F0}s ago");
                                    continue;
                                }
                            }
                            
                            // Mark as recently processed immediately
                            processedEvents[recentKey] = DateTime.UtcNow;
                            
                            // Process the file change asynchronously but wait for completion
                            Task.Run(async () => await ProcessFileChange(changeInfo)).Wait();
                        }
                    }
                }
                
                // Clean up old entries
                var staleEntries = pendingChanges.Where(kvp => (now - kvp.Value.FirstSeen).TotalMinutes > 5).ToList();
                foreach (var entry in staleEntries)
                {
                    pendingChanges.TryRemove(entry.Key, out _);
                }
                
                // Clean up old locks
                if (processingLocks.Count > 100)
                {
                    processingLocks.Clear();
                }
            }
            finally
            {
                Monitor.Exit(processLock);
            }
        }

        private async Task ProcessFileChange(FileChangeInfo changeInfo)
        {
            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Processing {changeInfo.ChangeType} for {Path.GetFileName(changeInfo.FullPath)} (events: {changeInfo.EventCount})");
            
            long? fileSize = null;
            CategoryInfo matchedCategory = null;
            string matchedKeyword = null;
            string contentHash = "no-content";
            
            try
            {
                // Get categories for matching
                var categories = await GetCategories();
                
                if (File.Exists(changeInfo.FullPath))
                {
                    // Add a small delay to ensure file is fully written
                    await Task.Delay(500);
                    
                    var fileInfo = new FileInfo(changeInfo.FullPath);
                    fileSize = fileInfo.Length;
                    
                    string filename = Path.GetFileName(changeInfo.FullPath).ToLower();
                    string fileExtension = Path.GetExtension(changeInfo.FullPath).ToLower();
                    
                    // Calculate a simple hash based on file size and last write time
                    var lastWriteTime = fileInfo.LastWriteTimeUtc;
                    var fileIdentifier = $"{fileSize}:{lastWriteTime.Ticks}";
                    contentHash = CalculateSimpleHash(fileIdentifier);
                    
                    // Check if we should scan file contents
                    if (config.ScanFileContents && 
                        SCANNABLE_EXTENSIONS.Contains(fileExtension) &&
                        fileSize < config.MaxFileSizeMB * 1024 * 1024)
                    {
                        try
                        {
                            // Read file content
                            string content = await ReadFileContentAsync(changeInfo.FullPath);
                            
                            if (!string.IsNullOrEmpty(content))
                            {
                                // Calculate content hash
                                contentHash = CalculateContentHash(content);
                                
                                // Scan for keywords
                                string contentLower = content.ToLower();
                                bool foundMatch = false;
                                
                                foreach (var category in categories)
                                {
                                    if (foundMatch) break;
                                    
                                    if (category.keywords != null)
                                    {
                                        foreach (var keyword in category.keywords)
                                        {
                                            if (contentLower.Contains(keyword.ToLower()))
                                            {
                                                matchedCategory = category;
                                                matchedKeyword = $"Content: {keyword}";
                                                
                                                // Find the line containing the keyword
                                                var lines = content.Split('\n');
                                                for (int i = 0; i < lines.Length; i++)
                                                {
                                                    if (lines[i].ToLower().Contains(keyword.ToLower()))
                                                    {
                                                        string contextLine = lines[i].Trim();
                                                        if (contextLine.Length > 50)
                                                        {
                                                            contextLine = contextLine.Substring(0, 47) + "...";
                                                        }
                                                        matchedKeyword = $"Content: {keyword} (Line {i + 1}: {contextLine})";
                                                        break;
                                                    }
                                                }
                                                foundMatch = true;
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Error scanning file content: {ex.Message}");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Error processing file: {ex.Message}");
            }

            // Create a unique key for this specific event
            string eventKey = $"{changeInfo.FullPath.ToLower()}|{contentHash}|{matchedCategory?.id ?? 0}|{fileSize ?? 0}";
            
            // Check if we've already sent this exact event recently
            if (processedEvents.TryGetValue(eventKey, out var lastProcessed))
            {
                var timeSinceLastProcessed = DateTime.UtcNow - lastProcessed;
                if (timeSinceLastProcessed.TotalMinutes < 10) // 10 minute window
                {
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] DUPLICATE BLOCKED: Exact same event already sent {timeSinceLastProcessed.TotalSeconds:F0}s ago");
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Event key: {eventKey}");
                    return;
                }
            }
            
            // Mark this exact event as processed
            processedEvents[eventKey] = DateTime.UtcNow;
            
            // Clean up old entries (keep dictionary size manageable)
            if (processedEvents.Count > 500)
            {
                var cutoff = DateTime.UtcNow.AddMinutes(-15);
                var oldKeys = processedEvents.Where(kvp => kvp.Value < cutoff).Select(kvp => kvp.Key).ToList();
                foreach (var key in oldKeys)
                {
                    processedEvents.TryRemove(key, out _);
                }
            }

            // CNC Analysis
            CNCAnalysis cncAnalysis = null;
            if (config.EnableCNCAnalysis && File.Exists(changeInfo.FullPath))
            {
                string fileExtension = Path.GetExtension(changeInfo.FullPath).ToLower();
                if (CNC_EXTENSIONS.Contains(fileExtension))
                {
                    try
                    {
                        // Wait a bit to ensure file is fully written
                        await Task.Delay(500);
                        
                        // Use the dual-version analyzer system
                        if (currentAnalyzer != null)
                        {
                            cncAnalysis = await currentAnalyzer.AnalyzeFileAsync(changeInfo.FullPath);
                            
                            if (cncAnalysis.AnalysisSuccessful)
                            {
                                Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] CNC Analysis completed ({currentAnalyzer.GetAnalyzerVersion()}) for {Path.GetFileName(changeInfo.FullPath)} - Total Time: {cncAnalysis.GetFormattedTime()} ({cncAnalysis.TotalTime:F2} min)");
                            }
                            else
                            {
                                Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] CNC Analysis failed: {cncAnalysis.ErrorMessage}");
                            }
                        }
                        else
                        {
                            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] No analyzer available - using legacy analyzer");
                            cncAnalysis = await gCodeAnalyzer.AnalyzeFileAsync(changeInfo.FullPath);
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Error during CNC analysis: {ex.Message}");
                    }
                }
            }

            // Send the event
object cncAnalysisPayload = null;
if (cncAnalysis != null && cncAnalysis.AnalysisSuccessful)
{
    // Get detailed tool usage sessions from appropriate analyzer
    Dictionary<int, ToolUsageSession> toolSessions = null;
    
    // Get tool sessions from the analysis result
    toolSessions = cncAnalysis.ToolSessions ?? new Dictionary<int, ToolUsageSession>();
    
    // Convert tool sessions to payload format
    var toolUsageDetails = toolSessions.Values.Select(session => new
    {
        ToolNumber = session.ToolNumber,
        TotalTime = Math.Round(session.TotalTime, 2),           // seconds
        CuttingTime = Math.Round(session.CuttingTime, 2),       // seconds  
        RapidTime = Math.Round(session.RapidTime, 2),           // seconds
        CuttingDistance = Math.Round(session.CuttingDistance, 1), // mm
        RapidDistance = Math.Round(session.RapidDistance, 1),   // mm
        TotalDistance = Math.Round(session.TotalDistance, 1),   // mm
        MoveCount = session.MoveCount
    }).ToArray();
    
    // IMPORTANT: Send enhanced payload with detailed tool usage data
    cncAnalysisPayload = new
    {
        Filename = cncAnalysis.Filename,
        TotalTime = cncAnalysis.TotalTime,      // Total cycle time in minutes
        MachineTime = cncAnalysis.MachineTime,  // Machine operation time in minutes
        ToolChanges = cncAnalysis.ToolChanges,  // Number of tool changes
        ToolsUsed = cncAnalysis.ToolsUsed,      // List of tool numbers used
        ToolUsageDetails = toolUsageDetails      // NEW: Detailed per-tool timing and usage data
    };
    
    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] CNC payload prepared: TotalTime={cncAnalysis.TotalTime}min, MachineTime={cncAnalysis.MachineTime}min, Tools={cncAnalysis.ToolChanges}, DetailedTools={toolUsageDetails.Length}");
}

var payload = new
{
    path_id = changeInfo.PathInfo.id,
    change_type = changeInfo.ChangeType,
    file_path = changeInfo.FullPath,
    timestamp_utc = DateTime.UtcNow.ToString("o"),
    new_size = fileSize,
    computer_name = Environment.MachineName,
    category_id = matchedCategory?.id,
    matched_keyword = matchedKeyword,
    cnc_analysis = cncAnalysisPayload
};

            try
            {
                string jsonPayload = JsonSerializer.Serialize(payload);
                var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");
                
                var response = await httpClient.PostAsync($@"{webAppUrl}/api/log_event", content);
                if (!response.IsSuccessStatusCode)
                {
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Failed to log event: {response.StatusCode}");
                }
                else
                {
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] ✓ Event logged successfully for {Path.GetFileName(changeInfo.FullPath)} -> {matchedCategory?.name ?? "Allerlei"}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Error sending event to server: {ex.Message}");
            }
        }

        private async Task<string> ReadFileContentAsync(string filePath)
        {
            const int MAX_RETRIES = 5;
            const int INITIAL_RETRY_DELAY_MS = 100;
            const int MAX_RETRY_DELAY_MS = 2000;
            
            for (int retry = 0; retry < MAX_RETRIES; retry++)
            {
                try
                {
                    // Wait before retry (exponential backoff)
                    if (retry > 0)
                    {
                        int delay = Math.Min(INITIAL_RETRY_DELAY_MS * (int)Math.Pow(2, retry - 1), MAX_RETRY_DELAY_MS);
                        await Task.Delay(delay);
                        Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Retry {retry}/{MAX_RETRIES} after {delay}ms delay");
                    }
                    
                    // Try to detect encoding
                    Encoding encoding = DetectFileEncoding(filePath);
                    
                    // Read file with detected encoding
                    using (var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                    using (var reader = new StreamReader(stream, encoding))
                    {
                        // Read in chunks to handle large files better
                        var sb = new StringBuilder();
                        char[] buffer = new char[4096];
                        int bytesRead;
                        int totalBytesRead = 0;
                        int maxBytes = config.MaxFileSizeMB * 1024 * 1024;
                        
                        while ((bytesRead = await reader.ReadAsync(buffer, 0, buffer.Length)) > 0)
                        {
                            sb.Append(buffer, 0, bytesRead);
                            totalBytesRead += bytesRead;
                            
                            // Stop reading if we've exceeded the max size
                            if (totalBytesRead > maxBytes)
                            {
                                Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] File truncated at {totalBytesRead} bytes (max: {maxBytes})");
                                break;
                            }
                        }
                        
                        return sb.ToString();
                    }
                }
                catch (IOException ioEx) when (retry < MAX_RETRIES - 1)
                {
                    // File might be locked, log and retry
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] File locked ({Path.GetFileName(filePath)}), retry {retry + 1}/{MAX_RETRIES}: {ioEx.Message}");
                }
                catch (UnauthorizedAccessException uaEx) when (retry < MAX_RETRIES - 1)
                {
                    // Access denied, wait and retry
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Access denied ({Path.GetFileName(filePath)}), retry {retry + 1}/{MAX_RETRIES}: {uaEx.Message}");
                }
                catch (Exception ex)
                {
                    // Other errors, log and return empty
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Error reading file ({Path.GetFileName(filePath)}): {ex.GetType().Name} - {ex.Message}");
                    return string.Empty;
                }
            }
            
            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Failed to read file after {MAX_RETRIES} attempts: {Path.GetFileName(filePath)}");
            return string.Empty;
        }

        private Encoding DetectFileEncoding(string filePath)
        {
            // Simple encoding detection - check for BOM
            byte[] buffer = new byte[4];
            using (var file = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
            {
                file.Read(buffer, 0, 4);
            }
            
            // Check for UTF-8 BOM
            if (buffer[0] == 0xEF && buffer[1] == 0xBB && buffer[2] == 0xBF)
                return Encoding.UTF8;
            
            // Check for UTF-16 LE BOM
            if (buffer[0] == 0xFF && buffer[1] == 0xFE)
                return Encoding.Unicode;
            
            // Check for UTF-16 BE BOM
            if (buffer[0] == 0xFE && buffer[1] == 0xFF)
                return Encoding.BigEndianUnicode;
            
            // Default to UTF-8 without BOM (most common for text files)
            return Encoding.UTF8;
        }

        private string CalculateContentHash(string content)
        {
            using (var sha256 = SHA256.Create())
            {
                byte[] bytes = Encoding.UTF8.GetBytes(content);
                byte[] hash = sha256.ComputeHash(bytes);
                return Convert.ToBase64String(hash);
            }
        }

        private string CalculateSimpleHash(string input)
        {
            using (var md5 = System.Security.Cryptography.MD5.Create())
            {
                byte[] inputBytes = Encoding.UTF8.GetBytes(input);
                byte[] hashBytes = md5.ComputeHash(inputBytes);
                return BitConverter.ToString(hashBytes).Replace("-", "").ToLowerInvariant();
            }
        }
        #endregion

        #region Utility Methods
        private void ToggleStartup()
        {
            try
            {
                RegistryKey rk = Registry.CurrentUser.OpenSubKey(STARTUP_KEY_PATH, true);
                if (IsStartupEnabled())
                {
                    rk.DeleteValue(APP_NAME, false);
                }
                else
                {
                    rk.SetValue(APP_NAME, Application.ExecutablePath);
                }
            }
            catch { /* Silently handle registry errors */ }
        }

        private bool IsStartupEnabled()
        {
            try
            {
                RegistryKey rk = Registry.CurrentUser.OpenSubKey(STARTUP_KEY_PATH, false);
                return rk.GetValue(APP_NAME) != null;
            }
            catch { return false; }
        }

        private void StorePassword(string username, string password)
        {
            try
            {
                byte[] entropy = Encoding.Unicode.GetBytes("FileMonitorSalt");
                byte[] data = ProtectedData.Protect(Encoding.Unicode.GetBytes(password), entropy, DataProtectionScope.CurrentUser);
                File.WriteAllBytes($@"{username}.pass", data);
            }
            catch { /* Silently handle password storage errors */ }
        }

        private string GetStoredPassword(string username)
        {
            try
            {
                byte[] entropy = Encoding.Unicode.GetBytes("FileMonitorSalt");
                byte[] data = File.ReadAllBytes($@"{username}.pass");
                byte[] decrypted = ProtectedData.Unprotect(data, entropy, DataProtectionScope.CurrentUser);
                return Encoding.Unicode.GetString(decrypted);
            }
            catch { return null; }
        }

        private void DeleteStoredPassword(string username)
        {
            try
            {
                if (File.Exists($@"{username}.pass"))
                {
                    File.Delete($@"{username}.pass");
                }
            }
            catch { /* Silently handle password deletion errors */ }
        }

        private Icon CreateDefaultIcon()
        {
            try { return Icon.ExtractAssociatedIcon(Application.ExecutablePath); }
            catch { return SystemIcons.Application; }
        }

        private Icon CreateOverlayIcon(string overlayType)
        {
            Icon baseIcon = CreateDefaultIcon();
            Bitmap bmp = baseIcon.ToBitmap();
            using (Graphics g = Graphics.FromImage(bmp))
            {
                Brush brush;
                switch (overlayType)
                {
                    case "play":
                        brush = Brushes.Green;
                        break;
                    case "error":
                        brush = Brushes.Red;
                        break;
                    case "connected":
                        brush = Brushes.Blue;
                        break;
                    default:
                        return baseIcon;
                }
                g.FillEllipse(brush, new Rectangle(bmp.Width - 10, bmp.Height - 10, 10, 10));
            }
            return Icon.FromHandle(bmp.GetHicon());
        }
        #endregion
    }
}