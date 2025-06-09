import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os
import re
import json
import requests

from config_utils import get_config_path, update_config

class DatabaseTab:
    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        self.config = self.load_config()
        self.build_tab()

    def toggle_database_enabled(self):
        self.save_config()
        self.update_database_ui_state()

    def update_database_ui_state(self):
        enabled = self.database_enabled_var.get()
        state = "normal" if enabled else "disabled"
        # Grey out all config widgets except the enable checkbox
        def set_state_recursive(widget, state):
            # Never disable the 'Database Inschakelen' checkbox
            if isinstance(widget, ttk.Checkbutton):
                return
            try:
                widget.config(state=state)
            except Exception:
                pass
            for child in widget.winfo_children():
                set_state_recursive(child, state)
        # Only apply to all children except the first row (checkbox)
        for child in self.config_frame.winfo_children():
            if isinstance(child, ttk.LabelFrame):
                for w in child.winfo_children():
                    set_state_recursive(w, state)
        if not enabled:
            self.connection_status_label.config(text="Niet verbonden", foreground="red")

    def build_tab(self):
        frame = tk.Frame(self.parent)
        frame.pack(fill='both', expand=True)

        # Database enabled toggle
        self.database_enabled_var = tk.BooleanVar(value=self.config.get('database_enabled', True))
        self.config_frame = ttk.Frame(frame)
        self.config_frame.pack(fill='x', padx=10, pady=10)

        config_frame = ttk.LabelFrame(self.config_frame, text="API Configuratie", padding=10)
        config_frame.pack(fill='x')
        # Remove extra space between label and entry
        config_frame.grid_columnconfigure(0, weight=0)
        config_frame.grid_columnconfigure(1, weight=1)
        config_frame.grid_columnconfigure(2, weight=0)
        config_frame.grid_columnconfigure(3, weight=0)
        config_frame.grid_columnconfigure(4, weight=0)

        # Database enabled toggle
        self.database_enabled_var = tk.BooleanVar(value=self.config.get('database_enabled', True))
        db_enable_chk = ttk.Checkbutton(config_frame, text="Database Inschakelen", variable=self.database_enabled_var, command=self.toggle_database_enabled)
        db_enable_chk.grid(row=0, column=0, columnspan=2, padx=(0,10), sticky=tk.W)
        # API config widgets start from row 1, all left-aligned
        self.api_url_var = tk.StringVar(value=self.config.get('api_url', 'http://localhost:5000/log'))
        self.user_var = tk.StringVar(value=self.config.get('user', os.getlogin() if hasattr(os, 'getlogin') else 'user'))
        ttk.Label(config_frame, text="API URL:").grid(row=1, column=0, sticky=tk.W, pady=(8,0))
        self.api_url_entry = ttk.Entry(config_frame, textvariable=self.api_url_var, width=40)
        self.api_url_entry.grid(row=1, column=1, sticky=tk.W)
        ttk.Label(config_frame, text="Gebruiker:").grid(row=2, column=0, sticky=tk.W)
        self.user_entry = ttk.Entry(config_frame, textvariable=self.user_var, width=18)
        self.user_entry.grid(row=2, column=1, sticky=tk.W)
        self.test_btn = ttk.Button(config_frame, text="Test verbinding", command=self.test_connection)
        self.test_btn.grid(row=3, column=0, sticky=tk.W, pady=(5,0))
        self.save_btn = ttk.Button(config_frame, text="Opslaan", command=self.save_config)
        self.save_btn.grid(row=3, column=1, sticky=tk.W, padx=(5,0), pady=(5,0))
        self.connection_status_label = ttk.Label(config_frame, text="Niet verbonden", foreground="red")
        self.connection_status_label.grid(row=3, column=2, sticky=tk.W, padx=(10,0), pady=(5,0))

        # Log event test
        log_btn = ttk.Button(frame, text="Log test event", command=self.log_test_event)
        log_btn.pack(pady=8)

        # --- Log viewer ---
        logs_frame = ttk.LabelFrame(frame, text="Logs", padding=10)
        logs_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self.logs_tree = ttk.Treeview(logs_frame, columns=("id", "timestamp", "event", "details", "user"), show="headings")
        for col in ("id", "timestamp", "event", "details", "user"):
            self.logs_tree.heading(col, text=col.capitalize())
            self.logs_tree.column(col, width=100 if col!="details" else 250, anchor=tk.W)
        self.logs_tree.pack(fill='both', expand=True)
        refresh_btn = ttk.Button(logs_frame, text="Ververs logs", command=self.refresh_logs)
        refresh_btn.pack(pady=4, anchor=tk.E)
        self.refresh_logs()

        # Copyright at bottom
        spacer = tk.Label(frame)
        spacer.pack(expand=True, fill='both')
        copyright_label = tk.Label(frame, text=' 2025 RVL', font=(None, 9), fg='#888888')
        copyright_label.pack(side=tk.BOTTOM, pady=2)

        # Test connection in background to avoid UI lag
        import threading
        if self.database_enabled_var.get():
            threading.Thread(target=self.check_connection, daemon=True).start()
        self.update_database_ui_state()

    def load_config(self):
        config_path = get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_config(self):
        config = {
            'api_url': self.api_url_var.get(),
            'user': self.user_var.get(),
            'database_enabled': self.database_enabled_var.get()
        }
        update_config(config)
        self.config = config
        if self.database_enabled_var.get():
            self.test_connection()


    def test_connection(self):
        url = self.api_url_var.get()
        try:
            # This one logs the test_connect event intentionally
            resp = requests.post(url, json={"event": "test_connect", "details": "Test verbinding", "user": self.user_var.get()}, timeout=3)
            if resp.status_code == 200 and resp.json().get('success'):
                self.connection_status_label.after(0, lambda: self.connection_status_label.config(text="Verbonden", foreground="green"))
                messagebox.showinfo("Succes", "Verbinding met API geslaagd!")
            else:
                self.connection_status_label.after(0, lambda: self.connection_status_label.config(text="Niet verbonden", foreground="red"))
                messagebox.showerror("Fout", f"API gaf geen succes terug:\n{resp.text}")
        except Exception as e:
            self.connection_status_label.after(0, lambda: self.connection_status_label.config(text="Niet verbonden", foreground="red"))
            messagebox.showerror("Verbindingsfout", f"Fout bij verbinden met API:\n{e}")

    def check_connection(self):
        url = self.api_url_var.get()
        try:
            # Use a GET request to /logs to check API connectivity without logging
            test_url = url.strip().replace('/log', '/logs')
            resp = requests.get(test_url, timeout=3)
            if resp.status_code == 200:
                self.connection_status_label.after(0, lambda: self.connection_status_label.config(text="Verbonden", foreground="green"))
            else:
                self.connection_status_label.after(0, lambda: self.connection_status_label.config(text="Niet verbonden", foreground="red"))
        except Exception:
            self.connection_status_label.after(0, lambda: self.connection_status_label.config(text="Niet verbonden", foreground="red"))


    def log_event(self, event, details=None):
        if not self.database_enabled_var.get():
            return False
        url = self.api_url_var.get()
        user = self.user_var.get()
        try:
            resp = requests.post(url, json={"event": event, "details": details, "user": user}, timeout=5)
            if resp.status_code == 200 and resp.json().get('success'):
                return True
            else:
                messagebox.showerror("Logfout", f"Kon niet loggen naar centrale API:\n{resp.text}")
                return False
        except Exception as e:
            messagebox.showerror("Logfout", f"Kon niet loggen naar centrale API:\n{e}")
            return False

    def log_project_closed(self, project_name):
        if not self.database_enabled_var.get():
            return False
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        import os
        project_base = os.path.splitext(os.path.basename(project_name))[0]
        details = f"Project {project_base} gesloten op {timestamp}"
        return self.log_event("CLOSED", details)

    def log_test_event(self):
        if not self.database_enabled_var.get():
            messagebox.showinfo("Uitgeschakeld", "Database logging is uitgeschakeld.")
            return
        if self.log_event("test_event", "Dit is een test van REST API logging."):
            messagebox.showinfo("Gelukt", "Test event gelogd naar centrale logging API.")

    def refresh_logs(self):
        if not self.database_enabled_var.get():
            self.logs_tree.delete(*self.logs_tree.get_children())
            return
        url = self.api_url_var.get().strip().replace('/log', '/logs')
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                logs = resp.json()
                self.logs_tree.delete(*self.logs_tree.get_children())
                from datetime import datetime
                for log in logs:
                    # Hide test events in the GUI
                    event = log.get('event', '')
                    if event in ('test_connect', 'test_event'):
                        continue
                    # Format timestamp to ISO8601 without microseconds or timezone
                    ts = log.get('timestamp')
                    try:
                        # Try parsing and reformatting
                        dt = datetime.fromisoformat(ts)
                        ts_fmt = dt.strftime('%Y-%m-%d %H:%M')
                    except Exception:
                        ts_fmt = ts or ''
                    # Show only filename without extension in details, if it matches the pattern
                    details = log.get('details')
                    if details and details.startswith('Project '):
                        match = re.match(r"Project (.+?) gesloten op (.+)", details)
                        if match:
                            filename = match.group(1)
                            details = f"Project {filename} gesloten op {match.group(2)}"
                    self.logs_tree.insert('', 'end', values=(log.get('id'), ts_fmt, log.get('event'), details, log.get('user')))
                else:
                    messagebox.showerror("Fout", f"Kon logs niet ophalen:\n{resp.text}")
        except Exception as e:
            messagebox.showerror("Fout", f"Kon logs niet ophalen:\n{e}")
