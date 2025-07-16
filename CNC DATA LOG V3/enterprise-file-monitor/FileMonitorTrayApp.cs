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
        public DateTime AnalyzedAt { get; set; }
        public bool AnalysisSuccessful { get; set; }
        public string ErrorMessage { get; set; }

        public CNCAnalysis()
        {
            MovementStats = new Dictionary<string, int>();
            ProcessesUsed = new List<string>();
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
    }

    public class GCodeAnalyzer
    {
        // Machine timing configuration (matching Python postprocessor EXACTLY)
        private const double RAPID_SPEED = 20000; // mm/min
        private const double TOOL_CHANGE_TIME = 20; // seconds
        private const double SPINDLE_START_TIME = 2; // seconds
        private const double SPINDLE_STOP_TIME = 1.5; // seconds
        private const double TCP_ON_TIME = 0.5; // seconds
        private const double TCP_OFF_TIME = 0.3; // seconds
        private const double CONTOUR_START_TIME = 0.5; // seconds
        private const double CONTOUR_END_TIME = 0.3; // seconds
        private const double DYNAMIC_SETUP_TIME = 0.5; // seconds
        private const double FLUSH_WAIT_TIME = 1.0; // seconds
        private const double COORDINATE_SETUP_TIME = 0.2; // seconds
        private const double GENERAL_CYCLE_TIME = 0.1; // seconds

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

        public async Task<CNCAnalysis> AnalyzeFileAsync(string filePath)
        {
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

                    // Process movements
                    var movement = ProcessMovement(cleanLine, analysis);
                    if (movement != null)
                    {
                        movements.Add(movement);
                    }
                }

                // Calculate machine operation time
                double machineOperationTime = CalculateMachineOperationTime(machineOps);

                // Calculate movement times (in minutes from movements)
                analysis.RapidTime = movements.Where(m => m.Code == "G0").Sum(m => m.Time);
                analysis.CuttingTime = movements.Where(m => m.Code == "G1" || m.Code == "G2" || m.Code == "G3").Sum(m => m.Time);
                
                
                // Set tool changes from machine operations
                analysis.ToolChanges = machineOps.ToolChanges;
                analysis.ProcessesCount = analysis.ProcessesUsed.Count;

                // Total cycle time = machine operations (seconds) + cutting time (converted to seconds) + rapid time (converted to seconds)
                double totalCycleTimeSeconds = machineOperationTime + (analysis.CuttingTime * 60) + (analysis.RapidTime * 60);
                
                // Store times in minutes for consistency with Python output
                analysis.TotalTime = totalCycleTimeSeconds / 60.0;  // Total time in minutes
                analysis.MachineTime = machineOperationTime / 60.0;  // Machine operation time in minutes
                
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

        private CNCMovement ProcessMovement(string line, CNCAnalysis analysis)
        {
            CNCMovement movement = null;

            // G0 - Rapid moves
            if (Regex.IsMatch(line, @"\bG0\b|\bG00\b"))
            {
                movement = CalculateMoveTime(line, RAPID_SPEED, "G0");
                if (movement != null && analysis.MovementStats.ContainsKey("G0"))
                    analysis.MovementStats["G0"]++;
                else if (movement != null)
                    analysis.MovementStats["G0"] = 1;
                    
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
                    if (movement != null && analysis.MovementStats.ContainsKey("G1"))
                        analysis.MovementStats["G1"]++;
                    else if (movement != null)
                        analysis.MovementStats["G1"] = 1;
                        
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
                    if (movement != null && analysis.MovementStats.ContainsKey(code))
                        analysis.MovementStats[code]++;
                    else if (movement != null)
                        analysis.MovementStats[code] = 1;
                        
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

        private double CalculateMachineOperationTime(MachineOperations ops)
        {
            // Calculate total machine operation time in seconds (matching Python logic)
            return ops.ToolChanges * TOOL_CHANGE_TIME +
                   ops.SpindleStarts * SPINDLE_START_TIME +
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

        public FileMonitorTrayApp()
        {
            InitializeForm();
            LoadConfiguration();
            InitializeLocalization();
            InitializeHttpClient();
            CreateTrayIcon();
            
            // Initialize CNC analyzer
            gCodeAnalyzer = new GCodeAnalyzer();
            
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
                if (config.MonitoringEnabled)
                {
                    await StartMonitoring();
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

            if (loginRetryCount >= MAX_LOGIN_RETRIES)
            {
                Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Max login retries reached ({MAX_LOGIN_RETRIES}). Stopping retry timer.");
                StopLoginRetryTimer();
                
                // Show notification that auto-login failed
                trayIcon.ShowBalloonTip(5000, "Login Failed", 
                    $"Failed to login after {MAX_LOGIN_RETRIES} attempts. Please login manually.", 
                    ToolTipIcon.Warning);
                return;
            }

            loginRetryCount++;
            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Login retry attempt {loginRetryCount}/{MAX_LOGIN_RETRIES}...");

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
                            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Login retry failed. Will try again in {LOGIN_RETRY_INTERVAL_MS / 1000} seconds.");
                        }
                    }
                    else
                    {
                        Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Server unreachable. Will try again in {LOGIN_RETRY_INTERVAL_MS / 1000} seconds.");
                    }
                }
                else
                {
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] No stored password found. Stopping retry timer.");
                    StopLoginRetryTimer();
                }
            }
            else
            {
                Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] No username configured. Stopping retry timer.");
                StopLoginRetryTimer();
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
                config.MonitoringEnabled = monitoringActive;
                SaveConfiguration();
                
                if (monitoringActive)
                {
                    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Monitoring started successfully. Watching {fileWatchers.Count} paths.");
                }
            }
            catch
            {
                monitoringActive = false;
                config.MonitoringEnabled = false;
                SaveConfiguration();
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
            
            // Save monitoring state to config
            config.MonitoringEnabled = false;
            SaveConfiguration();
            
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
                        
                        cncAnalysis = await gCodeAnalyzer.AnalyzeFileAsync(changeInfo.FullPath);
                        if (cncAnalysis.AnalysisSuccessful)
                        {
                            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] CNC Analysis completed for {Path.GetFileName(changeInfo.FullPath)} - Total Time: {cncAnalysis.GetFormattedTime()} ({cncAnalysis.TotalTime:F2} min)");
                        }
                        else
                        {
                            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] CNC Analysis failed: {cncAnalysis.ErrorMessage}");
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
    // IMPORTANT: Send only the fields the server expects
    cncAnalysisPayload = new
    {
        Filename = cncAnalysis.Filename,
        TotalTime = cncAnalysis.TotalTime,      // Total cycle time in minutes
        MachineTime = cncAnalysis.MachineTime,  // Machine operation time in minutes
        ToolChanges = cncAnalysis.ToolChanges   // Number of tool changes
    };
    
    Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] CNC payload prepared: TotalTime={cncAnalysis.TotalTime}min, MachineTime={cncAnalysis.MachineTime}min, Tools={cncAnalysis.ToolChanges}");
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