using System;
using System.Collections.Generic;
using System.Globalization;

namespace FileMonitorTray
{
    public class LocalizationManager
    {
        private static LocalizationManager _instance;
        public static LocalizationManager Instance => _instance ??= new LocalizationManager();

        private Dictionary<string, Dictionary<string, string>> translations;
        private string currentLanguage = "en";

        public event EventHandler LanguageChanged;

        private LocalizationManager()
        {
            InitializeTranslations();
            
            // Try to detect system language
            var systemLang = CultureInfo.CurrentUICulture.TwoLetterISOLanguageName;
            if (translations.ContainsKey(systemLang))
            {
                currentLanguage = systemLang;
            }
        }

        public string CurrentLanguage
        {
            get => currentLanguage;
            set
            {
                if (translations.ContainsKey(value) && currentLanguage != value)
                {
                    currentLanguage = value;
                    LanguageChanged?.Invoke(this, EventArgs.Empty);
                }
            }
        }

        public string[] AvailableLanguages => new[] { "en", "nl" };

        public string GetLanguageName(string code)
        {
            return code switch
            {
                "en" => "English",
                "nl" => "Nederlands",
                _ => code
            };
        }

        public string Translate(string key)
        {
            if (translations.TryGetValue(currentLanguage, out var langDict) &&
                langDict.TryGetValue(key, out var translation))
            {
                return translation;
            }

            // Fallback to English
            if (currentLanguage != "en" && 
                translations.TryGetValue("en", out var enDict) &&
                enDict.TryGetValue(key, out var enTranslation))
            {
                return enTranslation;
            }

            // Return key if no translation found
            return key;
        }

        // Convenience method for shorter syntax
        public string T(string key) => Translate(key);

        private void InitializeTranslations()
        {
            translations = new Dictionary<string, Dictionary<string, string>>
            {
                ["en"] = new Dictionary<string, string>
                {
                    // Application
                    ["app_title"] = "Enterprise File Monitor",
                    ["app_running"] = "File Monitor is running in the system tray",
                    ["already_running"] = "Enterprise File Monitor is already running in the system tray.",
                    
                    // Login
                    ["login_title"] = "Login - Enterprise File Monitor",
                    ["please_login"] = "Please login to start monitoring",
                    ["username"] = "Username:",
                    ["password"] = "Password:",
                    ["remember_me"] = "Remember me",
                    ["login"] = "Login",
                    ["cancel"] = "Cancel",
                    ["login_success"] = "Login successful",
                    ["login_failed"] = "Invalid username or password",
                    ["please_login_first"] = "Please login first",
                    ["not_logged_in"] = "Not Logged In",
                    ["validation_error"] = "Validation Error",
                    ["enter_username"] = "Please enter a username.",
                    ["enter_password"] = "Please enter a password.",
                    
                    // Tray Menu
                    ["user"] = "User",
                    ["open_web_interface"] = "Open Web Interface",
                    ["manual_entry"] = "Manual Entry...",
                    ["show_status"] = "Show Status",
                    ["toggle_monitoring"] = "Toggle Monitoring",
                    ["switch_user"] = "Switch User...",
                    ["language"] = "Language",
                    ["add_to_startup"] = "Add to Startup",
                    ["remove_from_startup"] = "Remove from Startup",
                    ["quit"] = "Quit",
                    
                    // Status
                    ["status_title"] = "File Monitor Status",
                    ["logged_in_as"] = "Logged in as",
                    ["monitor_status"] = "Monitor Status",
                    ["active_monitors"] = "Active Monitors",
                    ["monitored_directories"] = "Monitored Directories",
                    ["web_interface"] = "Web Interface",
                    ["running"] = "Running",
                    ["stopped"] = "Stopped",
                    ["active"] = "Active",
                    ["inactive"] = "Inactive",
                    ["status_not_logged_in"] = "Status: Not logged in\n\nPlease login to view monitoring status.",
                    ["unable_to_get_status"] = "Unable to get status",
                    ["connection_error"] = "Web service not responding.\nPlease check if the application is running.",
                    
                    // Manual Entry
                    ["manual_entry_title"] = "Manual Entry - File Monitor",
                    ["file_path"] = "File Path:",
                    ["browse"] = "Browse...",
                    ["category"] = "Category:",
                    ["keyword_optional"] = "Keyword (Optional):",
                    ["submit"] = "Submit",
                    ["submitting"] = "Submitting...",
                    ["enter_file_path"] = "Please enter a file path.",
                    ["select_category"] = "Please select a category.",
                    ["entry_added"] = "Entry added successfully!",
                    ["failed_to_add_entry"] = "Failed to add entry",
                    ["select_file"] = "Select File",
                    ["all_files"] = "All Files (*.*)|*.*",
                    
                    // Monitoring
                    ["monitoring_started"] = "Monitoring started",
                    ["monitoring_stopped"] = "Monitoring stopped",
                    ["failed_toggle_monitoring"] = "Failed to toggle monitoring",
                    ["unable_toggle_monitoring"] = "Unable to toggle monitoring",
                    ["could_not_start_monitoring"] = "Could not start monitoring",
                    
                    // Startup
                    ["startup_title"] = "Startup",
                    ["added_to_startup"] = "Added to Windows startup",
                    ["removed_from_startup"] = "Removed from Windows startup",
                    ["failed_modify_startup"] = "Failed to modify startup settings",
                    
                    // General
                    ["success"] = "Success",
                    ["error"] = "Error",
                    ["warning"] = "Warning",
                    ["information"] = "Information",
                    ["confirmation"] = "Confirmation",
                    ["yes"] = "Yes",
                    ["no"] = "No",
                    ["ok"] = "OK",
                    
                    // Errors
                    ["connection_error_server"] = "Cannot connect to server at {0}\nPlease ensure the server is running and accessible.",
                    ["startup_error"] = "Failed to start web application. Please ensure Python and required packages are installed.",
                    ["error_starting_app"] = "Error starting web application",
                    ["could_not_open_browser"] = "Could not open browser",
                    ["error_loading_categories"] = "Error loading categories",
                    
                    // Dialogs
                    ["switch_user_confirm"] = "Are you sure you want to logout and switch user?",
                    ["quit_confirm"] = "Are you sure you want to quit File Monitor?",
                    
                    // Tooltips
                    ["tooltip_not_logged_in"] = "Enterprise File Monitor - Not logged in",
                    ["tooltip_logged_in"] = "Enterprise File Monitor - {0} ({1})"
                },
                
                ["nl"] = new Dictionary<string, string>
                {
                    // Application
                    ["app_title"] = "Enterprise Bestandsmonitor",
                    ["app_running"] = "Bestandsmonitor draait in het systeemvak",
                    ["already_running"] = "Enterprise Bestandsmonitor draait al in het systeemvak.",
                    
                    // Login
                    ["login_title"] = "Inloggen - Enterprise Bestandsmonitor",
                    ["please_login"] = "Log in om monitoring te starten",
                    ["username"] = "Gebruikersnaam:",
                    ["password"] = "Wachtwoord:",
                    ["remember_me"] = "Onthoud mij",
                    ["login"] = "Inloggen",
                    ["cancel"] = "Annuleren",
                    ["login_success"] = "Inloggen geslaagd",
                    ["login_failed"] = "Ongeldige gebruikersnaam of wachtwoord",
                    ["please_login_first"] = "Log eerst in",
                    ["not_logged_in"] = "Niet Ingelogd",
                    ["validation_error"] = "Validatiefout",
                    ["enter_username"] = "Voer een gebruikersnaam in.",
                    ["enter_password"] = "Voer een wachtwoord in.",
                    
                    // Tray Menu
                    ["user"] = "Gebruiker",
                    ["open_web_interface"] = "Open Webinterface",
                    ["manual_entry"] = "Handmatige Invoer...",
                    ["show_status"] = "Toon Status",
                    ["toggle_monitoring"] = "Monitoring Aan/Uit",
                    ["switch_user"] = "Gebruiker Wisselen...",
                    ["language"] = "Taal",
                    ["add_to_startup"] = "Toevoegen aan Opstarten",
                    ["remove_from_startup"] = "Verwijderen van Opstarten",
                    ["quit"] = "Afsluiten",
                    
                    // Status
                    ["status_title"] = "Bestandsmonitor Status",
                    ["logged_in_as"] = "Ingelogd als",
                    ["monitor_status"] = "Monitor Status",
                    ["active_monitors"] = "Actieve Monitors",
                    ["monitored_directories"] = "Gemonitorde Mappen",
                    ["web_interface"] = "Webinterface",
                    ["running"] = "Actief",
                    ["stopped"] = "Gestopt",
                    ["active"] = "Actief",
                    ["inactive"] = "Inactief",
                    ["status_not_logged_in"] = "Status: Niet ingelogd\n\nLog in om de monitoring status te bekijken.",
                    ["unable_to_get_status"] = "Kan status niet ophalen",
                    ["connection_error"] = "Webservice reageert niet.\nControleer of de applicatie actief is.",
                    
                    // Manual Entry
                    ["manual_entry_title"] = "Handmatige Invoer - Bestandsmonitor",
                    ["file_path"] = "Bestandspad:",
                    ["browse"] = "Bladeren...",
                    ["category"] = "Categorie:",
                    ["keyword_optional"] = "Trefwoord (Optioneel):",
                    ["submit"] = "Verzenden",
                    ["submitting"] = "Verzenden...",
                    ["enter_file_path"] = "Voer een bestandspad in.",
                    ["select_category"] = "Selecteer een categorie.",
                    ["entry_added"] = "Invoer succesvol toegevoegd!",
                    ["failed_to_add_entry"] = "Toevoegen van invoer mislukt",
                    ["select_file"] = "Selecteer Bestand",
                    ["all_files"] = "Alle Bestanden (*.*)|*.*",
                    
                    // Monitoring
                    ["monitoring_started"] = "Monitoring gestart",
                    ["monitoring_stopped"] = "Monitoring gestopt",
                    ["failed_toggle_monitoring"] = "Monitoring aan/uit zetten mislukt",
                    ["unable_toggle_monitoring"] = "Kan monitoring niet aan/uit zetten",
                    ["could_not_start_monitoring"] = "Kon monitoring niet starten",
                    
                    // Startup
                    ["startup_title"] = "Opstarten",
                    ["added_to_startup"] = "Toegevoegd aan Windows opstarten",
                    ["removed_from_startup"] = "Verwijderd van Windows opstarten",
                    ["failed_modify_startup"] = "Wijzigen van opstartinstellingen mislukt",
                    
                    // General
                    ["success"] = "Succes",
                    ["error"] = "Fout",
                    ["warning"] = "Waarschuwing",
                    ["information"] = "Informatie",
                    ["confirmation"] = "Bevestiging",
                    ["yes"] = "Ja",
                    ["no"] = "Nee",
                    ["ok"] = "OK",
                    
                    // Errors
                    ["connection_error_server"] = "Kan geen verbinding maken met server op {0}\nZorg ervoor dat de server actief en bereikbaar is.",
                    ["startup_error"] = "Starten van webapplicatie mislukt. Zorg ervoor dat Python en vereiste pakketten zijn geïnstalleerd.",
                    ["error_starting_app"] = "Fout bij starten van webapplicatie",
                    ["could_not_open_browser"] = "Kon browser niet openen",
                    ["error_loading_categories"] = "Fout bij laden van categorieën",
                    
                    // Dialogs
                    ["switch_user_confirm"] = "Weet u zeker dat u wilt uitloggen en van gebruiker wilt wisselen?",
                    ["quit_confirm"] = "Weet u zeker dat u Bestandsmonitor wilt afsluiten?",
                    
                    // Tooltips
                    ["tooltip_not_logged_in"] = "Enterprise Bestandsmonitor - Niet ingelogd",
                    ["tooltip_logged_in"] = "Enterprise Bestandsmonitor - {0} ({1})"
                }
            };
        }
    }
}