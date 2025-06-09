import tkinter as tk
from tkinter import ttk, messagebox
from config_utils import get_config, save_config

import os
import sqlite3
import requests

PANEL_BG = "#f0f0f0"

class AdminPanel(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=PANEL_BG)
        frame = tk.Frame(self, bg=PANEL_BG)
        frame.pack(fill='both', expand=True)
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../database/central_logging.sqlite'))
        self.api_url = get_config().get('api_url', 'http://localhost:5000')
        self.config = get_config()
        # Sectioned config/actions area
        self.admin_frame = ttk.LabelFrame(frame, text="Database Beheer", padding=10)
        self.admin_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self.admin_frame.grid_columnconfigure(0, weight=1)
        self.admin_frame.grid_columnconfigure(1, weight=0)
        self.admin_frame.grid_columnconfigure(2, weight=1)
        self.admin_frame.grid_rowconfigure(3, weight=1)
        # --- Row 0: Database Control ---
        self.db_init_enabled_var = tk.BooleanVar(value=self.config.get('admin_db_init_enabled', True))
        self.db_init_enabled_var.trace_add('write', self.toggle_db_init_enabled)
        enable_chk = ttk.Checkbutton(self.admin_frame, text="Database activeren", variable=self.db_init_enabled_var, command=self.toggle_db_init_enabled)
        enable_chk.grid(row=0, column=0, padx=(0,10), pady=(2,8), sticky='w')
        self.terminate_db_on_exit_var = tk.BooleanVar(value=self.config.get('admin_terminate_db_on_exit', False))
        self.terminate_chk = ttk.Checkbutton(self.admin_frame, text="Terminate database on exit", variable=self.terminate_db_on_exit_var, command=self.save_terminate_db_on_exit)
        self.terminate_chk.grid(row=0, column=1, padx=(0,10), pady=(2,8), sticky='w')
        self.api_status_label = tk.Label(self.admin_frame, text="", font=(None, 10, 'bold'), bg=PANEL_BG)
        self.api_status_label.grid(row=0, column=2, padx=(10,0), pady=(2,8), sticky='e')
        # --- Row 1: Database API Actions ---
        stop_db_btn = ttk.Button(self.admin_frame, text="Stop Database API", command=self.on_stop_db_api)
        stop_db_btn.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
        view_log_btn = ttk.Button(self.admin_frame, text="View DB Log", command=self.open_db_log_viewer)
        view_log_btn.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        # --- Row 2: Database Maintenance ---
        self.init_btn = ttk.Button(self.admin_frame, text="Initialize Database", command=self.init_db)
        self.clear_btn = ttk.Button(self.admin_frame, text="Clear Logs", command=self.clear_logs)
        self.refresh_btn = ttk.Button(self.admin_frame, text="Refresh Info", command=self.update_db_info)
        self.init_btn.grid(row=2, column=0, padx=5, pady=5, sticky='ew')
        self.clear_btn.grid(row=2, column=1, padx=5, pady=5, sticky='ew')
        self.refresh_btn.grid(row=2, column=2, padx=5, pady=5, sticky='ew')
        # --- Row 3: Log Viewing ---
        self.open_logs_btn = ttk.Button(self.admin_frame, text="Open Logs in Browser", command=self.open_logs_html)
        self.open_logs_btn.grid(row=3, column=0, columnspan=3, padx=5, pady=(10, 0), sticky='ew')
        # --- Row 4: DB Info ---
        self.db_info_label = tk.Label(self.admin_frame, text="", bg=PANEL_BG, anchor="w", justify="left")
        self.db_info_label.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.update_db_info()
        self.start_api_status_thread()
        # Make all button columns expand
        self.admin_frame.grid_columnconfigure(0, weight=1)
        self.admin_frame.grid_columnconfigure(1, weight=1)
        self.admin_frame.grid_columnconfigure(2, weight=1)
        # --- Lock Admin Panel Button ---
        self.lock_admin_btn = ttk.Button(self.admin_frame, text="Lock Admin Panel", command=self.lock_admin_panel)
        self.lock_admin_btn.grid(row=5, column=0, columnspan=3, padx=10, pady=(10, 5), sticky='ew')

    def lock_admin_panel(self):
        # Try to call the main app's lock_admin_panel if available
        try:
            # self.master is frame, self.master.master is MainApp
            if hasattr(self.master.master, 'lock_admin_panel'):
                self.master.master.lock_admin_panel()
            else:
                tk.messagebox.showerror("Error", "Lock function not available in main app.")
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to lock admin panel: {e}")

        # Spacer and copyright
        spacer = tk.Label(frame, bg=PANEL_BG)
        spacer.pack(expand=True, fill='both')
        copyright_label = tk.Label(frame, text=' 2025 RVL', font=(None, 9), fg='#888888', bg=PANEL_BG)
        copyright_label.pack(side=tk.BOTTOM, pady=2)
        self.update_admin_ui_state()

    def toggle_db_init_enabled(self, *args):
        save_config({'admin_db_init_enabled': self.db_init_enabled_var.get()})
        self.update_admin_ui_state()

    def save_terminate_db_on_exit(self):
        save_config({'admin_terminate_db_on_exit': self.terminate_db_on_exit_var.get()})
        # If checked, terminate the database immediately
        if self.terminate_db_on_exit_var.get():
            self.terminate_db_log_api_process()

    def terminate_db_log_api_process(self):
        import psutil
        import sys
        found = False
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if p.info['cmdline'] and any('db_log_api.py' in str(arg) for arg in p.info['cmdline']):
                    found = True
                    p.terminate()
                    try:
                        p.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        p.kill()
            except Exception:
                pass
        return found

    def on_stop_db_api(self):
        from tkinter import messagebox
        result = self.terminate_db_log_api_process()
        if result:
            messagebox.showinfo('Database API', 'db_log_api.py process is gestopt.')
        else:
            messagebox.showinfo('Database API', 'Geen db_log_api.py proces gevonden om te stoppen.')

    def open_db_log_viewer(self):
        import os
        import tkinter as tk
        from tkinter import messagebox
        log_path = os.path.join(os.path.dirname(__file__), '../../database/db_log_api.log')
        log_path = os.path.abspath(log_path)
        if not os.path.exists(log_path):
            messagebox.showerror("Log Not Found", f"Could not find log file:\n{log_path}")
            return
        win = tk.Toplevel(self)
        win.title("Database Log Viewer")
        win.geometry("800x500")
        text = tk.Text(win, wrap='none')
        text.pack(fill='both', expand=True)
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            text.insert('1.0', f.read())
        text.config(state='disabled')

    def update_admin_ui_state(self):
        enabled = self.db_init_enabled_var.get()
        state = "normal" if enabled else "disabled"
        for widget in [self.db_info_label, self.init_btn, self.clear_btn, self.refresh_btn, self.open_logs_btn]:
            try:
                widget.config(state=state)
            except Exception:
                pass
        # Do NOT disable api_status_label or enable_chk
        self.start_api_status_thread()

    def update_db_info(self):
        exists = os.path.exists(self.db_path)
        size = os.path.getsize(self.db_path) if exists else 0
        count = self.get_log_count()
        self.db_info_label.config(text=f"DB Path: {self.db_path}\nExists: {exists} | Size: {size} bytes | Log Entries: {count}")
        self.start_api_status_thread()

    def get_log_count(self):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM logs')
            count = c.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 'N/A'

    def init_db(self):
        # Try API first
        try:
            url = self.api_url.rstrip('/') + '/init_db'
            resp = requests.post(url, timeout=5)
            if resp.status_code == 200 and resp.json().get('success'):
                messagebox.showinfo("Success", "Database initialized via API.")
                self.update_db_info()
                return
        except Exception:
            pass
        # Fallback to local
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                event TEXT,
                details TEXT,
                user TEXT)''')
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Database initialized locally.")
            self.update_db_info()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize DB: {e}")

    def open_logs_html(self):
        import webbrowser
        url = self.api_url.rstrip('/log') + '/logs_html'
        webbrowser.open(url)

    def start_api_status_thread(self):
        import threading
        if hasattr(self, '_api_status_thread') and self._api_status_thread.is_alive():
            return  # Only one status thread at a time
        self._api_status_thread = threading.Thread(target=self._api_status_worker, daemon=True)
        self._api_status_thread.start()

    def _api_status_worker(self):
        import requests
        import time
        # Only check if enabled
        if not self.db_init_enabled_var.get():
            self.after(0, lambda: self._set_api_status_label("API uitgeschakeld", "gray"))
            return
        url = self.api_url.rstrip('/log') + '/logs_html'
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                self.after(0, lambda: self._set_api_status_label("API running", "green"))
            else:
                self.after(0, lambda: self._set_api_status_label("API niet bereikbaar", "red"))
        except Exception:
            self.after(0, lambda: self._set_api_status_label("API niet bereikbaar", "red"))

    def _set_api_status_label(self, text, color):
        try:
            self.api_status_label.config(text=text, fg=color)
        except Exception:
            pass

    def clear_logs(self):
        confirm = messagebox.askyesno("Bevestigen", "Weet je zeker dat je alle logs wilt verwijderen?")
        if not confirm:
            return
        # Try API first
        try:
            url = self.api_url.rstrip('/') + '/clear_logs'
            resp = requests.post(url, timeout=5)
            if resp.status_code == 200 and resp.json().get('success'):
                messagebox.showinfo("Success", "Logs cleared via API.")
                self.update_db_info()
                return
        except Exception:
            pass
        # Fallback to local
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('DELETE FROM logs')
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Logs cleared locally.")
            self.update_db_info()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear logs: {e}")
