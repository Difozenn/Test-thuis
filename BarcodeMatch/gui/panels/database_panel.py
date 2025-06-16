import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
import requests
from config_utils import get_config_path, update_config
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



    def log_project_closed(self, project_name, on_error_recheck=None):
        """
        Post a AFGEMELD event to the API. If POST fails and database is enabled, call on_error_recheck (if provided).
        Returns True if success, False if error.
        """
        config_enabled = self.database_enabled_var.get() if hasattr(self, 'database_enabled_var') else True
        api_url = self.api_url_var.get() if hasattr(self, 'api_url_var') else 'http://localhost:5001/log'
        user = self.user_var.get() if hasattr(self, 'user_var') else 'user'
        payload = {
            "event": "AFGEMELD",
            "details": f"{project_name} afgemeld aan {user}",
            "project": project_name,
            "user": user
        }
        try:
            import requests
            resp = requests.post(api_url, json=payload, timeout=5)
            if resp.status_code == 200 and resp.json().get('success'):
                return True
            else:
                # Only recheck if database is enabled
                if config_enabled and on_error_recheck:
                    self.after(0, on_error_recheck)
                return False
        except Exception as e:
            if config_enabled and on_error_recheck:
                self.after(0, on_error_recheck)
            return False

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
                self.logs_tree.insert("", "end", values=("Fout", error, "", "", ""))
            found = False
            # For each project, keep only the latest OPEN or AFGEMELD event per user
            latest_status = {}
            from datetime import datetime
            for log in logs:
                if log.get('user', '') == user and log.get('project'):
                    project = log.get('project')
                    ts = log.get('timestamp', '')
                    try:
                        dt = datetime.fromisoformat(ts)
                    except Exception:
                        dt = ts
                    event = log.get('event', '').upper()
                    if event in ('OPEN', 'AFGEMELD'):
                        if project not in latest_status or (isinstance(dt, datetime) and isinstance(latest_status[project]['dt'], datetime) and dt > latest_status[project]['dt']):
                            latest_status[project] = {
                                'dt': dt,
                                'log': log
                            }
            for project, info in latest_status.items():
                found = True
                log = info['log']
                raw_ts = log.get('timestamp', '')
                formatted_ts = raw_ts
                try:
                    formatted_ts = datetime.fromisoformat(raw_ts).strftime('%Y-%m-%d %H:%M')
                except Exception:
                    pass
                self.logs_tree.insert("", "end", values=(
                    formatted_ts,
                    log.get("status", ""),
                    log.get("project", ""),
                    log.get("details", ""),
                    log.get("user", "")
                ))
            if not found:
                self.logs_tree.insert("", "end", values=("", "Geen logs gevonden", "", "", ""))
        except Exception as e:
            import tkinter
            if isinstance(e, tkinter.TclError):
                # Widget destroyed, ignore
                pass
            else:
                raise
