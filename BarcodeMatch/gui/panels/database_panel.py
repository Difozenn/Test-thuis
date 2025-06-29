import tkinter as tk
from tkinter import ttk, messagebox, Menu
import re
import os
import json
import requests
from config_utils import get_config_path, update_config
from datetime import datetime, date
import threading

class DatabasePanel(ttk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.main_app = main_app
        self.config = self.load_config()
        self._logs_refresh_running = False
        self._logs_thread = None
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
        
        self.logs_tree = ttk.Treeview(logs_frame, columns=("timestamp", "status", "project", "details", "user", "FilePath"), show="headings")
        self._log_sort_column = None
        self._log_sort_reverse = False
        
        for col in ("timestamp", "status", "project", "details", "user", "FilePath"):
            self.logs_tree.heading(col, text=col.capitalize(), command=lambda c=col: self._sort_logs_tree(c))
            if col == "FilePath":
                self.logs_tree.column(col, width=0, stretch=tk.NO)  # Hide the FilePath column
            else:
                self.logs_tree.column(col, width=100 if col not in ["details", "project"] else 180, anchor=tk.W)
        
        self.logs_tree.pack(fill='both', expand=True)

        # Right-click context menu
        self.tree_menu = tk.Menu(self, tearoff=0)
        self.tree_menu.add_command(label="Log 'OPEN' Event", command=lambda: self._log_manual_event("OPEN"))
        self.tree_menu.add_command(label="Log 'AFGEMELD' Event", command=lambda: self._log_manual_event("AFGEMELD"))
        self.logs_tree.bind("<Button-3>", self._show_tree_menu)
        self.logs_tree.bind("<Double-1>", self._on_log_double_click)

        spacer = tk.Label(frame)
        spacer.pack(expand=True, fill='both')
        copyright_label = tk.Label(self, text="© 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)

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

        log_status = str(item_values[1]).upper() # Status is the second column (index 1)
        project_name = str(item_values[2])    # Project is the third column (index 2)
        log_details = str(item_values[3]) if len(item_values) > 3 else ""
        log_user = str(item_values[4]).upper() if len(item_values) > 4 else ""
        file_path_from_db = str(item_values[5]) if len(item_values) > 5 else ""

        # DEBUG: Print extracted values
        print(f"[DBLCLICK DEBUG] Status: '{log_status}'")
        print(f"[DBLCLICK DEBUG] Project: '{project_name}'")
        print(f"[DBLCLICK DEBUG] Details: '{log_details}'")
        print(f"[DBLCLICK DEBUG] User: '{log_user}'")
        print(f"[DBLCLICK DEBUG] File path from DB: '{file_path_from_db}'")

        if log_status == 'OPEN' or log_status == 'EXCEL_GENERATED':
            if not project_name:
                print("[DBLCLICK DEBUG] No project name found")
                messagebox.showwarning("Geen project", "Geen projectnaam gevonden voor deze log entry.")
                return

            path_to_load = None

            # PRIORITY 1: Use the exact file_path from database if it's a valid Excel file
            print(f"[DBLCLICK DEBUG] PRIORITY 1: Checking direct Excel file path")
            print(f"[DBLCLICK DEBUG] file_path_from_db: '{file_path_from_db}'")
            print(f"[DBLCLICK DEBUG] Is Excel file: {file_path_from_db.lower().endswith(('.xlsx', '.xls')) if file_path_from_db else False}")
            print(f"[DBLCLICK DEBUG] File exists: {os.path.exists(file_path_from_db) if file_path_from_db else False}")
            
            if file_path_from_db and file_path_from_db.lower().endswith(('.xlsx', '.xls')) and os.path.exists(file_path_from_db):
                path_to_load = file_path_from_db
                print(f"[DBLCLICK] Found Excel file directly from database: {path_to_load}")
                self.main_app.switch_to_scanner_and_load(path_to_load)
                return

            # PRIORITY 2: If file_path_from_db is a directory, search for Excel files in it
            print(f"[DBLCLICK DEBUG] PRIORITY 2: Checking if path is directory")
            print(f"[DBLCLICK DEBUG] Is directory: {os.path.isdir(file_path_from_db) if file_path_from_db else False}")
            
            if file_path_from_db and file_path_from_db != 'None' and file_path_from_db.strip() and os.path.isdir(file_path_from_db):
                print(f"[DBLCLICK] Searching for Excel in directory from database: {file_path_from_db}")
                # Determine the base for the Excel filename based on the user type
                excel_filename_base = ""
                if log_user in ['GANNOMAT', 'KL GANNOMAT']:  # Handle both variants
                    excel_filename_base = project_name
                    print(f"[DBLCLICK] User is GANNOMAT-type, using project_name '{project_name}' for Excel filename.")
                else: # Default behavior for OPUS and others
                    excel_filename_base = os.path.basename(os.path.normpath(file_path_from_db))
                    print(f"[DBLCLICK] User is {log_user}, using directory base name '{excel_filename_base}' for Excel filename.")

                excel_filename_updated = f"{excel_filename_base}_updated.xlsx"
                excel_filename_original = f"{excel_filename_base}.xlsx"

                potential_paths = [
                    os.path.join(file_path_from_db, excel_filename_updated),
                    os.path.join(file_path_from_db, excel_filename_original)
                ]
                
                print(f"[DBLCLICK DEBUG] Potential paths to check:")
                for i, p_path in enumerate(potential_paths):
                    print(f"[DBLCLICK DEBUG]   {i+1}. {p_path} (exists: {os.path.exists(p_path)})")

                for p_path in potential_paths:
                    if os.path.exists(p_path):
                        path_to_load = p_path
                        print(f"[DBLCLICK] Found Excel using DB directory path: {path_to_load}")
                        self.main_app.switch_to_scanner_and_load(path_to_load)
                        return

                print(f"[DBLCLICK] Excel not found in DB directory '{file_path_from_db}'. Proceeding to fallbacks.")

            # PRIORITY 3: Parse path from log_details (Fallback for older logs)
            print(f"[DBLCLICK DEBUG] PRIORITY 3: Parsing path from log details")
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
                self.main_app.switch_to_scanner_and_load(path_to_load)
                return
            elif parsed_path_used and not path_to_load: # Parsed path but file not found there
                messagebox.showwarning("Bestand niet gevonden (Log Pad)",
                                       f"Excel-bestand niet gevonden op het pad vermeld in de log details:\n{parsed_base_path}")
                return # Stop if we used parsed path and failed

            # PRIORITY 4: Fallback to BarcodeMatch 'default_base_dir' (Basis map)
            print(f"[DBLCLICK DEBUG] PRIORITY 4: Checking fallback 'default_base_dir'")
            print(f"[DBLCLICK] Path not found in log details or file not at parsed path. Falling back to 'default_base_dir'.")
            
            app_config = self.main_app.load_app_config()
            print(f"[DBLCLICK DEBUG] App config loaded: {app_config}")
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
                self.main_app.switch_to_scanner_and_load(path_to_load)
            else:
                print(f"[DBLCLICK DEBUG] No Excel file found in any location")
                messagebox.showwarning("Bestand niet gevonden (Fallback)",
                                       f"Excel-bestand '{excel_filename_original_fallback}' of '{excel_filename_updated_fallback}'\nniet gevonden in de geconfigureerde 'Basis map':\n{default_bm_base_dir}")
        else:
            print(f"[DBLCLICK DEBUG] Not an OPEN or EXCEL_GENERATED status: {log_status}")
            # Optionally, provide feedback if a non-OPEN item is double-clicked
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

        details = f"{project_name} handmatig op '{event_type}' gezet door {user}"
        self.log_event(event_type, project_name, details)

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
            response = requests.post(url, json=payload, timeout=3)
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

    def log_event(self, event, project_name, details, on_error_recheck=None, base_mo_code=None, is_rep_variant=None):
        """Post a generic event to the API, optionally including base_mo_code and is_rep_variant."""
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

        try:
            resp = requests.post(api_url, json=payload, timeout=5)
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

    def log_project_closed(self, project_name, on_error_recheck=None, base_mo_code=None, is_rep_variant=None):
        """
        Post a AFGEMELD event to the API, including base_mo_code and is_rep_variant if provided.
        If POST fails and database is enabled, call on_error_recheck (if provided).
        Returns True if success, False if error.
        """
        user = self.user_var.get() if hasattr(self, 'user_var') else 'user'
        details = f"{project_name} afgemeld aan {user}"
        return self.log_event("AFGEMELD", project_name, details, on_error_recheck, base_mo_code=base_mo_code, is_rep_variant=is_rep_variant)

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
                response = requests.get(logs_url, timeout=5)
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
                
            # Clear the tree
            for row in self.logs_tree.get_children():
                self.logs_tree.delete(row)

            user = self.user_var.get() if hasattr(self, 'user_var') else ''
            if error:
                self.logs_tree.insert("", "end", values=("Fout", error, "", "", user, ""))
                return # Stop further processing if there's an error fetching logs

            if not logs:
                self.logs_tree.insert("", "end", values=("", "Geen logs gevonden voor gebruiker", "", "", user, ""))
                return

            latest_events = {}
            today = date.today()

            for log_entry in logs:
                # Process only logs for the current user
                if log_entry.get('user') != user:
                    continue

                project_name = log_entry.get('project')
                status = log_entry.get('status', '').upper() # Ensure status is uppercase for comparison
                timestamp_str = log_entry.get('timestamp')

                if not project_name or not status or not timestamp_str:
                    continue # Skip logs with missing essential data

                try:
                    log_datetime = datetime.fromisoformat(timestamp_str)
                    log_date = log_datetime.date()
                except ValueError:
                    continue # Skip logs with invalid timestamp format

                # Apply filtering: AFGEMELD only for today, OPEN always considered
                if status == 'AFGEMELD' and log_date != today:
                    continue
                
                # If status is not OPEN or AFGEMELD, skip (unless you want to include others)
                if status not in ['OPEN', 'AFGEMELD', 'EXCEL_GENERATED']:
                    continue

                # Logic to keep the most relevant log: latest OPEN, or today's latest AFGEMELD
                current_latest = latest_events.get(project_name)
                if not current_latest:
                    latest_events[project_name] = log_entry
                else:
                    current_latest_datetime = datetime.fromisoformat(current_latest['timestamp'])
                    current_latest_status = current_latest['status'].upper()

                    if status in ['OPEN', 'EXCEL_GENERATED']:
                        # An OPEN or EXCEL_GENERATED event always takes precedence if it's newer,
                        # or if the current latest is AFGEMELD
                        if log_datetime > current_latest_datetime or current_latest_status == 'AFGEMELD':
                            latest_events[project_name] = log_entry
                    elif status == 'AFGEMELD': # And we know it's from today due to earlier filter
                        # An AFGEMELD event only replaces an older AFGEMELD or if current is older OPEN
                        if current_latest_status == 'AFGEMELD' and log_datetime > current_latest_datetime:
                            latest_events[project_name] = log_entry
                        # If current_latest is OPEN, AFGEMELD (even if newer) doesn't replace it unless you want that behavior
                        # The current logic prefers keeping an OPEN status visible over a more recent AFGEMELD one.
                        # For now, if current is OPEN, today's AFGEMELD does not replace it.
            
            # Sort by timestamp descending to show newest first
            sorted_log_items = sorted(latest_events.values(), key=lambda l: datetime.fromisoformat(l['timestamp']), reverse=True)

            if not sorted_log_items:
                self.logs_tree.insert("", "end", values=("", "Geen relevante logs gevonden", "", "", user, ""))
            else:
                for log_item in sorted_log_items:
                    # Format timestamp for display if needed, e.g., to exclude microseconds
                    display_ts = datetime.fromisoformat(log_item['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    file_path = log_item.get('file_path', '')
                    self.logs_tree.insert("", "end", values=(
                        display_ts,
                        log_item.get('status', ''),
                        log_item.get('project', ''),
                        log_item.get('details', ''),
                        log_item.get('user', ''),
                        file_path
                    ))
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