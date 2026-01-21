import tkinter as tk
from tkinter import ttk, messagebox, Menu
import re
import os
import json
import requests
from config_utils import get_config_path, update_config
from datetime import datetime, date
import threading
import subprocess

class DatabasePanel(ttk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.main_app = main_app
        self.config = self.load_config()
        self._logs_refresh_running = False
        self._logs_thread = None
        self._all_log_items = []  # Store all log items for filtering
        self._setup_ui()

    def load_config(self):
        config_file = get_config_path()
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                try:
                    return json.load(f)
                except Exception:
                    return {}
        return {}

    def save_config(self):
        updates = {
            'database_enabled': self.database_enabled_var.get(),
            'api_url': self.api_url_var.get(),
            'user': self.user_var.get()
        }
        update_config(updates)
        self.config = self.load_config()
        
        # Trigger a database connection recheck after config changes
        if hasattr(self.main_app, 'recheck_db_connection'):
            self.main_app.recheck_db_connection()

    def toggle_database_enabled(self):
        self.save_config()
        self.update_database_ui_state()

    def update_database_ui_state(self):
        enabled = self.database_enabled_var.get()
        state = "normal" if enabled else "disabled"
        def set_state_recursive(widget, state):
            if isinstance(widget, ttk.Checkbutton):
                return
            try:
                widget.config(state=state)
            except Exception:
                pass
            for child in widget.winfo_children():
                set_state_recursive(child, state)
        for child in self.config_frame.winfo_children():
            if isinstance(child, ttk.LabelFrame):
                for w in child.winfo_children():
                    set_state_recursive(w, state)
        if not enabled:
            self.connection_status_label.config(text="Uitgeschakeld", foreground="orange")

    def update_connection_status(self, status, color):
        """Called by the main app to update connection status"""
        if hasattr(self, 'connection_status_label'):
            try:
                if self.connection_status_label.winfo_exists():
                    # Only update if database is enabled
                    if self.database_enabled_var.get():
                        self.connection_status_label.config(text=status, foreground=color)
                    else:
                        self.connection_status_label.config(text="Uitgeschakeld", foreground="orange")
            except tk.TclError:
                pass  # Widget destroyed
            except Exception as e:
                print(f'[DB PANEL ERROR] Failed to update status: {e}')

    def _setup_ui(self):
        frame = tk.Frame(self)
        frame.pack(fill='both', expand=True)
        self.database_enabled_var = tk.BooleanVar(value=self.config.get('database_enabled', True))
        self.config_frame = ttk.Frame(frame)
        self.config_frame.pack(fill='x', padx=10, pady=10)
        config_frame = ttk.LabelFrame(self.config_frame, text="API Configuratie", padding=10)
        config_frame.pack(fill='x')
        config_frame.grid_columnconfigure(0, weight=0)
        config_frame.grid_columnconfigure(1, weight=1)
        config_frame.grid_columnconfigure(2, weight=0)
        config_frame.grid_columnconfigure(3, weight=0)
        config_frame.grid_columnconfigure(4, weight=0)
        
        db_enable_chk = ttk.Checkbutton(config_frame, text="Database Inschakelen", variable=self.database_enabled_var, command=self.toggle_database_enabled)
        db_enable_chk.grid(row=0, column=0, columnspan=2, padx=(0,10), sticky=tk.W)
        
        ttk.Label(config_frame, text="API URL:").grid(row=1, column=0, sticky=tk.W)
        self.api_url_var = tk.StringVar(value=self.config.get('api_url', 'http://localhost:5001/log'))
        api_url_entry = ttk.Entry(config_frame, textvariable=self.api_url_var, width=40)
        api_url_entry.grid(row=1, column=1, sticky=tk.W)
        
        ttk.Label(config_frame, text="Gebruiker:").grid(row=2, column=0, sticky=tk.W)
        self.user_var = tk.StringVar(value=self.config.get('user', ''))
        user_entry = ttk.Entry(config_frame, textvariable=self.user_var, width=20)
        user_entry.grid(row=2, column=1, sticky=tk.W)

        # Always show 'Niet verbonden' (red) on panel open until tested
        self.user_entry = user_entry
        self.test_btn = ttk.Button(config_frame, text="Test verbinding", command=self.test_connection)
        self.test_btn.grid(row=5, column=0, sticky=tk.W, pady=(5,0))
        self.save_btn = ttk.Button(config_frame, text="Opslaan", command=self.save_config)
        self.save_btn.grid(row=5, column=1, sticky=tk.W, padx=(5,0), pady=(5,0))
        self.connection_status_label = ttk.Label(config_frame, text="Niet verbonden", foreground="red")
        self.connection_status_label.grid(row=5, column=2, sticky=tk.W, padx=(10,0), pady=(5,0))
        
        log_btn = ttk.Button(frame, text="Log test event", command=self.log_test_event)
        log_btn.pack(pady=8)
        
        logs_frame = ttk.LabelFrame(frame, text="Logs", padding=10)
        logs_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create search frame
        search_frame = ttk.Frame(logs_frame)
        search_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Label(search_frame, text="Zoeken:").pack(side='left', padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self._filter_logs())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side='left', padx=(0, 5))
        
        ttk.Button(search_frame, text="Wissen", command=self._clear_search, width=8).pack(side='left')
        
        # Create a frame to hold the treeview and scrollbar
        tree_frame = ttk.Frame(logs_frame)
        tree_frame.pack(fill='both', expand=True)
        
        # Create vertical scrollbar
        tree_scroll = ttk.Scrollbar(tree_frame, orient='vertical')
        tree_scroll.pack(side='right', fill='y')
        
        self.logs_tree = ttk.Treeview(tree_frame, columns=("timestamp", "status", "project", "details", "user", "FilePath"), 
                                     show="headings", yscrollcommand=tree_scroll.set)
        self._log_sort_column = None
        self._log_sort_reverse = False
        
        # Configure scrollbar
        tree_scroll.config(command=self.logs_tree.yview)
        
        for col in ("timestamp", "status", "project", "details", "user", "FilePath"):
            self.logs_tree.heading(col, text=col.capitalize(), command=lambda c=col: self._sort_logs_tree(c))
            if col == "FilePath":
                self.logs_tree.column(col, width=0, stretch=tk.NO)  # Hide the FilePath column
            else:
                self.logs_tree.column(col, width=100 if col not in ["details", "project"] else 180, anchor=tk.W)
        
        self.logs_tree.pack(side='left', fill='both', expand=True)

        # Configure tag for SPOED projects (red background)
        self.logs_tree.tag_configure('spoed', background='#ff6666', foreground='#ffffff')

        # Right-click context menu
        self.tree_menu = tk.Menu(self, tearoff=0)
        # self.tree_menu.add_command(label="Log 'OPEN' Event", command=lambda: self._log_manual_event("OPEN"))
        # self.tree_menu.add_separator()
        # self.tree_menu.add_command(label="Start Manual Session", command=self._start_manual_session)
        # self.tree_menu.add_command(label="Finish Manual Session", command=self._finish_manual_session)
        # self.tree_menu.add_separator()
        self.tree_menu.add_command(label="Log 'AFGEMELD' Event", command=lambda: self._log_manual_event("AFGEMELD"))
        self.logs_tree.bind("<Button-3>", self._show_tree_menu)
        self.logs_tree.bind("<Double-1>", self._on_log_double_click)

        spacer = tk.Label(frame)
        spacer.pack(expand=True, fill='both')
        copyright_label = tk.Label(self, text="© 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)

    def _normalize_network_path(self, path):
        """Normalize a network path and try to resolve it if it doesn't exist.
        
        Handles cases where:
        - Path uses mapped drive (Y:\) on one PC but UNC (\\server\share\) on another
        - Path uses forward slashes vs backslashes
        - Path has trailing slashes or spaces
        
        Returns: (normalized_path, exists) tuple
        """
        if not path or path == 'None':
            return None, False
        
        # Clean and normalize the path
        path = path.strip()
        normalized = os.path.normpath(path)
        
        print(f"[PATH DEBUG] Original: '{path}'")
        print(f"[PATH DEBUG] Normalized: '{normalized}'")
        print(f"[PATH DEBUG] Exists: {os.path.exists(normalized)}")
        
        # If the normalized path exists, return it
        if os.path.exists(normalized):
            return normalized, True
        
        # Try with raw string (sometimes helps with network paths)
        if os.path.exists(path):
            print(f"[PATH DEBUG] Raw path exists (normalized didn't)")
            return path, True
        
        # If it's a UNC path that doesn't exist, log it
        if normalized.startswith('\\\\'):
            print(f"[PATH DEBUG] UNC path not accessible: {normalized}")
            print(f"[PATH DEBUG] This may indicate network connectivity issues or unmapped network drive")
        
        # If it's a mapped drive that doesn't exist, log it
        if len(normalized) > 1 and normalized[1] == ':':
            drive_letter = normalized[0]
            print(f"[PATH DEBUG] Mapped drive '{drive_letter}:' not accessible")
            print(f"[PATH DEBUG] Drive may not be mapped on this computer")
            print(f"[PATH DEBUG] Attempting to resolve {drive_letter}: to UNC path...")

            try:
                unc_root = self._get_unc_for_drive(drive_letter)
                print(f"[PATH DEBUG] UNC lookup result for {drive_letter}: = '{unc_root}'")
                if unc_root:
                    rebuilt = os.path.normpath(unc_root + normalized[2:])
                    print(f"[PATH DEBUG] Resolved {drive_letter}: to UNC '{unc_root}' -> '{rebuilt}' (exists: {os.path.exists(rebuilt)})")
                    if os.path.exists(rebuilt):
                        return rebuilt, True
                else:
                    print(f"[PATH DEBUG] No UNC mapping found for {drive_letter}: in 'net use' output")
                    # Fallback: Try hardcoded mapping for known drives
                    drive_mappings = {
                        'Y': r'\\172.30.2.54\vlecad',
                        'N': r'\\192.168.244.155\Vlecad',
                        'G': r'\\Mintjens-VM-03\Gebruikers\boere',
                        'J': r'\\mintjens-vm-03\DISK2',
                        'K': r'\\192.168.244.153\Grundner-KAM',
                        'L': r'\\mintjens-vm-03\Rapporten',
                        'O': r'\\192.168.244.92\OptAuf',
                        'T': r'\\192.168.244.150\Grundner'
                    }
                    unc_root = drive_mappings.get(drive_letter.upper())
                    if unc_root:
                        print(f"[PATH DEBUG] Using hardcoded mapping for {drive_letter}: -> {unc_root}")
                        rebuilt = os.path.normpath(unc_root + normalized[2:])
                        print(f"[PATH DEBUG] Rebuilt path: '{rebuilt}' (exists: {os.path.exists(rebuilt)})")
                        if os.path.exists(rebuilt):
                            return rebuilt, True
            except Exception as e:
                print(f"[PATH DEBUG] Error resolving mapped drive to UNC: {e}")
                import traceback
                traceback.print_exc()
        
        return normalized, False

    def _get_unc_for_drive(self, drive_letter):
        try:
            print(f"[PATH DEBUG] Running 'net use' to find UNC for {drive_letter}:")
            output = subprocess.check_output(["cmd", "/C", "net use"], stderr=subprocess.STDOUT)
            text = output.decode(errors='ignore')
            print(f"[PATH DEBUG] net use output:\n{text}")
            # Match pattern like "OK           Y:        \\172.30.2.54\vlecad"
            # The pattern handles both \\server\share and \\IP\share formats
            pattern = rf"{re.escape(drive_letter.upper())}:\s+(\\\\[\d\w\.\-]+\\[\w\-]+)"
            print(f"[PATH DEBUG] Searching for pattern: {pattern}")
            for line in text.splitlines():
                m = re.search(pattern, line, re.IGNORECASE)
                if m:
                    print(f"[PATH DEBUG] Found match in line: {line}")
                    unc_path = m.group(1)
                    print(f"[PATH DEBUG] Extracted UNC: {unc_path}")
                    return unc_path
            print(f"[PATH DEBUG] No match found for {drive_letter}: in net use output")
        except Exception as e:
            print(f"[PATH DEBUG] Exception in _get_unc_for_drive: {e}")
            import traceback
            traceback.print_exc()
        return None

    def _on_log_double_click(self, event):
        """Handles double-click events on the logs_tree with enhanced debugging."""
        print("[DBLCLICK DEBUG] Double-click detected")
        
        item_id = self.logs_tree.identify_row(event.y)
        if not item_id:
            print("[DBLCLICK DEBUG] No item identified at click position")
            return

        item_values = self.logs_tree.item(item_id, 'values')
        print(f"[DBLCLICK DEBUG] Raw item values: {item_values}")
        print(f"[DBLCLICK DEBUG] Number of values: {len(item_values) if item_values else 0}")
        
        if not item_values or len(item_values) < 3:
            print(f"[DBLCLICK DEBUG] Insufficient data in row")
            return # Not enough data in the row

        log_status = str(item_values[1] or '').upper() # Status is the second column (index 1)
        project_name = str(item_values[2])    # Project is the third column (index 2)
        log_details = str(item_values[3]) if len(item_values) > 3 else ""
        log_user = str(item_values[4] or '').upper() if len(item_values) > 4 else ""
        file_path_from_db = str(item_values[5]) if len(item_values) > 5 else ""

        # DEBUG: Print extracted values
        print(f"[DBLCLICK DEBUG] Status: '{log_status}'")
        print(f"[DBLCLICK DEBUG] Project: '{project_name}'")
        print(f"[DBLCLICK DEBUG] Details: '{log_details}'")
        print(f"[DBLCLICK DEBUG] User: '{log_user}'")
        print(f"[DBLCLICK DEBUG] File path from DB: '{file_path_from_db}'")

        if log_status in ['OPEN', 'EXCEL_GENERATED', 'BEZIG']:
            if not project_name:
                print("[DBLCLICK DEBUG] No project name found")
                messagebox.showwarning("Geen project", "Geen projectnaam gevonden voor deze log entry.")
                return
            
            # Special handling for BEZIG status - session is already paused (we're on database panel)
            if log_status == 'BEZIG':
                print(f"[DBLCLICK DEBUG] Handling BEZIG status for {log_user}")
                
                # The session is already paused because we're on the database panel
                # Just confirm if user wants to resume work
                result = messagebox.askyesno(
                    "Hervat Werk Sessie", 
                    f"Project '{project_name}' heeft een gepauzeerde sessie voor gebruiker {log_user}.\n\n"
                    "Wilt u de sessie hervatten en het Excel bestand openen?",
                    icon='question'
                )
                
                if not result:  # No clicked
                    return
                # If Yes clicked, continue to find and open the Excel file
                # The session will automatically resume when switching to scanner panel

            path_to_load = None

            # If file_path is empty (like for SESSION_RESUME), look it up from the API
            if not file_path_from_db or file_path_from_db == 'None' or not file_path_from_db.strip():
                print(f"[DBLCLICK DEBUG] No file path in event, looking up from OPEN event for project: {project_name}, user: {log_user}")
                try:
                    import requests
                    # Use the API to get the file path
                    api_url = self.api_url_var.get()
                    logs_url = api_url.replace('/log', '/logs')
                    
                    # Query the API for OPEN events for this user/project
                    # Bypass proxy for local API calls (important for computers with proxy configuration)
                    response = requests.get(logs_url, timeout=2, proxies={"http": None, "https": None})
                    if response.status_code == 200:
                        logs = response.json()
                        # Find the most recent OPEN event for this user/project with a file path
                        for log in logs:
                            if (log.get('user') == log_user and 
                                log.get('project') == project_name and 
                                log.get('event') == 'OPEN' and 
                                log.get('file_path') and 
                                log.get('file_path') != 'None'):
                                file_path_from_db = log.get('file_path')
                                print(f"[DBLCLICK DEBUG] Found file path from OPEN event via API: {file_path_from_db}")
                                break
                except Exception as e:
                    print(f"[DBLCLICK DEBUG] Error looking up OPEN event via API: {e}")

            # Now use the file path (either from the event or looked up from OPEN)
            if file_path_from_db and file_path_from_db.lower().endswith(('.xlsx', '.xls')):
                # Normalize the path for network compatibility
                normalized_path, path_exists = self._normalize_network_path(file_path_from_db)
                
                if path_exists:
                    path_to_load = normalized_path
                    print(f"[DBLCLICK] Using Excel file path from database: {path_to_load}")
                    self.main_app.switch_to_scanner_and_load(path_to_load, user=log_user)
                    return
                else:
                    print(f"[DBLCLICK] Excel file from DB not accessible: {file_path_from_db}")
                    
                    # Provide detailed diagnostic information
                    diagnostic_info = f"Origineel pad: {file_path_from_db}\n"
                    if normalized_path != file_path_from_db:
                        diagnostic_info += f"Genormaliseerd pad: {normalized_path}\n"
                    
                    # Check if it's a network path
                    if file_path_from_db.startswith('\\\\') or (normalized_path and normalized_path.startswith('\\\\')):
                        diagnostic_info += "\nType: UNC netwerkpad (\\\\server\\share\\...)"
                    elif len(file_path_from_db) > 1 and file_path_from_db[1] == ':':
                        drive = file_path_from_db[0]
                        diagnostic_info += f"\nType: Gekoppelde netwerkschijf ({drive}:)"
                    
                    messagebox.showerror(
                        "Netwerkpad niet toegankelijk",
                        f"Het Excel-bestand kan niet worden geopend:\n\n{diagnostic_info}\n\n"
                        f"Mogelijke oorzaken:\n"
                        f"• Netwerkschijf is niet gekoppeld op deze computer\n"
                        f"• Netwerklocatie is niet toegankelijk\n"
                        f"• Pad gebruikt een andere schijfletter op deze computer\n"
                        f"• Bestand is verplaatst of verwijderd\n\n"
                        f"Controleer of de netwerklocatie toegankelijk is in Windows Verkenner."
                    )
                    return

            # PRIORITY 2: If file_path_from_db is a directory, search for Excel files in it
            print(f"[DBLCLICK DEBUG] PRIORITY 2: Checking if path is directory")
            
            # Normalize directory path for network compatibility
            normalized_dir_path, dir_exists = self._normalize_network_path(file_path_from_db)
            print(f"[DBLCLICK DEBUG] Is directory: {os.path.isdir(normalized_dir_path) if normalized_dir_path else False}")
            
            if normalized_dir_path and dir_exists and os.path.isdir(normalized_dir_path):
                print(f"[DBLCLICK] Searching for Excel in directory from database: {normalized_dir_path}")
                # Determine the base for the Excel filename based on the user type
                excel_filename_base = ""
                if log_user in ['GANNOMAT', 'KL GANNOMAT']:  # Handle both variants
                    excel_filename_base = project_name
                    print(f"[DBLCLICK] User is GANNOMAT-type, using project_name '{project_name}' for Excel filename.")
                else: # Default behavior for OPUS and others
                    excel_filename_base = os.path.basename(os.path.normpath(normalized_dir_path))
                    print(f"[DBLCLICK] User is {log_user}, using directory base name '{excel_filename_base}' for Excel filename.")

                excel_filename_updated = f"{excel_filename_base}_updated.xlsx"
                excel_filename_original = f"{excel_filename_base}.xlsx"

                potential_paths = [
                    os.path.join(normalized_dir_path, excel_filename_updated),
                    os.path.join(normalized_dir_path, excel_filename_original)
                ]
                
                print(f"[DBLCLICK DEBUG] Potential paths to check:")
                for i, p_path in enumerate(potential_paths):
                    print(f"[DBLCLICK DEBUG]   {i+1}. {p_path} (exists: {os.path.exists(p_path)})")

                for p_path in potential_paths:
                    if os.path.exists(p_path):
                        path_to_load = p_path
                        print(f"[DBLCLICK] Found Excel using DB directory path: {path_to_load}")
                        self.main_app.switch_to_scanner_and_load(path_to_load, user=log_user)
                        return

                print(f"[DBLCLICK] Excel not found in DB directory '{normalized_dir_path}'. Proceeding to fallbacks.")

            # PRIORITY 3: Check config for last Excel file (especially useful for ACCURA/BOERE)
            print(f"[DBLCLICK DEBUG] PRIORITY 3: Checking config last_excel_file")
            app_config = self.main_app.load_app_config()
            last_excel_file = app_config.get('Paths', {}).get('last_excel_file', '')
            print(f"[DBLCLICK DEBUG] last_excel_file from config: '{last_excel_file}'")
            
            if last_excel_file and os.path.exists(last_excel_file):
                # Check if this file matches the current project by MO number
                mo_match = project_name.split('_')[0] if '_' in project_name else project_name
                if mo_match in os.path.basename(last_excel_file):
                    print(f"[DBLCLICK] Found matching Excel from config: {last_excel_file}")
                    self.main_app.switch_to_scanner_and_load(last_excel_file, user=log_user)
                    return

            # PRIORITY 4: Handle ACCURA/BOERE type users with dedicated directories
            print(f"[DBLCLICK DEBUG] PRIORITY 4: Checking ACCURA/BOERE type directories")
            if log_user in ['ACCURA', 'BOERE']:
                # Get configured directory from BarcodeMatch config
                accura_dir = app_config.get('accura_output_dir', 'C:/ACCURA')
                boere_dir = app_config.get('boere_output_dir', 'C:/BOERE')
                
                # Use the appropriate directory based on user
                user_directory = accura_dir if log_user == 'ACCURA' else boere_dir
                print(f"[DBLCLICK DEBUG] Checking {log_user} directory: {user_directory}")
                
                if os.path.isdir(user_directory):
                    # Look for files matching project pattern
                    import glob
                    mo_number = project_name.split('_')[0] if '_' in project_name else project_name
                    
                    # Try multiple patterns to find the Excel file
                    patterns = [
                        f"{user_directory}/*{mo_number}*.xlsx",  # Match by MO number anywhere in filename
                        f"{user_directory}/{mo_number}_*.xlsx",  # Match starting with MO number
                        f"{user_directory}/*_{mo_number}_*.xlsx" # Match with MO number in middle
                    ]
                    
                    matching_files = []
                    for pattern in patterns:
                        print(f"[DBLCLICK DEBUG] Trying search pattern: {pattern}")
                        files = glob.glob(pattern)
                        if files:
                            matching_files.extend(files)
                            print(f"[DBLCLICK DEBUG] Found {len(files)} files with this pattern")
                    
                    # Remove duplicates while preserving order
                    seen = set()
                    unique_files = []
                    for f in matching_files:
                        if f not in seen:
                            seen.add(f)
                            unique_files.append(f)
                    matching_files = unique_files
                    
                    print(f"[DBLCLICK DEBUG] Found {len(matching_files)} unique matching files total")
                    
                    if matching_files:
                        # Sort by modification time (newest first)
                        matching_files.sort(key=os.path.getmtime, reverse=True)
                        path_to_load = matching_files[0]
                        print(f"[DBLCLICK] Found {log_user} Excel file: {path_to_load}")
                        self.main_app.switch_to_scanner_and_load(path_to_load, user=log_user)
                        return
                    else:
                        print(f"[DBLCLICK DEBUG] No Excel files found in {user_directory} for MO number {mo_number}")

            # PRIORITY 5: Parse path from log_details (Fallback for older logs)
            print(f"[DBLCLICK DEBUG] PRIORITY 5: Parsing path from log details")
            parsed_path_used = False
            # Updated regex to find any path-like string, matching new and old log formats.
            path_match = re.search(r"([A-Za-z]:\\[\S]+|[A-Za-z]:/[\S]+|\\\\\\[\S]+)", log_details)
            print(f"[DBLCLICK DEBUG] Path regex match: {path_match.group(1) if path_match else 'None'}")

            if path_match:
                parsed_base_path = path_match.group(1).strip()
                print(f"[DBLCLICK] Parsed base path from details: '{parsed_base_path}' for user '{log_user}'")
                
                excel_filename_base = ""
                if log_user == 'OPUS':
                    # For OPUS, Excel filename is often the same as the containing folder's name
                    excel_filename_base = os.path.basename(os.path.normpath(parsed_base_path))
                elif log_user in ['GANNOMAT', 'KL GANNOMAT']:
                    # For GANNOMAT, Excel filename is typically project_name.xlsx in the parsed_base_path
                    excel_filename_base = project_name
                else: # Fallback or unknown user type from log
                    excel_filename_base = project_name 
                    print(f"[DBLCLICK] Unknown or missing user ('{log_user}') in log for path parsing, defaulting to project_name for Excel filename.")

                if excel_filename_base:
                    excel_filename_updated = f"{excel_filename_base}_updated.xlsx"
                    excel_filename_original = f"{excel_filename_base}.xlsx"

                    potential_paths = [
                        os.path.join(parsed_base_path, excel_filename_updated),
                        os.path.join(parsed_base_path, excel_filename_original)
                    ]
                    
                    print(f"[DBLCLICK DEBUG] Parsed path potential files:")
                    for i, p_path in enumerate(potential_paths):
                        print(f"[DBLCLICK DEBUG]   {i+1}. {p_path} (exists: {os.path.exists(p_path)})")
                    
                    for p_path in potential_paths:
                        if os.path.exists(p_path):
                            path_to_load = p_path
                            parsed_path_used = True
                            print(f"[DBLCLICK] Found Excel using parsed path: {path_to_load}")
                            break
                else:
                    print(f"[DBLCLICK] Could not determine excel_filename_base from parsed path and user type.")

            if path_to_load:
                self.main_app.switch_to_scanner_and_load(path_to_load, user=log_user)
                return
            elif parsed_path_used and not path_to_load: # Parsed path but file not found there
                messagebox.showwarning("Bestand niet gevonden (Log Pad)",
                                       f"Excel-bestand niet gevonden op het pad vermeld in de log details:\n{parsed_base_path}")
                return # Stop if we used parsed path and failed

            # PRIORITY 6: Fallback to BarcodeMatch 'default_base_dir' (Basis map)
            print(f"[DBLCLICK DEBUG] PRIORITY 6: Checking fallback 'default_base_dir'")
            print(f"[DBLCLICK] Path not found in log details or file not at parsed path. Falling back to 'default_base_dir'.")
            
            default_bm_base_dir = app_config.get('default_base_dir', '')
            print(f"[DBLCLICK DEBUG] default_base_dir: '{default_bm_base_dir}'")

            if not default_bm_base_dir:
                print(f"[DBLCLICK DEBUG] No default_base_dir configured")
                messagebox.showwarning("Configuratie Fout",
                                       "'Basis map' (default_base_dir) is niet ingesteld in de Import paneel configuratie (BarcodeMatch).\nKan het Excel-bestand niet vinden.")
                return

            # Using project_name for fallback, as it's the most general case
            excel_filename_original_fallback = f"{project_name}.xlsx"
            excel_filename_updated_fallback = f"{project_name}_updated.xlsx"

            potential_fallback_paths = [
                os.path.join(default_bm_base_dir, excel_filename_updated_fallback),
                os.path.join(default_bm_base_dir, excel_filename_original_fallback)
            ]
            
            print(f"[DBLCLICK DEBUG] Fallback potential paths:")
            for i, p_path in enumerate(potential_fallback_paths):
                print(f"[DBLCLICK DEBUG]   {i+1}. {p_path} (exists: {os.path.exists(p_path)})")

            for p_path in potential_fallback_paths:
                if os.path.exists(p_path):
                    path_to_load = p_path
                    print(f"[DBLCLICK] Found Excel using fallback 'default_base_dir': {path_to_load}")
                    break
            
            if path_to_load:
                self.main_app.switch_to_scanner_and_load(path_to_load, user=log_user)
            else:
                print(f"[DBLCLICK DEBUG] No Excel file found in any location")
                messagebox.showwarning("Bestand niet gevonden (Fallback)",
                                       f"Excel-bestand '{excel_filename_original_fallback}' of '{excel_filename_updated_fallback}'\nniet gevonden in de geconfigureerde 'Basis map':\n{default_bm_base_dir}")
        elif log_status == 'AFGEMELD':
            print(f"[DBLCLICK DEBUG] Project is AFGEMELD, showing confirmation dialog")
            # Show confirmation dialog for AFGEMELD projects
            result = messagebox.askyesno(
                "Project Afgemeld", 
                f"Project '{project_name}' is al afgemeld.\nWilt u het nog steeds openen?",
                icon='question'
            )
            
            if result:  # User clicked Yes
                print(f"[DBLCLICK DEBUG] User chose to open AFGEMELD project")
                # Try to find the Excel file - it might be archived
                path_to_load = None
                
                # First check if file still exists at original location
                if file_path_from_db and file_path_from_db.lower().endswith(('.xlsx', '.xls')) and os.path.exists(file_path_from_db):
                    path_to_load = file_path_from_db
                    print(f"[DBLCLICK] Found Excel file at original location: {path_to_load}")
                else:
                    # Check archive location - BarcodeMatch creates "Archief" subdirectory
                    print(f"[DBLCLICK DEBUG] Checking for archived files")
                    excel_filename_base = project_name
                    potential_archive_files = [
                        f"{excel_filename_base}_updated.xlsx",
                        f"{excel_filename_base}.xlsx"
                    ]
                    
                    # Check multiple possible archive locations
                    archive_locations = []
                    
                    # 1. If we have a directory path from DB, check "Archief" subdirectory
                    if file_path_from_db and os.path.isdir(file_path_from_db):
                        archive_locations.append(os.path.join(file_path_from_db, "Archief"))
                    
                    # 2. Check default_base_dir/Archief
                    app_config = self.main_app.load_app_config()
                    default_base_dir = app_config.get('default_base_dir', '')
                    if default_base_dir and os.path.exists(default_base_dir):
                        archive_locations.append(os.path.join(default_base_dir, "Archief"))
                    
                    print(f"[DBLCLICK DEBUG] Archive locations to check: {archive_locations}")
                    
                    for archive_dir in archive_locations:
                        if os.path.exists(archive_dir):
                            print(f"[DBLCLICK DEBUG] Checking archive directory: {archive_dir}")
                            for filename in potential_archive_files:
                                archive_path = os.path.join(archive_dir, filename)
                                if os.path.exists(archive_path):
                                    path_to_load = archive_path
                                    print(f"[DBLCLICK] Found Excel in archive: {path_to_load}")
                                    break
                            if path_to_load:
                                break
                
                if path_to_load:
                    self.main_app.switch_to_scanner_and_load(path_to_load, user=log_user)
                else:
                    messagebox.showwarning(
                        "Bestand niet gevonden",
                        f"Excel-bestand voor project '{project_name}' niet gevonden.\n"
                        "Het bestand is mogelijk gearchiveerd of verplaatst."
                    )
            else:
                print(f"[DBLCLICK DEBUG] User chose not to open AFGEMELD project")
        else:
            print(f"[DBLCLICK DEBUG] Not a supported status for double-click: {log_status}")
            # Optionally, provide feedback if a non-supported item is double-clicked
            pass

    def _sort_logs_tree(self, col):
        data = [(self.logs_tree.set(k, col), k) for k in self.logs_tree.get_children("")]
        # Try to convert to int or float if possible for numeric sort
        def try_num(val):
            try:
                return int(val)
            except Exception:
                try:
                    return float(val)
                except Exception:
                    return val.lower() if isinstance(val, str) else val
        data.sort(key=lambda t: try_num(t[0]), reverse=(self._log_sort_column == col and not self._log_sort_reverse))
        self._log_sort_reverse = not (self._log_sort_column == col and self._log_sort_reverse)
        self._log_sort_column = col
        for idx, (val, k) in enumerate(data):
            self.logs_tree.move(k, '', idx)
    
    def _is_spoed_project(self, project_name):
        """Check if project name contains SPOED patterns"""
        if not project_name:
            return False

        # Convert to uppercase for case-insensitive matching
        project_upper = project_name.upper()

        # Check for SPOED patterns
        spoed_patterns = ['_SPOED_', '_SPOED', 'SPOED_', 'SPOED']
        for pattern in spoed_patterns:
            if pattern in project_upper:
                return True

        return False

    def _clear_search(self):
        """Clear the search field"""
        self.search_var.set('')
    
    def _filter_logs(self):
        """Filter the displayed logs based on search text"""
        search_text = self.search_var.get().lower().strip()

        # Store the currently selected item's data for restoration
        selected_item_data = None
        selected_items = self.logs_tree.selection()
        if selected_items:
            try:
                # Get the values of the first selected item
                selected_item_data = self.logs_tree.item(selected_items[0], 'values')
            except (tk.TclError, IndexError):
                selected_item_data = None

        # Clear current tree
        for item in self.logs_tree.get_children():
            self.logs_tree.delete(item)

        # If no search text, show all items
        if not search_text:
            items_to_show = self._all_log_items
        else:
            # Filter items that match search text in any column
            items_to_show = []
            for item_values in self._all_log_items:
                # Search in timestamp, status, project, details, and user columns
                searchable_text = ' '.join(str(v).lower() for v in item_values[:5])  # First 5 columns (exclude FilePath)
                if search_text in searchable_text:
                    items_to_show.append(item_values)

        # Re-populate tree with filtered items
        new_item_to_select = None
        for item_values in items_to_show:
            # Check if this is a SPOED project (project is 3rd column, index 2)
            project_name = item_values[2] if len(item_values) > 2 else ''
            is_spoed = self._is_spoed_project(project_name)

            # Insert with appropriate tag for SPOED projects
            if is_spoed:
                new_item = self.logs_tree.insert("", "end", values=item_values, tags=('spoed',))
            else:
                new_item = self.logs_tree.insert("", "end", values=item_values)

            # Check if this item matches the previously selected item
            if (selected_item_data and len(selected_item_data) >= 3 and
                len(item_values) >= 3 and
                # Match by project name and status (most reliable identifiers)
                selected_item_data[2] == item_values[2] and  # project
                selected_item_data[1] == item_values[1]):    # status
                new_item_to_select = new_item

        # Re-apply sort if one was active
        if self._log_sort_column:
            data = [(self.logs_tree.set(k, self._log_sort_column), k) for k in self.logs_tree.get_children("")]
            def try_num(val):
                try:
                    return int(val)
                except Exception:
                    try:
                        return float(val)
                    except Exception:
                        return val.lower() if isinstance(val, str) else val
            data.sort(key=lambda t: try_num(t[0]), reverse=self._log_sort_reverse)
            for idx, (val, k) in enumerate(data):
                self.logs_tree.move(k, '', idx)

        # Restore selection if we found a matching item
        if new_item_to_select:
            try:
                self.logs_tree.selection_set(new_item_to_select)
                self.logs_tree.focus(new_item_to_select)
                # Ensure the selected item is visible
                self.logs_tree.see(new_item_to_select)
            except tk.TclError:
                pass  # Selection restoration failed, but that's okay

    def _pause_work_session(self, user, project):
        """Pause a work session by sending PAUZE event to the API."""
        try:
            config = self.main_app.load_app_config()
            api_url = config.get('api_url', 'http://localhost:5001/log')
            
            # Send PAUZE event
            data = {
                'event': 'PAUZE',
                'project': project,
                'user': user,
                'details': 'Sessie gepauzeerd via database panel'
            }
            
            response = requests.post(api_url, json=data, timeout=5, proxies={"http": None, "https": None})
            if response.ok:
                messagebox.showinfo("Sessie Gepauzeerd", 
                    f"Werk sessie voor {user} op project '{project}' is gepauzeerd.\n\n"
                    "De sessie kan hervat worden door opnieuw te scannen in BarcodeMaster.")
                # Refresh the logs to show the updated status
                self._on_logs_refresh()
            else:
                messagebox.showerror("Fout", f"Kon sessie niet pauzeren: {response.text}")
                
        except Exception as e:
            messagebox.showerror("Fout", f"Fout bij pauzeren van sessie: {str(e)}")
    
    def _show_tree_menu(self, event):
        """Display the context menu on right-click."""
        row_id = self.logs_tree.identify_row(event.y)
        if row_id:
            self.logs_tree.selection_set(row_id)
            self.tree_menu.post(event.x_root, event.y_root)

    def _log_manual_event(self, event_type):
        """Log a manual event from the context menu."""
        selected_item = self.logs_tree.focus()
        if not selected_item:
            messagebox.showwarning("Geen selectie", "Selecteer een project in de lijst.")
            return

        item_data = self.logs_tree.item(selected_item)
        project_name = item_data['values'][2]  # Assuming 'project' is the 3rd column
        user = self.user_var.get()

        # If this is an AFGEMELD event, close any active sessions for this project
        if event_type == "AFGEMELD":
            # First, close sessions via API to ensure proper handling
            try:
                config_file_path = get_config_path()
                if os.path.exists(config_file_path):
                    with open(config_file_path, 'r') as f:
                        config = json.load(f)
                    
                    api_url = config.get('api_url', '')
                    if api_url:
                        # Close sessions via dedicated endpoint
                        close_data = {
                            'user': user,
                            'project': project_name,
                            'timestamp': datetime.now().isoformat(),
                            'item_count': 0  # Will be updated by AFGEMELD event
                        }
                        
                        try:
                            response = requests.post(api_url.replace('/log', '/session/close'),
                                                   json=close_data, timeout=2, proxies={"http": None, "https": None})
                            if response.ok:
                                result = response.json()
                                if result.get('sessions_closed', 0) > 0:
                                    print(f"[DATABASE] Closed {result['sessions_closed']} session(s) for project {project_name}")
                        except Exception as e:
                            print(f"[DATABASE] Error closing sessions: {e}")
            except Exception as e:
                print(f"[DATABASE] Error reading config for session close: {e}")
            
            # Also check scanner panel for local session cleanup
            if hasattr(self, 'main_app') and self.main_app:
                scanner_panel = self.main_app.get_panel_by_name("Scanner")
                if scanner_panel and hasattr(scanner_panel, 'current_session_id'):
                    if scanner_panel.current_session_id:
                        current_project = scanner_panel._extract_project_from_filename(
                            scanner_panel.excel_file_path_var.get()
                        )
                        if current_project and current_project == project_name:
                            print(f"[DATABASE] Clearing local scanner session for project {project_name}")
                            scanner_panel._end_session()

        details = f"{project_name} handmatig op '{event_type}' gezet door {user}"
        self.log_event(event_type, project_name, details)

    def _start_manual_session(self):
        """Start a manual session for the selected project."""
        selected_item = self.logs_tree.focus()
        if not selected_item:
            messagebox.showwarning("Geen selectie", "Selecteer een project in de lijst.")
            return

        item_data = self.logs_tree.item(selected_item)
        if len(item_data['values']) < 3:
            messagebox.showerror("Fout", "Onvoldoende projectgegevens beschikbaar.")
            return

        project_name = item_data['values'][2]
        project_status = (item_data['values'][1] or '').upper()
        user = self.user_var.get()

        # Check if project is in OPEN status
        if project_status != 'OPEN':
            messagebox.showwarning("Ongeldige status", 
                                 f"Kan alleen een sessie starten voor OPEN projecten.\nHuidige status: {project_status}")
            return

        # Confirm with user
        if not messagebox.askyesno("Bevestig sessie start", 
                                   f"Weet u zeker dat u een handmatige sessie wilt starten voor:\n\n"
                                   f"Project: {project_name}\nGebruiker: {user}"):
            return

        try:
            # Call the manual session start API
            api_url = self.api_url_var.get()
            base_url = api_url.replace('/log', '')
            
            response = requests.post(f"{base_url}/session/manual_start",
                                   json={
                                       'user': user,
                                       'project': project_name,
                                       'timestamp': datetime.now().isoformat()
                                   },
                                   timeout=2, proxies={"http": None, "https": None})  # Reduced timeout
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    messagebox.showinfo("Succes", f"Handmatige sessie gestart voor {project_name}")
                    self.refresh_logs()  # Refresh to show updated status
                else:
                    messagebox.showerror("Fout", f"API fout: {result.get('error', 'Onbekende fout')}")
            else:
                messagebox.showerror("Fout", f"HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Verbindingsfout", f"Kan geen verbinding maken met de API:\n{str(e)}")
        except Exception as e:
            messagebox.showerror("Fout", f"Onverwachte fout: {str(e)}")

    def _finish_manual_session(self):
        """Finish a manual session with item count input."""
        selected_item = self.logs_tree.focus()
        if not selected_item:
            messagebox.showwarning("Geen selectie", "Selecteer een project in de lijst.")
            return

        item_data = self.logs_tree.item(selected_item)
        if len(item_data['values']) < 3:
            messagebox.showerror("Fout", "Onvoldoende projectgegevens beschikbaar.")
            return

        project_name = item_data['values'][2]
        project_status = (item_data['values'][1] or '').upper()
        user = self.user_var.get()

        # Check if project is in BEZIG status
        if project_status != 'BEZIG':
            messagebox.showwarning("Ongeldige status", 
                                 f"Kan alleen een sessie afronden voor BEZIG projecten.\nHuidige status: {project_status}")
            return

        # Create dialog for item count input
        dialog = tk.Toplevel(self)
        dialog.title("Sessie afronden")
        dialog.geometry("350x200")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        # Dialog content
        tk.Label(dialog, text=f"Sessie afronden voor:", font=('Arial', 10, 'bold')).pack(pady=10)
        tk.Label(dialog, text=f"Project: {project_name}", font=('Arial', 9)).pack(pady=5)
        tk.Label(dialog, text=f"Gebruiker: {user}", font=('Arial', 9)).pack(pady=5)
        
        tk.Label(dialog, text="Aantal verwerkte items:", font=('Arial', 10)).pack(pady=(20, 5))
        
        item_count_var = tk.StringVar()
        item_count_entry = tk.Entry(dialog, textvariable=item_count_var, font=('Arial', 12), width=10, justify='center')
        item_count_entry.pack(pady=5)
        item_count_entry.focus()

        result = {'confirmed': False, 'item_count': 0}

        def on_finish():
            try:
                item_count = int(item_count_var.get())
                if item_count < 0:
                    messagebox.showerror("Ongeldige invoer", "Aantal items moet 0 of hoger zijn.")
                    return
                result['confirmed'] = True
                result['item_count'] = item_count
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Ongeldige invoer", "Voer een geldig getal in.")

        def on_cancel():
            dialog.destroy()

        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Afronden", command=on_finish, bg='#4CAF50', fg='white', 
                 font=('Arial', 10, 'bold'), width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Annuleren", command=on_cancel, bg='#f44336', fg='white', 
                 font=('Arial', 10), width=10).pack(side=tk.LEFT, padx=5)

        # Bind Enter key to finish
        item_count_entry.bind('<Return>', lambda e: on_finish())
        dialog.bind('<Escape>', lambda e: on_cancel())

        # Wait for dialog to close
        dialog.wait_window()

        if not result['confirmed']:
            return

        try:
            # Call the manual session finish API
            api_url = self.api_url_var.get()
            base_url = api_url.replace('/log', '')
            
            response = requests.post(f"{base_url}/session/manual_finish",
                                   json={
                                       'user': user,
                                       'project': project_name,
                                       'item_count': result['item_count'],
                                       'timestamp': datetime.now().isoformat()
                                   },
                                   timeout=2, proxies={"http": None, "https": None})  # Reduced timeout
            
            if response.status_code == 200:
                api_result = response.json()
                if api_result.get('success'):
                    work_minutes = api_result.get('work_minutes', 0)
                    messagebox.showinfo("Succes", 
                                      f"Handmatige sessie afgerond voor {project_name}\n\n"
                                      f"Items verwerkt: {result['item_count']}\n"
                                      f"Werktijd: {work_minutes:.1f} minuten")
                    
                    # Also close any active scanner session for this project
                    if hasattr(self, 'main_app') and self.main_app:
                        scanner_panel = self.main_app.get_panel_by_name("Scanner")
                        if scanner_panel and hasattr(scanner_panel, 'current_session_id'):
                            if scanner_panel.current_session_id:
                                current_project = scanner_panel._extract_project_from_filename(
                                    scanner_panel.excel_file_path_var.get()
                                )
                                if current_project and current_project == project_name:
                                    print(f"[DATABASE] Closing scanner session for project {project_name} after manual finish")
                                    scanner_panel._end_session()
                    
                    # Send AFGEMELD event to complete the workflow with item count
                    self.log_project_closed(project_name, item_count=result['item_count'])
                    self.refresh_logs()  # Refresh to show updated status
                else:
                    messagebox.showerror("Fout", f"API fout: {api_result.get('error', 'Onbekende fout')}")
            else:
                messagebox.showerror("Fout", f"HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Verbindingsfout", f"Kan geen verbinding maken met de API:\n{str(e)}")
        except Exception as e:
            messagebox.showerror("Fout", f"Onverwachte fout: {str(e)}")

    def start_auto_refresh(self):
        """
        Call this method after the panel is packed/shown to start background log refresh.
        Example: panel = DatabasePanel(...); panel.pack(); panel.start_auto_refresh()
        """
        self._logs_refresh_running = True
        def background_refresh():
            import time
            while getattr(self, '_logs_refresh_running', False):
                try:
                    # Check if widget still exists
                    if not self.winfo_exists():
                        break
                        
                    # Schedule refresh in main thread
                    self.after(0, self.refresh_logs)
                    
                except tk.TclError:
                    break  # Widget destroyed
                except Exception as e:
                    print(f"[ERROR] Background refresh error: {e}")
                    break
                    
                time.sleep(10)  # Refresh every 10 seconds
            
            print("[INFO] Background refresh thread ended")
            
        self._logs_thread = threading.Thread(target=background_refresh, daemon=True)
        self._logs_thread.start()

    def destroy(self):
        """Clean up when panel is destroyed"""
        self._logs_refresh_running = False
        if self._logs_thread and self._logs_thread.is_alive():
            # Give thread time to exit gracefully
            self._logs_thread.join(timeout=0.5)
        super().destroy()

    def test_connection(self):
        """Test the connection to the API."""
        url = self.api_url_var.get()
        payload = {
            "event": "test_connect",
            "details": "Test verbinding",
            "project": "TestProject",
            "user": self.user_var.get() if hasattr(self, 'user_var') else 'testuser'
        }
        try:
            response = requests.post(url, json=payload, timeout=2, proxies={"http": None, "https": None})  # Reduced timeout
            if response.status_code == 200 and response.json().get('success'):
                self.connection_status_label.config(text="Verbonden (TEST)", foreground="green")
                print('[DB PANEL] Manual test connection successful')
            else:
                self.connection_status_label.config(text=f"Fout: {response.status_code}", foreground="red")
                messagebox.showerror("Verbinding mislukt", f"Fout bij POST naar API:\n{response.text}")
                print(f'[DB PANEL] Manual test connection failed: {response.status_code}')
        except Exception as e:
            self.connection_status_label.config(text="Niet verbonden", foreground="red")
            messagebox.showerror("Verbinding mislukt", f"Kon geen verbinding maken met de API:\n{e}")
            print(f'[DB PANEL] Manual test connection exception: {e}')

    def log_event(self, event, project_name, details, on_error_recheck=None, base_mo_code=None, is_rep_variant=None, item_count=None):
        """Post a generic event to the API, optionally including base_mo_code, is_rep_variant, and item_count."""
        if not self.database_enabled_var.get():
            return False

        api_url = self.api_url_var.get()
        user = self.user_var.get()
        payload = {
            "event": event,
            "details": details,
            "project": project_name,
            "user": user
        }
        if base_mo_code is not None:
            payload['base_mo_code'] = base_mo_code
        if is_rep_variant is not None:
            payload['is_rep_variant'] = is_rep_variant
        if item_count is not None:
            payload['item_count'] = item_count

        try:
            resp = requests.post(api_url, json=payload, timeout=2, proxies={"http": None, "https": None})  # Reduced timeout
            if resp.status_code in [200, 201] and resp.json().get('success'):
                messagebox.showinfo("Succes", f"Event '{event}' voor '{project_name}' succesvol gelogd.")
                self.refresh_logs()
                return True
            else:
                messagebox.showerror("Fout", f"Fout bij loggen van event: {resp.text}")
                if on_error_recheck:
                    on_error_recheck()
                return False
        except Exception as e:
            messagebox.showerror("API Fout", f"Kon geen verbinding maken met de API: {e}")
            if on_error_recheck:
                on_error_recheck()
            return False

    def log_project_closed(self, project_name, on_error_recheck=None, base_mo_code=None, is_rep_variant=None, item_count=None):
        """
        Post a AFGEMELD event to the API, including base_mo_code, is_rep_variant, and item_count if provided.
        If POST fails and database is enabled, call on_error_recheck (if provided).
        Returns True if success, False if error.
        """
        user = self.user_var.get() if hasattr(self, 'user_var') else 'user'
        details = f"{project_name} afgemeld aan {user}"
        return self.log_event("AFGEMELD", project_name, details, on_error_recheck, base_mo_code=base_mo_code, is_rep_variant=is_rep_variant, item_count=item_count)

    def set_db_recheck_callback(self, callback):
        """Set a callback to be called when a connection recheck is needed (e.g., from log_project_closed)."""
        self._db_recheck_callback = callback

    def log_test_event(self):
        """Stub for log event."""
        messagebox.showinfo("Log Event", "Log event test is niet geïmplementeerd in deze migratie.")

    def refresh_logs(self):
        """Start a worker thread to fetch logs so the UI never blocks."""
        def fetch_logs():
            logs = []
            error = None
            try:
                url = self.api_url_var.get()
                logs_url = url.replace('/log', '/logs')

                # Add user filter to get all logs for this user (avoids 500-entry limit competition with other users)
                user = self.user_var.get() if hasattr(self, 'user_var') else ''
                params = {'user': user} if user else {}

                response = requests.get(logs_url, params=params, timeout=2, proxies={"http": None, "https": None})  # Reduced timeout
                if response.status_code == 200:
                    logs = response.json()
                    # Update connection status on successful logs fetch
                    if hasattr(self, 'connection_status_label'):
                        self.after(0, lambda: self._safe_update_connection_label("Verbonden (LOGS)", "green"))
                else:
                    error = f"Fout: {response.status_code}"
            except Exception as e:
                error = str(e)
            
            # Schedule UI update in the main thread
            self.after(0, lambda: self._update_logs_ui(logs, error))
        
        threading.Thread(target=fetch_logs, daemon=True).start()
    
    def _safe_update_connection_label(self, text, color):
        """Safely update connection label"""
        try:
            if self.connection_status_label.winfo_exists():
                self.connection_status_label.config(text=text, foreground=color)
        except tk.TclError:
            pass  # Widget destroyed

    def _update_logs_ui(self, logs, error=None):
        """Update the logs UI with fetched data."""
        try:
            # Check if widget still exists
            if not self.logs_tree.winfo_exists():
                return
            
            # Store the currently selected item's data for restoration
            selected_item_data = None
            selected_items = self.logs_tree.selection()
            if selected_items:
                try:
                    # Get the values of the first selected item
                    selected_item_data = self.logs_tree.item(selected_items[0], 'values')
                except (tk.TclError, IndexError):
                    selected_item_data = None
            
            # Store the current sort state
            saved_sort_column = self._log_sort_column
            saved_sort_reverse = self._log_sort_reverse
                
            # Clear the tree
            for row in self.logs_tree.get_children():
                self.logs_tree.delete(row)

            user = self.user_var.get() if hasattr(self, 'user_var') else ''
            if error:
                self._all_log_items = [("Fout", error, "", "", user, "")]
                self.logs_tree.insert("", "end", values=self._all_log_items[0])
                return # Stop further processing if there's an error fetching logs

            if not logs:
                self._all_log_items = [("", "Geen logs gevonden voor gebruiker", "", "", user, "")]
                self.logs_tree.insert("", "end", values=self._all_log_items[0])
                return

            # First pass: identify projects that have been AFGEMELD more than a day ago
            completed_projects = set()
            today = date.today()
            
            for log_entry in logs:
                if log_entry.get('user') != user:
                    continue
                    
                project_name = log_entry.get('project')
                status = (log_entry.get('status') or '').upper()
                timestamp_str = log_entry.get('timestamp')
                
                if not project_name or not status or not timestamp_str:
                    continue
                    
                try:
                    log_datetime = datetime.fromisoformat(timestamp_str)
                    log_date = log_datetime.date()
                except ValueError:
                    continue
                
                # If this project has an AFGEMELD status older than today, mark it as completed
                if status == 'AFGEMELD' and log_date < today:
                    completed_projects.add(project_name)
            
            # Second pass: build latest_events, excluding completed projects entirely
            latest_events = {}
            
            for log_entry in logs:
                # Process only logs for the current user
                if log_entry.get('user') != user:
                    continue

                project_name = log_entry.get('project')
                status = (log_entry.get('status') or '').upper() # Ensure status is uppercase for comparison
                timestamp_str = log_entry.get('timestamp')

                if not project_name or not status or not timestamp_str:
                    continue # Skip logs with missing essential data
                
                # Skip ALL events for projects that have been completed (AFGEMELD > 1 day ago)
                if project_name in completed_projects:
                    continue

                try:
                    log_datetime = datetime.fromisoformat(timestamp_str)
                    log_date = log_datetime.date()
                except ValueError:
                    continue # Skip logs with invalid timestamp format
                
                # If status is not OPEN or AFGEMELD, skip (unless you want to include others)
                if status not in ['OPEN', 'AFGEMELD', 'EXCEL_GENERATED', 'BEZIG']:
                    continue

                # Logic to keep the most relevant log: latest OPEN, or today's latest AFGEMELD
                current_latest = latest_events.get(project_name)
                if not current_latest:
                    latest_events[project_name] = log_entry
                else:
                    current_latest_datetime = datetime.fromisoformat(current_latest['timestamp'])
                    current_latest_status = (current_latest.get('status') or '').upper()

                    if status in ['OPEN', 'EXCEL_GENERATED']:
                        # An OPEN or EXCEL_GENERATED event always takes precedence if it's newer,
                        # or if the current latest is AFGEMELD
                        if log_datetime > current_latest_datetime or current_latest_status == 'AFGEMELD':
                            latest_events[project_name] = log_entry
                    elif status == 'AFGEMELD': # Current or recent AFGEMELD
                        # An AFGEMELD event only replaces an older AFGEMELD or if current is older OPEN
                        if current_latest_status == 'AFGEMELD' and log_datetime > current_latest_datetime:
                            latest_events[project_name] = log_entry
                        # If current_latest is OPEN, AFGEMELD (even if newer) doesn't replace it unless you want that behavior
                        # The current logic prefers keeping an OPEN status visible over a more recent AFGEMELD one.
                        # For now, if current is OPEN, today's AFGEMELD does not replace it.
            
            # Sort by timestamp descending to show newest first
            sorted_log_items = sorted(latest_events.values(), key=lambda l: datetime.fromisoformat(l['timestamp']), reverse=True)

            if not sorted_log_items:
                self._all_log_items = [("", "Geen relevante logs gevonden", "", "", user, "")]
                self.logs_tree.insert("", "end", values=self._all_log_items[0])
            else:
                # Store all log items for filtering
                self._all_log_items = []
                new_item_to_select = None
                for log_item in sorted_log_items:
                    # Format timestamp for display if needed, e.g., to exclude microseconds
                    display_ts = datetime.fromisoformat(log_item['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    file_path = log_item.get('file_path', '')
                    item_values = (
                        display_ts,
                        log_item.get('status', ''),
                        log_item.get('project', ''),
                        log_item.get('details', ''),
                        log_item.get('user', ''),
                        file_path
                    )
                    self._all_log_items.append(item_values)

                    # Check if this is a SPOED project
                    is_spoed = self._is_spoed_project(log_item.get('project', ''))

                    # Insert with appropriate tag for SPOED projects
                    if is_spoed:
                        new_item = self.logs_tree.insert("", "end", values=item_values, tags=('spoed',))
                    else:
                        new_item = self.logs_tree.insert("", "end", values=item_values)
                    
                    # Check if this item matches the previously selected item
                    if (selected_item_data and len(selected_item_data) >= 3 and 
                        len(item_values) >= 3 and
                        # Match by project name and status (most reliable identifiers)
                        selected_item_data[2] == item_values[2] and  # project
                        selected_item_data[1] == item_values[1]):    # status
                        new_item_to_select = new_item
                
                # Restore selection if we found a matching item
                if new_item_to_select:
                    try:
                        self.logs_tree.selection_set(new_item_to_select)
                        self.logs_tree.focus(new_item_to_select)
                        # Ensure the selected item is visible
                        self.logs_tree.see(new_item_to_select)
                    except tk.TclError:
                        pass  # Selection restoration failed, but that's okay
                
                # Re-apply search filter if active
                if hasattr(self, 'search_var') and self.search_var.get().strip():
                    self._filter_logs()
                else:
                    # Re-apply the sort state if it was set
                    if saved_sort_column:
                        # Restore the sort state variables
                        self._log_sort_column = saved_sort_column
                        self._log_sort_reverse = saved_sort_reverse
                        # Re-sort the tree
                        data = [(self.logs_tree.set(k, saved_sort_column), k) for k in self.logs_tree.get_children("")]
                        def try_num(val):
                            try:
                                return int(val)
                            except Exception:
                                try:
                                    return float(val)
                                except Exception:
                                    return val.lower() if isinstance(val, str) else val
                        data.sort(key=lambda t: try_num(t[0]), reverse=saved_sort_reverse)
                        for idx, (val, k) in enumerate(data):
                            self.logs_tree.move(k, '', idx)
        except tk.TclError:
            # This can happen if the widget is destroyed while a refresh is pending
            pass # Silently ignore, as the panel is being closed
        except Exception as e:
            # Log other unexpected errors, or show them in the UI if appropriate
            print(f"Error updating logs UI: {e}") # For debugging
            try:
                # Attempt to show a generic error in the tree if it's still usable
                if self.logs_tree.winfo_exists():
                    for row in self.logs_tree.get_children(): 
                        self.logs_tree.delete(row)
                    self.logs_tree.insert("", "end", values=("Error", f"UI Update Error: {e}", "", "", "", ""))
            except Exception: # If even that fails, just pass
                pass