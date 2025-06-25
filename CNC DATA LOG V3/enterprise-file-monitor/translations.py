# translations.py - Language and Translation Module
"""
Language and translation management for Enterprise File Monitor
"""

from flask_login import current_user

# Supported languages configuration
LANGUAGES = {
    'en': 'English',
    'nl': 'Nederlands'
}

# Translation dictionary
TRANSLATIONS = {
    'en': {
        # Navigation
        'dashboard': 'Dashboard',
        'events': 'Events',
        'manual_entry': 'Manual Entry',
        'reports': 'Reports',
        'administration': 'ADMINISTRATION',
        'categories': 'Categories',
        'settings': 'Settings',
        'users': 'Users',
        'change_password': 'Change Password',
        'logout': 'Logout',
        'login': 'Login',
        
        # Dashboard
        'monitor_overview': 'Monitor overview and statistics',
        'filter_by_user': 'Filter by User:',
        'all_users': 'All Users',
        'showing_data_for': 'Showing data for:',
        'clear_filter': 'Clear Filter',
        'total_events': 'Total Events',
        'todays_events': "Today's Events",
        'monitor_status': 'Monitor Status',
        'active_directories': 'Active Directories',
        'event_trend': 'Event Trend (Last 7 Days)',
        'category_distribution': 'Category Distribution',
        'events_by_user': 'Events by User',
        'recent_events': 'Recent Events',
        'view_all': 'View All',
        'view_dashboard': 'View Dashboard',
        'view_events': 'View Events',
        
        # File change tracking
        'file_changes_distribution': 'File Changes Distribution',
        'top_changed_files': 'Top Changed Files',
        'no_file_changes_yet': 'No file changes detected yet',
        'start_monitoring_files_message': 'Start monitoring files to see change statistics',
        'monitored_files': 'Monitored Files',
        'total_file_changes': 'Total Changes',
        'most_active_files': 'Most Active Files',
        'no_file_changes_detected': 'No file changes detected',
        'change_history_for': 'Change History for',
        'total_changes': 'Total Changes',
        'last_change': 'Last Change',
        'size_change': 'Size Change',
        'error_loading_history': 'Error loading change history',
        'monitored_paths': 'Monitored Paths',
        'file_or_directory_path': 'File or Directory Path',
        'add_path': 'Add Path',
        'browse_file': 'Browse File',
        'browse_directory': 'Browse Directory',
        'last_modified': 'Last Modified',
        'size': 'Size',
        'not_checked_yet': 'Not checked yet',
        'directory_monitoring': 'Directory monitoring',
        'no_paths_configured': 'No paths configured',
        'path_validation': 'Path Validation',
        'path_exists': 'Path exists',
        'path_is_directory': 'Path is a directory',
        'path_is_file': 'Path is a file',
        'path_readable': 'Path is readable',
        
        # Common
        'actions': 'Actions',
        'time': 'Time',
        'timestamp': 'Timestamp',
        'category': 'Category',
        'file': 'File',
        'file_path': 'File Path',
        'computer': 'Computer',
        'user': 'User',
        'type': 'Type',
        'keyword': 'Keyword',
        'keywords': 'Keywords',
        'file_patterns': 'File Patterns',
        'date': 'Date',
        'from_date': 'From Date',
        'to_date': 'To Date',
        'filter': 'Filter',
        'submit': 'Submit',
        'cancel': 'Cancel',
        'save': 'Save',
        'delete': 'Delete',
        'edit': 'Edit',
        'add': 'Add',
        'create': 'Create',
        'update': 'Update',
        'enable': 'Enable',
        'disable': 'Disable',
        'active': 'Active',
        'inactive': 'Inactive',
        'status': 'Status',
        'running': 'Running',
        'stopped': 'Stopped',
        'yes': 'Yes',
        'no': 'No',
        'confirm_delete': 'Are you sure you want to delete this?',
        'no_results': 'No results found',
        'loading': 'Loading...',
        'remove': 'Remove',
        'previous': 'Previous',
        'next': 'Next',
        'me': 'Me',
        'admin': 'Admin',
        'recursive': 'Recursive',
        'directory': 'Directory',
        'details': 'Details',
        'yesterday': 'Yesterday',
        'day': 'Day',
        'validate': 'Validate',
        'high': 'High',
        'medium': 'Medium',
        'low': 'Low',
        'off': 'Off',
        'efficiency': 'Efficiency',
        'current_week': 'Current Week',
        'daily_schedule': 'Daily Schedule',
        'day_of_week': 'Day of Week',
        'all_categories': 'All Categories',
        'amount': 'Amount',
        'description': 'Description',
        
        # Categories
        'manage_categories': 'Manage event categories',
        'add_category': 'Add Category',
        'edit_category': 'Edit Category',
        'category_name': 'Category Name',
        'color': 'Color',
        'no_keywords': 'No keywords defined',
        'no_patterns': 'No patterns defined',
        'no_categories_defined': 'No categories defined yet',
        'create_one_now': 'Create one now',
        'define_category': 'Define keywords and patterns for automatic categorization',
        'enter_keyword': 'Enter keyword',
        'add_keyword': 'Add Keyword',
        'file_patterns_regex': 'File Patterns (regex)',
        'eg_log': 'e.g., .*\\.log',
        'add_pattern': 'Add Pattern',
        
        # Events
        'browse_filter_events': 'Browse and filter recorded events',
        'uncategorized': 'Uncategorized',
        'no_events_found': 'No events found',
        
        # Users
        'manage_users': 'Manage system users and permissions',
        'add_user': 'Add User',
        'username': 'Username',
        'email': 'Email',
        'password': 'Password',
        'role': 'Role',
        'created': 'Created',
        'operator': 'Operator',
        'you': 'You',
        'reset_password': 'Reset Password',
        'new_password': 'New Password',
        
        # Change Password
        'update_your_password': 'Update your account password',
        'current_password': 'Current Password',
        'confirm_password': 'Confirm Password',
        
        # Enhanced Dashboard
        'work_hours': 'Work Hours',
        'work_start_time': 'Work Start Time',
        'work_end_time': 'Work End Time',
        'work_hours_configuration': 'Weekly Work Hours Configuration',
        'work_hours_description': 'Configure work hours for each day of the week for normalized reporting and analysis',
        'save_work_hours': 'Save Work Hours',
        'last_refresh': 'Last Refresh',
        'date_range': 'Date Range',
        'refresh': 'Refresh',
        'today': 'Today',
        'this_week': 'This Week',
        'last_week': 'Last Week',
        'this_month': 'This Month',
        'last_month': 'Last Month',
        'this_quarter': 'This Quarter',
        'this_year': 'This Year',
        'custom_range': 'Custom Range',
        'avg_events_per_hour': 'Avg Events/Hour',
        'during_work_hours': 'During work hours',
        'active_paths': 'Active Paths',
        'files': 'Files',
        'directories': 'Directories',
        'total': 'Total',
        'recent_activity': 'Recent Activity',
        'last_50_events': 'Last 50 events',
        'no_recent_activity': 'No recent activity',
        'events_per_category': 'Events per Category',
        'daily_activity': 'Daily Activity',
        'events_per_work_hour': 'Events per Work Hour',
        'normalized': 'Normalized',
        'events_per_monitored_path': 'Events per Monitored File',
        'hourly_activity_today': 'Hourly Activity Today',
        'export': 'Export',
        'top_categories_today': 'Top Categories Today',
        'user_activity_today': 'User Activity Today',
        'no_data': 'No data',
        'operators_only': 'Operators Only',
        'normalized_events': 'Normalized Events',
        'path': 'Path',
        
        # Weekly Work Hours
        'monday': 'Monday',
        'tuesday': 'Tuesday', 
        'wednesday': 'Wednesday',
        'thursday': 'Thursday',
        'friday': 'Friday',
        'saturday': 'Saturday',
        'sunday': 'Sunday',
        'hours_per_day': 'Hours per Day',
        'total_weekly_hours': 'Total Weekly Hours',
        'average_daily_hours': 'Average Daily Hours',
        'working_days': 'Working Days',
        'non_working_days': 'Non-Working Days',
        'events_per_hour': 'Events per Hour',
        'weekly_activity_normalized': 'Weekly Activity Normalized (Events per Work Hour)',
        'no_work_hours_configured': 'No work hours configured',
        'configure_work_hours': 'Configure Work Hours',
        
        # Reports
        'generate_export_reports': 'Generate and export professional reports',
        'dashboard_report': 'Dashboard Report',
        'export_dashboard_charts': 'Export all dashboard charts and KPIs',
        'detailed_excel_report': 'Detailed Excel Report',
        'comprehensive_data_export': 'Comprehensive data export with multiple sheets',
        'summary_report': 'Summary Report',
        'high_level_overview': 'High-level overview with key metrics',
        'audit_report': 'Audit Report',
        'compliance_security_report': 'Compliance and security audit trail',
        'configure_report': 'Configure Report',
        'configure_dashboard_report': 'Configure Dashboard Report',
        'configure_detailed_report': 'Configure Detailed Report',
        'configure_summary_report': 'Configure Summary Report',
        'configure_audit_report': 'Configure Audit Report',
        'dashboard_charts_to_include': 'Dashboard Charts to Include',
        'work_hour_analysis': 'Work Hour Analysis',
        'kpi_summary': 'KPI Summary',
        'data_to_include': 'Data to Include',
        'event_details': 'Event Details',
        'statistical_summary': 'Statistical Summary',
        'file_change_history': 'File Change History',
        'audit_sections': 'Audit Sections',
        'user_activity_log': 'User Activity Log',
        'access_patterns': 'Access Patterns',
        'anomaly_detection': 'Anomaly Detection',
        'export_format': 'Export Format',
        'preview': 'Preview',
        'generate_report': 'Generate Report',
        'report_preview': 'Report Preview',
        'recent_reports': 'Recent Reports',
        'report_name': 'Report Name',
        'generated_by': 'Generated By',
        'no_recent_reports': 'No recent reports',
        'confirm_delete_report': 'Are you sure you want to delete this report?',
        'report_not_found': 'Report not found',
        
        # Messages
        'login_required': 'Please login to continue',
        'invalid_credentials': 'Invalid username or password',
        'logout_success': 'You have been logged out',
        'password_changed': 'Password changed successfully',
        'incorrect_password': 'Current password is incorrect',
        'passwords_not_match': 'Passwords do not match',
        'event_added': 'Event added successfully',
        'events_added': 'Events added successfully',
        'category_added': 'Category added successfully',
        'category_updated': 'Category updated successfully',
        'category_deleted': 'Category deleted successfully',
        'user_added': 'User added successfully',
        'password_reset': 'Password reset for',
        'directory_added': 'Directory added successfully',
        'directory_exists': 'Directory does not exist',
        'already_monitored': 'This directory is already being monitored by this user',
        'no_permission': 'You do not have permission to perform this action',
        'admin_required': 'You need administrator privileges to access this page',
        'work_hours_updated': 'Work hours updated successfully',
        'invalid_work_hours': 'Invalid work hours specified',
        
        # Language
        'language': 'Language',
        'language_settings': 'Language Settings',
        'select_language': 'Select Language',
        'language_updated': 'Language preference updated',
        
        # Database Control
        'database_control': 'Database Control',
        'create_database_backup': 'Create a backup of the entire database',
        'backup_database': 'Backup Database',
        'restore_database': 'Restore Database',
        'restore_from_backup': 'Restore database from a backup file',
        'export_data': 'Export Data',
        'export_to_various_formats': 'Export data to CSV, JSON, or SQL formats',
        'backup_now': 'Backup Now',
        'restore': 'Restore',
        'export': 'Export',
        'backup_options': 'Backup Options',
        'restore_options': 'Restore Options',
        'export_options': 'Export Options',
        'backup_type': 'Backup Type',
        'full_backup': 'Full Backup',
        'includes_all_data': 'Includes all data and settings',
        'data_only': 'Data Only',
        'excludes_system_settings': 'Excludes system settings and users',
        'structure_only': 'Structure Only',
        'database_schema_only': 'Database schema only (no data)',
        'compression': 'Compression',
        'compress_backup': 'Compress backup',
        'backup_note': 'Backup Note',
        'optional_description': 'Optional description',
        'create_backup': 'Create Backup',
        'recent_backups': 'Recent Backups',
        'backup_date': 'Backup Date',
        'upload_backup_file': 'Upload Backup File',
        'accepted_formats': 'Accepted formats',
        'restore_warning': 'Warning: Restoring will replace all current data!',
        'upload_and_restore': 'Upload and Restore',
        'export_format': 'Export Format',
        'data_to_export': 'Data to Export',
        'data_cleanup': 'Data Cleanup',
        'remove_old_events': 'Remove Old Events',
        'older_than_30_days': 'Older than 30 days',
        'older_than_60_days': 'Older than 60 days',
        'older_than_90_days': 'Older than 90 days',
        'older_than_180_days': 'Older than 180 days',
        'older_than_1_year': 'Older than 1 year',
        'cleanup': 'Cleanup',
        'events_to_delete': 'Events to delete',
        'optimize_database': 'Optimize Database',
        'optimize_description': 'Reclaim space and improve performance',
        'optimize_now': 'Optimize Now',
        'scheduled_backups': 'Scheduled Backups',
        'enable_automatic_backups': 'Enable automatic backups',
        'daily': 'Daily',
        'weekly': 'Weekly',
        'monthly': 'Monthly',
        'retention_policy': 'Retention Policy',
        'keep_for_7_days': 'Keep for 7 days',
        'keep_for_30_days': 'Keep for 30 days',
        'keep_for_90_days': 'Keep for 90 days',
        'keep_for_1_year': 'Keep for 1 year',
        'save_schedule': 'Save Schedule',
        'last_backup': 'Last backup',
        'danger_zone': 'Danger Zone',
        'danger_zone_warning': 'These actions are irreversible and will permanently delete data.',
        'reset_database': 'Reset Database',
        'delete_all_events': 'Delete all events but keep settings',
        'delete_all_data': 'Delete All Data',
        'complete_database_wipe': 'Complete database wipe (keeps admin only)',
        'processing': 'Processing',
        'please_wait': 'Please wait',
        'database_size': 'Database Size',
        'oldest_event': 'Oldest Event',
        'total_events': 'Total Events',
        'total_users': 'Total Users',
        'monitored_paths': 'Monitored Paths',
        'confirm_restore_warning': 'Are you sure you want to restore this backup? This will replace all current data!',
        'restoring_database': 'Restoring database...',
        'restore_successful': 'Database restored successfully!',
        'confirm_restore_upload_warning': 'Are you sure? This will replace all current database data with the uploaded file!',
        'confirm_cleanup_warning': 'Are you sure you want to delete these events? This action cannot be undone.',
        'confirm_reset_database': 'Are you sure you want to reset the database? All events will be deleted!',
        'confirm_reset_database_final': 'This is your final warning! All events will be permanently deleted. Continue?',
        'resetting_database': 'Resetting database...',
        'database_reset_successful': 'Database reset successful!',
        'type_delete_to_confirm': 'Type "DELETE" to confirm you want to delete all data:',
        'deleting_all_data': 'Deleting all data...',
        'all_data_deleted': 'All data has been deleted. You will be logged out.',
        'confirm_delete_backup': 'Are you sure you want to delete this backup?',
        'no_backups_found': 'No backups found',
        'backup_created_successfully': 'Backup created successfully',
        'no_file_uploaded': 'No file uploaded',
        'no_file_selected': 'No file selected',
        'database_restored_successfully': 'Database restored successfully',
        'no_database_in_zip': 'No database file found in zip',
        'sql_restore_not_implemented': 'SQL restore not yet implemented',
        'unsupported_file_format': 'Unsupported file format',
        'restore_failed': 'Restore failed',
        'deleted': 'Deleted',
        'old_events': 'old events',
        'database_optimized': 'Database optimized successfully',
        'optimization_failed': 'Optimization failed',
        'backup_schedule_updated': 'Backup schedule updated'
    },
    'nl': {
        # Dutch translations (keeping key ones and updating as needed)
        'dashboard': 'Dashboard',
        'events': 'Items',  # Changed from 'Gebeurtenissen' to 'Items'
        'manual_entry': 'Handmatige Invoer',
        'reports': 'Rapporten',
        'administration': 'BEHEER',
        'categories': 'Categorieën',
        'settings': 'Instellingen',
        'users': 'Gebruikers',
        'change_password': 'Wachtwoord Wijzigen',
        'logout': 'Uitloggen',
        'login': 'Inloggen',
        
        'file_changes_distribution': 'Bestandswijzigingen Verdeling',
        'top_changed_files': 'Meest Gewijzigde Bestanden',
        'no_file_changes_yet': 'Nog geen bestandswijzigingen gedetecteerd',
        'start_monitoring_files_message': 'Begin met het monitoren van bestanden om wijzigingsstatistieken te zien',
        'monitored_files': 'Gemonitorde Bestanden',
        'total_file_changes': 'Totaal Wijzigingen',
        'most_active_files': 'Meest Actieve Bestanden',
        'no_file_changes_detected': 'Geen bestandswijzigingen gedetecteerd',
        'change_history_for': 'Wijzigingsgeschiedenis voor',
        'total_changes': 'Totaal Wijzigingen',
        'last_change': 'Laatste Wijziging',
        'size_change': 'Grootte Wijziging',
        'error_loading_history': 'Fout bij laden wijzigingsgeschiedenis',
        'monitored_paths': 'Gemonitorde Paden',
        'file_or_directory_path': 'Bestand of Directory Pad',
        'add_path': 'Voeg Pad Toe',
        'browse_file': 'Bladeren door Bestanden',
        'browse_directory': 'Bladeren door Directory',
        'last_modified': 'Laatst Gewijzigd',
        'size': 'Grootte',
        'not_checked_yet': 'Nog niet gecontroleerd',
        'directory_monitoring': 'Directory Monitoring',
        'no_paths_configured': 'Geen paden geconfigureerd',
        'path_validation': 'Pad Validatie',
        'path_exists': 'Pad bestaat',
        'path_is_directory': 'Pad is een directory',
        'path_is_file': 'Pad is een bestand',
        'path_readable': 'Pad is leesbaar',
        
        'work_hours': 'Werkuren',
        'work_start_time': 'Werk Starttijd',
        'work_end_time': 'Werk Eindtijd',
        'work_hours_configuration': 'Wekelijkse Werkuren Configuratie',
        'work_hours_description': 'Configureer werkuren voor elke dag van de week voor genormaliseerde rapportage en analyse',
        'save_work_hours': 'Werkuren Opslaan',
        'last_refresh': 'Laatste Verversing',
        'date_range': 'Datumbereik',
        'refresh': 'Vernieuwen',
        'avg_events_per_hour': 'Gem. Items/Uur',  # Changed from 'Gebeurtenissen' to 'Items'
        'during_work_hours': 'Tijdens werkuren',
        'active_paths': 'Actieve Paden',
        'recent_activity': 'Recente Activiteit',
        'last_50_events': 'Laatste 50 items',  # Changed from 'gebeurtenissen' to 'items'
        'no_recent_activity': 'Geen recente activiteit',
        'events_per_category': 'Items per Categorie',  # Changed from 'Gebeurtenissen' to 'Items'
        'daily_activity': 'Dagelijkse Activiteit',
        'events_per_work_hour': 'Items per Werkuur',  # Changed from 'Gebeurtenissen' to 'Items'
        'normalized': 'Genormaliseerd',
        'events_per_monitored_path': 'Items per Gemonitord Bestand',  # Changed to 'bestand' and 'Items'
        'hourly_activity_today': 'Uurlijkse Activiteit van Vandaag',
        'operators_only': 'Alleen Operators',
        
        # Weekly Work Hours Dutch
        'monday': 'Maandag',
        'tuesday': 'Dinsdag',
        'wednesday': 'Woensdag', 
        'thursday': 'Donderdag',
        'friday': 'Vrijdag',
        'saturday': 'Zaterdag',
        'sunday': 'Zondag',
        'hours_per_day': 'Uren per Dag',
        'total_weekly_hours': 'Totaal Wekelijks Uren',
        'average_daily_hours': 'Gemiddeld Dagelijks Uren',
        'working_days': 'Werkdagen',
        'non_working_days': 'Niet-Werkdagen',
        'events_per_hour': 'Items per Uur',  # Changed from 'Gebeurtenissen' to 'Items'
        'weekly_activity_normalized': 'Wekelijkse Activiteit Genormaliseerd (Items per Werkuur)',  # Changed
        'no_work_hours_configured': 'Geen werkuren geconfigureerd',
        'configure_work_hours': 'Werkuren Configureren',
        
        'running': 'Actief',
        'stopped': 'Gestopt',
        'active': 'Actief',
        'inactive': 'Inactief',
        'login_required': 'Log in om door te gaan',
        'invalid_credentials': 'Ongeldige gebruikersnaam of wachtwoord',
        'logout_success': 'U bent uitgelogd',
        
        # Common Dutch translations
        'actions': 'Acties',
        'time': 'Tijd',
        'timestamp': 'Tijdstempel',
        'category': 'Categorie',
        'file': 'Bestand',
        'file_path': 'Bestandspad',
        'computer': 'Computer',
        'user': 'Gebruiker',
        'type': 'Type',
        'keyword': 'Sleutelwoord',
        'keywords': 'Sleutelwoorden',
        'file_patterns': 'Bestandspatronen',
        'date': 'Datum',
        'from_date': 'Van Datum',
        'to_date': 'Tot Datum',
        'filter': 'Filter',
        'submit': 'Versturen',
        'cancel': 'Annuleren',
        'save': 'Opslaan',
        'delete': 'Verwijderen',
        'edit': 'Bewerken',
        'add': 'Toevoegen',
        'create': 'Aanmaken',
        'update': 'Bijwerken',
        'enable': 'Inschakelen',
        'disable': 'Uitschakelen',
        'status': 'Status',
        'yes': 'Ja',
        'no': 'Nee',
        'confirm_delete': 'Weet je zeker dat je dit wilt verwijderen?',
        'no_results': 'Geen resultaten gevonden',
        'loading': 'Laden...',
        'remove': 'Verwijderen',
        'previous': 'Vorige',
        'next': 'Volgende',
        'me': 'Ik',
        'admin': 'Beheerder',
        'recursive': 'Recursief',
        'directory': 'Directory',
        'details': 'Details',
        'yesterday': 'Gisteren',
        'day': 'Dag',
        'validate': 'Valideren',
        'high': 'Hoog',
        'medium': 'Gemiddeld',
        'low': 'Laag',
        'off': 'Uit',
        'efficiency': 'Efficiëntie',
        'current_week': 'Huidige Week',
        'daily_schedule': 'Dagelijkse Planning',
        'day_of_week': 'Dag van de Week',
        'all_categories': 'Alle Categorieën',
        'today': 'Vandaag',
        'path': 'Pad',
        'files': 'Bestanden',
        'directories': 'Mappen',
        'total': 'Totaal',
        'amount': 'Aantal',
        'description': 'Beschrijving',
        'event_added': 'Item toegevoegd',
        'events_added': 'Items toegevoegd',
        
        # Database Control Dutch
        'database_control': 'Database Beheer',
        'create_database_backup': 'Maak een backup van de volledige database',
        'backup_database': 'Database Backup',
        'restore_database': 'Database Herstellen',
        'restore_from_backup': 'Herstel database van een backup bestand',
        'export_data': 'Data Exporteren',
        'export_to_various_formats': 'Exporteer data naar CSV, JSON of SQL formaten',
        'backup_now': 'Nu Backuppen',
        'restore': 'Herstellen',
        'export': 'Exporteren',
        'backup_options': 'Backup Opties',
        'restore_options': 'Herstel Opties',
        'export_options': 'Export Opties',
        'backup_type': 'Backup Type',
        'full_backup': 'Volledige Backup',
        'includes_all_data': 'Bevat alle data en instellingen',
        'data_only': 'Alleen Data',
        'excludes_system_settings': 'Exclusief systeeminstellingen en gebruikers',
        'structure_only': 'Alleen Structuur',
        'database_schema_only': 'Alleen database schema (geen data)',
        'compression': 'Compressie',
        'compress_backup': 'Backup comprimeren',
        'backup_note': 'Backup Notitie',
        'optional_description': 'Optionele beschrijving',
        'create_backup': 'Backup Maken',
        'recent_backups': 'Recente Backups',
        'backup_date': 'Backup Datum',
        'upload_backup_file': 'Upload Backup Bestand',
        'accepted_formats': 'Geaccepteerde formaten',
        'restore_warning': 'Waarschuwing: Herstellen zal alle huidige data vervangen!',
        'upload_and_restore': 'Upload en Herstel',
        'export_format': 'Export Formaat',
        'data_to_export': 'Te Exporteren Data',
        'data_cleanup': 'Data Opschonen',
        'remove_old_events': 'Verwijder Oude Gebeurtenissen',
        'older_than_30_days': 'Ouder dan 30 dagen',
        'older_than_60_days': 'Ouder dan 60 dagen',
        'older_than_90_days': 'Ouder dan 90 dagen',
        'older_than_180_days': 'Ouder dan 180 dagen',
        'older_than_1_year': 'Ouder dan 1 jaar',
        'cleanup': 'Opschonen',
        'events_to_delete': 'Te verwijderen gebeurtenissen',
        'optimize_database': 'Database Optimaliseren',
        'optimize_description': 'Ruimte vrijmaken en prestaties verbeteren',
        'optimize_now': 'Nu Optimaliseren',
        'scheduled_backups': 'Geplande Backups',
        'enable_automatic_backups': 'Automatische backups inschakelen',
        'daily': 'Dagelijks',
        'weekly': 'Wekelijks',
        'monthly': 'Maandelijks',
        'retention_policy': 'Bewaarbeleid',
        'keep_for_7_days': 'Bewaar 7 dagen',
        'keep_for_30_days': 'Bewaar 30 dagen',
        'keep_for_90_days': 'Bewaar 90 dagen',
        'keep_for_1_year': 'Bewaar 1 jaar',
        'save_schedule': 'Schema Opslaan',
        'last_backup': 'Laatste backup',
        'danger_zone': 'Gevaarlijke Zone',
        'danger_zone_warning': 'Deze acties zijn onomkeerbaar en zullen permanent data verwijderen.',
        'reset_database': 'Database Resetten',
        'delete_all_events': 'Verwijder alle gebeurtenissen maar behoud instellingen',
        'delete_all_data': 'Alle Data Verwijderen',
        'complete_database_wipe': 'Volledige database wipe (behoudt alleen admin)',
        'processing': 'Verwerken',
        'please_wait': 'Even geduld',
        'database_size': 'Database Grootte',
        'oldest_event': 'Oudste Gebeurtenis',
        'total_events': 'Totaal Gebeurtenissen',
        'total_users': 'Totaal Gebruikers',
        'monitored_paths': 'Gemonitorde Paden',
        'confirm_restore_warning': 'Weet je zeker dat je deze backup wilt herstellen? Dit zal alle huidige data vervangen!',
        'restoring_database': 'Database herstellen...',
        'restore_successful': 'Database succesvol hersteld!',
        'confirm_restore_upload_warning': 'Weet je het zeker? Dit zal alle huidige database data vervangen met het geüploade bestand!',
        'confirm_cleanup_warning': 'Weet je zeker dat je deze gebeurtenissen wilt verwijderen? Deze actie kan niet ongedaan worden gemaakt.',
        'confirm_reset_database': 'Weet je zeker dat je de database wilt resetten? Alle gebeurtenissen worden verwijderd!',
        'confirm_reset_database_final': 'Dit is je laatste waarschuwing! Alle gebeurtenissen worden permanent verwijderd. Doorgaan?',
        'resetting_database': 'Database resetten...',
        'database_reset_successful': 'Database reset succesvol!',
        'type_delete_to_confirm': 'Typ "DELETE" om te bevestigen dat je alle data wilt verwijderen:',
        'deleting_all_data': 'Alle data verwijderen...',
        'all_data_deleted': 'Alle data is verwijderd. Je wordt uitgelogd.',
        'confirm_delete_backup': 'Weet je zeker dat je deze backup wilt verwijderen?',
        'no_backups_found': 'Geen backups gevonden',
        'backup_created_successfully': 'Backup succesvol aangemaakt',
        'no_file_uploaded': 'Geen bestand geüpload',
        'no_file_selected': 'Geen bestand geselecteerd',
        'database_restored_successfully': 'Database succesvol hersteld',
        'no_database_in_zip': 'Geen database bestand gevonden in zip',
        'sql_restore_not_implemented': 'SQL herstel nog niet geïmplementeerd',
        'unsupported_file_format': 'Niet ondersteund bestandsformaat',
        'restore_failed': 'Herstel mislukt',
        'deleted': 'Verwijderd',
        'old_events': 'oude gebeurtenissen',
        'database_optimized': 'Database succesvol geoptimaliseerd',
        'optimization_failed': 'Optimalisatie mislukt',
        'backup_schedule_updated': 'Backup schema bijgewerkt',
        
        # Missing Dutch translations - added 2025-06-24
        'access_patterns': 'Toegangspatronen',
        'active_directories': 'Actieve Directories',
        'add_category': 'Categorie Toevoegen',
        'add_keyword': 'Sleutelwoord Toevoegen',
        'add_pattern': 'Patroon Toevoegen',
        'add_user': 'Gebruiker Toevoegen',
        'admin_required': 'Je hebt beheerdersrechten nodig om deze pagina te bekijken',
        'all_users': 'Alle Gebruikers',
        'already_monitored': 'Deze directory wordt al gemonitord door deze gebruiker',
        'anomaly_detection': 'Anomalie Detectie',
        'audit_report': 'Audit Rapport',
        'audit_sections': 'Audit Secties',
        'browse_filter_events': 'Bekijk en filter opgenomen gebeurtenissen',
        'category_added': 'Categorie succesvol toegevoegd',
        'category_deleted': 'Categorie succesvol verwijderd',
        'category_distribution': 'Categorie Verdeling',
        'category_name': 'Categorie Naam',
        'category_updated': 'Categorie succesvol bijgewerkt',
        'clear_filter': 'Filter Wissen',
        'color': 'Kleur',
        'compliance_security_report': 'Compliance en beveiligings audit trail',
        'comprehensive_data_export': 'Uitgebreide data export met meerdere sheets',
        'configure_audit_report': 'Audit Rapport Configureren',
        'configure_dashboard_report': 'Dashboard Rapport Configureren',
        'configure_detailed_report': 'Gedetailleerd Rapport Configureren',
        'configure_report': 'Rapport Configureren',
        'configure_summary_report': 'Samenvatting Rapport Configureren',
        'confirm_delete_report': 'Weet je zeker dat je dit rapport wilt verwijderen?',
        'confirm_password': 'Wachtwoord Bevestigen',
        'create_one_now': 'Maak er nu een aan',
        'created': 'Aangemaakt',
        'current_password': 'Huidig Wachtwoord',
        'custom_range': 'Aangepast Bereik',
        'dashboard_charts_to_include': 'Dashboard Grafieken om Op Te Nemen',
        'dashboard_report': 'Dashboard Rapport',
        'data_to_include': 'Data om Op Te Nemen',
        'define_category': 'Definieer sleutelwoorden en patronen voor automatische categorisering',
        'detailed_excel_report': 'Gedetailleerd Excel Rapport',
        'directory_added': 'Directory succesvol toegevoegd',
        'directory_exists': 'Directory bestaat niet',
        'edit_category': 'Categorie Bewerken',
        'eg_log': 'bijv., .*\\.log',
        'email': 'E-mail',
        'enter_keyword': 'Voer sleutelwoord in',
        'event_details': 'Gebeurtenis Details',
        'event_trend': 'Gebeurtenis Trend (Laatste 7 Dagen)',
        'events_by_user': 'Gebeurtenissen per Gebruiker',
        'export_dashboard_charts': 'Exporteer alle dashboard grafieken en KPI\'s',
        'file_change_history': 'Bestand Wijzigingsgeschiedenis',
        'file_patterns_regex': 'Bestandspatronen (regex)',
        'filter_by_user': 'Filter op Gebruiker:',
        'generate_export_reports': 'Genereer en exporteer professionele rapporten',
        'generate_report': 'Rapport Genereren',
        'generated_by': 'Gegenereerd Door',
        'high_level_overview': 'Overzicht op hoog niveau met belangrijke statistieken',
        'incorrect_password': 'Huidig wachtwoord is onjuist',
        'invalid_work_hours': 'Ongeldige werkuren opgegeven',
        'kpi_summary': 'KPI Samenvatting',
        'language': 'Taal',
        'language_settings': 'Taal Instellingen',
        'language_updated': 'Taalvoorkeur bijgewerkt',
        'last_month': 'Vorige Maand',
        'last_week': 'Vorige Week',
        'manage_categories': 'Beheer gebeurtenis categorieën',
        'manage_users': 'Beheer systeemgebruikers en rechten',
        'monitor_overview': 'Monitor overzicht en statistieken',
        'monitor_status': 'Monitor Status',
        'new_password': 'Nieuw Wachtwoord',
        'no_categories_defined': 'Nog geen categorieën gedefinieerd',
        'no_data': 'Geen data',
        'no_events_found': 'Geen gebeurtenissen gevonden',
        'no_keywords': 'Geen sleutelwoorden gedefinieerd',
        'no_patterns': 'Geen patronen gedefinieerd',
        'no_permission': 'Je hebt geen toestemming om deze actie uit te voeren',
        'no_recent_reports': 'Geen recente rapporten',
        'normalized_events': 'Genormaliseerde Gebeurtenissen',
        'operator': 'Operator',
        'password': 'Wachtwoord',
        'password_changed': 'Wachtwoord succesvol gewijzigd',
        'password_reset': 'Wachtwoord reset voor',
        'passwords_not_match': 'Wachtwoorden komen niet overeen',
        'preview': 'Voorbeeld',
        'recent_events': 'Recente Gebeurtenissen',
        'recent_reports': 'Recente Rapporten',
        'report_name': 'Rapport Naam',
        'report_not_found': 'Rapport niet gevonden',
        'report_preview': 'Rapport Voorbeeld',
        'reset_password': 'Wachtwoord Resetten',
        'role': 'Rol',
        'select_language': 'Selecteer Taal',
        'showing_data_for': 'Toont data voor:',
        'statistical_summary': 'Statistische Samenvatting',
        'summary_report': 'Samenvatting Rapport',
        'this_month': 'Deze Maand',
        'this_quarter': 'Dit Kwartaal',
        'this_week': 'Deze Week',
        'this_year': 'Dit Jaar',
        'todays_events': 'Gebeurtenissen van Vandaag',
        'top_categories_today': 'Top Categorieën Vandaag',
        'uncategorized': 'Ongecategoriseerd',
        'update_your_password': 'Werk je account wachtwoord bij',
        'user_activity_log': 'Gebruiker Activiteit Log',
        'user_activity_today': 'Gebruiker Activiteit Vandaag',
        'user_added': 'Gebruiker succesvol toegevoegd',
        'username': 'Gebruikersnaam',
        'view_all': 'Bekijk Alles',
        'view_dashboard': 'Bekijk Dashboard',
        'view_events': 'Bekijk Gebeurtenissen',
        'work_hour_analysis': 'Werkuren Analyse',
        'work_hours_updated': 'Werkuren succesvol bijgewerkt',
        'you': 'Jij',
        'allerlei': 'Allerlei',
        'amount': 'Aantal',
    }
}

def get_translation(key, lang=None):
    """
    Get translation for a key in the specified language
    
    Args:
        key (str): Translation key
        lang (str, optional): Language code. If None, uses current user's language
        
    Returns:
        str: Translated text or original key if translation not found
    """
    if lang is None:
        lang = getattr(current_user, 'language', 'en') if current_user.is_authenticated else 'en'
    
    return TRANSLATIONS.get(lang, {}).get(key, key)

def get_current_language():
    """
    Get the current user's language preference
    
    Returns:
        str: Language code (defaults to 'en')
    """
    return getattr(current_user, 'language', 'en') if current_user.is_authenticated else 'en'

def get_available_languages():
    """
    Get list of available languages
    
    Returns:
        dict: Dictionary of language codes and names
    """
    return LANGUAGES.copy()

def setup_translations(app):
    """
    Setup translation context processor for Flask app
    
    Args:
        app: Flask application instance
    """
    @app.context_processor
    def inject_translations():
        """Context processor to make translations available in templates"""
        def t(key):
            return get_translation(key)
        
        return {
            't': t,
            'current_language': get_current_language(),
            'available_languages': get_available_languages()
        }

def add_translations(new_translations):
    """
    Add new translations to the existing dictionary
    
    Args:
        new_translations (dict): Dictionary with language codes as keys
                                and translation dictionaries as values
    """
    for lang_code, translations in new_translations.items():
        if lang_code in TRANSLATIONS:
            TRANSLATIONS[lang_code].update(translations)
        else:
            TRANSLATIONS[lang_code] = translations

def export_translations_to_file(filename, lang_code=None):
    """
    Export translations to a JSON file for external editing
    
    Args:
        filename (str): Output filename
        lang_code (str, optional): Specific language to export, or all if None
    """
    import json
    
    if lang_code:
        data = {lang_code: TRANSLATIONS.get(lang_code, {})}
    else:
        data = TRANSLATIONS
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def import_translations_from_file(filename):
    """
    Import translations from a JSON file
    
    Args:
        filename (str): Input filename
    """
    import json
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            new_translations = json.load(f)
            add_translations(new_translations)
        return True
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error importing translations: {e}")
        return False

def get_missing_translations(target_lang='en'):
    """
    Find missing translations compared to target language
    
    Args:
        target_lang (str): Reference language (usually 'en')
        
    Returns:
        dict: Missing translations per language
    """
    if target_lang not in TRANSLATIONS:
        return {}
    
    target_keys = set(TRANSLATIONS[target_lang].keys())
    missing = {}
    
    for lang_code, translations in TRANSLATIONS.items():
        if lang_code != target_lang:
            lang_keys = set(translations.keys())
            missing_keys = target_keys - lang_keys
            if missing_keys:
                missing[lang_code] = list(missing_keys)
    
    return missing

def validate_translations():
    """
    Validate translation completeness and report statistics
    
    Returns:
        dict: Statistics about translation coverage
    """
    if 'en' not in TRANSLATIONS:
        return {'error': 'English translations not found'}
    
    english_count = len(TRANSLATIONS['en'])
    stats = {
        'total_keys': english_count,
        'languages': {},
        'missing_translations': get_missing_translations()
    }
    
    for lang_code, translations in TRANSLATIONS.items():
        count = len(translations)
        coverage = (count / english_count * 100) if english_count > 0 else 0
        stats['languages'][lang_code] = {
            'count': count,
            'coverage': round(coverage, 1)
        }
    
    return stats