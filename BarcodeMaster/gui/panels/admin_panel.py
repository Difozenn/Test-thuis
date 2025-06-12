import tkinter as tk
from tkinter import ttk, messagebox
from config_utils import get_config, save_config

import os
import sqlite3
import requests
import subprocess
import time
import sys
import threading
import socket

PANEL_BG = "#f0f0f0"

class AdminPanel(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=PANEL_BG)
        frame = tk.Frame(self, bg=PANEL_BG)
        frame.pack(fill='both', expand=True)
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../database/central_logging.sqlite'))
        self.api_url = get_config().get('api_url', 'http://localhost:5001')
        self.config = get_config()
        self.lan_ip = 'Detecting...'
        threading.Thread(target=self._detect_lan_ip, daemon=True).start()
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
        self.init_btn = ttk.Button(self.admin_frame, text="Start Database API", command=self.init_db)
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
        lan_ip = getattr(self, 'lan_ip', 'Detecting...')
        self.db_info_label.config(text=f"DB Path: {self.db_path}\nExists: {exists} | Size: {size} bytes | Log Entries: {count}\nLan IP: {lan_ip}")
        self.start_api_status_thread()

    def _detect_lan_ip(self):
        ip = '127.0.0.1'  # Default to loopback

        # Attempt 1: Get IPs associated with the hostname
        try:
            hostname = socket.gethostname()
            addresses = socket.gethostbyname_ex(hostname)[2]
            for addr in addresses:
                if not addr.startswith('127.') and not addr.startswith('169.254.'):
                    # Basic check for IPv4 format
                    if addr.count('.') == 3 and all(0 <= int(p) < 256 for p in addr.split('.')):
                        ip = addr
                        break  # Use the first valid one found
            # If 'ip' is still '127.0.0.1', gethostbyname_ex didn't find a better one or failed.
        except socket.gaierror: # Hostname not resolvable
            pass
        except Exception:
            pass # Other errors

        # Attempt 2: If previous attempt yielded 127.0.0.1, try UDP connection trick
        if ip == '127.0.0.1':
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(0.1)  # Short timeout
                s.connect(('8.8.8.8', 80))  # Google's public DNS
                potential_ip = s.getsockname()[0]
                s.close()
                if not potential_ip.startswith('127.'):
                    ip = potential_ip
            except Exception:
                # Attempt 3: Fallback UDP trick if public DNS fails (e.g., no internet)
                if ip == '127.0.0.1': # Check again, as previous attempt might have failed
                    try:
                        s_local = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s_local.settimeout(0.1)
                        s_local.connect(('10.255.255.255', 1)) # Non-routable private IP
                        potential_ip_local = s_local.getsockname()[0]
                        s_local.close()
                        if not potential_ip_local.startswith('127.'):
                            ip = potential_ip_local
                    except Exception:
                        pass # ip remains '127.0.0.1'

        self.lan_ip = ip
        self.after(0, self.update_db_info)


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

    def _get_db_api_script_path(self):
        """Determines the path to the db_log_api.py script or db_log_api.exe."""
        try:
            # Prefer .exe if present (for packaged apps)
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                # PyInstaller bundle
                exe_path = os.path.join(sys._MEIPASS, 'database', 'db_log_api.exe')
                py_path = os.path.join(sys._MEIPASS, 'database', 'db_log_api.py')
            else:
                # Running from source
                current_dir = os.path.dirname(os.path.abspath(__file__))
                exe_path = os.path.abspath(os.path.join(current_dir, '..', '..', 'database', 'db_log_api.exe'))
                py_path = os.path.abspath(os.path.join(current_dir, '..', '..', 'database', 'db_log_api.py'))
            if os.path.exists(exe_path):
                return exe_path
            elif os.path.exists(py_path):
                return py_path
            else:
                return None
        except Exception:
            return None # Path determination error

    def init_db(self):
        threading.Thread(target=self._init_db_worker, daemon=True).start()

    def _init_db_worker(self):
        db_api_script_path = self._get_db_api_script_path()
        is_exe = db_api_script_path and db_api_script_path.endswith('.exe')

        def show_messagebox(kind, title, msg):
            # Schedule messagebox on the main thread
            self.after(0, lambda: getattr(messagebox, kind)(title, msg))
        def update_info():
            self.after(0, self.update_db_info)

        if not db_api_script_path or not os.path.exists(db_api_script_path):
            show_messagebox("showerror", "Script Not Found",
                f"Database API script/exe (db_log_api.py or db_log_api.exe) could not be located.\n"
                f"Expected at: {db_api_script_path or 'path determination error'}\n"
                "API server cannot be launched. Will attempt local DB initialization only.")
        else:
            try:
                if is_exe:
                    subprocess.Popen([db_api_script_path], cwd=os.path.dirname(db_api_script_path))
                else:
                    python_executable = "pythonw.exe" if os.name == 'nt' else "python"
                    script_dir = os.path.dirname(db_api_script_path)
                    creation_flags = 0
                    if os.name == 'nt' and python_executable == "python.exe":
                        creation_flags = subprocess.CREATE_NO_WINDOW
                    subprocess.Popen([python_executable, db_api_script_path],
                                     cwd=script_dir,
                                     creationflags=creation_flags)
                show_messagebox("showinfo", "Server Launch",
                    "Attempting to start the Database API server.\n"
                    "Please wait about 5 seconds for it to initialize.")
                time.sleep(5)
            except FileNotFoundError:
                show_messagebox("showerror", "Execution Error",
                    f"Could not launch: {db_api_script_path}.\n"
                    "Please ensure the file is present and, if a Python script, that Python is installed and in your system's PATH.")
            except Exception as e:
                show_messagebox("showerror", "Launch Error", f"Failed to launch Database API server: {e}")
        # --- Attempt to connect to the API (which was hopefully just launched or already running) ---
        try:
            url = self.api_url.rstrip('/') + '/init_db'
            resp = requests.post(url, timeout=10)
            if resp.status_code == 200 and resp.json().get('success'):
                show_messagebox("showinfo", "Success", "Database initialized via API.")
                update_info()
                return
            else:
                error_message = resp.json().get('message', 'Unknown API error') if resp.headers.get('content-type') == 'application/json' else resp.text
                show_messagebox("showerror", "API Error",
                    f"Failed to initialize DB via API (Status: {resp.status_code}): {error_message}\n"
                    "This could be due to the server still starting, an issue on the server, or it was not launched successfully.")
        except requests.exceptions.RequestException as e:
            show_messagebox("showerror", "API Connection Error",
                f"Could not connect to API to initialize DB: {e}\n"
                "Ensure the Database API server was launched successfully, is not blocked by a firewall, and the API URL in config.json is correct.")
        except Exception as e:
            show_messagebox("showerror", "API Call Error",
                f"An unexpected error occurred during API call: {e}")
        # --- Fallback to local DB initialization if API method failed ---
        show_messagebox("showinfo", "Fallback", "Attempting local database initialization as API method failed or was skipped.")
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                event TEXT,
                details TEXT,
                user TEXT
                )''')
            conn.commit()
            conn.close()
            show_messagebox("showinfo", "Success", "Database initialized locally (fallback).")
            update_info()
        except Exception as e:
            show_messagebox("showerror", "Local DB Error", f"Failed to initialize DB locally: {e}")

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
