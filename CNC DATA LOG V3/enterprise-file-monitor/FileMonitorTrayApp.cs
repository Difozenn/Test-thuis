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
using System.Net;
using System.Linq;
using System.Text.RegularExpressions;

namespace FileMonitorTray
{
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
        private Timer statusTimer;
        private List<FileSystemWatcher> fileWatchers = new List<FileSystemWatcher>();
        private Dictionary<FileSystemWatcher, MonitoredPathInfo> watcherInfoMap = new Dictionary<FileSystemWatcher, MonitoredPathInfo>();
        private const string APP_NAME = "CNC DATALOG";
        private const string CONFIG_FILE = "tray_config.json";
        private const string STARTUP_KEY_PATH = @"Software\Microsoft\Windows\CurrentVersion\Run";
        
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

        // Configuration class
        public class AppConfig
        {
            public string Username { get; set; } = "";
            public string WebAppUrl { get; set; } = "http://localhost:5002";
            public string Language { get; set; } = "en";
            public bool ScanFileContents { get; set; } = true;
            public int MaxFileSizeMB { get; set; } = 10; // Max file size to scan in MB
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

        private AppConfig config;
        private LocalizationManager localization;

        public FileMonitorTrayApp()
        {
            InitializeForm();
            LoadConfiguration();
            InitializeLocalization();
            InitializeHttpClient();
            CreateTrayIcon();
            
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
                await StartMonitoringOnStartup();
            }
            else if (!string.IsNullOrEmpty(config.Username))
            {
                ShowLoginDialog();
            }

            // Start status checking timer
            statusTimer = new Timer();
            statusTimer.Interval = 30000; // Check every 30 seconds
            statusTimer.Tick += async (s, e) => 
            {
                // Verify connection on each timer tick
                await UpdateTrayIcon();
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

            StopMonitoring(); // Stop file watchers on logout
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
                trayIcon.Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
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
                    trayIcon.Icon = monitoringActive ? CreateOverlayIcon("play") : CreateDefaultIcon();
                }
                else
                {
                    // Server is reachable but returned an error (e.g., 401 Unauthorized after session expired)
                    authenticated = false;
                    currentUser = "";
                    StopMonitoring(); // Stop monitoring if session is lost
                    trayIcon.Text = $@"{APP_NAME} - {localization.T("tooltip_not_logged_in")}";
                    trayIcon.Icon = CreateOverlayIcon("error");
                }
            }
            catch
            {
                // Server is unreachable
                authenticated = false;
                currentUser = "";
                StopMonitoring(); // Stop monitoring if server is down
                trayIcon.Text = $@"{APP_NAME} - {localization.T("tooltip_server_unreachable")}";
                trayIcon.Icon = CreateOverlayIcon("error");
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
            string statusMessage = $@"User: {currentUser}\n" +
                                 $@"Server: {webAppUrl}\n" +
                                 $@"Monitoring: {(monitoringActive ? "Active" : "Inactive")}\n" +
                                 $@"Watching: {fileWatchers.Count} paths\n" +
                                 $@"Content Scanning: {(config.ScanFileContents ? "Enabled" : "Disabled")}\n" +
                                 $@"Max Scan Size: {config.MaxFileSizeMB} MB";
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
            if (trayIcon != null) trayIcon.Visible = false;
            Application.Exit();
        }

        #region File Monitoring
        private async Task StartMonitoringOnStartup()
        {
            if (authenticated) await StartMonitoring();
        }

        private async Task ToggleMonitoring()
        {
            if (monitoringActive)
            {
                StopMonitoring();
            }
            else
            {
                await StartMonitoring();
            }
            await UpdateTrayIcon();
        }

        private async Task StartMonitoring()
        {
            if (!authenticated) return;

            StopMonitoring(); 

            try
            {
                var response = await httpClient.GetAsync($@"{webAppUrl}/api/paths");
                if (!response.IsSuccessStatusCode) return;

                string jsonResponse = await response.Content.ReadAsStringAsync();
                var pathsToMonitor = JsonSerializer.Deserialize<List<MonitoredPathInfo>>(jsonResponse, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

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
            }
            catch
            {
                monitoringActive = false;
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
        }

        private void OnFileSystemEvent(object sender, FileSystemEventArgs e)
        {
            if (watcherInfoMap.TryGetValue((FileSystemWatcher)sender, out var pathInfo))
            {
                LogFileChangeAsync(pathInfo, e.ChangeType.ToString(), e.FullPath);
            }
        }

        private void OnRenamed(object sender, RenamedEventArgs e)
        {
            if (watcherInfoMap.TryGetValue((FileSystemWatcher)sender, out var pathInfo))
            {
                LogFileChangeAsync(pathInfo, "deleted", e.OldFullPath);
                LogFileChangeAsync(pathInfo, "created", e.FullPath);
            }
        }

        private async void LogFileChangeAsync(MonitoredPathInfo pathInfo, string changeType, string fullPath)
        {
            long? fileSize = null;
            CategoryInfo matchedCategory = null;
            string matchedKeyword = null;
            
            try
            {
                // Get categories for matching
                var categories = await GetCategories();
                
                if (File.Exists(fullPath))
                {
                    var fileInfo = new FileInfo(fullPath);
                    fileSize = fileInfo.Length;
                    
                    // First, check file patterns and filename keywords
                    string filename = Path.GetFileName(fullPath).ToLower();
                    string fileExtension = Path.GetExtension(fullPath).ToLower();
                    
                    foreach (var category in categories)
                    {
                        // Check file patterns
                        if (category.file_patterns != null)
                        {
                            foreach (var pattern in category.file_patterns)
                            {
                                try
                                {
                                    if (Regex.IsMatch(fullPath, pattern, RegexOptions.IgnoreCase))
                                    {
                                        matchedCategory = category;
                                        matchedKeyword = $"Pattern: {pattern}";
                                        break;
                                    }
                                }
                                catch { /* Invalid regex pattern */ }
                            }
                        }
                        
                        if (matchedCategory != null) break;
                        
                        // Check keywords in filename
                        if (category.keywords != null)
                        {
                            foreach (var keyword in category.keywords)
                            {
                                if (filename.Contains(keyword.ToLower()))
                                {
                                    matchedCategory = category;
                                    matchedKeyword = $"Filename: {keyword}";
                                    break;
                                }
                            }
                        }
                        
                        if (matchedCategory != null) break;
                    }
                    
                    // If no match yet and content scanning is enabled, scan file contents
                    if (matchedCategory == null && config.ScanFileContents && 
                        SCANNABLE_EXTENSIONS.Contains(fileExtension) &&
                        fileSize < config.MaxFileSizeMB * 1024 * 1024)
                    {
                        try
                        {
                            // Read file content with appropriate encoding
                            string content = await ReadFileContentAsync(fullPath);
                            
                            if (!string.IsNullOrEmpty(content))
                            {
                                string contentLower = content.ToLower();
                                
                                foreach (var category in categories)
                                {
                                    if (category.keywords != null)
                                    {
                                        foreach (var keyword in category.keywords)
                                        {
                                            if (contentLower.Contains(keyword.ToLower()))
                                            {
                                                matchedCategory = category;
                                                matchedKeyword = $"Content: {keyword}";
                                                
                                                // Find the line containing the keyword for better context
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
                                                break;
                                            }
                                        }
                                    }
                                    
                                    if (matchedCategory != null) break;
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"Error scanning file content for {fullPath}: {ex.Message}");
                        }
                    }
                }
            }
            catch { /* Ignore errors if file is gone or inaccessible */ }

            var payload = new
            {
                path_id = pathInfo.id,
                change_type = changeType.ToLower(),
                file_path = fullPath,
                timestamp_utc = DateTime.UtcNow.ToString("o"), // ISO 8601 format
                new_size = fileSize,
                computer_name = Environment.MachineName,
                category_id = matchedCategory?.id,
                matched_keyword = matchedKeyword
            };

            try
            {
                string jsonPayload = JsonSerializer.Serialize(payload);
                var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");
                
                await httpClient.PostAsync($@"{webAppUrl}/api/log_event", content);
            }
            catch
            {
                // Silent fail for event logging
            }
        }

        private async Task<string> ReadFileContentAsync(string filePath)
        {
            const int MAX_RETRIES = 3;
            const int RETRY_DELAY_MS = 100;
            
            for (int retry = 0; retry < MAX_RETRIES; retry++)
            {
                try
                {
                    // Try to detect encoding
                    Encoding encoding = DetectFileEncoding(filePath);
                    
                    // Read file with detected encoding
                    using (var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                    using (var reader = new StreamReader(stream, encoding))
                    {
                        return await reader.ReadToEndAsync();
                    }
                }
                catch (IOException) when (retry < MAX_RETRIES - 1)
                {
                    // File might be locked, wait and retry
                    await Task.Delay(RETRY_DELAY_MS);
                }
                catch
                {
                    // Other errors, return empty
                    return string.Empty;
                }
            }
            
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