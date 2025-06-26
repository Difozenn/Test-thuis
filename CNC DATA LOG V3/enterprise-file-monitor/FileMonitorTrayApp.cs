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
        private const string APP_NAME = "CNC DATALOG";
        private const string CONFIG_FILE = "tray_config.json";
        private const string STARTUP_KEY_PATH = @"Software\Microsoft\Windows\CurrentVersion\Run";

        // Configuration class
        public class AppConfig
        {
            public string Username { get; set; } = "";
            public string WebAppUrl { get; set; } = "http://localhost:5002";
            public string Language { get; set; } = "en";
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
                    Console.WriteLine($"Loading config from: {Path.GetFullPath(CONFIG_FILE)}");
                    Console.WriteLine($"Config content: {json}");
                    
                    config = JsonSerializer.Deserialize<AppConfig>(json) ?? new AppConfig();
                    Console.WriteLine($"Loaded URL: {config.WebAppUrl}");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error loading config: {ex.Message}");
                    config = new AppConfig();
                }
            }
            else
            {
                Console.WriteLine($"Config file not found at: {Path.GetFullPath(CONFIG_FILE)}");
            }
            
            // Check environment variable for URL
            string envUrl = Environment.GetEnvironmentVariable("FILE_MONITOR_URL");
            if (!string.IsNullOrEmpty(envUrl))
            {
                Console.WriteLine($"Overriding URL with environment variable: {envUrl}");
                config.WebAppUrl = envUrl;
            }
            
            webAppUrl = config.WebAppUrl;
            
            Console.WriteLine($"Final URL: {webAppUrl}");
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
                CreateTrayMenu(); // Refresh menu with new language
                UpdateTrayIcon().Wait();
            };
        }

        private void InitializeHttpClient()
        {
            cookieContainer = new CookieContainer();
            var handler = new HttpClientHandler()
            {
                CookieContainer = cookieContainer,
                UseCookies = true
            };
            
            httpClient = new HttpClient(handler);
            httpClient.Timeout = TimeSpan.FromSeconds(10);
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
                return response.IsSuccessStatusCode;
            }
            catch
            {
                return false;
            }
        }

        // REMOVED - The web app should run on a separate server, not started by the tray app

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
                var loginData = new FormUrlEncodedContent(new[]
                {
                    new KeyValuePair<string, string>("username", username),
                    new KeyValuePair<string, string>("password", password)
                });

                var response = await httpClient.PostAsync($"{webAppUrl}/login", loginData);
                
                if (response.IsSuccessStatusCode || response.StatusCode == HttpStatusCode.Redirect)
                {
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
                        // No balloon tip for login success
                        return true;
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Login error: {ex.Message}");
            }
            
            return false;
        }

        private void Logout()
        {
            try
            {
                httpClient.GetAsync($"{webAppUrl}/logout").Wait(5000);
            }
            catch { }
            
            authenticated = false;
            currentUser = "";
            monitoringActive = false;
            
            if (!string.IsNullOrEmpty(config.Username))
            {
                DeleteStoredPassword(config.Username);
                config.Username = "";
                SaveConfiguration();
            }
            
            UpdateTrayIcon().Wait();
        }

        private async Task StartMonitoringOnStartup()
        {
            if (!authenticated) return;

            try
            {
                var response = await httpClient.PostAsync($"{webAppUrl}/api/monitor/start", null);
                if (response.IsSuccessStatusCode)
                {
                    monitoringActive = true;
                    // No balloon tip for monitoring started
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error starting monitoring: {ex.Message}");
            }
        }

        private void CreateTrayIcon()
        {
            trayIcon = new NotifyIcon();
            
            // Create default icon
            try
            {
                // Load the icon from the executable's resources
                trayIcon.Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
            }
            catch
            {
                // Fallback to a default system icon if loading fails
                trayIcon.Icon = SystemIcons.Application;
            }
            trayIcon.Text = localization.T("tooltip_not_logged_in");
            trayIcon.Visible = true;
            
            CreateTrayMenu();
            
            // Handle double-click to open browser
            trayIcon.DoubleClick += (s, e) => OpenBrowser();
            
            // Handle context menu click
            trayIcon.MouseUp += TrayIcon_MouseUp;
        }

        private void TrayIcon_MouseUp(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Right)
            {
                // Refresh menu with current state
                CreateTrayMenu();
                
                // Show the context menu manually at cursor position
                trayMenu.Show(Cursor.Position);
            }
            else if (e.Button == MouseButtons.Left)
            {
                // Hide any open context menu when clicking elsewhere
                if (trayMenu != null && trayMenu.Visible)
                {
                    trayMenu.Hide();
                }
            }
        }

        private void CreateTrayMenu()
        {
            if (trayMenu != null)
            {
                trayMenu.Dispose();
            }
            
            trayMenu = new ContextMenuStrip();
            
            // Add event handlers for better menu management
            trayMenu.Opening += (s, e) =>
            {
                // Refresh authentication status when menu opens
                Task.Run(async () => await UpdateTrayIcon());
            };
            
            trayMenu.Closed += (s, e) =>
            {
                // Ensure menu is properly disposed when closed
                if (trayMenu != null && trayMenu.IsDisposed == false)
                {
                    trayMenu.Hide();
                }
            };
            
            if (authenticated)
            {
                trayMenu.Items.Add($"{localization.T("user")}: {currentUser}").Enabled = false;
                trayMenu.Items.Add(new ToolStripSeparator());
                trayMenu.Items.Add(localization.T("open_web_interface"), null, (s, e) => OpenBrowser());
                trayMenu.Items.Add(localization.T("manual_entry"), null, (s, e) => ShowManualEntry());
                trayMenu.Items.Add("Add Files/Directories...", null, (s, e) => ShowFileSelector());
                trayMenu.Items.Add(new ToolStripSeparator());
                trayMenu.Items.Add(localization.T("show_status"), null, async (s, e) => await ShowStatus());
                trayMenu.Items.Add(localization.T("toggle_monitoring"), null, async (s, e) => await ToggleMonitoring());
                trayMenu.Items.Add(new ToolStripSeparator());
                trayMenu.Items.Add(localization.T("switch_user"), null, (s, e) => SwitchUser());
            }
            else
            {
                trayMenu.Items.Add(localization.T("login"), null, (s, e) => ShowLoginDialog());
                trayMenu.Items.Add(localization.T("open_web_interface"), null, (s, e) => OpenBrowser());
                trayMenu.Items.Add(new ToolStripSeparator());
            }
            
            // Language submenu
            var languageMenu = new ToolStripMenuItem(localization.T("language"));
            foreach (string langCode in localization.AvailableLanguages)
            {
                var langItem = new ToolStripMenuItem(localization.GetLanguageName(langCode))
                {
                    Checked = langCode == localization.CurrentLanguage,
                    Tag = langCode
                };
                langItem.Click += (s, e) =>
                {
                    var item = s as ToolStripMenuItem;
                    localization.CurrentLanguage = (string)item.Tag;
                };
                languageMenu.DropDownItems.Add(langItem);
            }
            trayMenu.Items.Add(languageMenu);
            
            string startupText = IsStartupEnabled() ? 
                localization.T("remove_from_startup") : localization.T("add_to_startup");
            trayMenu.Items.Add(startupText, null, (s, e) => ToggleStartup());
            trayMenu.Items.Add(new ToolStripSeparator());
            trayMenu.Items.Add(localization.T("quit"), null, (s, e) => QuitApplication());
        }

        private Icon CreateDefaultIcon()
        {
            try
            {
                // Load the icon from the executable's resources
                return Icon.ExtractAssociatedIcon(Application.ExecutablePath);
            }
            catch
            {
                // Fallback to a default system icon if loading fails
                return SystemIcons.Application;
            }
        }

        // Add this method to verify authentication is still valid
        private async Task<bool> VerifyAuthentication()
        {
            if (!authenticated)
                return false;
                
            try
            {
                var response = await httpClient.GetAsync($"{webAppUrl}/api/monitor/status");
                if (response.IsSuccessStatusCode)
                {
                    return true;
                }
                else if (response.StatusCode == HttpStatusCode.Unauthorized || 
                         response.StatusCode == HttpStatusCode.Forbidden)
                {
                    // Server says we're not authenticated
                    authenticated = false;
                    currentUser = "";
                    return false;
                }
            }
            catch (HttpRequestException)
            {
                // Can't connect to server - show as disconnected
                return false;
            }
            catch (TaskCanceledException)
            {
                // Timeout - server not responding
                return false;
            }
            
            return authenticated;
        }

        // Updated UpdateTrayIcon method
        private async Task UpdateTrayIcon()
        {
            bool isConnected = await VerifyAuthentication();
            
            if (isConnected)
            {
                string status = monitoringActive ? localization.T("active") : localization.T("inactive");
                trayIcon.Text = string.Format(localization.T("tooltip_logged_in"), currentUser, status);
                
                // Check monitoring status
                try
                {
                    var response = await httpClient.GetAsync($"{webAppUrl}/api/monitor/status");
                    if (response.IsSuccessStatusCode)
                    {
                        string json = await response.Content.ReadAsStringAsync();
                        var statusData = JsonSerializer.Deserialize<JsonElement>(json);
                        monitoringActive = statusData.GetProperty("running").GetBoolean();
                    }
                }
                catch
                {
                    monitoringActive = false;
                }
            }
            else
            {
                // Not connected or not authenticated
                authenticated = false;
                currentUser = "";
                monitoringActive = false;
                trayIcon.Text = localization.T("tooltip_not_logged_in") + $" ({webAppUrl})";
                
                // Refresh menu to show login option
                CreateTrayMenu();
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
                            this.Invoke(() => CreateTrayMenu());
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
                MessageBox.Show(localization.T("please_login_first"), localization.T("not_logged_in"), 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                ShowLoginDialog();
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
                ShowError($"Error opening manual entry form: {ex.Message}");
            }
        }

        private void ShowFileSelector()
        {
            if (!authenticated)
            {
                MessageBox.Show(localization.T("please_login_first"), localization.T("not_logged_in"), 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                ShowLoginDialog();
                return;
            }

            try
            {
                using (var fileSelectorForm = new FileSelectorForm(httpClient, webAppUrl, currentUser, localization))
                {
                    fileSelectorForm.ShowDialog();
                }
            }
            catch (Exception ex)
            {
                ShowError($"Error opening file selector form: {ex.Message}");
            }
        }

        // Updated ShowStatus method with connection check
        private async Task ShowStatus()
        {
            // First verify we're actually connected
            bool isConnected = await VerifyAuthentication();
            
            if (!isConnected)
            {
                MessageBox.Show($"Not connected to server at {webAppUrl}\n\nThe server appears to be offline or you are not authenticated.",
                    localization.T("status_title"), MessageBoxButtons.OK, MessageBoxIcon.Warning);
                
                // Update UI to reflect disconnected state
                authenticated = false;
                CreateTrayMenu();
                return;
            }

            try
            {
                var response = await httpClient.GetAsync($"{webAppUrl}/api/monitor/status");
                if (response.IsSuccessStatusCode)
                {
                    string json = await response.Content.ReadAsStringAsync();
                    var data = JsonSerializer.Deserialize<JsonElement>(json);
                    
                    bool running = data.GetProperty("running").GetBoolean();
                    int paths = data.GetProperty("paths").GetInt32();
                    int files = data.TryGetProperty("files", out var f) ? f.GetInt32() : 0;
                    int directories = data.TryGetProperty("directories", out var d) ? d.GetInt32() : 0;
                    int monitors = data.TryGetProperty("monitors_count", out var mc) ? mc.GetInt32() : 0;
                    
                    string message = $"{localization.T("logged_in_as")}: {currentUser}\n" +
                                   $"{localization.T("monitor_status")}: {(running ? localization.T("running") : localization.T("stopped"))}\n" +
                                   $"{localization.T("active_monitors")}: {monitors}\n" +
                                   $"Total Paths: {paths}\n" +
                                   $"• Files: {files}\n" +
                                   $"• Directories: {directories}\n\n" +
                                   $"{localization.T("web_interface")}: {webAppUrl}";
                    
                    MessageBox.Show(message, localization.T("status_title"), 
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
                else
                {
                    MessageBox.Show($"Server responded with error: {response.StatusCode}\nURL: {webAppUrl}", 
                        localization.T("error"), MessageBoxButtons.OK, MessageBoxIcon.Error);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Cannot connect to server at {webAppUrl}\n\nError: {ex.Message}",
                    localization.T("connection_error"), MessageBoxButtons.OK, MessageBoxIcon.Error);
                    
                // Clear authentication state
                authenticated = false;
                CreateTrayMenu();
            }
        }

        private void ShowError(string message)
        {
            // Silent error handling - log to console instead
            Console.WriteLine($"Error: {message}");
        }

        private async Task ToggleMonitoring()
        {
            if (!await VerifyAuthentication())
            {
                MessageBox.Show(localization.T("please_login_first"), localization.T("not_logged_in"), 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                ShowLoginDialog();
                return;
            }

            try
            {
                // Get current status first
                var statusResponse = await httpClient.GetAsync($"{webAppUrl}/api/monitor/status");
                if (statusResponse.IsSuccessStatusCode)
                {
                    string json = await statusResponse.Content.ReadAsStringAsync();
                    var data = JsonSerializer.Deserialize<JsonElement>(json);
                    bool running = data.GetProperty("running").GetBoolean();
                    
                    string endpoint = running ? "/api/monitor/stop" : "/api/monitor/start";
                    var response = await httpClient.PostAsync($"{webAppUrl}{endpoint}", null);
                    
                    if (response.IsSuccessStatusCode)
                    {
                        monitoringActive = !running;
                        // No balloon notifications for monitoring status changes
                        await UpdateTrayIcon();
                    }
                    else
                    {
                        ShowError(localization.T("failed_toggle_monitoring"));
                    }
                }
            }
            catch (Exception)
            {
                // Silently handle monitoring toggle errors
            }
        }

        private void SwitchUser()
        {
            // No confirmation dialog
            Logout();
            CreateTrayMenu();
            ShowLoginDialog();
        }

        private bool IsStartupEnabled()
        {
            try
            {
                using (var key = Registry.CurrentUser.OpenSubKey(STARTUP_KEY_PATH, false))
                {
                    return key?.GetValue(APP_NAME) != null;
                }
            }
            catch
            {
                return false;
            }
        }

        private void ToggleStartup()
        {
            try
            {
                using (var key = Registry.CurrentUser.OpenSubKey(STARTUP_KEY_PATH, true))
                {
                    if (IsStartupEnabled())
                    {
                        key?.DeleteValue(APP_NAME, false);
                    }
                    else
                    {
                        string appPath = Application.ExecutablePath;
                        key?.SetValue(APP_NAME, $"\"{appPath}\"");
                    }
                }
                
                CreateTrayMenu(); // Refresh menu
            }
            catch (Exception)
            {
                // Silently handle startup registry errors
            }
        }

        private void QuitApplication()
        {
            // No confirmation, just exit
            statusTimer?.Stop();
            
            trayIcon.Visible = false;
            Application.Exit();
        }

        // Password storage using Windows Data Protection API
        private void StorePassword(string username, string password)
        {
            try
            {
                byte[] data = Encoding.UTF8.GetBytes(password);
                byte[] encrypted = ProtectedData.Protect(data, null, DataProtectionScope.CurrentUser);
                string fileName = $"{username}_pwd.dat";
                File.WriteAllBytes(fileName, encrypted);
            }
            catch
            {
                // Ignore password storage errors
            }
        }

        private string GetStoredPassword(string username)
        {
            try
            {
                string fileName = $"{username}_pwd.dat";
                if (File.Exists(fileName))
                {
                    byte[] encrypted = File.ReadAllBytes(fileName);
                    byte[] data = ProtectedData.Unprotect(encrypted, null, DataProtectionScope.CurrentUser);
                    return Encoding.UTF8.GetString(data);
                }
            }
            catch
            {
                // Ignore password retrieval errors
            }
            return "";
        }

        private void DeleteStoredPassword(string username)
        {
            try
            {
                string fileName = $"{username}_pwd.dat";
                if (File.Exists(fileName))
                {
                    File.Delete(fileName);
                }
            }
            catch
            {
                // Ignore deletion errors
            }
        }

        protected override void SetVisibleCore(bool value)
        {
            base.SetVisibleCore(false); // Always keep form hidden
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            e.Cancel = true; // Prevent form from closing, just hide it
            this.Hide();
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                statusTimer?.Stop();
                statusTimer?.Dispose();
                trayIcon?.Dispose();
                trayMenu?.Dispose();
                httpClient?.Dispose();
            }
            base.Dispose(disposing);
        }
    }
}