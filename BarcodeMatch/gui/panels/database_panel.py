import tkinter as tk
from tkinter import ttk, messagebox
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
            self.connection_status_label.config(text="Niet verbonden", foreground="red")

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
        self.database_enabled_var = tk.BooleanVar(value=self.config.get('database_enabled', True))
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
        # Do not set to 'Verbonden' or green on panel open. Only update after a successful test_connection().
        log_btn = ttk.Button(frame, text="Log test event", command=self.log_test_event)
        log_btn.pack(pady=8)
        logs_frame = ttk.LabelFrame(frame, text="Logs", padding=10)
        logs_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self.logs_tree = ttk.Treeview(logs_frame, columns=("timestamp", "status", "project", "details", "user"), show="headings")
        self._log_sort_column = None
        self._log_sort_reverse = False
        for col in ("timestamp", "status", "project", "details", "user"):
            self.logs_tree.heading(col, text=col.capitalize(), command=lambda c=col: self._sort_logs_tree(c))
            self.logs_tree.column(col, width=100 if col not in ["details", "project"] else 180, anchor=tk.W)
        self.logs_tree.pack(fill='both', expand=True)

        # Right-click context menu
        self.tree_menu = tk.Menu(self, tearoff=0)
        self.tree_menu.add_command(label="Log 'OPEN' Event", command=lambda: self._log_manual_event("OPEN"))
        self.tree_menu.add_command(label="Log 'AFGEMELD' Event", command=lambda: self._log_manual_event("AFGEMELD"))
        self.logs_tree.bind("<Button-3>", self._show_tree_menu)

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


        # Do NOT start logs refresh here to avoid blocking panel load.
        # Call self.start_auto_refresh() from the main app or menu after showing the panel.
        pass

        spacer = tk.Label(frame)
        spacer.pack(expand=True, fill='both')
        copyright_label = tk.Label(self, text=" 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)

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
                    if hasattr(self, 'logs_tree') and self.logs_tree.winfo_exists():
                        self.after(0, self.refresh_logs)
                    else:
                        break
                except Exception:
                    break
                time.sleep(10)  # Refresh every 10 seconds
        self._logs_thread = threading.Thread(target=background_refresh, daemon=True)
        self._logs_thread.start()

    def destroy(self):
        self._logs_refresh_running = False
        super().destroy()

    def test_connection(self):
        url = self.api_url_var.get()
        import requests, json
        payload = {
            "event": "TEST",
            "details": "Test verbinding",
            "project": "TestProject",
            "user": self.user_var.get() if hasattr(self, 'user_var') else 'testuser'
        }
        try:
            response = requests.post(url, json=payload, timeout=3)
            if response.status_code == 200 and response.json().get('success'):
                self.connection_status_label.config(text="Verbonden (POST)", foreground="green")
            else:
                self.connection_status_label.config(text=f"Fout: {response.status_code}", foreground="red")
                messagebox.showerror("Verbinding mislukt", f"Fout bij POST naar API:\n{response.text}")
        except Exception as e:
            self.connection_status_label.config(text="Niet verbonden", foreground="red")
            messagebox.showerror("Verbinding mislukt", f"Kon geen verbinding maken met de API:\n{e}")



    def log_event(self, event, project_name, details, on_error_recheck=None):
        """Post a generic event to the API."""
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

        try:
            resp = requests.post(api_url, json=payload, timeout=5)
            if resp.status_code == 200 and resp.json().get('success'):
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

    def log_project_closed(self, project_name, on_error_recheck=None):
        """
        Post a AFGEMELD event to the API. If POST fails and database is enabled, call on_error_recheck (if provided).
        Returns True if success, False if error.
        """
        config_enabled = self.database_enabled_var.get() if hasattr(self, 'database_enabled_var') else True
        api_url = self.api_url_var.get() if hasattr(self, 'api_url_var') else 'http://localhost:5001/log'
        user = self.user_var.get() if hasattr(self, 'user_var') else 'user'
        details = f"{project_name} afgemeld aan {user}"
        return self.log_event("AFGEMELD", project_name, details, on_error_recheck)

    def set_db_recheck_callback(self, callback):
        """Set a callback to be called when a connection recheck is needed (e.g., from log_project_closed)."""
        self._db_recheck_callback = callback

    def log_test_event(self):
        # Stub for log event
        messagebox.showinfo("Log Event", "Log event test is niet geïmplementeerd in deze migratie.")

    def refresh_logs(self):
        # Start a worker thread to fetch logs so the UI never blocks
        import threading
        def fetch_logs():
            import requests
            logs = []
            error = None
            try:
                url = self.api_url_var.get()
                logs_url = url.replace('/log', '/logs')
                response = requests.get(logs_url, timeout=5)
                if response.status_code == 200:
                    logs = response.json()
                else:
                    error = f"Fout: {response.status_code}"
            except Exception as e:
                error = str(e)
            # Schedule UI update in the main thread
            def update_label_and_logs():
                if not error and logs:
                    # If logs received successfully, set label to green
                    if hasattr(self, "connection_status_label") and self.connection_status_label.winfo_exists():
                        self.connection_status_label.config(text="Verbonden (GET)", foreground="green")
                self._update_logs_ui(logs, error)
            self.after(0, update_label_and_logs)
        threading.Thread(target=fetch_logs, daemon=True).start()

    def _update_logs_ui(self, logs, error=None):
        try:
            # Clear the tree
            for row in self.logs_tree.get_children():
                self.logs_tree.delete(row)

            user = self.user_var.get() if hasattr(self, 'user_var') else ''
            if error:
                self.logs_tree.insert("", "end", values=("Fout", error, "", "", user))
                return # Stop further processing if there's an error fetching logs

            if not logs:
                self.logs_tree.insert("", "end", values=("", "Geen logs gevonden voor gebruiker", "", "", user))
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
                if status not in ['OPEN', 'AFGEMELD']:
                    continue

                # Logic to keep the most relevant log: latest OPEN, or today's latest AFGEMELD
                current_latest = latest_events.get(project_name)
                if not current_latest:
                    latest_events[project_name] = log_entry
                else:
                    current_latest_datetime = datetime.fromisoformat(current_latest['timestamp'])
                    current_latest_status = current_latest['status'].upper()

                    if status == 'OPEN':
                        # An OPEN event always takes precedence if it's newer,
                        # or if the current latest is AFGEMELD (OPEN is preferred over AFGEMELD)
                        if log_datetime > current_latest_datetime or current_latest_status == 'AFGEMELD':
                            latest_events[project_name] = log_entry
                    elif status == 'AFGEMELD': # And we know it's from today due to earlier filter
                        # An AFGEMELD event only replaces an older AFGEMELD or if current is older OPEN
                        if current_latest_status == 'AFGEMELD' and log_datetime > current_latest_datetime:
                            latest_events[project_name] = log_entry
                        # If current_latest is OPEN, AFGEMELD (even if newer) doesn't replace it unless you want that behavior
                        # The current logic prefers keeping an OPEN status visible over a more recent AFGEMELD one.
                        # If an OPEN is older, and this AFGEMELD is today and newer, it could replace it if logic changes.
                        # For now, if current is OPEN, today's AFGEMELD does not replace it.
            
            # Sort by timestamp descending to show newest first
            sorted_log_items = sorted(latest_events.values(), key=lambda l: datetime.fromisoformat(l['timestamp']), reverse=True)

            if not sorted_log_items:
                self.logs_tree.insert("", "end", values=("", "Geen relevante logs gevonden", "", "", user))
            else:
                for log_item in sorted_log_items:
                    # Format timestamp for display if needed, e.g., to exclude microseconds
                    display_ts = datetime.fromisoformat(log_item['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    self.logs_tree.insert("", "end", values=(
                        display_ts,
                        log_item.get('status', ''),
                        log_item.get('project', ''),
                        log_item.get('details', ''),
                        log_item.get('user', '')
                    ))
        except tkinter.TclError:
            # This can happen if the widget is destroyed while a refresh is pending
            pass # Silently ignore, as the panel is being closed
        except Exception as e:
            # Log other unexpected errors, or show them in the UI if appropriate
            print(f"Error updating logs UI: {e}") # For debugging
            try:
                # Attempt to show a generic error in the tree if it's still usable
                if self.logs_tree.winfo_exists():
                    for row in self.logs_tree.get_children(): self.logs_tree.delete(row)
                    self.logs_tree.insert("", "end", values=("Error", f"UI Update Error: {e}", "", "", ""))
            except Exception: # If even that fails, just pass
                pass
