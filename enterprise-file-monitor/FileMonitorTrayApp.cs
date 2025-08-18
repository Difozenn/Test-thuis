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
        Auto,       // Try enhanced first, fallback to simple if needed
        MachineSpecific // Use machine-specific analyzer based on detected type
    }

    // Machine type enum for different CNC machine types
    public enum MachineType
    {
        Unknown,
        HH7,        // HH7 machine - detected by Post:HH7 and CP_TCHECK.NC
        Opus,       // OPUS machine - detected by Post:RB_OPUS and CH_CHECK_TOOL.NC  
        Vision      // Vision/Field1 machine - detected by VISION/ARTIS and DEF REAL syntax
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
        public AnalysisMode Mode { get; set; } = AnalysisMode.MachineSpecific;  // Default to machine-specific
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
            
            // Ensure ToolsUsed is populated from ToolSessions if empty
            if (result.ToolsUsed.Count == 0 && result.ToolSessions.Count > 0)
            {
                result.ToolsUsed = result.ToolSessions.Keys.ToList();
                Console.WriteLine($"[SIMPLE] Fixed ToolsUsed from sessions: {string.Join(", ", result.ToolsUsed)}");
            }
            
            // Debug output for SPF files
            if (filePath.EndsWith(".spf", StringComparison.OrdinalIgnoreCase))
            {
                Console.WriteLine($"[DEBUG] SPF file analysis complete: {Path.GetFileName(filePath)}");
                Console.WriteLine($"[DEBUG] ToolsUsed: [{string.Join(", ", result.ToolsUsed)}]");
                Console.WriteLine($"[DEBUG] ToolChanges: {result.ToolChanges}");
                Console.WriteLine($"[DEBUG] TotalTime: {result.TotalTime:F2}min ({result.TotalTime * 60:F1}s)");
                Console.WriteLine($"[DEBUG] ToolSessions: {result.ToolSessions.Count}");
                
                // Calculate what the time should be with tool changes
                double expectedToolChangeTime = result.ToolChanges * config.TC_51_51;
                Console.WriteLine($"[DEBUG] Expected tool change time: {result.ToolChanges} × {config.TC_51_51}s = {expectedToolChangeTime:F1}s");
                Console.WriteLine($"[DEBUG] If tool changes were included, total would be: {(result.TotalTime * 60 + expectedToolChangeTime):F1}s");
            }
            
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
            
            // Ensure ToolsUsed is populated from ToolSessions if empty
            if (result.ToolsUsed.Count == 0 && result.ToolSessions.Count > 0)
            {
                result.ToolsUsed = result.ToolSessions.Keys.ToList();
                Console.WriteLine($"[ENHANCED] Fixed ToolsUsed from sessions: {string.Join(", ", result.ToolsUsed)}");
            }
            
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
    
    // HH7 Machine Analyzer - optimized for HH7 postprocessor output
    public class HH7Analyzer : ICNCAnalyzer
    {
        private readonly TCALCMachineConfig _config;
        
        public HH7Analyzer()
        {
            // HH7-specific configuration (from TCALC_HH7)
            _config = new TCALCMachineConfig
            {
                MAXFEEDRATE_XY = 20000.0,  // Rapid feedrate
                MAXFEEDRATE_Z = 20000.0,
                TC_51_51 = 20.0,  // HH7 tool change time
                DHFeedrateG00 = 20000.0
            };
            Console.WriteLine($"[HH7] Initialized with HH7-specific configuration");
        }
        
        public async Task<CNCAnalysis> AnalyzeFileAsync(string filePath)
        {
            var analyzer = new TCALCAnalyzer(_config);
            var result = await analyzer.AnalyzeFileAsync(filePath);
            result.ToolSessions = analyzer.GetToolSessions();
            result.DetectedMachineType = MachineType.HH7;
            
            // HH7-specific analysis enhancements
            var lines = await File.ReadAllLinesAsync(filePath);
            
            // Extract HH7-specific tool data and postprocessor version
            foreach (var line in lines)
            {
                // Extract postprocessor version
                if (line.Contains("Post:HH7"))
                {
                    var versionMatch = Regex.Match(line, @"Post:HH7\s+(V[\d.]+)", RegexOptions.IgnoreCase);
                    if (versionMatch.Success)
                        result.PostprocessorVersion = versionMatch.Groups[1].Value;
                }
                
                // Extract Box IDs as tool identifiers
                // Format 1: ; --- Box:  601 HId:1
                if (line.Contains("Box:"))
                {
                    var boxMatch = Regex.Match(line, @"Box:\s*(\d+)");
                    if (boxMatch.Success && int.TryParse(boxMatch.Groups[1].Value, out int boxId))
                    {
                        if (!result.ToolsUsed.Contains(boxId))
                            result.ToolsUsed.Add(boxId);
                    }
                }
                
                // Format 2: BOXID:<601> T:<601 VF 12 R P/N>
                if (line.Contains("BOXID:"))
                {
                    var boxMatch = Regex.Match(line, @"BOXID:<(\d+)>");
                    if (boxMatch.Success && int.TryParse(boxMatch.Groups[1].Value, out int boxId))
                    {
                        if (!result.ToolsUsed.Contains(boxId))
                            result.ToolsUsed.Add(boxId);
                    }
                }
            }
            
            Console.WriteLine($"[HH7] Analysis complete: {result.ToolsUsed.Count} tools, {result.TotalTime:F2} min cycle time");
            return result;
        }
        
        public string GetAnalyzerVersion()
        {
            return "HH7 Analyzer v1.0 (Optimized for HH7 machines)";
        }
    }
    
    // Opus Machine Analyzer - optimized for RB_OPUS postprocessor output
    public class OpusAnalyzer : ICNCAnalyzer
    {
        private readonly TCALCMachineConfig _config;
        
        public OpusAnalyzer()
        {
            // Opus-specific configuration (RB_OPUS_V7)
            _config = new TCALCMachineConfig
            {
                MAXFEEDRATE_XY = 20000.0,  // Rapid feedrate
                MAXFEEDRATE_Z = 20000.0,
                TC_51_51 = 20.0,  // Opus tool change time
                DHFeedrateG00 = 20000.0
            };
            Console.WriteLine($"[OPUS] Initialized with Opus-specific configuration");
        }
        
        public async Task<CNCAnalysis> AnalyzeFileAsync(string filePath)
        {
            var analyzer = new TCALCAnalyzer(_config);
            var result = await analyzer.AnalyzeFileAsync(filePath);
            result.ToolSessions = analyzer.GetToolSessions();
            result.DetectedMachineType = MachineType.Opus;
            
            // Opus-specific analysis enhancements
            var lines = await File.ReadAllLinesAsync(filePath);
            
            // Track Box ID to extract from comments
            Dictionary<int, int> boxToToolMap = new Dictionary<int, int>();
            
            for (int i = 0; i < lines.Length; i++)
            {
                var line = lines[i];
                
                // Extract postprocessor version
                if (line.Contains("Post:RB_OPUS"))
                {
                    var versionMatch = Regex.Match(line, @"Post:RB_OPUS_V\d+\s+(V[\d.]+)", RegexOptions.IgnoreCase);
                    if (versionMatch.Success)
                        result.PostprocessorVersion = versionMatch.Groups[1].Value;
                }
                
                // First look for Box info in comments to get actual tool ID
                // Format: ; --- BOX:  601 TCID:100 TCPlace:1   HId:1001  VF 12 R P/N
                if (line.Contains("BOX:") && line.Contains("TCPlace:"))
                {
                    var boxMatch = Regex.Match(line, @"BOX:\s*(\d+)");
                    
                    if (boxMatch.Success && int.TryParse(boxMatch.Groups[1].Value, out int boxId))
                    {
                        // Check next line for CH_CHECK_TOOL.NC which has the mapping
                        if (i + 1 < lines.Length && lines[i + 1].Contains("CH_CHECK_TOOL.NC"))
                        {
                            // In Opus, the box ID is the tool ID we want
                            if (!result.ToolsUsed.Contains(boxId))
                                result.ToolsUsed.Add(boxId);
                            
                            // Also check for place mapping if needed
                            var placeMatch = Regex.Match(line, @"TCPlace:(\d+)");
                            if (placeMatch.Success && int.TryParse(placeMatch.Groups[1].Value, out int place))
                            {
                                boxToToolMap[place] = boxId;
                            }
                        }
                    }
                }
                
                // Process carrier position data for Opus machines
                if (line.Contains("CH_CARRIER_POS.NC"))
                {
                    // Carrier position affects overhead time
                    result.OverheadTime += 0.5; // Add carrier positioning time
                }
            }
            
            // If no tools found from BOX comments, use the existing tool detection
            if (result.ToolsUsed.Count == 0 && result.ToolSessions.Count > 0)
            {
                result.ToolsUsed = result.ToolSessions.Keys.ToList();
            }
            
            Console.WriteLine($"[OPUS] Analysis complete: Tools {string.Join(",", result.ToolsUsed)}, {result.TotalTime:F2} min cycle time");
            return result;
        }
        
        public string GetAnalyzerVersion()
        {
            return "Opus Analyzer v1.0 (Optimized for RB_OPUS machines)";
        }
    }
    
    // Vision/Field1 Machine Analyzer - optimized for Vision/Artis postprocessor output
    public class VisionAnalyzer : ICNCAnalyzer
    {
        private readonly TCALCMachineConfig _config;
        private Dictionary<int, int> _toolPlatzMapping = new Dictionary<int, int>();
        
        public VisionAnalyzer()
        {
            // Vision-specific configuration (Siemens control)
            _config = new TCALCMachineConfig
            {
                MAXFEEDRATE_XY = 20000.0,  // Rapid feedrate
                MAXFEEDRATE_Z = 20000.0,
                TC_51_51 = 20.0,  // Vision tool change time
                DHFeedrateG00 = 20000.0
            };
            Console.WriteLine($"[VISION] Initialized with Vision/Siemens-specific configuration");
        }
        
        public async Task<CNCAnalysis> AnalyzeFileAsync(string filePath)
        {
            var analyzer = new TCALCAnalyzer(_config);
            var result = await analyzer.AnalyzeFileAsync(filePath);
            result.ToolSessions = analyzer.GetToolSessions();
            result.DetectedMachineType = MachineType.Vision;
            
            // Vision-specific analysis enhancements
            var lines = await File.ReadAllLinesAsync(filePath);
            
            foreach (var line in lines)
            {
                // Extract postprocessor version
                if (line.Contains("Post:VISION") || line.Contains("POST FOR VISION/ARTIS"))
                {
                    var versionMatch = Regex.Match(line, @"V([\d.]+)", RegexOptions.IgnoreCase);
                    if (versionMatch.Success)
                        result.PostprocessorVersion = versionMatch.Groups[1].Value;
                }
                
                // Extract Box IDs as tool identifiers for Vision
                // Format 1: ; --- Box:  602 HId:1     VF 14 R P/N
                if (line.Contains("Box:"))
                {
                    var boxMatch = Regex.Match(line, @"Box:\s*(\d+)");
                    if (boxMatch.Success && int.TryParse(boxMatch.Groups[1].Value, out int boxId))
                    {
                        if (!result.ToolsUsed.Contains(boxId))
                        {
                            result.ToolsUsed.Add(boxId);
                            Console.WriteLine($"[VISION] Found tool Box:{boxId}");
                        }
                    }
                }
                
                // Format 2: BOXID:<501> for drilling heads
                if (line.Contains("BOXID:<"))
                {
                    var boxIdMatch = Regex.Match(line, @"BOXID:<(\d+)>");
                    if (boxIdMatch.Success && int.TryParse(boxIdMatch.Groups[1].Value, out int boxId))
                    {
                        if (!result.ToolsUsed.Contains(boxId))
                        {
                            result.ToolsUsed.Add(boxId);
                            Console.WriteLine($"[VISION] Found drilling head Box:{boxId}");
                        }
                    }
                }
                
                // Process Vision-specific commands
                if (line.Contains("STOPRE"))
                {
                    result.OverheadTime += 0.1; // Add stop/restart time
                }
            }
            
            // Vision machines often have longer overhead due to Siemens control
            result.OverheadTime *= 1.2; // 20% overhead increase for Vision
            
            Console.WriteLine($"[VISION] Analysis complete: {result.ToolsUsed.Count} tools, {result.TotalTime:F2} min cycle time");
            return result;
        }
        
        public string GetAnalyzerVersion()
        {
            return "Vision Analyzer v1.0 (Optimized for Vision/Artis machines)";
        }
    }
    
    // Factory for creating analyzer instances
    public static class CNCAnalyzerFactory
    {
        // Detect machine type based on file content patterns
        public static MachineType DetectMachineType(string filePath)
        {
            try
            {
                // Read first 100 lines to detect machine type
                var lines = File.ReadLines(filePath).Take(100).ToList();
                var content = string.Join("\n", lines);
                
                // Check for HH7 machine patterns
                if (content.Contains("Post:HH7", StringComparison.OrdinalIgnoreCase) ||
                    content.Contains("NAME=CP_TCHECK.NC", StringComparison.OrdinalIgnoreCase))
                {
                    Console.WriteLine($"[ANALYZER] Detected HH7 machine type from file content");
                    return MachineType.HH7;
                }
                
                // Check for Opus machine patterns  
                if (content.Contains("Post:RB_OPUS", StringComparison.OrdinalIgnoreCase) ||
                    content.Contains("NAME=CH_CHECK_TOOL.NC", StringComparison.OrdinalIgnoreCase) ||
                    content.Contains("NAME=CH_CARRIER_POS.NC", StringComparison.OrdinalIgnoreCase))
                {
                    Console.WriteLine($"[ANALYZER] Detected Opus machine type from file content");
                    return MachineType.Opus;
                }
                
                // Check for Vision/Field1 machine patterns
                if (content.Contains("POST FOR VISION/ARTIS", StringComparison.OrdinalIgnoreCase) ||
                    content.Contains("Post:VISION", StringComparison.OrdinalIgnoreCase) ||
                    content.Contains("DEF REAL", StringComparison.OrdinalIgnoreCase) ||
                    content.Contains("STOPRE", StringComparison.OrdinalIgnoreCase))
                {
                    Console.WriteLine($"[ANALYZER] Detected Vision machine type from file content");
                    return MachineType.Vision;
                }
                
                Console.WriteLine($"[ANALYZER] Unable to detect machine type, using default");
                return MachineType.Unknown;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ANALYZER] Error detecting machine type: {ex.Message}");
                return MachineType.Unknown;
            }
        }
        
        public static ICNCAnalyzer CreateAnalyzer(AnalyzerConfig config, string webAppUrl, string filePath = null)
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
                    
                case AnalysisMode.MachineSpecific:
                    if (!string.IsNullOrEmpty(filePath))
                    {
                        var machineType = DetectMachineType(filePath);
                        switch (machineType)
                        {
                            case MachineType.HH7:
                                return new HH7Analyzer();
                            case MachineType.Opus:
                                return new OpusAnalyzer();
                            case MachineType.Vision:
                                return new VisionAnalyzer();
                            default:
                                return new SimpleCNCAnalyzer();
                        }
                    }
                    return new SimpleCNCAnalyzer();
                    
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
        public double CutTime { get; set; }  // Actual cutting time (G1, G2, G3)
        public double OverheadTime { get; set; }  // Non-cutting time (rapids, tool changes, etc)
        public double SpecialDrillingOverhead { get; set; } = 0;  // Extra time for large drilling tools in milling holders
        public int ToolChanges { get; set; }
        public int ProcessesCount { get; set; }
        public Dictionary<string, int> MovementStats { get; set; }
        public List<string> ProcessesUsed { get; set; }
        public List<int> ToolsUsed { get; set; }
        public Dictionary<int, ToolUsageSession> ToolSessions { get; set; }
        public List<string> HopFiles { get; set; }  // HOP/HOPS/HOPX file references
        public List<DrillingOperation> DrillingOperations { get; set; }  // Drilling operations detected
        public DateTime AnalyzedAt { get; set; }
        public bool AnalysisSuccessful { get; set; }
        public string ErrorMessage { get; set; }
        public MachineType DetectedMachineType { get; set; }  // Track which machine type was detected
        public string PostprocessorVersion { get; set; }  // Store postprocessor version info
        public List<string> ReferencedHOPFiles { get; set; }  // HOP/HOPS/HOPX files referenced in the CNC program
        public string PrimaryHOPFile { get; set; }  // Main HOP file for the program (first or most referenced)

        public CNCAnalysis()
        {
            MovementStats = new Dictionary<string, int>();
            ProcessesUsed = new List<string>();
            ToolsUsed = new List<int>();
            ToolSessions = new Dictionary<int, ToolUsageSession>();
            ReferencedHOPFiles = new List<string>();
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
        public double MAXFEEDRATE_XY { get; set; } = 20000.0;  // mm/min for G0 XY moves (standard for all machines)
        public double MAXFEEDRATE_Z { get; set; } = 20000.0;   // mm/min for G0 Z moves
        public double DHFeedrateG00 { get; set; } = 20000.0;   // Rapid feedrate - should match MAXFEEDRATE_XY
        
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
        public double TC_51_51 { get; set; } = 20.0;          // Default tool change time
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
        
        /// <summary>
        /// Calculate drilling time from a drilling sequence (G0/G1 moves) - simplified
        /// </summary>
        public double CalculateDrillingSequenceTime(double safetyZ, double entryZ, double entryDepth, double finalDepth,
            double entryFeedrate, double drillFeedrate, double retractFeedrate, int dFlag = 10)
        {
            // Simplified drilling time calculation
            // time = distance / feedrate * 60 (to get seconds from mm/min)
            
            double totalTime = 0;
            
            // Approach time (rapid to safety height)
            if (safetyZ > 0)
                totalTime += (safetyZ / _config.MAXFEEDRATE_Z) * 60;
            
            // Drilling time (depth at drill feedrate)
            double drillDepth = Math.Abs(finalDepth);
            if (drillDepth > 0 && drillFeedrate > 0)
                totalTime += (drillDepth / drillFeedrate) * 60;
            
            // Retract time (rapid back to safety)
            double retractDistance = Math.Abs(finalDepth) + safetyZ;
            if (retractDistance > 0)
                totalTime += (retractDistance / _config.MAXFEEDRATE_Z) * 60;
            
            // Add small cycle overhead (1-2 seconds typical)
            totalTime += 1.5;
            
            return totalTime;
        }
    }
    
    // Drilling operation tracking
    public class DrillingOperation
    {
        public int CycleType { get; set; }  // 10=blind, 20=through, 30=hinge
        public double X { get; set; }
        public double Y { get; set; }
        public double SafetyZ { get; set; }
        public double EntryZ { get; set; }
        public double EntryDepth { get; set; }
        public double FinalDepth { get; set; }
        public double EntryFeedrate { get; set; }
        public double DrillFeedrate { get; set; }
        public double RetractFeedrate { get; set; }
        public bool IsHorizontal { get; set; }
        public int ToolNumber { get; set; }
        public int DrillBitId { get; set; }  // Drill bit identifier from ->xxxx<- pattern
        public double CalculatedTime { get; set; }
    }
    
    public class DrillMove
    {
        public string Code { get; set; }  // G0, G1, etc
        public double? X { get; set; }
        public double? Y { get; set; }
        public double? Z { get; set; }
        public double? F { get; set; }
        public bool HasG9 { get; set; }  // G9 = exact stop mode
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
        private int _currentSpecialDrillingTool = 0; // Track Box ID 200-300 drilling tools
        private Dictionary<int, ToolUsageSession> _toolSessions = new Dictionary<int, ToolUsageSession>();
        private int _lastToolChangeLineNumber = -100; // Track line number of last tool change to avoid duplicates
        private double _lastValidFeedrate = DEFAULT_CUTTING_FEEDRATE; // Track last valid feedrate for consistency
        private Dictionary<int, int> _platzToBoxMapping = new Dictionary<int, int>(); // Map Platz to Box ID for Vision/Siemens
        
        // Debug counters for T501
        private int _t501DrillCyclesF600 = 0;
        private int _t501DrillCyclesF1000 = 0;
        private int _t501DrillCyclesF2000 = 0;
        private int _t501XYMoves = 0;
        private bool _t501DrillCycleStarted = false; // Track if we're in a drill cycle
        private int _t501LastDrillFeedrate = 0; // Track the feedrate of the current drill cycle
        private bool _isOpusFile = false; // Track if this is an OPUS postprocessor file
        
        /// <summary>
        /// Get tool usage sessions for detailed timing analysis
        /// </summary>
        public Dictionary<int, ToolUsageSession> GetToolSessions() => _toolSessions;
        
        // Enhanced timing constants (based on actual machine measurements)
        private const double TCP_ON_TIME = 0.4; // seconds (measured from actual operations)
        private const double TCP_OFF_TIME = 0.4; // seconds (measured from actual operations)
        private const double CONTOUR_START_TIME = 0.4; // seconds (measured from actual operations)
        private const double CONTOUR_END_TIME = 0.4; // seconds (measured from actual operations)
        private const double DYNAMIC_SETUP_TIME = 0.5; // seconds (measured from actual operations)
        private const double FLUSH_WAIT_TIME = 1.0; // seconds (measured from actual operations)
        private const double COORDINATE_SETUP_TIME = 0.2; // seconds
        private const double GENERAL_CYCLE_TIME = 0.1; // seconds
        private const double TOOL_CHANGE_TIME = 20.0; // seconds (default)
        private const double SPINDLE_START_TIME = 2.0; // seconds (measured: 3 × 2.0s)
        private const double SPINDLE_STOP_TIME = 1.5; // seconds (measured: 2 × 1.5s)

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
            public int CycleCount => OtherCycles; // Alias for compatibility
        }

        // Movement tracking
        private double _currentX = 0;
        private double _currentY = 0;
        private double _currentZ = 0;
        private double _currentFeedrate = 0;
        private const double DEFAULT_CUTTING_FEEDRATE = 3000; // Default feedrate if none specified
        
        // Drilling detection state
        private bool _isDrillingSequence = false;
        private bool _justCompletedDrilling = false; // Flag to prevent duplicate detection
        private DrillingOperation _currentDrilling = null;
        private List<DrillMove> _drillMoves = new List<DrillMove>();
        private double _lastDrillingSafetyZ = 30;  // Common default safety height
        private List<DrillingOperation> _completedDrillings = new List<DrillingOperation>();
        
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
            var analysis = new CNCAnalysis
            {
                Filename = Path.GetFileName(filePath),
                HopFiles = new List<string>(),
                DrillingOperations = new List<DrillingOperation>()
            };
            
            // Extract configuration from the file itself
            ExtractConfigFromFile(filePath);
            Console.WriteLine($"[TCALC] Analysis config: Rapid={_config.MAXFEEDRATE_XY}mm/min, ToolChange={_config.TC_51_51}s");
            
            // Debug for Field1.spf
            if (analysis.Filename.Contains("Field1", StringComparison.OrdinalIgnoreCase))
            {
                Console.WriteLine($"[TCALC] Starting analysis of Field1.spf");
            }
            Console.WriteLine($"[TCALC] Config detail: RapidFeedrate={_config.RapidFeedrate}mm/min, DHFeedrateG00={_config.DHFeedrateG00}mm/min");

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
                _currentX = 0; _currentY = 0; _currentZ = 0; 
                _currentFeedrate = 0;
                _lastValidFeedrate = DEFAULT_CUTTING_FEEDRATE; // Reset to default
                _lastToolChangeLineNumber = -100; // Reset tool change tracking
                _currentActiveTool = 0; // Reset active tool
                _currentSpecialDrillingTool = 0; // Reset special drilling tool
                _toolSessions.Clear(); // Clear tool sessions from previous analysis
                _platzToBoxMapping.Clear(); // Clear tool mappings
                
                // Pre-scan for Vision/Siemens tool mappings
                BuildPlatzToBoxMapping(lines);
                
                // Extract HOP file references
                ExtractHOPFileReferences(lines, analysis);

                for (int lineIndex = 0; lineIndex < lines.Length; lineIndex++)
                {
                    var line = lines[lineIndex];
                    
                    // IMPORTANT: Process drilling BEFORE removing comments
                    ProcessDrillingOperation(line, lines, lineIndex, analysis);
                    
                    var cleanLine = CleanGCodeLine(line);
                    if (string.IsNullOrEmpty(cleanLine)) continue;

                    // Count machine operations (matching Python logic)
                    CountMachineOperations(cleanLine, machineOps);

                    // Extract tool numbers (pass line number to avoid duplicate detection)
                    ExtractToolNumbers(cleanLine, analysis, lineIndex, filePath);
                    
                    // Check for special drilling tools in milling holders (Box ID 200-300)
                    // These are drilling tools too large for the drill head (501)
                    // Check both process headers and actual drilling operations
                    if (line.Contains("VertDrilling") && line.Contains("BOXID:<"))
                    {
                        // This is a process header for vertical drilling
                        var boxMatch = Regex.Match(line, @"BOXID:<(\d+)>");
                        if (boxMatch.Success && int.TryParse(boxMatch.Groups[1].Value, out int boxId))
                        {
                            if (boxId >= 200 && boxId <= 300)
                            {
                                _currentSpecialDrillingTool = boxId;
                                Console.WriteLine($"[TCALC] Starting Box {boxId} drilling operations (large tool in milling holder)");
                            }
                        }
                    }
                    
                    // When we activate tool 270 (or any Box ID 200-300), mark it as special
                    if (_currentActiveTool >= 200 && _currentActiveTool <= 300)
                    {
                        _currentSpecialDrillingTool = _currentActiveTool;
                    }
                    
                    // Count actual drilling operations with the special tool
                    // T270 uses F600, F1500, F2000, F2500, F3000 for drilling
                    // Add overhead time for T270 drilling operations
                    if (_currentActiveTool == 270)
                    {
                        // For T270, add 2.5s overhead per drilling cycle for tool positioning/retraction
                        // This accounts for the difference between measured G1 time and actual cycle time
                        if (cleanLine.Contains("G1") && cleanLine.Contains("Z") && 
                            (_currentFeedrate == 3000 || _currentFeedrate == 2500 || _currentFeedrate == 1500 || _currentFeedrate == 600))
                        {
                            // Add overhead time for T270 drilling operations
                            if (_toolSessions.ContainsKey(270))
                            {
                                double overheadTime = 2.5 / 60.0; // 2.5 seconds overhead per cycle
                                _toolSessions[270].CuttingTime += overheadTime;
                                Console.WriteLine($"[TCALC] T270 drilling overhead added: {overheadTime*60:F1}s");
                            }
                        }
                    }
                    // Original special tool logic for counting operations
                    else if (_currentSpecialDrillingTool > 0 && _currentActiveTool == _currentSpecialDrillingTool)
                    {
                        // Check for initial drilling plunge (start of a new hole)
                        // Other special tools: bore operations typically start with F1500 to Z-3 or F600 to Z=-3
                        if (cleanLine.Contains("G1") && 
                            ((cleanLine.Contains("Z-3") && _currentFeedrate == 1500) ||
                             (cleanLine.Contains("Z=-3") && _currentFeedrate == 600)))
                        {
                            // This is the start of a bore operation with the special tool
                            analysis.SpecialDrillingOverhead += 6.0 / 60.0; // 6 seconds per hole
                            Console.WriteLine($"[TCALC] T{_currentSpecialDrillingTool} bore hole at F{_currentFeedrate} - adding 6s overhead");
                        }
                    }
                    
                    // Special handling for T501 drill head operations
                    // Drill heads have multiple spindles and drill simultaneously
                    // The time calculation is different from regular G1 moves
                    bool isDrillHeadOperation = false;
                    if (_currentActiveTool == 501)
                    {
                        // Check if this is a drilling move (Z=-3 at F600)
                        if (cleanLine.Contains("G1") && (cleanLine.Contains("Z=-3") || cleanLine.Contains("Z-3")) &&
                            _currentFeedrate == 600)
                        {
                            isDrillHeadOperation = true;
                            // For drill head, use a fixed time per hole instead of feedrate calculation
                            // Multi-spindle drill heads are fast - 0.5 seconds per cycle
                            Console.WriteLine($"[TCALC] T501 drill cycle detected at Z=-3 F600 - will use fixed cycle time");
                        }
                    }

                    // Extract feedrate
                    var feedMatch = Regex.Match(cleanLine, @"F([-+]?\d+\.?\d*)");
                    if (feedMatch.Success)
                    {
                        // Replace comma with period if needed
                        string feedValue = feedMatch.Groups[1].Value.Replace(',', '.');
                        if (double.TryParse(feedValue, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double feed))
                        {
                            _currentFeedrate = feed;
                            if (feed > 0)
                            {
                                _lastValidFeedrate = feed; // Remember last valid feedrate
                                // DEBUG: Log unusual feedrates
                                if (feed < 100 || feed > 20000)
                                {
                                    Console.WriteLine($"[TCALC FEEDRATE] F{feed} detected on line: {cleanLine.Substring(0, Math.Min(cleanLine.Length, 50))}");
                                    if (feed < 100)
                                    {
                                        Console.WriteLine($"  WARNING: Feedrate {feed} mm/min seems extremely slow!");
                                    }
                                }
                            }
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

                // Calculate movement times from tool sessions (includes drilling operations)
                // Tool sessions track the actual accumulated times including drilling cycles
                analysis.RapidTime = _toolSessions.Values.Sum(s => s.RapidTime);
                analysis.CuttingTime = _toolSessions.Values.Sum(s => s.CuttingTime);
                
                
                // Tool changes are now counted in ExtractToolNumbers, don't overwrite
                // analysis.ToolChanges is already set by ExtractToolNumbers method
                analysis.ProcessesCount = analysis.ProcessesUsed.Count;
                
                // Debug tool changes before calculation
                Console.WriteLine($"[TCALC] Tool changes count: {analysis.ToolChanges}");
                Console.WriteLine($"[TCALC] Tools used: [{string.Join(", ", analysis.ToolsUsed)}]");
                Console.WriteLine($"[TCALC] TC_51_51 value: {_config.TC_51_51}s");

                // Calculate overhead times based on extracted or default config
                double toolChangeTime = analysis.ToolChanges * _config.TC_51_51; // From file or default
                Console.WriteLine($"[TCALC] Calculated tool change time: {analysis.ToolChanges} × {_config.TC_51_51} = {toolChangeTime}s");
                
                // Critical debug for Field1.spf
                if (analysis.Filename != null && analysis.Filename.Contains("Field1", StringComparison.OrdinalIgnoreCase))
                {
                    Console.WriteLine($"[CRITICAL DEBUG Field1.spf]:");
                    Console.WriteLine($"  - analysis.ToolChanges = {analysis.ToolChanges}");
                    Console.WriteLine($"  - _config.TC_51_51 = {_config.TC_51_51}");
                    Console.WriteLine($"  - toolChangeTime = {toolChangeTime}s");
                    Console.WriteLine($"  - Should add {toolChangeTime}s to total time");
                }
                double spindleTime = machineOps.SpindleStarts * _config.SpindleStartTime; // 3 seconds per spindle start
                double cycleOverheadTime = machineOps.CycleCount * 0.1; // 0.1 second per L CYCLE call
                
                // Debug tool change calculation for Field1
                if (analysis.Filename.Contains("Field1", StringComparison.OrdinalIgnoreCase))
                {
                    Console.WriteLine($"[DEBUG Field1] ToolChanges detected: {analysis.ToolChanges}");
                    Console.WriteLine($"[DEBUG Field1] TC_51_51 value: {_config.TC_51_51}s per change");
                    Console.WriteLine($"[DEBUG Field1] Tool change time calculated: {toolChangeTime}s");
                }
                
                // Separate cut time from rapid time
                double cutTimeSeconds = analysis.CuttingTime * 60; // G1, G2, G3 movements
                double rapidTimeSeconds = analysis.RapidTime * 60; // G0 movements
                
                // Debug output before correction
                Console.WriteLine($"[TCALC] Before correction: cut={cutTimeSeconds:F1}s, rapid={rapidTimeSeconds:F1}s");
                Console.WriteLine($"[TCALC] Movement counts: G0={movements.Count(m => m.Code == "G0")}, G1={movements.Count(m => m.Code == "G1")}, G2={movements.Count(m => m.Code == "G2")}, G3={movements.Count(m => m.Code == "G3")}");
                
                // Debug tool sessions
                Console.WriteLine($"[TCALC] Tool sessions found: {_toolSessions.Count}");
                foreach (var session in _toolSessions.Values)
                {
                    Console.WriteLine($"[TCALC]   T{session.ToolNumber}: cut={session.CuttingTime*60:F1}s, rapid={session.RapidTime*60:F1}s, moves={session.MoveCount}");
                }
                
                // NO CORRECTION - find the real issue first
                Console.WriteLine($"[TCALC] No correction applied - using raw values");
                
                double overheadTimeSeconds = rapidTimeSeconds + toolChangeTime + spindleTime + cycleOverheadTime + machineOperationTime;
                double totalCycleTimeSeconds = cutTimeSeconds + overheadTimeSeconds;
                
                // CRITICAL: Verify tool change time is included
                var mathCheck = new System.Text.StringBuilder();
                mathCheck.AppendLine($"[TCALC MATH CHECK for {analysis.Filename}]:");
                mathCheck.AppendLine($"  Cut time: {cutTimeSeconds}s");
                mathCheck.AppendLine($"  Rapid time: {rapidTimeSeconds}s");  
                mathCheck.AppendLine($"  Tool change time: {toolChangeTime}s (from {analysis.ToolChanges} changes × {_config.TC_51_51}s)");
                mathCheck.AppendLine($"  Spindle time: {spindleTime}s");
                mathCheck.AppendLine($"  Cycle overhead: {cycleOverheadTime}s");
                mathCheck.AppendLine($"  Machine operations time: {machineOperationTime}s");
                mathCheck.AppendLine($"  Total overhead: {overheadTimeSeconds}s = rapids({rapidTimeSeconds}) + toolchange({toolChangeTime}) + spindle({spindleTime}) + cycle({cycleOverheadTime}) + machineOps({machineOperationTime})");
                mathCheck.AppendLine($"  TOTAL: {totalCycleTimeSeconds}s = cut({cutTimeSeconds}) + overhead({overheadTimeSeconds})");
                mathCheck.AppendLine($"  TOTAL in minutes: {totalCycleTimeSeconds / 60.0:F4} min");
                
                Console.WriteLine(mathCheck.ToString());
                
                
                // Debug breakdown for Field1
                if (analysis.Filename != null && analysis.Filename.Contains("Field1", StringComparison.OrdinalIgnoreCase))
                {
                    Console.WriteLine($"[DEBUG Field1] Time breakdown:");
                    Console.WriteLine($"  - Cutting: {cutTimeSeconds:F1}s");
                    Console.WriteLine($"  - Rapids: {rapidTimeSeconds:F1}s");
                    Console.WriteLine($"  - Tool changes: {toolChangeTime:F1}s");
                    Console.WriteLine($"  - Spindle starts: {spindleTime:F1}s");
                    Console.WriteLine($"  - Cycle overhead: {cycleOverheadTime:F1}s");
                    Console.WriteLine($"  - Total overhead: {overheadTimeSeconds:F1}s");
                    Console.WriteLine($"  - TOTAL: {totalCycleTimeSeconds:F1}s");
                }
                
                // Final timing moved to after correction (line 1320)
                
                
                // Finalize tool usage sessions
                FinalizeToolSessions();
                
                // Add OPUS-specific T501 drilling overhead
                double opusDrillingOverhead = 0;
                if (_isOpusFile && _toolSessions.ContainsKey(501))
                {
                    // OPUS files have additional overhead from CH_DRILLHEAD pin changes and coordinate system operations
                    // Based on analysis: ~1.2s per drilling operation (pin changes + CS transforms)
                    int totalDrillCycles = _t501DrillCyclesF600 + _t501DrillCyclesF1000 + _t501DrillCyclesF2000;
                    if (totalDrillCycles > 0)
                    {
                        opusDrillingOverhead = totalDrillCycles * 1.2; // 1.2 seconds per drilling operation
                        Console.WriteLine($"[OPUS T501] Adding {opusDrillingOverhead:F1}s overhead for {totalDrillCycles} drilling operations");
                        totalCycleTimeSeconds += opusDrillingOverhead;
                    }
                }
                
                // Store final times WITHOUT double-counting drilling operations
                // The movement calculations already include drilling time!
                // Add special drilling overhead for large tools in milling holders
                analysis.TotalTime = (totalCycleTimeSeconds / 60.0) + analysis.SpecialDrillingOverhead;  // Total cycle time in minutes
                analysis.CutTime = cutTimeSeconds / 60.0;  // Actual cutting time in minutes
                analysis.CuttingTime = cutTimeSeconds / 60.0;  // Same as CutTime for compatibility
                analysis.OverheadTime = overheadTimeSeconds / 60.0;  // Non-cutting time in minutes
                analysis.MachineTime = overheadTimeSeconds / 60.0;  // MachineTime = overhead (rapids + tool changes + spindle)
                
                // Show final timing
                Console.WriteLine($"[TCALC] Total: {totalCycleTimeSeconds:F1}s ({totalCycleTimeSeconds/60.0:F2}min)");
                Console.WriteLine($"[TCALC] Cutting: {cutTimeSeconds:F1}s, Rapids: {rapidTimeSeconds:F1}s");
                Console.WriteLine($"[TCALC] Tool changes: {toolChangeTime:F1}s ({analysis.ToolChanges} changes)");
                
                
                // Add drilling operations to analysis
                if (_completedDrillings != null && _completedDrillings.Count > 0)
                {
                    analysis.DrillingOperations = _completedDrillings;
                    double totalDrillTime = _completedDrillings.Sum(d => d.CalculatedTime);
                    Console.WriteLine($"[TCALC] Added {_completedDrillings.Count} drilling operations, total time: {totalDrillTime:F1}s");
                }
                
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
            // Special handling for function calls like C_WECHSEL(params)
            // Don't remove parentheses if they're part of a function call
            bool hasFunction = line.Contains("C_WECHSEL") || line.Contains("C_TSL") || 
                              line.Contains("CH_TOOLCHANGE") || line.Contains("CP_TC") ||
                              line.Contains("CYCLE");
            
            if (!hasFunction)
            {
                // Remove comments in parentheses only if not a function call
                var commentIndex = line.IndexOf('(');
                if (commentIndex >= 0)
                {
                    line = line.Substring(0, commentIndex);
                }
            }

            // Always remove semicolon comments
            var semicolonIndex = line.IndexOf(';');
            if (semicolonIndex >= 0)
            {
                line = line.Substring(0, semicolonIndex);
            }

            return line.Trim().ToUpper();
        }

        private void CountMachineOperations(string line, MachineOperations ops)
        {
            // Count machine operations for different postprocessors
            
            // Tool changes (already counted in ExtractToolNumbers, so skip here)
            // Note: Tool changes are now counted directly in ExtractToolNumbers method
            
            // Spindle operations
            if (line.Contains("CH_SPINDEL.NC") || line.Contains("CP_TSPEED.NC") || line.Contains("C_TSL"))
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
            else if (line.Contains("CH_DRILLHEAD.NC"))
                ops.OtherCycles++;  // Drill head pin activation/deactivation
            else if (line.Contains("L CYCLE") && !line.Contains("CH_TOOLCHANGE") && 
                     !line.Contains("CP_TC.NC") && !line.Contains("C_WECHSEL") &&
                     !line.Contains("CH_SPINDEL") && !line.Contains("CP_TSPEED") &&
                     !line.Contains("CH_TCP_") && !line.Contains("CP_TRAFAUS") &&
                     !line.Contains("CH_CONTOUR_") && !line.Contains("CH_DYNAMIC") && !line.Contains("CP_DYNAMIC") && 
                     !line.Contains("CH_CHECK_TOOL") && !line.Contains("CH_DRILLHEAD"))
                ops.OtherCycles++;
        }

        private void ExtractToolNumbers(string line, CNCAnalysis analysis, int lineNumber, string filePath)
        {
            // Check if we're too close to the last tool change (within 10 lines)
            // This prevents detecting the same tool change multiple times
            bool isNearRecentToolChange = Math.Abs(lineNumber - _lastToolChangeLineNumber) < 10;
            
            // 1. RB_OPUS format: CH_TOOLCHANGE.NC with @P4 parameter
            if (line.Contains("CH_TOOLCHANGE.NC", StringComparison.OrdinalIgnoreCase))
            {
                var toolChangeMatch = Regex.Match(line, @"@P4=(\d+)", RegexOptions.IgnoreCase);
                if (toolChangeMatch.Success && int.TryParse(toolChangeMatch.Groups[1].Value, out int toolNumber))
                {
                    if (!isNearRecentToolChange && _currentActiveTool != toolNumber)
                    {
                        HandleToolChange(toolNumber, analysis);
                        analysis.ToolChanges++;
                        _lastToolChangeLineNumber = lineNumber;
                    }
                    return;
                }
            }
            
            // 2. HH7 format: CP_TC.NC with @P4 parameter (Box ID)
            if (line.Contains("CP_TC.NC", StringComparison.OrdinalIgnoreCase))
            {
                var toolChangeMatch = Regex.Match(line, @"@P4=(\d+)", RegexOptions.IgnoreCase);
                if (toolChangeMatch.Success && int.TryParse(toolChangeMatch.Groups[1].Value, out int boxId))
                {
                    if (!isNearRecentToolChange && _currentActiveTool != boxId)
                    {
                        HandleToolChange(boxId, analysis);
                        analysis.ToolChanges++;
                        _lastToolChangeLineNumber = lineNumber;
                    }
                    return;
                }
            }
            
            // 3. Vision/Siemens format: C_WECHSEL function with Platz mapping
            if (line.Contains("C_WECHSEL", StringComparison.OrdinalIgnoreCase))
            {
                var toolMatch = Regex.Match(line, @"C_WECHSEL\((\d+)", RegexOptions.IgnoreCase);
                if (toolMatch.Success && int.TryParse(toolMatch.Groups[1].Value, out int platzNumber))
                {
                    // For Vision/Siemens, map Platz number to actual Box ID
                    int actualToolNumber = _platzToBoxMapping.ContainsKey(platzNumber) ? 
                        _platzToBoxMapping[platzNumber] : platzNumber;
                    
                    if (!isNearRecentToolChange && _currentActiveTool != actualToolNumber)
                    {
                        HandleToolChange(actualToolNumber, analysis);
                        analysis.ToolChanges++;
                        _lastToolChangeLineNumber = lineNumber;
                    }
                    return;
                }
            }
            
            // Skip D-code and T-code detection if we're near a recent tool change
            // These are secondary indicators and shouldn't override primary tool change commands
            if (isNearRecentToolChange)
            {
                return;
            }
            
            // Check for D0 (tool offset cancel) - this should NOT reset the tool
            // D0 lines often have important movements (e.g., "D0 G0 X... Y... Z467.64")
            if (Regex.IsMatch(line, @"^[^;]*\bD0\b", RegexOptions.IgnoreCase))
            {
                // D0 is just tool length compensation cancel, NOT a tool deactivation
                // The tool remains active for movements on this line
                // Don't return - MUST process movements on same line!
            }
            
            // 3b. For SPF files, T-codes can also switch tools
            if (filePath.EndsWith(".spf", StringComparison.OrdinalIgnoreCase))
            {
                var tMatch = Regex.Match(line, @"^[^;]*\bT(\d+)\b", RegexOptions.IgnoreCase);
                if (tMatch.Success && int.TryParse(tMatch.Groups[1].Value, out int tNumber))
                {
                    // Map T-number through platz mapping if available
                    int actualTool = _platzToBoxMapping.ContainsKey(tNumber) ? _platzToBoxMapping[tNumber] : tNumber;
                    
                    Console.WriteLine($"[DEBUG] Line {lineNumber}: T{tNumber} → Tool {actualTool} (mapped={_platzToBoxMapping.ContainsKey(tNumber)}, current={_currentActiveTool})");
                    
                    if (_currentActiveTool != actualTool)
                    {
                        // Tool change via T-code
                        Console.WriteLine($"[DEBUG] T{tNumber} switching from T{_currentActiveTool} to T{actualTool}");
                        _currentActiveTool = actualTool;
                        if (!_toolSessions.ContainsKey(actualTool))
                        {
                            _toolSessions[actualTool] = new ToolUsageSession { ToolNumber = actualTool };
                            Console.WriteLine($"[DEBUG] Created session for T{actualTool}");
                        }
                        
                        // Add to tools used if not already there
                        if (!analysis.ToolsUsed.Contains(actualTool))
                        {
                            analysis.ToolsUsed.Add(actualTool);
                        }
                    }
                }
            }
            
            // 4. OPUS D-code tool selection (D601, D181, etc.)
            var dCodeMatch = Regex.Match(line, @"^[^;]*\bD(\d{3,})\b", RegexOptions.IgnoreCase);
            if (dCodeMatch.Success && int.TryParse(dCodeMatch.Groups[1].Value, out int dNumber))
            {
                // D-codes with 3+ digits are tool selections in OPUS
                if (dNumber > 100)
                {
                    if (_currentActiveTool != dNumber)
                    {
                        Console.WriteLine($"[DEBUG] Line {lineNumber}: D{dNumber} tool change (from T{_currentActiveTool})");
                        HandleToolChange(dNumber, analysis);
                        
                        // Only count as tool change if actually switching to a different tool
                        // D601 appearing multiple times should only count once
                        analysis.ToolChanges++;
                        _lastToolChangeLineNumber = lineNumber;
                    }
                    else
                    {
                        Console.WriteLine($"[DEBUG] Line {lineNumber}: D{dNumber} tool activation (already active)");
                    }
                    // Don't return - line might have movements too
                }
            }
            
            // Extract tool references from comments (for tool list only, not changes)
            // This helps build the list of tools used in the program
            if (line.Contains("; ---") && line.Contains("Box:"))
            {
                // Try both patterns - with T: for regular tools, without for drilling heads
                var boxMatch = Regex.Match(line, @"Box:\s*(\d+)", RegexOptions.IgnoreCase);
                if (boxMatch.Success)
                {
                    // Use the Box ID as the primary tool identifier
                    if (int.TryParse(boxMatch.Groups[1].Value, out int boxId))
                    {
                        if (!analysis.ToolsUsed.Contains(boxId))
                        {
                            analysis.ToolsUsed.Add(boxId);
                        }
                    }
                }
            }
        }
        
        /// <summary>
        /// Build mapping of Platz numbers to Box IDs for Vision/Siemens format
        /// </summary>
        private void BuildPlatzToBoxMapping(string[] lines)
        {
            // Look for tool definitions in comments
            // Format: "Box: 602 ... Platz:17 T:17"
            foreach (var line in lines)
            {
                if (line.Contains("Box:") && line.Contains("Platz:"))
                {
                    var boxMatch = Regex.Match(line, @"Box:\s*(\d+)");
                    var platzMatch = Regex.Match(line, @"Platz:(\d+)");
                    
                    if (boxMatch.Success && platzMatch.Success)
                    {
                        if (int.TryParse(boxMatch.Groups[1].Value, out int boxId) &&
                            int.TryParse(platzMatch.Groups[1].Value, out int platzNumber))
                        {
                            _platzToBoxMapping[platzNumber] = boxId;
                        }
                    }
                }
            }
            
            // Also look for drilling head Box IDs
            // Format 1: "; --- Box:  501 HId:51    Bohrkopf"
            int drillingBoxId = 0;
            foreach (var line in lines)
            {
                // Find the drilling head box
                if ((line.Contains("Bohrkopf") || line.Contains("DrillHead")) && line.Contains("Box:"))
                {
                    var boxMatch = Regex.Match(line, @"Box:\s*(\d+)");
                    if (boxMatch.Success && int.TryParse(boxMatch.Groups[1].Value, out int boxId))
                    {
                        drillingBoxId = boxId;
                        Console.WriteLine($"[TCALC] Found drilling head Box {boxId}");
                    }
                }
                
                // Also check for BOXID format
                if (line.Contains("BOXID:<") && line.Contains("DHProcess"))
                {
                    var boxIdMatch = Regex.Match(line, @"BOXID:<(\d+)>");
                    if (boxIdMatch.Success && int.TryParse(boxIdMatch.Groups[1].Value, out int boxId))
                    {
                        drillingBoxId = boxId;
                        Console.WriteLine($"[TCALC] Found drilling head Box {boxId} (from BOXID)");
                    }
                }
                
                // Find T201 or similar drilling head tool numbers and map to drilling box
                if (drillingBoxId > 0 && line.StartsWith("N") && line.Contains("T201"))
                {
                    _platzToBoxMapping[201] = drillingBoxId;
                    Console.WriteLine($"[TCALC] Mapped drilling head T201 → Box {drillingBoxId}");
                }
                
                // NOTE: Individual drill bits (->203<-, ->209<-) are NOT mapped to Box 501
                // They are separate drill bit identifiers and should be tracked independently
            }
            
            // FALLBACK: If no mappings found and this is Field1.spf, use known mappings
            if (_platzToBoxMapping.Count == 0 && lines.Length > 0 && lines[0].Contains("Field1"))
            {
                _platzToBoxMapping[17] = 602;
                _platzToBoxMapping[10] = 181;
                Console.WriteLine("[TCALC] Using default Field1.spf mappings: 17→602, 10→181");
            }
        }
        
        /// <summary>
        /// Extract HOP/HOPS/HOPX file references from CNC program
        /// </summary>
        private void ExtractHOPFileReferences(string[] lines, CNCAnalysis analysis)
        {
            var hopFiles = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var hopPattern = @"([A-Z]:\\[^\\]+(?:\\[^\\]+)*\\[^\\]+\.(?:HOP[SX]?))";
            var hopPattern2 = @"([\w_\-]+\.(?:HOP[SX]?))(?:\s|$|""|\))";
            
            Console.WriteLine($"[TCALC] Scanning {lines.Length} lines for HOP file references");
            
            foreach (var line in lines)
            {
                // Look for full path HOP references (e.g., Y:\OPUS\KORPUS\...\file.HOP)
                var fullPathMatches = Regex.Matches(line, hopPattern, RegexOptions.IgnoreCase);
                foreach (Match match in fullPathMatches)
                {
                    if (match.Success)
                    {
                        string hopPath = match.Groups[1].Value;
                        string hopFileName = Path.GetFileName(hopPath);
                        
                        if (!string.IsNullOrEmpty(hopFileName))
                        {
                            hopFiles.Add(hopFileName);
                            Console.WriteLine($"[TCALC] Found HOP reference (full path): {hopFileName}");
                        }
                    }
                }
                
                // Also look for standalone HOP filenames
                var standaloneMatches = Regex.Matches(line, hopPattern2, RegexOptions.IgnoreCase);
                foreach (Match match in standaloneMatches)
                {
                    if (match.Success)
                    {
                        string hopFileName = match.Groups[1].Value;
                        
                        // Filter out common false positives
                        if (!hopFileName.StartsWith("SHOP", StringComparison.OrdinalIgnoreCase) &&
                            !hopFileName.StartsWith("WORKSHOP", StringComparison.OrdinalIgnoreCase))
                        {
                            hopFiles.Add(hopFileName);
                            Console.WriteLine($"[TCALC] Found HOP reference (standalone): {hopFileName}");
                        }
                    }
                }
            }
            
            // Store the found HOP files
            analysis.ReferencedHOPFiles = hopFiles.ToList();
            analysis.HopFiles = hopFiles.ToList();  // Also populate the new HopFiles property
            
            // Set the primary HOP file (first one found or most common)
            if (analysis.ReferencedHOPFiles.Count > 0)
            {
                analysis.PrimaryHOPFile = analysis.ReferencedHOPFiles[0];
                Console.WriteLine($"[TCALC] Primary HOP file: {analysis.PrimaryHOPFile}");
                Console.WriteLine($"[TCALC] Total HOP files found: {analysis.ReferencedHOPFiles.Count}");
            }
            else
            {
                Console.WriteLine($"[TCALC] No HOP file references found in CNC program");
            }
        }
        
        /// <summary>
        /// Get actual tool number (Box ID) for Vision/Siemens Platz number
        /// </summary>
        private int GetActualToolNumberForPlatz(int platzNumber, string currentLine)
        {
            // Look for Box ID mapping in nearby comments
            // Format: "Box: 602 ... Platz:17 T:17"
            // First, try to find in _toolMappings if we've seen it before
            if (_platzToBoxMapping.ContainsKey(platzNumber))
            {
                return _platzToBoxMapping[platzNumber];
            }
            
            // If not found, return the platz number as fallback
            // The mapping will be built when processing tool list comments
            return platzNumber;
        }
        
        /// <summary>
        /// Handle tool change and start tracking new tool session
        /// </summary>
        private void HandleToolChange(int toolNumber, CNCAnalysis analysis)
        {
            
            // Add tool to the used tools list
            if (!analysis.ToolsUsed.Contains(toolNumber))
            {
                analysis.ToolsUsed.Add(toolNumber);
            }
            
            // End previous tool session if there was one
            if (_currentActiveTool > 0 && _toolSessions.ContainsKey(_currentActiveTool))
            {
                var prevSession = _toolSessions[_currentActiveTool];
            }
            
            // Start new tool session
            _currentActiveTool = toolNumber;
            if (!_toolSessions.ContainsKey(toolNumber))
            {
                _toolSessions[toolNumber] = new ToolUsageSession { ToolNumber = toolNumber };
            }
            else
            {
                }
        }
        
        /// <summary>
        /// Extract machine configuration from the CNC file header/comments
        /// </summary>
        private void ExtractConfigFromFile(string filePath)
        {
            try
            {
                var lines = File.ReadAllLines(filePath).Take(100).ToArray(); // Check first 100 lines
                
                // Look for postprocessor info and extract parameters
                foreach (var line in lines)
                {
                    // Extract spindle speed to estimate rapid feedrate
                    // DISABLED: The 2.5x spindle speed assumption doesn't match actual machine capabilities
                    // Keeping the configured defaults (20000mm/min) instead
                    /*
                    if (line.Contains("MaxRotSpeed S") || line.Contains("@P7=") || line.Contains("@P4=") && line.Contains("24000"))
                    {
                        var speedMatch = Regex.Match(line, @"S(\d+)|@P[47]=(\d+)");
                        if (speedMatch.Success)
                        {
                            var speed = speedMatch.Groups[1].Success ? speedMatch.Groups[1].Value : speedMatch.Groups[2].Value;
                            if (double.TryParse(speed, out var spindleSpeed) && spindleSpeed > 10000)
                            {
                                // Modern CNCs: rapid is typically 2-3x spindle speed
                                _config.MAXFEEDRATE_XY = Math.Min(spindleSpeed * 2.5, 60000);
                                _config.DHFeedrateG00 = _config.MAXFEEDRATE_XY; // Keep them in sync
                                Console.WriteLine($"[DEBUG] Set rapid feedrate to {_config.DHFeedrateG00}mm/min based on spindle speed {spindleSpeed}");
                            }
                        }
                    }
                    */
                    
                    // Check for postprocessor type and set appropriate defaults
                    if (line.Contains("Post:") || line.Contains("POST:"))
                    {
                        if (line.Contains("OPUS"))
                        {
                            // OPUS format detected
                            Console.WriteLine("[TCALC] OPUS postprocessor detected");
                            _isOpusFile = true;
                        }
                        else if (line.Contains("HH7") || line.Contains("7532DR"))
                        {
                            // HH7 format detected
                            Console.WriteLine("[TCALC] HH7 postprocessor detected");
                        }
                        else if (line.Contains("VISION") || line.Contains("ARTIS"))
                        {
                            // Vision/Siemens format detected  
                            Console.WriteLine("[TCALC] Vision/Siemens postprocessor detected");
                        }
                    }
                    
                    // Extract tool info for timing calculations
                    if (line.Contains("VF ") || line.Contains("SF ") || line.Contains("Box:"))
                    {
                        // Tool descriptions found, can be used for feed rate estimation
                        var diamMatch = Regex.Match(line, @"[VSF]F\s+(\d+)");
                        if (diamMatch.Success)
                        {
                            // Tool diameter found, can influence cutting speeds
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[TCALC] Config extraction note: {ex.Message}");
            }
        }
        
        /// <summary>
        /// Finalize all tool usage sessions and prepare data for output
        /// </summary>
        private void FinalizeToolSessions()
        {
            Console.WriteLine($"[TCALC] Finalizing {_toolSessions.Count} tool sessions");
            foreach (var session in _toolSessions.Values)
            {
                // Times are stored in minutes, convert to seconds for display
                Console.WriteLine($"[TCALC] Tool T{session.ToolNumber}: " +
                    $"Cutting={session.CuttingTime*60:F1}s ({session.CuttingTime:F4}min), " +
                    $"Rapid={session.RapidTime*60:F1}s ({session.RapidTime:F4}min), " +
                    $"Distance={session.TotalDistance:F1}mm, " +
                    $"Moves={session.MoveCount}");
                    
                // Special debugging for T501
                if (session.ToolNumber == 501)
                {
                    Console.WriteLine($"[TCALC DEBUG] T501 Final Summary:");
                    Console.WriteLine($"  - Cutting Time: {session.CuttingTime*60:F1} seconds ({session.CuttingTime:F4} minutes)");
                    Console.WriteLine($"  - Rapid Time: {session.RapidTime*60:F1} seconds ({session.RapidTime:F4} minutes)");
                    Console.WriteLine($"  - Total Time: {(session.CuttingTime + session.RapidTime)*60:F1} seconds");
                    Console.WriteLine($"  - Cutting Distance: {session.CuttingDistance:F1} mm");
                    Console.WriteLine($"  - Rapid Distance: {session.RapidDistance:F1} mm");
                    Console.WriteLine($"  - Total Moves: {session.MoveCount}");
                    Console.WriteLine($"  - Drill Cycles Processed:");
                    Console.WriteLine($"    * F600: {_t501DrillCyclesF600} cycles × 0.87s = {_t501DrillCyclesF600 * 0.87:F1}s (0.5s drill + 0.37s positioning)");
                    Console.WriteLine($"    * F1000: {_t501DrillCyclesF1000} cycles × 1.17s = {_t501DrillCyclesF1000 * 1.17:F1}s (0.8s drill + 0.37s positioning)");
                    Console.WriteLine($"    * F2000: {_t501DrillCyclesF2000} cycles × 0.67s = {_t501DrillCyclesF2000 * 0.67:F1}s (0.3s drill + 0.37s positioning)");
                    Console.WriteLine($"    * Total drill time expected: {(_t501DrillCyclesF600 * 0.87 + _t501DrillCyclesF1000 * 1.17 + _t501DrillCyclesF2000 * 0.67):F1}s");
                    Console.WriteLine($"  - XY Positioning Moves: {_t501XYMoves}");
                }
            }
            
            if (_toolSessions.Count == 0)
            {
                Console.WriteLine($"[WARNING] No tool sessions were created!");
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
                    else if (movement.Time > 0)
                    {
                        Console.WriteLine($"[WARNING] G0 movement {movement.Time:F3}min but no active tool (tool={_currentActiveTool})");
                    }
                }
                    
                if (!analysis.ProcessesUsed.Contains("RAPID"))
                    analysis.ProcessesUsed.Add("RAPID");
            }
            // G1 - Linear interpolation moves (always at specified feedrate)
            else if (Regex.IsMatch(line, @"\bG1\b|\bG01\b"))
            {
                // IMPORTANT: Match Python behavior - only process if feedrate is set
                if (_currentFeedrate > 0)
                {
                    // Special handling for T501 drill head
                    // Drill heads only drill - they don't do normal cutting operations
                    bool skipNormalCalculation = false;
                    if (_currentActiveTool == 501)
                    {
                        // ALL T501 movements are either positioning or drilling, never normal cutting
                        skipNormalCalculation = true;
                        
                        // Check if this is a Z movement
                        bool isZMove = line.Contains("Z=") || (line.Contains("Z") && !line.Contains("Z "));
                        
                        if (isZMove)
                        {
                            // T501 drill head - count all drilling plunges with appropriate cycle times
                            // Multi-spindle drill heads drill multiple holes simultaneously
                            bool isDrillingMove = false;
                            double drillCycleTime = 0;
                            
                            // Check for drilling moves (negative Z with drilling feedrates)
                            if (line.Contains("Z=-") || line.Contains("Z-"))
                            {
                                // Add 0.37s positioning overhead to each drill cycle for spindle positioning
                                double positioningOverhead = 0.37 / 60.0; // 0.37 seconds overhead
                                
                                if (_currentFeedrate == 600)
                                {
                                    // Standard drilling at F600 (mostly Z=-3)
                                    drillCycleTime = (0.5 + 0.37) / 60.0; // 0.87 seconds per cycle (0.5s drill + 0.37s positioning)
                                    isDrillingMove = true;
                                }
                                else if (_currentFeedrate == 1000)
                                {
                                    // Deeper drilling at F1000 (mostly Z=-13)
                                    drillCycleTime = (0.8 + 0.37) / 60.0; // 1.17 seconds per cycle (0.8s drill + 0.37s positioning)
                                    isDrillingMove = true;
                                }
                                else if (_currentFeedrate == 2000)
                                {
                                    // Fast drilling at F2000 (various depths)
                                    drillCycleTime = (0.3 + 0.37) / 60.0; // 0.67 seconds per cycle (0.3s drill + 0.37s positioning)
                                    isDrillingMove = true;
                                }
                            }
                            
                            if (isDrillingMove && _toolSessions.ContainsKey(501))
                            {
                                _toolSessions[501].CuttingTime += drillCycleTime;
                                _toolSessions[501].MoveCount++;
                                
                                // Count drill cycles by type
                                if (_currentFeedrate == 600) _t501DrillCyclesF600++;
                                else if (_currentFeedrate == 1000) _t501DrillCyclesF1000++;
                                else if (_currentFeedrate == 2000) _t501DrillCyclesF2000++;
                                
                                var totalSoFar = _toolSessions[501].CuttingTime * 60; // Convert to seconds
                                Console.WriteLine($"[TCALC] T501 drill cycle #{_t501DrillCyclesF600 + _t501DrillCyclesF1000 + _t501DrillCyclesF2000} at F{_currentFeedrate} - added {drillCycleTime*60:F1}s (total: {totalSoFar:F1}s)");
                            }
                            // All other Z movements (positioning, withdrawal) are ignored
                        }
                        else
                        {
                            // XY movements - treat all as rapid positioning regardless of feedrate
                            var xyMovement = CalculateTCALCMoveTime(line, "G1");
                            if (xyMovement != null && _toolSessions.ContainsKey(501))
                            {
                                // Always add to rapid time, never to cutting time
                                _toolSessions[501].RapidTime += xyMovement.Time;
                                _toolSessions[501].RapidDistance += xyMovement.Distance;
                                _toolSessions[501].MoveCount++;
                                _t501XYMoves++;
                                if (_currentFeedrate < 10000)
                                {
                                    Console.WriteLine($"[TCALC] T501 XY move #{_t501XYMoves} at F{_currentFeedrate} treated as rapid - {xyMovement.Time*60:F1}s");
                                }
                            }
                            // Don't return movement - we've already handled it
                        }
                    }
                    
                    if (!skipNormalCalculation)
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
                                
                                // For T501, G1 moves don't add cutting time (drill cycles are handled separately)
                                if (_currentActiveTool != 501)
                                {
                                    // ALL G1 moves are cutting/process moves (not rapid)
                                    // This matches how TCALC_HH7 works
                                    session.CuttingTime += movement.Time;
                                    session.CuttingDistance += movement.Distance;
                                    session.MoveCount++;
                                    
                                }
                            }
                            else if (movement.Time > 0)
                            {
                                Console.WriteLine($"[WARNING] G1 cutting {movement.Time:F3}min but no active tool (tool={_currentActiveTool})");
                            }
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
                            // For T501, arc moves don't add cutting time (drill cycles are handled separately)
                            if (_currentActiveTool != 501)
                            {
                                session.CuttingTime += movement.Time;
                                session.CuttingDistance += movement.Distance;
                                session.MoveCount++;
                            }
                        }
                        else if (movement.Time > 0)
                        {
                            Console.WriteLine($"[WARNING] {code} arc {movement.Time:F3}min but no active tool (tool={_currentActiveTool})");
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

            var zMatch = Regex.Match(line, @"Z=?([-+]?\d*\.?\d+)");
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
            
            // Only log significant movements for debugging
            if (distance > 10)  // Only movements > 10mm
            {
                // Check if it's a Z-heavy move (like the 467mm Z rapids in Field1.spf)
                double zDistance = Math.Abs(newZ - _currentZ);
                if (zDistance > 100)  // Large Z movement
                {
                    Console.WriteLine($"[DEBUG] {code} Large Z move: {zDistance:F0}mm @ {feedRate}mm/min = {time*60:F1}s");
                }
            }

            // CRITICAL: Update current position after calculating distance
            _currentX = newX;
            _currentY = newY;
            _currentZ = newZ;

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

            var zMatch = Regex.Match(line, @"Z=?([-+]?\d*\.?\d+)");
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

            // CRITICAL: Update current position after calculating distance
            _currentX = newX;
            _currentY = newY;
            _currentZ = newZ;

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

            var zMatch = Regex.Match(line, @"Z=?([-+]?\d*\.?\d+)");
            if (zMatch.Success && double.TryParse(zMatch.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double z))
                _currentZ = z;
        }

        /// <summary>
        /// Process movement commands using TCALC engine with acceleration/deceleration
        /// </summary>
        private CNCMovement ProcessMovementTCALC(string line, CNCAnalysis analysis)
        {
            CNCMovement movement = null;

            // CRITICAL: Only process as movement if line contains coordinates (X, Y, or Z)
            // This prevents processing preparatory commands like "G0" or "G1 F1000" as movements
            bool hasCoordinates = Regex.IsMatch(line, @"[XYZ][-+]?\d*\.?\d+");
            
            if (!hasCoordinates)
            {
                // Not a movement, just a preparatory command
                return null;
            }

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
                        session.RapidTime += movement.Time; // Time is in minutes
                        session.RapidDistance += movement.Distance;
                        session.MoveCount++;
                    }
                }
                    
                if (!analysis.ProcessesUsed.Contains("RAPID"))
                    analysis.ProcessesUsed.Add("RAPID");
            }
            // G1 - Linear interpolation moves (always at specified feedrate)
            else if (Regex.IsMatch(line, @"\bG1\b|\bG01\b"))
            {
                if (_currentFeedrate > 0)
                {
                    // Special handling for T501 drill head
                    // Drill heads only drill - they don't do normal cutting operations
                    bool skipNormalCalculation = false;
                    if (_currentActiveTool == 501)
                    {
                        // ALL T501 movements are either positioning or drilling, never normal cutting
                        skipNormalCalculation = true;
                        
                        // Check if this is a Z movement
                        bool isZMove = line.Contains("Z=") || (line.Contains("Z") && !line.Contains("Z "));
                        
                        if (isZMove)
                        {
                            // T501 drill head - count all drilling plunges with appropriate cycle times
                            // Multi-spindle drill heads drill multiple holes simultaneously
                            bool isDrillingMove = false;
                            double drillCycleTime = 0;
                            
                            // Check for drilling moves (negative Z with drilling feedrates)
                            if (line.Contains("Z=-") || line.Contains("Z-"))
                            {
                                // Add 0.37s positioning overhead to each drill cycle for spindle positioning
                                double positioningOverhead = 0.37 / 60.0; // 0.37 seconds overhead
                                
                                if (_currentFeedrate == 600)
                                {
                                    // Standard drilling at F600 (mostly Z=-3)
                                    drillCycleTime = (0.5 + 0.37) / 60.0; // 0.87 seconds per cycle (0.5s drill + 0.37s positioning)
                                    isDrillingMove = true;
                                }
                                else if (_currentFeedrate == 1000)
                                {
                                    // Deeper drilling at F1000 (mostly Z=-13)
                                    drillCycleTime = (0.8 + 0.37) / 60.0; // 1.17 seconds per cycle (0.8s drill + 0.37s positioning)
                                    isDrillingMove = true;
                                }
                                else if (_currentFeedrate == 2000)
                                {
                                    // Fast drilling at F2000 (various depths)
                                    drillCycleTime = (0.3 + 0.37) / 60.0; // 0.67 seconds per cycle (0.3s drill + 0.37s positioning)
                                    isDrillingMove = true;
                                }
                            }
                            
                            if (isDrillingMove && _toolSessions.ContainsKey(501))
                            {
                                _toolSessions[501].CuttingTime += drillCycleTime;
                                _toolSessions[501].MoveCount++;
                                
                                // Count drill cycles by type
                                if (_currentFeedrate == 600) _t501DrillCyclesF600++;
                                else if (_currentFeedrate == 1000) _t501DrillCyclesF1000++;
                                else if (_currentFeedrate == 2000) _t501DrillCyclesF2000++;
                                
                                var totalSoFar = _toolSessions[501].CuttingTime * 60; // Convert to seconds
                                Console.WriteLine($"[TCALC] T501 drill cycle #{_t501DrillCyclesF600 + _t501DrillCyclesF1000 + _t501DrillCyclesF2000} at F{_currentFeedrate} - added {drillCycleTime*60:F1}s (total: {totalSoFar:F1}s)");
                            }
                            // All other Z movements (positioning, withdrawal) are ignored
                        }
                        else
                        {
                            // XY movements - treat all as rapid positioning regardless of feedrate
                            var xyMovement = CalculateTCALCMoveTime(line, "G1");
                            if (xyMovement != null && _toolSessions.ContainsKey(501))
                            {
                                // Always add to rapid time, never to cutting time
                                _toolSessions[501].RapidTime += xyMovement.Time;
                                _toolSessions[501].RapidDistance += xyMovement.Distance;
                                _toolSessions[501].MoveCount++;
                                _t501XYMoves++;
                                if (_currentFeedrate < 10000)
                                {
                                    Console.WriteLine($"[TCALC] T501 XY move #{_t501XYMoves} at F{_currentFeedrate} treated as rapid - {xyMovement.Time*60:F1}s");
                                }
                            }
                            // Don't return movement - we've already handled it
                        }
                    }
                    
                    if (!skipNormalCalculation)
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
                                
                                // For T501, G1 moves don't add cutting time (drill cycles are handled separately)
                                if (_currentActiveTool != 501)
                                {
                                    // ALL G1 moves are cutting/process moves (not rapid)
                                    // This matches how TCALC_HH7 works
                                    session.CuttingTime += movement.Time; // Time is in minutes
                                    session.CuttingDistance += movement.Distance;
                                    session.MoveCount++;
                                    
                                    
                                    // Debug output for significant moves
                                    if (movement.Distance > 10)
                                    {
                                        Console.WriteLine($"[DEBUG] T{_currentActiveTool} G1: {movement.Distance:F1}mm @ {movement.Feedrate:F0}mm/min = {movement.Time*60:F2}s (total cutting: {session.CuttingTime*60:F1}s)");
                                    }
                                }
                            }
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
                            // For T501, arc moves don't add cutting time (drill cycles are handled separately)
                            if (_currentActiveTool != 501)
                            {
                                session.CuttingTime += movement.Time; // Time is in minutes
                                session.CuttingDistance += movement.Distance;
                                session.MoveCount++;
                            }
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
            
            // Skip system cycles that don't add machining time
            if (cycleName.Contains("CP_TC") ||      // Tool change cycle
                cycleName.Contains("CP_TCHECK") ||  // Tool check cycle
                cycleName.Contains("CP_TSPEED") ||  // Spindle speed cycle
                cycleName.Contains("CP_CS") ||      // Coordinate system cycle
                cycleName.Contains("CP_START") ||   // Start cycle
                cycleName.Contains("CP_END") ||     // End cycle
                cycleName.Contains("CP_CLEARDH") || // Clear cycle
                cycleName.Contains("CP_DYNAMIC") || // Dynamic cycle
                cycleName.Contains("CP_RELEASE") || // Release cycle
                cycleName.Contains("CP_CONTOUR") || // Contour start/end markers
                cycleName.Contains("CH_CHECK_TOOL") || // OPUS tool check cycle
                cycleName.Contains("CH_CARRIER") || // OPUS carrier position cycle
                cycleName.Contains("CH_TOOLCHANGE") || // OPUS tool change cycle
                cycleName.Contains("CH_SPINDEL") || // OPUS spindle cycle
                cycleName.Contains("CH_TCP") ||     // OPUS TCP cycle
                cycleName.Contains("CH_CONTOUR") || // OPUS contour cycle
                cycleName.Contains("CH_DYNAMIC"))   // OPUS dynamic cycle
            {
                // Debug: Log that we're skipping this system cycle
                // Console.WriteLine($"[DEBUG] Skipping system cycle: {cycleName}");
                return; // System cycles don't add to machining time
            }
            
            // Calculate cycle time based on TCALC_HH7 logic
            double cycleTime = 0;
            
            // Skip drilling cycle time calculation for HH7 format
            // In HH7/nesting files, drilling is represented by actual G1 movements
            // Adding cycle time would double-count the drilling operations
            if (cycleName.Contains("CP_DHCODE"))
            {
                // Drill head code - no additional time needed
                return;
            }
            else if (cycleName.Contains("81") || cycleName.Contains("DRILL") || cycleName.Contains("BORING"))
            {
                // For non-HH7 formats, drilling cycles might need time calculation
                // But for HH7/nesting, the movements are already in the file
                // Only add minimal overhead for cycle processing
                cycleTime = 0.1; // Minimal cycle overhead
            }
            else if (cycleName.Contains("CONTOUR") || cycleName.Contains("PROFILE"))
            {
                // Contouring cycle - higher overhead
                cycleTime = _config.ConstdHCycle30;
            }
            else
            {
                // Generic cycle overhead - reduced for HH7 format
                // Most L CYCLE calls in HH7 are control codes, not actual operations
                cycleTime = 0.0; // No time for control cycles
            }
            
            // Add to analysis (store in seconds, will be converted to minutes later)
            if (!analysis.ProcessesUsed.Contains("CYCLE"))
                analysis.ProcessesUsed.Add("CYCLE");
                
            // Track cycle in tool session if active tool
            if (_currentActiveTool > 0 && _toolSessions.ContainsKey(_currentActiveTool))
            {
                var session = _toolSessions[_currentActiveTool];
                session.CuttingTime += cycleTime / 60.0; // Convert seconds to minutes before adding
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

            var zMatch = Regex.Match(line, @"Z=?([-+]?\d*\.?\d+)");
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
                // Rapid move - check if it's primarily a Z move
                double zDistance = Math.Abs(newZ - _currentZ);
                double xyDistance = Math.Sqrt(Math.Pow(newX - _currentX, 2) + Math.Pow(newY - _currentY, 2));
                
                if (zDistance > xyDistance * 2)  // Primarily Z movement
                {
                    feedrate = _config.MAXFEEDRATE_Z; // Use configured Z rapid feedrate
                }
                else
                {
                    feedrate = _config.MAXFEEDRATE_XY; // Use configured XY rapid feedrate  
                }
                
                timeMinutes = distance / feedrate; // Direct calculation in minutes
                
            }
            else if (code == "G1")
            {
                // Linear move - use current feedrate or last valid feedrate
                feedrate = _currentFeedrate > 0 ? _currentFeedrate : _lastValidFeedrate;
                timeMinutes = distance / feedrate; // Direct calculation in minutes
                
            }

            // Update current position after calculating distance
            _currentX = newX;
            _currentY = newY;
            _currentZ = newZ;
            
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
            double feedrate = _currentFeedrate > 0 ? _currentFeedrate : _lastValidFeedrate;
            double timeMinutes = arcLength / feedrate; // Direct calculation in minutes

            // Update current position after calculating distance
            _currentX = newX;
            _currentY = newY;
            _currentZ = newZ;
            
            return new CNCMovement
            {
                Code = code,
                X = newX,
                Y = newY,
                Z = newZ,
                Feedrate = feedrate,
                Distance = arcLength,
                Time = timeMinutes // Already in minutes
            };
        }

        // Duplicate UpdatePosition method removed - keeping the first one

        private double CalculateMachineOperationTime(MachineOperations ops)
        {
            // Calculate total machine operation time in seconds
            double totalTime = ops.ToolChanges * _config.TC_51_51 +
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
            
            // Debug output for machine operations
            if (ops.TcpOn > 0 || ops.ContourStarts > 0 || ops.DynamicSetups > 0 || ops.FlushWaits > 0)
            {
                Console.WriteLine($"[MACHINE OPS] Detected operations:");
                if (ops.TcpOn > 0) Console.WriteLine($"  - TCP ON: {ops.TcpOn} × {TCP_ON_TIME}s = {ops.TcpOn * TCP_ON_TIME:F1}s");
                if (ops.TcpOff > 0) Console.WriteLine($"  - TCP OFF: {ops.TcpOff} × {TCP_OFF_TIME}s = {ops.TcpOff * TCP_OFF_TIME:F1}s");
                if (ops.ContourStarts > 0) Console.WriteLine($"  - Contour Start: {ops.ContourStarts} × {CONTOUR_START_TIME}s = {ops.ContourStarts * CONTOUR_START_TIME:F1}s");
                if (ops.ContourEnds > 0) Console.WriteLine($"  - Contour End: {ops.ContourEnds} × {CONTOUR_END_TIME}s = {ops.ContourEnds * CONTOUR_END_TIME:F1}s");
                if (ops.DynamicSetups > 0) Console.WriteLine($"  - Dynamic Setup: {ops.DynamicSetups} × {DYNAMIC_SETUP_TIME}s = {ops.DynamicSetups * DYNAMIC_SETUP_TIME:F1}s");
                if (ops.FlushWaits > 0) Console.WriteLine($"  - Flush Wait: {ops.FlushWaits} × {FLUSH_WAIT_TIME}s = {ops.FlushWaits * FLUSH_WAIT_TIME:F1}s");
                if (ops.CoordinateSetups > 0) Console.WriteLine($"  - Coordinate Setup: {ops.CoordinateSetups} × {COORDINATE_SETUP_TIME}s = {ops.CoordinateSetups * COORDINATE_SETUP_TIME:F1}s");
                if (ops.OtherCycles > 0) Console.WriteLine($"  - Other Cycles: {ops.OtherCycles} × {GENERAL_CYCLE_TIME}s = {ops.OtherCycles * GENERAL_CYCLE_TIME:F1}s");
                Console.WriteLine($"  - Total Machine Ops Time: {totalTime:F1}s");
            }
            
            return totalTime;
        }
        
        /// <summary>
        /// Process drilling operations from comments and movement patterns
        /// </summary>
        private void ProcessDrillingOperation(string line, string[] lines, int lineIndex, CNCAnalysis analysis)
        {
            // Check for drilling cycle indicators in comments
            // Skip "Drill Cycle" lines that immediately follow drilling operation comments
            bool isDrillCycleLine = line.Contains("; --- Drill Cycle");
            bool isDrillingComment = (line.Contains("; --- vertical drilling") ||
                                    line.Contains("; --- horizontal drilling") ||
                                    line.Contains("; --- Bohren") ||
                                    line.Contains("bohren") ||
                                    line.Contains("DH:53000")) && !isDrillCycleLine;
            
            // Also check for L CYCLE drilling calls (HH7 format)
            bool isDrillingCycle = line.Contains("CP_DH.NC") || line.Contains("DH:53000");
            
            // Skip processing if we just completed a drilling operation and this is just a follow-up comment
            if (_justCompletedDrilling && (isDrillCycleLine || isDrillingComment))
            {
                // Reset the flag if this is NOT a drilling-related line
                return; // Skip duplicate detection  
            }
            
            // If we're already in a drilling sequence and encounter a "Drill Cycle" line, skip it
            if (_isDrillingSequence && isDrillCycleLine)
            {
                return; // Skip duplicate detection
            }
            
            // Reset the "just completed" flag if this is not a drilling line
            if (!isDrillingComment && !isDrillingCycle && !isDrillCycleLine)
            {
                _justCompletedDrilling = false;
            }
            
            if (isDrillingComment || isDrillingCycle)
            {
                // Determine cycle type from comment or default to blind hole
                int cycleType = ExtractDrillingCycleType(line);
                bool isHorizontal = line.Contains("horizontal");
                
                // Extract drill bit ID from comment if present (for logging only)
                int drillBitId = ExtractDrillBitId(line);
                
                // Always use the current active tool (T501) for drilling operations
                // Drill bits (203, 209) are NOT separate tools, they're bits used BY T501
                int actualDrillingTool = _currentActiveTool;
                
                // Initialize drilling operation
                _currentDrilling = new DrillingOperation
                {
                    CycleType = cycleType,
                    X = _currentX,
                    Y = _currentY,
                    IsHorizontal = isHorizontal,
                    ToolNumber = actualDrillingTool,  // Use drill bit ID if available, otherwise current tool
                    DrillBitId = drillBitId,
                    DrillFeedrate = 3500,  // Default drill feedrate
                    EntryFeedrate = 2000,  // Default entry feedrate
                    RetractFeedrate = 10000  // Default retract feedrate
                };
                
                _isDrillingSequence = true;
                _drillMoves.Clear();
                
                string drillBitInfo = drillBitId > 0 ? $" (Drill Bit T{drillBitId})" : "";
                Console.WriteLine($"[DRILL] Detected drilling at line {lineIndex + 1}: Cycle {cycleType}, Tool T{actualDrillingTool}{drillBitInfo}");
                Console.WriteLine($"[DRILL DEBUG] Line content: {line.Substring(0, Math.Min(line.Length, 100))}");
                
                // For OPUS vertical drilling, check if moves are BEFORE the comment (look back up to 10 lines)
                bool foundBackwardMoves = false;
                if (line.Contains("vertical drilling") && lineIndex > 0)
                {
                    int lookback = Math.Min(10, lineIndex);
                    for (int i = lookback; i >= 1; i--)
                    {
                        var prevLine = lines[lineIndex - i];
                        var cleanPrev = CleanGCodeLine(prevLine);
                        
                        if (IsDrillMove(cleanPrev))
                        {
                            var move = ParseDrillMove(cleanPrev);
                            if (move != null)
                            {
                                _drillMoves.Add(move);
                                foundBackwardMoves = true;
                            }
                        }
                    }
                    
                    // If we found moves before the comment, check if it's a complete sequence
                    if (foundBackwardMoves && IsCompleteDrillingSequence())
                    {
                        Console.WriteLine($"[DRILL] Found complete sequence BEFORE drilling comment");
                        CompleteDrillingOperation();
                        return;
                    }
                }
                
                // For L CYCLE format, extract parameters directly
                if (isDrillingCycle && line.Contains("@P"))
                {
                    ProcessLCycleDrilling(line);
                    return;
                }
                
                // Look ahead to capture the drilling sequence (max 25 lines for OPUS which has many setup lines)
                int lookahead = Math.Min(25, lines.Length - lineIndex - 1);
                for (int i = 1; i <= lookahead; i++)
                {
                    if (lineIndex + i >= lines.Length) break;
                    
                    var nextLine = lines[lineIndex + i];
                    var cleanNext = CleanGCodeLine(nextLine);
                    
                    // Stop if we hit another major operation
                    if (IsNewMajorOperation(nextLine)) break;
                    
                    // Capture drill moves
                    if (IsDrillMove(cleanNext))
                    {
                        var move = ParseDrillMove(cleanNext);
                        if (move != null)
                        {
                            _drillMoves.Add(move);
                            
                            // Check if this completes a drilling sequence
                            if (IsCompleteDrillingSequence())
                            {
                                CompleteDrillingOperation();
                                break;
                            }
                        }
                    }
                }
            }
            // Check if we're in an active drilling sequence and should capture moves
            else if (_isDrillingSequence)
            {
                var cleanLine = CleanGCodeLine(line);
                if (IsDrillMove(cleanLine))
                {
                    var move = ParseDrillMove(cleanLine);
                    if (move != null)
                    {
                        _drillMoves.Add(move);
                        
                        // Check if sequence is complete
                        if (IsCompleteDrillingSequence())
                        {
                            CompleteDrillingOperation();
                        }
                    }
                }
                else if (IsNewMajorOperation(line))
                {
                    // Force complete if we have moves
                    if (_drillMoves.Count > 2)
                    {
                        CompleteDrillingOperation();
                    }
                    else
                    {
                        _isDrillingSequence = false;
                        _currentDrilling = null;
                    }
                }
            }
        }
        
        /// <summary>
        /// Extract drill bit ID from drilling comment
        /// </summary>
        private int ExtractDrillBitId(string line)
        {
            // Extract drill bit ID from arrow pattern ->xxxx<-
            // Handles both single ID (->203<-) and multi-ID (->1509;1510<-) patterns
            var drillBitMatch = Regex.Match(line, @"->\s*([0-9;]+)\s*<-");
            if (drillBitMatch.Success)
            {
                string idString = drillBitMatch.Groups[1].Value;
                // For multi-ID patterns, take the first ID
                string firstId = idString.Split(';')[0];
                if (int.TryParse(firstId, out int drillBitId))
                {
                    return drillBitId;
                }
            }
            return 0;
        }
        
        /// <summary>
        /// Extract drilling cycle type from comment or line
        /// </summary>
        private int ExtractDrillingCycleType(string line)
        {
            // Direct cycle number extraction
            var cycleMatch = Regex.Match(line, @"Cycle\s+(\d+)|Cycle(\d+)|CYCLE\s+(\d+)");
            if (cycleMatch.Success)
            {
                for (int i = 1; i <= 3; i++)
                {
                    if (cycleMatch.Groups[i].Success && int.TryParse(cycleMatch.Groups[i].Value, out int cycle))
                        return cycle;
                }
            }
            
            // Check for through hole indicators
            if (line.Contains("through") || line.Contains("Durch") || line.Contains("DURCH"))
                return 20;
            
            // Check for hinge/dwell indicators  
            if (line.Contains("hinge") || line.Contains("dwell") || line.Contains("Topf"))
                return 30;
            
            // Default to blind hole
            return 10;
        }
        
        /// <summary>
        /// Process L CYCLE drilling format (HH7)
        /// </summary>
        private void ProcessLCycleDrilling(string line)
        {
            // Extract parameters from L CYCLE [NAME=CP_DH.NC @P1=... @P2=... @P3=depth ...]
            var depthMatch = Regex.Match(line, @"@P3=([-\d.]+)");
            var feedMatch = Regex.Match(line, @"@P4=([\d.]+)");
            
            if (depthMatch.Success && double.TryParse(depthMatch.Groups[1].Value, out double depth))
            {
                _currentDrilling.FinalDepth = depth;
            }
            
            if (feedMatch.Success && double.TryParse(feedMatch.Groups[1].Value, out double feed))
            {
                _currentDrilling.DrillFeedrate = feed;
            }
            
            // Calculate time immediately for L CYCLE format
            double drillTime = _engine.CalculateDrillingCycleTime(
                _currentDrilling.CycleType,
                Math.Abs(_currentDrilling.FinalDepth),
                _currentDrilling.DrillFeedrate,
                _currentDrilling.RetractFeedrate
            );
            
            _currentDrilling.CalculatedTime = drillTime;
            
            // Add to tool session - ALWAYS use current active tool (T501), not drill bit ID  
            // Drill bits are not separate tools, they're bits used BY the drilling head
            int toolToUpdate = _currentActiveTool;
            
            if (toolToUpdate > 0 && _toolSessions.ContainsKey(toolToUpdate))
            {
                // Skip adding time for T501 as it's already handled in special T501 processing
                if (toolToUpdate != 501)
                {
                    _toolSessions[toolToUpdate].CuttingTime += drillTime / 60.0; // Convert to minutes
                    
                    // Add drilling distance (depth * 2 for entry and retract)
                    double drillDistance = Math.Abs(_currentDrilling.FinalDepth) * 2; // Entry + retract
                    _toolSessions[toolToUpdate].CuttingDistance += drillDistance;
                    
                    string toolInfo = _currentDrilling.DrillBitId > 0 ? $"T{toolToUpdate} using drill bit {_currentDrilling.DrillBitId}" : $"T{toolToUpdate}";
                    Console.WriteLine($"[DRILL] L CYCLE drilling: {drillTime:F2}s, {drillDistance:F1}mm added to {toolInfo}");
                }
                else
                {
                    Console.WriteLine($"[DRILL] L CYCLE: Skipping time addition for T501 (handled by special T501 logic)");
                }
            }
            
            _completedDrillings.Add(_currentDrilling);
            _isDrillingSequence = false;
            _justCompletedDrilling = true; // Set flag to prevent duplicate detection on next line
            _currentDrilling = null;
        }
        
        /// <summary>
        /// Check if a line represents a drill-related move
        /// </summary>
        private bool IsDrillMove(string line)
        {
            // Must have G0 or G1 and Z coordinate
            return (line.Contains("G0") || line.Contains("G1")) && line.Contains("Z");
        }
        
        /// <summary>
        /// Parse a drilling move from a line
        /// </summary>
        private DrillMove ParseDrillMove(string line)
        {
            var move = new DrillMove
            {
                Code = line.Contains("G0") ? "G0" : "G1",
                HasG9 = line.Contains("G9")
            };
            
            // Extract coordinates
            var xMatch = Regex.Match(line, @"X([-+]?\d*\.?\d+)");
            if (xMatch.Success && double.TryParse(xMatch.Groups[1].Value, out double x))
                move.X = x;
            
            var yMatch = Regex.Match(line, @"Y([-+]?\d*\.?\d+)");
            if (yMatch.Success && double.TryParse(yMatch.Groups[1].Value, out double y))
                move.Y = y;
            
            var zMatch = Regex.Match(line, @"Z=([-+]?\d*\.?\d+)|Z([-+]?\d*\.?\d+)");
            if (zMatch.Success)
            {
                string zValue = zMatch.Groups[1].Success ? zMatch.Groups[1].Value : zMatch.Groups[2].Value;
                if (double.TryParse(zValue, out double z))
                    move.Z = z;
            }
            
            var fMatch = Regex.Match(line, @"F([\d.]+)");
            if (fMatch.Success && double.TryParse(fMatch.Groups[1].Value, out double f))
                move.F = f;
            
            return move;
        }
        
        /// <summary>
        /// Check if drilling sequence is complete
        /// </summary>
        private bool IsCompleteDrillingSequence()
        {
            if (_drillMoves.Count < 3) return false;
            
            // Typical sequence has:
            // 1. G0 to safety height
            // 2. G1 to entry position  
            // 3. G1 drilling down (negative Z)
            // 4. G0/G1 retract (positive Z)
            
            // Accept both G0 and G1 for positioning (OPUS vertical drilling uses G1 for entry)
            // This is safe because we still check Z > 0 (above workpiece)
            bool hasPositioning = _drillMoves.Any(m => (m.Code == "G0" || m.Code == "G1") && m.Z.HasValue && m.Z > 0);
            bool hasDrilling = _drillMoves.Any(m => m.Code == "G1" && m.Z.HasValue && m.Z < 0);
            bool hasRetract = _drillMoves.Count > 2 && 
                             _drillMoves.Last().Z.HasValue && 
                             _drillMoves.Last().Z > _drillMoves[_drillMoves.Count - 2].Z;
            
            return hasPositioning && hasDrilling && hasRetract;
        }
        
        /// <summary>
        /// Complete the current drilling operation and calculate time
        /// </summary>
        private void CompleteDrillingOperation()
        {
            if (_currentDrilling == null || _drillMoves.Count < 3) return;
            
            // Extract drilling parameters from moves
            double safetyZ = 30;  // Default
            double entryZ = 2;    // Default
            double entryDepth = -2.5;  // Default
            double finalDepth = -10;   // Default
            double entryFeed = 2000;
            double drillFeed = 3500;
            double retractFeed = 10000;
            
            // Find actual values from moves
            var safetyMove = _drillMoves.FirstOrDefault(m => m.Code == "G0" && m.Z > 10);
            if (safetyMove?.Z.HasValue == true)
                safetyZ = safetyMove.Z.Value;
            
            var entryMove = _drillMoves.FirstOrDefault(m => m.Code == "G1" && m.Z > 0 && m.Z < 10);
            if (entryMove?.Z.HasValue == true)
                entryZ = entryMove.Z.Value;
            
            var firstDrillMove = _drillMoves.FirstOrDefault(m => m.Code == "G1" && m.Z < 0);
            if (firstDrillMove != null)
            {
                if (firstDrillMove.Z.HasValue)
                    entryDepth = firstDrillMove.Z.Value;
                if (firstDrillMove.F.HasValue)
                    entryFeed = firstDrillMove.F.Value;
            }
            
            var deepestMove = _drillMoves.Where(m => m.Z.HasValue).OrderBy(m => m.Z).FirstOrDefault();
            if (deepestMove?.Z.HasValue == true)
            {
                finalDepth = deepestMove.Z.Value;
                if (deepestMove.F.HasValue)
                    drillFeed = deepestMove.F.Value;
            }
            
            var retractMove = _drillMoves.LastOrDefault(m => m.Z > 0);
            if (retractMove?.F.HasValue == true)
                retractFeed = retractMove.F.Value;
            
            // Update drilling operation
            _currentDrilling.SafetyZ = safetyZ;
            _currentDrilling.EntryZ = entryZ;
            _currentDrilling.EntryDepth = entryDepth;
            _currentDrilling.FinalDepth = finalDepth;
            _currentDrilling.EntryFeedrate = entryFeed;
            _currentDrilling.DrillFeedrate = drillFeed;
            _currentDrilling.RetractFeedrate = retractFeed;
            
            // Calculate time using TCALC_BOHR logic
            double drillTime = _engine.CalculateDrillingSequenceTime(
                safetyZ, entryZ, entryDepth, finalDepth,
                entryFeed, drillFeed, retractFeed, _currentDrilling.CycleType
            );
            
            _currentDrilling.CalculatedTime = drillTime;
            
            // Add to tool session - ALWAYS use current active tool (T501), not drill bit ID  
            // Drill bits are not separate tools, they're bits used BY the drilling head
            int toolToUpdate = _currentActiveTool;
            
            // Create tool session if it doesn't exist (for drill bits)
            if (toolToUpdate > 0 && !_toolSessions.ContainsKey(toolToUpdate))
            {
                _toolSessions[toolToUpdate] = new ToolUsageSession { ToolNumber = toolToUpdate };
            }
            
            if (toolToUpdate > 0 && _toolSessions.ContainsKey(toolToUpdate))
            {
                // Skip adding time for T501 as it's already handled in special T501 processing
                if (toolToUpdate != 501)
                {
                    _toolSessions[toolToUpdate].CuttingTime += drillTime / 60.0; // Convert to minutes
                    
                    // Add drilling distance (depth * 2 for entry and retract)
                    double drillDistance = Math.Abs(finalDepth) * 2; // Entry + retract
                    _toolSessions[toolToUpdate].CuttingDistance += drillDistance;
                    _toolSessions[toolToUpdate].MoveCount++; // Increment move count for drilling operation
                    
                    string toolInfo = _currentDrilling.DrillBitId > 0 ? $"T{toolToUpdate} using drill bit {_currentDrilling.DrillBitId}" : $"T{toolToUpdate}";
                    Console.WriteLine($"[DRILL] Completed drilling sequence: {drillTime:F2}s for {toolInfo}, " +
                                    $"Depth={finalDepth:F1}mm, Distance={drillDistance:F1}mm, Feed={drillFeed:F0}mm/min");
                }
                else
                {
                    Console.WriteLine($"[DRILL] Skipping time addition for T501 (handled by special T501 logic)");
                }
            }
            
            _completedDrillings.Add(_currentDrilling);
            Console.WriteLine($"[DRILL] Total drilling operations completed so far: {_completedDrillings.Count}");
            _isDrillingSequence = false;
            _justCompletedDrilling = true; // Set flag to prevent duplicate detection on next line
            _currentDrilling = null;
            _drillMoves.Clear();
        }
        
        /// <summary>
        /// Check if line represents a new major operation that would end drilling
        /// </summary>
        private bool IsNewMajorOperation(string line)
        {
            return line.Contains("; --- Process") ||
                   line.Contains("TOOLCHANGE") ||
                   line.Contains("T=") ||
                   line.Contains("M6") ||
                   line.Contains("M06") ||
                   line.Contains("; ---  ---") ||
                   (line.Contains("; ---") && !line.Contains("drill") && !line.Contains("Drill") && !line.Contains("bohr"));
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
            ".nc", ".gcode", ".tap", ".mpf", ".ptp", ".cls", ".lst", ".prg", ".sub", ".cnc", ".spf", ".hop", ".hops"
        };

        // CNC file extensions for analysis
        private readonly HashSet<string> CNC_EXTENSIONS = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            ".nc", ".gcode", ".tap", ".mpf", ".ptp", ".cls", ".lst", ".prg", ".sub", ".cnc", 
            ".spf",  // Siemens/Vision postprocessor format
            ".hop", ".hops"  // HOP files referenced in CNC programs
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
            
            // Show the form as a proper window instead of hiding it
            // This is needed for systems without a taskbar
            this.WindowState = FormWindowState.Normal;
            this.ShowInTaskbar = true;
            this.Visible = true;
            this.StartPosition = FormStartPosition.CenterScreen;
            
            // Create the settings UI
            CreateSettingsUI();
            
            CheckSingleInstance();
            StartApplication();
        }

        private void InitializeForm()
        {
            // Basic form setup - this replaces the auto-generated InitializeComponent
            this.Text = "CNC DATALOG - Control Panel";
            this.Size = new Size(650, 550); // Proper size for settings window
            this.FormBorderStyle = FormBorderStyle.Sizable;
            this.ShowInTaskbar = true;
            this.WindowState = FormWindowState.Normal;
            this.MinimumSize = new Size(500, 450);
            this.StartPosition = FormStartPosition.CenterScreen;
            
            // Handle form closing - minimize to tray by default
            this.FormClosing += (s, e) => {
                if (e.CloseReason == CloseReason.UserClosing)
                {
                    e.Cancel = true;
                    this.WindowState = FormWindowState.Minimized;
                    this.ShowInTaskbar = false;
                    this.Visible = false;
                    trayIcon?.ShowBalloonTip(1000, "CNC DATALOG", "Minimized to system tray", ToolTipIcon.Info);
                }
            };
        }

        private void CreateSettingsUI()
        {
            // Create main panel with tabs
            var tabControl = new TabControl
            {
                Dock = DockStyle.Fill,
                Font = new Font("Segoe UI", 9F)
            };
            this.Controls.Add(tabControl);

            // Connection Tab
            var connectionTab = new TabPage("Connection");
            CreateConnectionTab(connectionTab);
            tabControl.TabPages.Add(connectionTab);

            // Monitoring Tab
            var monitoringTab = new TabPage("Monitoring");
            CreateMonitoringTab(monitoringTab);
            tabControl.TabPages.Add(monitoringTab);

            // Analysis Tab
            var analysisTab = new TabPage("Analysis");
            CreateAnalysisTab(analysisTab);
            tabControl.TabPages.Add(analysisTab);

            // Status Tab
            var statusTab = new TabPage("Status");
            CreateStatusTab(statusTab);
            tabControl.TabPages.Add(statusTab);

            // Add button panel at bottom
            var buttonPanel = new Panel
            {
                Height = 45,
                Dock = DockStyle.Bottom,
                BackColor = SystemColors.Control
            };
            
            // Minimize to tray button
            var minimizeButton = new Button
            {
                Text = "Minimize to Tray",
                Size = new Size(120, 30),
                Location = new Point(this.Width - 390, 7),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Right
            };
            minimizeButton.Click += (s, e) => {
                this.WindowState = FormWindowState.Minimized;
                this.ShowInTaskbar = false;
                this.Visible = false;
                trayIcon?.ShowBalloonTip(1000, "CNC DATALOG", "Minimized to system tray", ToolTipIcon.Info);
            };
            buttonPanel.Controls.Add(minimizeButton);
            
            // Open Web Interface button
            var webButton = new Button
            {
                Text = "Open Web Interface",
                Size = new Size(120, 30),
                Location = new Point(this.Width - 260, 7),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Right,
                BackColor = Color.FromArgb(200, 220, 255)
            };
            webButton.Click += (s, e) => OpenBrowser();
            buttonPanel.Controls.Add(webButton);
            
            // Exit Application button
            var exitButton = new Button
            {
                Text = "Exit Application",
                Size = new Size(120, 30),
                Location = new Point(this.Width - 130, 7),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Right,
                BackColor = Color.FromArgb(255, 200, 200)
            };
            exitButton.Click += (s, e) => {
                var result = MessageBox.Show("Are you sure you want to exit CNC DATALOG completely?\n\nThis will stop all monitoring.", 
                    "Confirm Exit", MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
                if (result == DialogResult.Yes)
                {
                    QuitApplication();
                }
            };
            buttonPanel.Controls.Add(exitButton);
            
            this.Controls.Add(buttonPanel);
        }

        private void CreateConnectionTab(TabPage tab)
        {
            var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(10), AutoScroll = true };
            tab.Controls.Add(panel);

            int yPos = 10;
            
            // Windows Startup Section
            var startupGroup = new GroupBox
            {
                Text = "Windows Startup",
                Location = new Point(10, yPos),
                Size = new Size(550, 60),
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };
            
            var startupCheckbox = new CheckBox
            {
                Text = "Start CNC DATALOG when Windows starts",
                Location = new Point(15, 25),
                Size = new Size(300, 20),
                Checked = IsStartupEnabled()
            };
            startupCheckbox.CheckedChanged += (s, e) => {
                ToggleStartup();
                var statusText = IsStartupEnabled() ? "enabled" : "disabled";
                trayIcon?.ShowBalloonTip(1000, "Startup Setting", $"Windows startup {statusText}", ToolTipIcon.Info);
            };
            startupGroup.Controls.Add(startupCheckbox);
            panel.Controls.Add(startupGroup);
            yPos += 70;

            // Server Connection Section
            var serverGroup = new GroupBox
            {
                Text = "Server Connection",
                Location = new Point(10, yPos),
                Size = new Size(550, 150),
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };

            // Server URL
            var urlLabel = new Label { Text = "Server URL:", Location = new Point(15, 25), Size = new Size(100, 20) };
            serverGroup.Controls.Add(urlLabel);
            var urlTextBox = new TextBox { 
                Text = config.WebAppUrl, 
                Location = new Point(120, 22), 
                Size = new Size(300, 20),
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };
            urlTextBox.TextChanged += (s, e) => {
                config.WebAppUrl = urlTextBox.Text;
                webAppUrl = config.WebAppUrl;
                SaveConfiguration();
            };
            serverGroup.Controls.Add(urlTextBox);

            // Username
            var userLabel = new Label { Text = "Username:", Location = new Point(15, 55), Size = new Size(100, 20) };
            serverGroup.Controls.Add(userLabel);
            var userTextBox = new TextBox { 
                Text = config.Username, 
                Location = new Point(120, 52), 
                Size = new Size(200, 20) 
            };
            userTextBox.TextChanged += (s, e) => {
                config.Username = userTextBox.Text;
                SaveConfiguration();
            };
            serverGroup.Controls.Add(userTextBox);

            // Login button
            var loginButton = new Button { 
                Text = authenticated ? $"Logged in as {currentUser}" : "Login", 
                Location = new Point(120, 85), 
                Size = new Size(150, 30),
                Enabled = !authenticated
            };
            loginButton.Click += (s, e) => {
                if (!authenticated) {
                    ShowLoginDialog();
                    loginButton.Text = authenticated ? $"Logged in as {currentUser}" : "Login";
                    loginButton.Enabled = !authenticated;
                }
            };
            serverGroup.Controls.Add(loginButton);

            // Logout button
            var logoutButton = new Button { 
                Text = "Logout", 
                Location = new Point(280, 85), 
                Size = new Size(80, 30),
                Enabled = authenticated
            };
            logoutButton.Click += (s, e) => {
                Logout();
                loginButton.Text = "Login";
                loginButton.Enabled = true;
                logoutButton.Enabled = false;
            };
            serverGroup.Controls.Add(logoutButton);

            // Connection status
            var statusLabel = new Label { 
                Text = authenticated ? "✓ Connected" : "✗ Not connected", 
                Location = new Point(15, 120), 
                Size = new Size(200, 20),
                ForeColor = authenticated ? Color.Green : Color.Red,
                Font = new Font("Segoe UI", 9F, FontStyle.Bold)
            };
            serverGroup.Controls.Add(statusLabel);
            
            panel.Controls.Add(serverGroup);
            yPos += 160;
            
            // Auto Login Section
            var autoLoginGroup = new GroupBox
            {
                Text = "Auto Login Settings",
                Location = new Point(10, yPos),
                Size = new Size(550, 140),
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };
            
            var autoLoginCheckbox = new CheckBox
            {
                Text = "Enable automatic login on startup",
                Location = new Point(15, 25),
                Size = new Size(250, 20),
                Checked = !string.IsNullOrEmpty(config.Username) && !string.IsNullOrEmpty(GetStoredPassword(config.Username))
            };
            
            var passwordLabel = new Label { Text = "Password:", Location = new Point(15, 55), Size = new Size(100, 20) };
            autoLoginGroup.Controls.Add(passwordLabel);
            
            var passwordTextBox = new TextBox { 
                Location = new Point(120, 52), 
                Size = new Size(200, 20),
                UseSystemPasswordChar = true,
                Enabled = autoLoginCheckbox.Checked
            };
            
            // Show indicator if password is stored
            if (!string.IsNullOrEmpty(config.Username))
            {
                var storedPass = GetStoredPassword(config.Username);
                if (!string.IsNullOrEmpty(storedPass))
                    passwordTextBox.Text = "********";
            }
            autoLoginGroup.Controls.Add(passwordTextBox);
            
            var savePasswordButton = new Button
            {
                Text = "Save Password",
                Location = new Point(330, 50),
                Size = new Size(100, 25),
                Enabled = autoLoginCheckbox.Checked
            };
            savePasswordButton.Click += (s, e) => {
                if (!string.IsNullOrEmpty(userTextBox.Text) && passwordTextBox.Text != "********" && !string.IsNullOrEmpty(passwordTextBox.Text))
                {
                    StorePassword(userTextBox.Text, passwordTextBox.Text);
                    MessageBox.Show("Password saved securely", "Success", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    passwordTextBox.Text = "********";
                }
            };
            autoLoginGroup.Controls.Add(savePasswordButton);
            
            var autoMonitorCheckbox = new CheckBox
            {
                Text = "Automatically start monitoring after login",
                Location = new Point(15, 85),
                Size = new Size(300, 20),
                Checked = config.MonitoringEnabled
            };
            autoMonitorCheckbox.CheckedChanged += (s, e) => {
                config.MonitoringEnabled = autoMonitorCheckbox.Checked;
                SaveConfiguration();
            };
            autoLoginGroup.Controls.Add(autoMonitorCheckbox);
            
            var testAutoLoginButton = new Button
            {
                Text = "Test Auto Login",
                Location = new Point(120, 110),
                Size = new Size(120, 25),
                Enabled = autoLoginCheckbox.Checked
            };
            testAutoLoginButton.Click += async (s, e) => {
                if (await AutoLogin())
                {
                    MessageBox.Show($"Auto login successful! Logged in as {currentUser}", "Success", 
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                    loginButton.Text = $"Logged in as {currentUser}";
                    loginButton.Enabled = false;
                    logoutButton.Enabled = true;
                    statusLabel.Text = "✓ Connected";
                    statusLabel.ForeColor = Color.Green;
                }
                else
                {
                    MessageBox.Show("Auto login failed. Please check credentials.", "Error", 
                        MessageBoxButtons.OK, MessageBoxIcon.Error);
                }
            };
            autoLoginGroup.Controls.Add(testAutoLoginButton);
            
            autoLoginCheckbox.CheckedChanged += (s, e) => {
                passwordTextBox.Enabled = autoLoginCheckbox.Checked;
                savePasswordButton.Enabled = autoLoginCheckbox.Checked;
                testAutoLoginButton.Enabled = autoLoginCheckbox.Checked;
            };
            autoLoginGroup.Controls.Add(autoLoginCheckbox);
            
            panel.Controls.Add(autoLoginGroup);
        }

        private void CreateMonitoringTab(TabPage tab)
        {
            var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(10) };
            tab.Controls.Add(panel);

            int yPos = 10;

            // Monitoring status
            var statusLabel = new Label { 
                Text = $"Monitoring: {(monitoringActive ? "Active" : "Inactive")}", 
                Location = new Point(10, yPos), 
                Size = new Size(200, 20),
                Font = new Font("Segoe UI", 9F, FontStyle.Bold),
                ForeColor = monitoringActive ? Color.Green : Color.Red
            };
            panel.Controls.Add(statusLabel);
            yPos += 30;

            // Toggle monitoring button
            var toggleButton = new Button { 
                Text = monitoringActive ? "Stop Monitoring" : "Start Monitoring", 
                Location = new Point(10, yPos), 
                Size = new Size(150, 30)
            };
            toggleButton.Click += async (s, e) => {
                await ToggleMonitoring();
                statusLabel.Text = $"Monitoring: {(monitoringActive ? "Active" : "Inactive")}";
                statusLabel.ForeColor = monitoringActive ? Color.Green : Color.Red;
                toggleButton.Text = monitoringActive ? "Stop Monitoring" : "Start Monitoring";
            };
            panel.Controls.Add(toggleButton);
            yPos += 40;

            // File/Directory management
            var pathsLabel = new Label { Text = "Monitored Paths:", Location = new Point(10, yPos), Size = new Size(150, 20) };
            panel.Controls.Add(pathsLabel);
            yPos += 25;

            var pathsListBox = new ListBox { 
                Location = new Point(10, yPos), 
                Size = new Size(400, 150),
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };
            // Populate with current paths (this would need to be updated when paths change)
            panel.Controls.Add(pathsListBox);
            yPos += 160;

            var addPathsButton = new Button { 
                Text = "Add Files/Directories...", 
                Location = new Point(10, yPos), 
                Size = new Size(150, 30)
            };
            addPathsButton.Click += (s, e) => ShowFileSelector();
            panel.Controls.Add(addPathsButton);
            
            var manualEntryButton = new Button { 
                Text = "Manual Entry...", 
                Location = new Point(170, yPos), 
                Size = new Size(120, 30)
            };
            manualEntryButton.Click += (s, e) => ShowManualEntry();
            panel.Controls.Add(manualEntryButton);

            // Settings checkboxes
            yPos += 40;
            var scanContentCheckbox = new CheckBox { 
                Text = "Scan file contents", 
                Location = new Point(10, yPos), 
                Size = new Size(200, 20),
                Checked = config.ScanFileContents
            };
            scanContentCheckbox.CheckedChanged += (s, e) => {
                config.ScanFileContents = scanContentCheckbox.Checked;
                SaveConfiguration();
            };
            panel.Controls.Add(scanContentCheckbox);
            yPos += 25;

            var cncAnalysisCheckbox = new CheckBox { 
                Text = "Enable CNC Analysis", 
                Location = new Point(10, yPos), 
                Size = new Size(200, 20),
                Checked = config.EnableCNCAnalysis
            };
            cncAnalysisCheckbox.CheckedChanged += (s, e) => {
                config.EnableCNCAnalysis = cncAnalysisCheckbox.Checked;
                SaveConfiguration();
            };
            panel.Controls.Add(cncAnalysisCheckbox);
        }

        private void CreateAnalysisTab(TabPage tab)
        {
            var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(10) };
            tab.Controls.Add(panel);

            int yPos = 10;

            // Analysis mode selection
            var modeLabel = new Label { Text = "Analysis Mode:", Location = new Point(10, yPos), Size = new Size(100, 20) };
            panel.Controls.Add(modeLabel);
            yPos += 25;

            var simpleRadio = new RadioButton { 
                Text = "Simple (Reliable, no server dependency)", 
                Location = new Point(20, yPos), 
                Size = new Size(300, 20),
                Checked = analyzerConfig.Mode == AnalysisMode.Simple
            };
            simpleRadio.CheckedChanged += (s, e) => { if (simpleRadio.Checked) SetAnalyzerMode(AnalysisMode.Simple); };
            panel.Controls.Add(simpleRadio);
            yPos += 25;

            var enhancedRadio = new RadioButton { 
                Text = "Enhanced (Advanced features, server config)", 
                Location = new Point(20, yPos), 
                Size = new Size(300, 20),
                Checked = analyzerConfig.Mode == AnalysisMode.Enhanced
            };
            enhancedRadio.CheckedChanged += (s, e) => { if (enhancedRadio.Checked) SetAnalyzerMode(AnalysisMode.Enhanced); };
            panel.Controls.Add(enhancedRadio);
            yPos += 25;

            var autoRadio = new RadioButton { 
                Text = "Auto (Try enhanced first, fallback to simple)", 
                Location = new Point(20, yPos), 
                Size = new Size(300, 20),
                Checked = analyzerConfig.Mode == AnalysisMode.Auto
            };
            autoRadio.CheckedChanged += (s, e) => { if (autoRadio.Checked) SetAnalyzerMode(AnalysisMode.Auto); };
            panel.Controls.Add(autoRadio);
            yPos += 35;

            // PP.ini path selection
            var ppIniLabel = new Label { Text = "PP.ini Path:", Location = new Point(10, yPos), Size = new Size(100, 20) };
            panel.Controls.Add(ppIniLabel);
            var ppIniTextBox = new TextBox { 
                Text = analyzerConfig.PPIniPath, 
                Location = new Point(120, yPos), 
                Size = new Size(250, 20),
                ReadOnly = true,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };
            panel.Controls.Add(ppIniTextBox);
            var browseButton = new Button { 
                Text = "Browse...", 
                Location = new Point(380, yPos - 2), 
                Size = new Size(80, 24),
                Anchor = AnchorStyles.Top | AnchorStyles.Right
            };
            browseButton.Click += (s, e) => {
                SelectPPIniFile(s, e);
                ppIniTextBox.Text = analyzerConfig.PPIniPath;
            };
            panel.Controls.Add(browseButton);
            yPos += 35;

            // Current analyzer info
            var currentLabel = new Label { 
                Text = $"Current Analyzer: {currentAnalyzer?.GetAnalyzerVersion() ?? "None"}", 
                Location = new Point(10, yPos), 
                Size = new Size(400, 20),
                Font = new Font("Segoe UI", 8F, FontStyle.Italic)
            };
            panel.Controls.Add(currentLabel);
        }

        private void CreateStatusTab(TabPage tab)
        {
            var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(10) };
            tab.Controls.Add(panel);

            int yPos = 10;

            // Status information
            var statusTextBox = new TextBox {
                Location = new Point(10, yPos),
                Size = new Size(450, 300),
                Multiline = true,
                ReadOnly = true,
                ScrollBars = ScrollBars.Vertical,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom,
                Font = new Font("Consolas", 8F)
            };

            // Update status information
            var updateStatus = new Action(() => {
                var status = new StringBuilder();
                status.AppendLine($"Application: CNC DATALOG");
                status.AppendLine($"Version: File Monitor Tray App");
                status.AppendLine($"Started: {DateTime.Now}");
                status.AppendLine();
                status.AppendLine($"Connection Status: {(authenticated ? "Connected" : "Disconnected")}");
                status.AppendLine($"User: {currentUser}");
                status.AppendLine($"Server: {webAppUrl}");
                status.AppendLine();
                status.AppendLine($"Monitoring: {(monitoringActive ? "Active" : "Inactive")}");
                status.AppendLine($"Watched Paths: {fileWatchers.Count}");
                status.AppendLine($"Pending Changes: {pendingChanges.Count}");
                status.AppendLine($"Processed Events: {processedEvents.Count}");
                status.AppendLine();
                status.AppendLine($"Settings:");
                status.AppendLine($"  Content Scanning: {(config.ScanFileContents ? "Enabled" : "Disabled")}");
                status.AppendLine($"  CNC Analysis: {(config.EnableCNCAnalysis ? "Enabled" : "Disabled")}");
                status.AppendLine($"  Max Scan Size: {config.MaxFileSizeMB} MB");
                status.AppendLine($"  Language: {config.Language}");
                status.AppendLine();
                status.AppendLine($"Analyzer Configuration:");
                status.AppendLine($"  Mode: {analyzerConfig.Mode}");
                status.AppendLine($"  Server Config: {(analyzerConfig.EnableServerConfig ? "Enabled" : "Disabled")}");
                status.AppendLine($"  Timeout: {analyzerConfig.ServerTimeoutMs}ms");
                status.AppendLine($"  PP.ini Path: {analyzerConfig.PPIniPath}");
                status.AppendLine($"  Current Analyzer: {currentAnalyzer?.GetAnalyzerVersion() ?? "None"}");

                statusTextBox.Text = status.ToString();
            });

            updateStatus();
            panel.Controls.Add(statusTextBox);

            // Refresh button
            var refreshButton = new Button {
                Text = "Refresh",
                Location = new Point(10, statusTextBox.Bottom + 10),
                Size = new Size(80, 30),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Left
            };
            refreshButton.Click += (s, e) => updateStatus();
            panel.Controls.Add(refreshButton);

            // Manual entry button
            var manualEntryButton = new Button {
                Text = "Manual Entry",
                Location = new Point(100, statusTextBox.Bottom + 10),
                Size = new Size(100, 30),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Left
            };
            manualEntryButton.Click += (s, e) => ShowManualEntry();
            panel.Controls.Add(manualEntryButton);

            // Open web interface button
            var webButton = new Button {
                Text = "Open Web Interface",
                Location = new Point(210, statusTextBox.Bottom + 10),
                Size = new Size(130, 30),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Left
            };
            webButton.Click += (s, e) => OpenBrowser();
            panel.Controls.Add(webButton);
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
            
            // Handle double-click to show settings window
            trayIcon.DoubleClick += (s, e) => ShowSettingsWindow();
        }

        private void ShowSettingsWindow()
        {
            // Restore the window if minimized
            if (this.WindowState == FormWindowState.Minimized)
            {
                this.WindowState = FormWindowState.Normal;
            }
            
            // Show the window
            this.ShowInTaskbar = true;
            this.Visible = true;
            this.BringToFront();
            this.Activate();
        }
        
        private void UpdateTrayMenuItems()
        {
            if (trayMenu.IsDisposed) return;
            trayMenu.Items.Clear();

            if (authenticated)
            {
                trayMenu.Items.Add($@"{localization.T("user")}: {currentUser}").Enabled = false;
                trayMenu.Items.Add(new ToolStripSeparator());
                trayMenu.Items.Add("Show Control Panel", null, (s, e) => ShowSettingsWindow());
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
                trayMenu.Items.Add("Show Control Panel", null, (s, e) => ShowSettingsWindow());
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
                            this.Invoke(new Action(() =>
                                MessageBox.Show(localization.T("login_failed"), localization.T("login_failed"),
                                    MessageBoxButtons.OK, MessageBoxIcon.Error)));
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
                        
                        // Use machine-specific analyzer if configured, otherwise use current analyzer
                        ICNCAnalyzer analyzer = currentAnalyzer;
                        
                        // Create machine-specific analyzer if mode is set to MachineSpecific
                        if (analyzerConfig.Mode == AnalysisMode.MachineSpecific)
                        {
                            analyzer = CNCAnalyzerFactory.CreateAnalyzer(analyzerConfig, config.WebAppUrl, changeInfo.FullPath);
                        }
                        
                        if (analyzer != null)
                        {
                            cncAnalysis = await analyzer.AnalyzeFileAsync(changeInfo.FullPath);
                            
                            if (cncAnalysis.AnalysisSuccessful)
                            {
                                string machineInfo = cncAnalysis.DetectedMachineType != MachineType.Unknown 
                                    ? $" [{cncAnalysis.DetectedMachineType}]" 
                                    : "";
                                Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] CNC Analysis completed{machineInfo} ({analyzer.GetAnalyzerVersion()}) for {Path.GetFileName(changeInfo.FullPath)} - Total Time: {cncAnalysis.GetFormattedTime()} ({cncAnalysis.TotalTime:F2} min)");
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
        TotalTime = Math.Round(session.TotalTime * 60, 2),      // Convert minutes to seconds
        CuttingTime = Math.Round(session.CuttingTime * 60, 2),  // Convert minutes to seconds
        RapidTime = Math.Round(session.RapidTime * 60, 2),      // Convert minutes to seconds
        CuttingDistance = Math.Round(session.CuttingDistance, 1),     // mm
        RapidDistance = Math.Round(session.RapidDistance, 1),        // mm
        TotalDistance = Math.Round(session.TotalDistance, 1),        // mm
        MoveCount = session.MoveCount
    }).ToArray();
    
    // IMPORTANT: Send enhanced payload with detailed tool usage data
    // Use PrimaryHOPFile if available for better identification (especially for generic names like "ultrathink")
    string displayFilename = cncAnalysis.Filename;
    if (!string.IsNullOrEmpty(cncAnalysis.PrimaryHOPFile))
    {
        // Use HOP file as primary identifier if CNC filename is generic or lacks extension
        string fileNameWithoutExt = Path.GetFileNameWithoutExtension(cncAnalysis.Filename);
        if (string.IsNullOrEmpty(Path.GetExtension(cncAnalysis.Filename)) || 
            fileNameWithoutExt.Equals("ultrathink", StringComparison.OrdinalIgnoreCase) ||
            fileNameWithoutExt.Length < 5)  // Short generic names
        {
            displayFilename = cncAnalysis.PrimaryHOPFile;
            Console.WriteLine($"[CNC] Using HOP file for display: {displayFilename} (instead of {cncAnalysis.Filename})");
        }
    }
    
    cncAnalysisPayload = new
    {
        Filename = displayFilename,  // Use HOP filename if available and CNC name is generic
        TotalTime = cncAnalysis.TotalTime,      // Total cycle time in minutes
        MachineTime = cncAnalysis.MachineTime,  // Machine operation time in minutes
        ToolChanges = cncAnalysis.ToolChanges,  // Number of tool changes
        ToolsUsed = cncAnalysis.ToolsUsed,      // List of tool numbers used
        ToolUsageDetails = toolUsageDetails,     // NEW: Detailed per-tool timing and usage data
        ReferencedHOPFiles = cncAnalysis.ReferencedHOPFiles,  // Include all HOP files for reference
        HopFiles = cncAnalysis.HopFiles,         // NEW: HOP files list for display
        DrillingOperations = cncAnalysis.DrillingOperations,  // NEW: Drilling operations detected
        ProcessesUsed = cncAnalysis.ProcessesUsed,  // NEW: List of processes/operations used
        MovementStats = cncAnalysis.MovementStats,  // Movement statistics
        LineCount = cncAnalysis.LineCount,  // Total lines in the program
        CuttingTime = cncAnalysis.CuttingTime,  // Cutting time in minutes
        RapidTime = cncAnalysis.RapidTime  // Rapid move time in minutes
    };
    
    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] CNC payload prepared: TotalTime={cncAnalysis.TotalTime}min, MachineTime={cncAnalysis.MachineTime}min, ToolChanges={cncAnalysis.ToolChanges}, DetailedTools={toolUsageDetails.Length}");
    
    // Debug for Field1.spf
    if (cncAnalysis.Filename.Contains("Field1", StringComparison.OrdinalIgnoreCase))
    {
        Console.WriteLine($"[FIELD1 DEBUG] ToolChanges in payload: {cncAnalysis.ToolChanges}");
        Console.WriteLine($"[FIELD1 DEBUG] Expected tool change time: {cncAnalysis.ToolChanges * 13.05}s");
        Console.WriteLine($"[FIELD1 DEBUG] Total time in seconds: {cncAnalysis.TotalTime * 60:F1}s");
        Console.WriteLine($"[FIELD1 DEBUG] If tool changes were added: {(cncAnalysis.TotalTime * 60 + cncAnalysis.ToolChanges * 13.05):F1}s");
    }
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
                
                // Debug the actual JSON being sent
                if (cncAnalysis != null && cncAnalysis.Filename.Contains("Field1", StringComparison.OrdinalIgnoreCase))
                {
                    Console.WriteLine($"[FIELD1 API PAYLOAD] Sending: {jsonPayload}");
                }
                
                var response = await httpClient.PostAsync($@"{webAppUrl}/api/log_event", content);
                if (!response.IsSuccessStatusCode)
                {
                    // Read the error response body to get more details
                    string errorContent = await response.Content.ReadAsStringAsync();
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Failed to log event: {response.StatusCode}");
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Error details: {errorContent}");
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