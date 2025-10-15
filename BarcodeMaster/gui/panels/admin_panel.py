import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial.tools.list_ports
import threading
import time
import queue
import os
import subprocess
import requests
import socket
import webbrowser
import psutil
import sys
import shutil
from datetime import datetime
from tkinter import filedialog
from config_utils import get_config, save_config
import config_manager
from com_splitter import ComSplitter
from path_utils import get_resource_path, get_writable_path
from database.db_log_api import run_api_server, stop_api_server
from urllib.parse import urlparse

PANEL_BG = "#f0f0f0"

class AdminPanel(tk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.app = app
        self.splitter_instance = None
        self.log_queue = queue.Queue()
        self.api_status_thread_stop = threading.Event()
        self.db_api_thread = None
        self._running = True  # Flag to track if panel is still running

        # Define db_path here to be accessible by all tab creation methods
        self.db_path = get_writable_path('database/central_logging.sqlite')
        self.db_log_path = get_writable_path('database/db_log_api.log')

        # Backup tab related variables
        self.backup_enabled_var = tk.BooleanVar()
        self.backup_directory_var = tk.StringVar()
        self.backup_interval_var = tk.StringVar()
        self.last_backup_status_var = tk.StringVar()
        self.backup_thread = None
        self.backup_thread_stop_event = threading.Event()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Database Tab
        self.db_tab_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.db_tab_frame, text='Database Beheer')
        self._create_db_tab(self.db_tab_frame)

        # COM Splitter Tab
        self.splitter_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.splitter_frame, text='COM Splitter')
        self._create_splitter_widgets()

        # Backup Tab
        self.backup_tab_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.backup_tab_frame, text='Backup')
        self._create_backup_tab(self.backup_tab_frame)
        
        # Excel Output Tab
        self.excel_output_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.excel_output_frame, text='Excel Output')
        self._create_excel_output_tab(self.excel_output_frame)
        
        # User Configuration Tab
        self.user_config_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.user_config_frame, text='Gebruiker Configuratie')
        self._create_user_config_tab(self.user_config_frame)

        self._initial_backup_scheduler_start() # Start scheduler if enabled in config

        self._create_lock_button()

        self.process_log_queue()

    def _create_db_tab(self, tab):
        self.api_url = get_config().get('api_url', 'http://localhost:5001')
        self.lan_ip = 'Detecteren...'
        threading.Thread(target=self._detect_lan_ip, daemon=True).start()

        # --- UI Widgets ---
        info_frame = ttk.LabelFrame(tab, text="Database Informatie")
        info_frame.pack(fill='x', padx=5, pady=5)
        info_frame.columnconfigure(1, weight=1)

        self.db_path_label = self._create_info_row(info_frame, "Database Pad:", self.db_path, 0)
        self.api_url_label = self._create_info_row(info_frame, "API URL:", self.api_url, 1)
        self.lan_ip_label = self._create_info_row(info_frame, "LAN IP Adres:", self.lan_ip, 2)
        self.api_status_label = self._create_info_row(info_frame, "API Status:", "Onbekend", 3)
        self.log_count_label = self._create_info_row(info_frame, "Aantal Logboeken:", "N/A", 4)

        control_frame = ttk.LabelFrame(tab, text="Beheer")
        control_frame.pack(fill='x', padx=5, pady=5)

        self.start_api_btn = ttk.Button(control_frame, text="Start API", command=self._start_db_api, state='disabled')
        self.start_api_btn.pack(side='left', padx=5, pady=5)

        self.stop_api_btn = ttk.Button(control_frame, text="Stop API", command=self._stop_db_api, state='disabled')
        self.stop_api_btn.pack(side='left', padx=5, pady=5)

        ttk.Label(control_frame, text="API wordt automatisch beheerd.").pack(side='left', padx=10)

        self.view_log_btn = ttk.Button(control_frame, text="Logboek Bekijken", command=self._view_db_log)
        self.view_log_btn.pack(side='left', padx=5, pady=5)

        self.view_log_browser_btn = ttk.Button(control_frame, text="Logboek in Browser", command=self._view_log_in_browser)
        self.view_log_browser_btn.pack(side='left', padx=5, pady=5)

        self.clear_log_btn = ttk.Button(control_frame, text="Logboek Wissen", command=self._clear_db_log)
        self.clear_log_btn.pack(side='left', padx=5, pady=5)

        # Startup Checkbox
        self.db_api_startup_var = tk.BooleanVar()
        start_db, _ = config_manager.get_startup_settings()
        self.db_api_startup_var.set(start_db)
        db_startup_check = ttk.Checkbutton(control_frame, text="Start bij opstarten", variable=self.db_api_startup_var, command=self._save_db_startup_setting)
        db_startup_check.pack(side='right', padx=10, pady=5)

        # Initial status update
        self._update_api_status_label(False, "N/A")
        # Start the background thread for continuous updates
        self.start_api_status_thread()

    def _create_info_row(self, parent, text, value, row):
        ttk.Label(parent, text=text).grid(row=row, column=0, sticky='w', padx=5, pady=2)
        label = ttk.Label(parent, text=value, anchor='w', wraplength=400)
        label.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
        return label

    def _detect_lan_ip(self):
        """
        Performs LAN IP detection in a background thread and schedules the UI update
        on the main thread to avoid threading issues with Tkinter.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # This is a blocking call, so it's good it's in a thread.
                s.connect(("8.8.8.8", 80))
                lan_ip = s.getsockname()[0]
        except Exception as e:
            lan_ip = f"Fout: {e}"

        def _update_ui():
            # This function will be executed on the main thread.
            if self.winfo_exists():
                self.lan_ip = lan_ip
                self.lan_ip_label.config(text=self.lan_ip)
        
        # Schedule the UI update to run on the main thread.
        self.after(0, _update_ui)

    def start_api_status_thread(self):
        threading.Thread(target=self._check_api_status_loop, daemon=True).start()

    def _update_api_status_label(self, is_active, log_count_text):
        """Updates the UI labels with pre-fetched data. Non-blocking."""
        if not self._running:
            return
            
        # Update API Status Label
        status_text = "Actief" if is_active else "Inactief"
        status_color = 'green' if is_active else 'red'
        
        if self.winfo_exists() and hasattr(self, 'api_status_label'):
            self.api_status_label.config(text=status_text, foreground=status_color)

        # Update Log Count Label
        if self.winfo_exists() and hasattr(self, 'log_count_label'):
            self.log_count_label.config(text=log_count_text)

    def _check_api_status_loop(self):
        """Background thread that continuously checks API status."""
        while not self.api_status_thread_stop.is_set() and self._running:
            try:
                # Check if API is active
                base_url = self.api_url.split('/log')[0]
                test_url = f"{base_url}/logs/count"
                response = requests.get(test_url, timeout=2)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        log_count = data.get('count', 0)
                        log_count_text = f"Logs in database: {log_count}"
                        is_active = True
                    else:
                        log_count_text = "Failed to get log count"
                        is_active = False
                else:
                    log_count_text = f"API returned status: {response.status_code}"
                    is_active = False
                    
            except requests.exceptions.RequestException as e:
                log_count_text = f"Connection error: {type(e).__name__}"
                is_active = False
            except Exception as e:
                log_count_text = f"Unexpected error: {str(e)}"
                is_active = False
            
            # Update the central status object
            if self.app.service_status:
                self.app.service_status.db_api_status = "Running" if is_active else "Inactive"

            # Use after_idle to ensure GUI update happens in main thread
            try:
                self.winfo_toplevel().after_idle(self._update_api_status_label, is_active, log_count_text)
            except Exception:
                # Widget might be destroyed
                break
            
            # Sleep for a bit before checking again
            time.sleep(3)

    def _start_db_api(self):
        try:
            # Get port from API URL
            port = 5001  # default
            try:
                parsed = urlparse(self.api_url)
                if parsed.port:
                    port = parsed.port
            except:
                pass
            
            # Start in thread
            self.db_api_thread = threading.Thread(
                target=run_api_server, 
                kwargs={'port': port},
                daemon=True
            )
            self.db_api_thread.start()
            messagebox.showinfo("API Beheer", "Database API is gestart.")
        except Exception as e:
            messagebox.showerror("API Fout", f"Kon de API niet starten:\n{e}")

    def _stop_db_api(self, silent=False):
        try:
            stop_api_server()
            if not silent:
                messagebox.showinfo("API Beheer", "Database API gestopt.")
        except Exception as e:
            if not silent:
                messagebox.showerror("Fout", f"Kon API niet stoppen: {e}")

    def _view_db_log(self):
        try:
            if sys.platform == "win32":
                os.startfile(self.db_log_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.db_log_path])
            else:
                subprocess.run(["xdg-open", self.db_log_path])
        except Exception as e:
            messagebox.showerror("Fout", f"Kon logboek niet openen:\n{e}")

    def _view_log_in_browser(self):
        try:
            # Construct the URL for the logs_html endpoint
            base_url = self.api_url.split('/log')[0] # Get the base URL
            log_url = f"{base_url}/logs_html"
            webbrowser.open(log_url)
        except Exception as e:
            messagebox.showerror("Fout", f"Kon de log in de browser niet openen:\n{e}")

    def _clear_db_log(self):
        if not messagebox.askyesno("Bevestigen", "Weet u zeker dat u ALLE logboekvermeldingen permanent wilt verwijderen? Deze actie kan niet ongedaan worden gemaakt."):
            return

        try:
            # Check if API is running first
            api_status_str = self.app.service_status.db_api_status.upper() if (self.app.service_status and self.app.service_status.db_api_status and self.app.service_status.db_api_status is not None) else "UNKNOWN"
            if "RUNNING" not in api_status_str and "ACTIEF" not in api_status_str and "STARTING" not in api_status_str:
                messagebox.showerror("Fout", "De Database API is niet actief. Kan logboek niet wissen.")
                return

            base_url = self.api_url.split('/log')[0]
            clear_url = f"{base_url}/clear_logs"
            response = requests.post(clear_url, timeout=5)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                messagebox.showinfo("Succes", "Alle logboekvermeldingen zijn succesvol verwijderd.")
                # Trigger an immediate update of the count
                self._update_api_status_label(True, "0") 
            else:
                messagebox.showerror("Fout", f"API Fout: {result.get('message', 'Onbekende fout')}")

        except requests.exceptions.RequestException as e:
            messagebox.showerror("API Fout", f"Kon geen verbinding maken met de API om het logboek te wissen:\n{e}")
        except Exception as e:
            messagebox.showerror("Fout", f"Een onverwachte fout is opgetreden:\n{e}")

    def _create_splitter_widgets(self):
        # --- Configuration Frame ---
        config_frame = ttk.LabelFrame(self.splitter_frame, text="COM Splitter Configuratie", padding=10)
        config_frame.pack(fill='x', padx=10, pady=10)
        config_frame.grid_columnconfigure(1, weight=1)

        # Physical Port
        ttk.Label(config_frame, text="Fysieke Scanner Poort:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.physical_port_var = tk.StringVar(value=get_config().get('splitter_physical_port', ''))
        self.physical_port_menu = ttk.Combobox(config_frame, textvariable=self.physical_port_var, state='readonly')
        self.physical_port_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        # Virtual Port 1
        ttk.Label(config_frame, text="Virtuele Poort 1 (Output):").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.virtual_port_1_var = tk.StringVar(value=get_config().get('splitter_virtual_port_1', ''))
        self.virtual_port_1_menu = ttk.Combobox(config_frame, textvariable=self.virtual_port_1_var, state='readonly')
        self.virtual_port_1_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

        # Virtual Port 2
        ttk.Label(config_frame, text="Virtuele Poort 2 (Output):").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.virtual_port_2_var = tk.StringVar(value=get_config().get('splitter_virtual_port_2', ''))
        self.virtual_port_2_menu = ttk.Combobox(config_frame, textvariable=self.virtual_port_2_var, state='readonly')
        self.virtual_port_2_menu.grid(row=2, column=1, padx=5, pady=5, sticky='ew')

        # Baud Rate
        ttk.Label(config_frame, text="Baudrate:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.baud_rate_var = tk.StringVar(value=get_config().get('splitter_baud_rate', '9600'))
        self.baud_rate_entry = ttk.Entry(config_frame, textvariable=self.baud_rate_var)
        self.baud_rate_entry.grid(row=3, column=1, padx=5, pady=5, sticky='ew')
        
        # Refresh Button
        self.refresh_splitter_ports_btn = ttk.Button(config_frame, text="Ververs Poortenlijst", command=self.refresh_splitter_ports)
        self.refresh_splitter_ports_btn.grid(row=0, column=2, rowspan=3, padx=10, pady=5, sticky='ns')

        # --- Control Frame ---
        control_frame = ttk.LabelFrame(self.splitter_frame, text="Bediening", padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=1)

        self.start_splitter_btn = ttk.Button(control_frame, text="Start Splitter", command=self._start_splitter)
        self.start_splitter_btn.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        
        self.stop_splitter_btn = ttk.Button(control_frame, text="Stop Splitter", command=self._stop_splitter, state='disabled')
        self.stop_splitter_btn.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        self.splitter_status_label = ttk.Label(control_frame, text="Status: Gestopt", foreground="red")
        self.splitter_status_label.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='w')

        # Startup Checkbox
        self.splitter_startup_var = tk.BooleanVar()
        _, start_splitter = config_manager.get_startup_settings()
        self.splitter_startup_var.set(start_splitter)
        splitter_startup_check = ttk.Checkbutton(control_frame, text="Start bij opstarten", variable=self.splitter_startup_var, command=self._save_splitter_startup_setting)
        splitter_startup_check.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='w')

        # --- Log Frame ---
        log_frame = ttk.LabelFrame(self.splitter_frame, text="Splitter Log", padding=10)
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', height=10, wrap=tk.WORD, bg="#2b2b2b", fg="white")
        self.log_text.pack(fill='both', expand=True)

        self.refresh_splitter_ports()

    def refresh_splitter_ports(self):
        try:
            ports = [port.device for port in serial.tools.list_ports.comports()]
            self.physical_port_menu['values'] = ports
            self.virtual_port_1_menu['values'] = ports
            self.virtual_port_2_menu['values'] = ports
            
            # Preserve existing selection if possible
            if self.physical_port_var.get() not in ports:
                self.physical_port_var.set(ports[0] if ports else '')
            if self.virtual_port_1_var.get() not in ports:
                self.virtual_port_1_var.set(ports[1] if len(ports) > 1 else '')
            if self.virtual_port_2_var.get() not in ports:
                self.virtual_port_2_var.set(ports[2] if len(ports) > 2 else '')

        except Exception as e:
            self.log_to_queue(f"Fout bij verversen poorten: {e}")


    def _start_splitter(self):
        physical_port = self.physical_port_var.get()
        vport1 = self.virtual_port_1_var.get()
        vport2 = self.virtual_port_2_var.get()
        baud_rate = self.baud_rate_var.get()

        if not all([physical_port, vport1, vport2, baud_rate]):
            messagebox.showerror("Fout", "Selecteer alstublieft alle COM-poorten en stel een baudrate in.")
            return
        
        if len({physical_port, vport1, vport2}) < 3:
            messagebox.showerror("Fout", "De geselecteerde poorten moeten uniek zijn.")
            return

        try:
            baud = int(baud_rate)
        except ValueError:
            messagebox.showerror("Fout", "De baudrate moet een getal zijn.")
            return

        # Save config before starting
        config_to_save = {
            'splitter_physical_port': physical_port,
            'splitter_virtual_port_1': vport1,
            'splitter_virtual_port_2': vport2,
            'splitter_baud_rate': baud_rate
        }
        save_config(config_to_save)
        
        splitter_config = {
            'physical_port': physical_port,
            'virtual_port_1': vport1,
            'virtual_port_2': vport2,
            'baud_rate': baud
        }

        self.splitter_instance = ComSplitter(splitter_config, self.log_to_queue)
        self.splitter_instance.start()

        self._set_splitter_controls_state('disabled')
        self.start_splitter_btn.config(state='disabled')
        self.stop_splitter_btn.config(state='normal')
        self.splitter_status_label.config(text="Status: Actief", foreground="green")
        self.log_to_queue("Splitter gestart.")

    def _stop_splitter(self):
        if self.splitter_instance:
            self.splitter_instance.stop()
            self.splitter_instance = None
        
        self._set_splitter_controls_state('readonly') # 'normal' for entry
        self.baud_rate_entry.config(state='normal')
        self.start_splitter_btn.config(state='normal')
        self.stop_splitter_btn.config(state='disabled')
        self.splitter_status_label.config(text="Status: Gestopt", foreground="red")
        self.log_to_queue("Splitter gestopt.")

    def _set_splitter_controls_state(self, state):
        # State should be 'disabled' when running, 'readonly'/'normal' when stopped
        self.physical_port_menu.config(state=state)
        self.virtual_port_1_menu.config(state=state)
        self.virtual_port_2_menu.config(state=state)
        self.baud_rate_entry.config(state='disabled' if state == 'disabled' else 'normal')
        self.refresh_splitter_ports_btn.config(state='disabled' if state == 'disabled' else 'normal')

    def log_to_queue(self, message):
        """Thread-safe method to add a log message to the queue."""
        self.log_queue.put(message)

    # --- Backup Tab Methods ---
    def _create_backup_tab(self, tab):
        config = get_config()
        self.backup_enabled_var.set(config.get('backup_enabled', False))
        self.backup_directory_var.set(config.get('backup_directory', ''))
        self.backup_interval_var.set(str(config.get('backup_interval_minutes', '1440')))
        self.last_backup_status_var.set(config.get('last_backup_status', 'Nog geen backups uitgevoerd.'))

        # --- Backup Settings Frame ---
        settings_frame = ttk.LabelFrame(tab, text="Backup Instellingen")
        settings_frame.pack(fill='x', padx=5, pady=5)
        settings_frame.columnconfigure(1, weight=1)

        # Enable Checkbox
        enable_check = ttk.Checkbutton(settings_frame, text="Automatische Backups Inschakelen", variable=self.backup_enabled_var, command=self._on_backup_enable_change)
        enable_check.grid(row=0, column=0, columnspan=3, sticky='w', padx=5, pady=5)

        # Backup Directory
        ttk.Label(settings_frame, text="Backup Map:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.backup_dir_entry = ttk.Entry(settings_frame, textvariable=self.backup_directory_var, state='readonly')
        self.backup_dir_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        self.browse_backup_dir_btn = ttk.Button(settings_frame, text="Bladeren...", command=self._browse_backup_directory)
        self.browse_backup_dir_btn.grid(row=1, column=2, sticky='e', padx=5, pady=2)

        # Backup Interval
        ttk.Label(settings_frame, text="Backup Interval (minuten):").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        self.backup_interval_entry = ttk.Entry(settings_frame, textvariable=self.backup_interval_var)
        self.backup_interval_entry.grid(row=2, column=1, sticky='ew', padx=5, pady=2)
        self.backup_interval_entry.bind("<FocusOut>", self._validate_and_save_backup_config)
        self.backup_interval_entry.bind("<Return>", self._validate_and_save_backup_config)

        # --- Backup Management & Status Frame ---
        status_frame = ttk.LabelFrame(tab, text="Backup Beheer & Status")
        status_frame.pack(fill='x', padx=5, pady=(10, 5)) # Changed pady_top to pady=(top, bottom)
        status_frame.columnconfigure(1, weight=1)

        manual_backup_btn = ttk.Button(status_frame, text="Nu Backuppen", command=self._trigger_manual_backup)
        manual_backup_btn.grid(row=0, column=0, padx=5, pady=5, sticky='w')

        ttk.Label(status_frame, text="Laatste Backup Status:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        last_status_label = ttk.Label(status_frame, textvariable=self.last_backup_status_var, wraplength=400)
        last_status_label.grid(row=1, column=1, sticky='ew', padx=5, pady=2)

        self._update_backup_ui_state() # Set initial UI state

    def _update_backup_ui_state(self):
        is_enabled = self.backup_enabled_var.get()
        state = 'normal' if is_enabled else 'disabled'
        readonly_state = 'readonly' if is_enabled else 'disabled' # Entry should be readonly when enabled, not normal

        if hasattr(self, 'backup_dir_entry'): # Ensure widgets exist
            self.backup_dir_entry.config(state=readonly_state if is_enabled else 'disabled') # Keep readonly for display, disable if not enabled
            self.browse_backup_dir_btn.config(state=state)
            self.backup_interval_entry.config(state=state)

    def _on_backup_enable_change(self):
        self._update_backup_ui_state()
        self._validate_and_save_backup_config() # Save current state
        self._restart_backup_scheduler()

    def _browse_backup_directory(self):
        directory = filedialog.askdirectory(title="Selecteer Backup Map")
        if directory:
            self.backup_directory_var.set(directory)
            self._validate_and_save_backup_config()

    def _validate_and_save_backup_config(self, event=None):
        current_config = get_config()
        try:
            interval = int(self.backup_interval_var.get())
            if interval <= 0:
                raise ValueError("Interval must be positive")
        except ValueError:
            messagebox.showerror("Fout", "Ongeldig backup interval. Moet een positief getal zijn.")
            # Revert to previously saved value or default
            self.backup_interval_var.set(str(current_config.get('backup_interval_minutes', '1440')))
            interval = int(self.backup_interval_var.get())

        backup_config = {
            'backup_enabled': self.backup_enabled_var.get(),
            'backup_directory': self.backup_directory_var.get(),
            'backup_interval_minutes': interval,
            'last_backup_status': self.last_backup_status_var.get() # Persist last known status
        }
        save_config(backup_config)
        if self.backup_enabled_var.get() and not self.backup_directory_var.get():
            messagebox.showwarning("Waarschuwing", "Automatische backups zijn ingeschakeld, maar er is geen backup map geselecteerd.")
        self._restart_backup_scheduler()

    def _trigger_manual_backup(self):
        if not self.backup_enabled_var.get():
             messagebox.showinfo("Info", "Backup functie is niet ingeschakeld. Schakel eerst in en selecteer een map.")
             return
        if not self.backup_directory_var.get():
            messagebox.showerror("Fout", "Geen backup map geselecteerd voor handmatige backup.")
            return
        self._perform_backup(manual=True)

    def _initial_backup_scheduler_start(self):
        if self.backup_enabled_var.get() and self.backup_directory_var.get():
            self._start_backup_scheduler()

    def _start_backup_scheduler(self):
        if self.backup_thread is None or not self.backup_thread.is_alive():
            if not self.backup_directory_var.get():
                self.log_to_queue("Backup scheduler niet gestart: geen backup map geconfigureerd.")
                return
            try:
                interval = int(self.backup_interval_var.get())
                if interval <= 0:
                    self.log_to_queue("Backup scheduler niet gestart: ongeldig interval.")
                    return
            except ValueError:
                self.log_to_queue("Backup scheduler niet gestart: ongeldig interval formaat.")
                return

            self.backup_thread_stop_event.clear()
            self.backup_thread = threading.Thread(target=self._backup_scheduler_loop, daemon=True)
            self.backup_thread.start()
            self.log_to_queue("Backup scheduler gestart.")

    def _stop_backup_scheduler(self):
        if self.backup_thread and self.backup_thread.is_alive():
            self.backup_thread_stop_event.set()
            self.backup_thread.join(timeout=5) # Wait for the thread to finish
            self.backup_thread = None
            self.log_to_queue("Backup scheduler gestopt.")

    def _restart_backup_scheduler(self):
        self._stop_backup_scheduler()
        if self.backup_enabled_var.get() and self.backup_directory_var.get():
            self._start_backup_scheduler()

    def _backup_scheduler_loop(self):
        self.log_to_queue("Backup scheduler loop gestart.")
        while not self.backup_thread_stop_event.is_set():
            try:
                interval_minutes = int(self.backup_interval_var.get())
                if interval_minutes <= 0:
                    self.log_to_queue(f"Ongeldig backup interval ({interval_minutes} min), scheduler pauzeert voor 60 sec.")
                    interval_seconds = 60 
                else:
                    interval_seconds = interval_minutes * 60
            except ValueError:
                self.log_to_queue("Ongeldig interval formaat, scheduler pauzeert voor 60 sec.")
                interval_seconds = 60
            
            # Wait for the interval, or until the stop event is set
            # The wait method returns True if the event was set before the timeout, False otherwise.
            interrupted = self.backup_thread_stop_event.wait(interval_seconds)

            if not interrupted and self.backup_enabled_var.get() and self.backup_directory_var.get():
                # Schedule _perform_backup to run in the main Tkinter thread
                try:
                    self.winfo_toplevel().after_idle(self._perform_backup, False) # manual=False
                except:
                    # Widget might be destroyed
                    break
            elif interrupted:
                self.log_to_queue("Backup scheduler loop onderbroken.")
                break # Exit loop if stop event is set
        self.log_to_queue("Backup scheduler loop beëindigd.")

    def _perform_backup(self, manual=False):
        backup_dir = self.backup_directory_var.get()
        # self.db_path is already defined in __init__

        if not backup_dir:
            status_msg = f"Fout: Backup map niet ingesteld. ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
            self.last_backup_status_var.set(status_msg)
            if manual:
                messagebox.showerror("Backup Fout", "Backup map is niet ingesteld.")
            self._validate_and_save_backup_config() # Save status
            return

        if not os.path.isdir(backup_dir):
            status_msg = f"Fout: Backup map '{backup_dir}' niet gevonden of is geen map. ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
            self.last_backup_status_var.set(status_msg)
            if manual:
                messagebox.showerror("Backup Fout", f"Backup map '{backup_dir}' niet gevonden of is geen map.")
            self._validate_and_save_backup_config() # Save status
            return

        if not os.path.isfile(self.db_path):
            status_msg = f"Fout: Database bestand '{self.db_path}' niet gevonden. ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
            self.last_backup_status_var.set(status_msg)
            if manual:
                messagebox.showerror("Backup Fout", f"Database bestand '{self.db_path}' niet gevonden.")
            self._validate_and_save_backup_config() # Save status
            return

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_filename = f'backup_{timestamp}.sqlite'
        backup_target_path = os.path.join(backup_dir, backup_filename)

        try:
            shutil.copy2(self.db_path, backup_target_path)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_msg = f"Succesvol gebackupt naar {backup_target_path} op {timestamp}"
            self.last_backup_status_var.set(status_msg)
            self.log_to_queue(f"Database backup succesvol: {backup_target_path}")
            if manual:
                messagebox.showinfo("Backup Succesvol", f"Database succesvol gebackupt naar:\n{backup_target_path}")
        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_msg = f"Backup Mislukt: {str(e)} ({timestamp})"
            self.last_backup_status_var.set(status_msg)
            self.log_to_queue(f"Database backup mislukt: {str(e)}")
            if manual:
                messagebox.showerror("Backup Mislukt", f"Fout tijdens backuppen:\n{str(e)}")
        finally:
            self._validate_and_save_backup_config() # Save the latest status

    # --- End of Backup Tab Methods ---
    
    def _create_excel_output_tab(self, tab):
        """Create Excel output directories configuration tab - loads from database"""
        # Load settings from database via API
        settings = self._load_settings_from_api()

        # --- Excel Output Settings Frame ---
        settings_frame = ttk.LabelFrame(tab, text="Excel Output Directory Configuratie")
        settings_frame.pack(fill='x', padx=5, pady=5)
        settings_frame.columnconfigure(1, weight=1)

        # Info label
        info_label = ttk.Label(
            settings_frame,
            text="Configureer de output directories voor alle gebruikers die Excel bestanden genereren.\nDeze directories worden gebruikt wanneer Excel bestanden worden gegenereerd uit de import processing.\n\n⚠️ Deze instellingen worden opgeslagen in de database en worden automatisch gebackupt.",
            wraplength=500
        )
        info_label.grid(row=0, column=0, columnspan=3, padx=5, pady=(5, 15), sticky='w')

        # Define all users that need Excel output directories
        # Note: NESTING only reads Excel files, doesn't generate output
        excel_users = ['ACCURA', 'BOERE', 'MASSIEF', 'HANDWERK']
        self.excel_output_vars = {}
        self.excel_entries = {}
        self.excel_browse_btns = {}

        # Create entry for each user
        for idx, user in enumerate(excel_users, start=1):
            ttk.Label(settings_frame, text=f"{user} Output Directory:").grid(row=idx, column=0, padx=5, pady=5, sticky='w')

            # Get path from database settings or use default
            default_dir = f'C:/{user}' if os.name == 'nt' else f'/tmp/{user}'
            key = f'{user.lower()}_output_dir'
            self.excel_output_vars[user] = tk.StringVar(value=settings.get(key, default_dir))
            self.excel_entries[user] = ttk.Entry(settings_frame, textvariable=self.excel_output_vars[user], state='readonly')
            self.excel_entries[user].grid(row=idx, column=1, padx=5, pady=5, sticky='ew')

            self.excel_browse_btns[user] = ttk.Button(
                settings_frame,
                text="Browse",
                command=lambda u=user: self._browse_output_dir(u, self.excel_output_vars[u])
            )
            self.excel_browse_btns[user].grid(row=idx, column=2, padx=5, pady=5)

        # Status Frame
        status_frame = ttk.LabelFrame(tab, text="Directory Status")
        status_frame.pack(fill='x', padx=5, pady=(10, 5))
        status_frame.columnconfigure(1, weight=1)

        # Status labels for each user
        self.excel_status_labels = {}
        for idx, user in enumerate(excel_users):
            self.excel_status_labels[user] = ttk.Label(status_frame, text="")
            self.excel_status_labels[user].grid(row=idx, column=0, columnspan=2, padx=5, pady=2, sticky='w')

        # Update status on creation
        self._update_excel_output_status()
    
    def _browse_output_dir(self, user_type, path_var):
        """Browse for output directory for Excel files - saves to database"""
        directory = filedialog.askdirectory(title=f"Select Output Directory for {user_type}")
        if directory:
            path_var.set(directory)
            # Save to database via API
            config_key = f'{user_type.lower()}_output_dir'
            if self._save_settings_to_api({config_key: directory}):
                self.log_to_queue(f"Output directory voor {user_type} opgeslagen in database: {directory}")
            else:
                # Fallback to config file if API fails
                save_config({config_key: directory})
                self.log_to_queue(f"Output directory voor {user_type} opgeslagen in config (API niet beschikbaar): {directory}")
            # Update status
            self._update_excel_output_status()

    def _load_settings_from_api(self):
        """Load settings from database via API"""
        try:
            base_url = self.api_url.split('/log')[0]
            response = requests.get(f"{base_url}/api/settings", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('settings', {})
        except Exception as e:
            self.log_to_queue(f"Kon instellingen niet laden van database: {e}")

        # Fallback to config file
        return get_config()

    def _save_settings_to_api(self, settings_dict):
        """Save settings to database via API"""
        try:
            base_url = self.api_url.split('/log')[0]
            response = requests.post(f"{base_url}/api/settings", json=settings_dict, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('success', False)
        except Exception as e:
            self.log_to_queue(f"Kon instellingen niet opslaan in database: {e}")
        return False
    
    def _update_excel_output_status(self):
        """Update the status labels for Excel output directories"""
        # Note: NESTING only reads Excel files, doesn't generate output
        excel_users = ['ACCURA', 'BOERE', 'MASSIEF', 'HANDWERK']

        for user in excel_users:
            if user in self.excel_output_vars and user in self.excel_status_labels:
                directory = self.excel_output_vars[user].get()
                if os.path.exists(directory) and os.path.isdir(directory):
                    self.excel_status_labels[user].config(
                        text=f"✓ {user} directory bestaat: {directory}",
                        foreground="green"
                    )
                else:
                    self.excel_status_labels[user].config(
                        text=f"✗ {user} directory bestaat niet: {directory}",
                        foreground="red"
                    )

    def process_log_queue(self):
        """Periodically called method to process messages from the log queue."""
        try:
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                self.log_text.config(state='normal')
                self.log_text.insert(tk.END, message + '\n')
                self.log_text.config(state='disabled')
                self.log_text.see(tk.END) # Auto-scroll
        finally:
            self.after(100, self.process_log_queue)
            
    def _create_lock_button(self):
        self.lock_button_frame = tk.Frame(self, bg=PANEL_BG)
        self.lock_button = ttk.Button(
            self.lock_button_frame,
            text="Admin Panel Vergrendelen",
            command=self.app.lock_admin_panel
        )
        self.lock_button.pack(pady=10)

    def set_lock_button_visibility(self, visible):
        """Shows or hides the admin lock button."""
        if visible and self.winfo_exists():
            self.lock_button_frame.pack(side='bottom', fill='x')
        elif self.winfo_exists():
            self.lock_button_frame.pack_forget()
    
    # --- User Configuration Tab Methods ---
    def _create_user_config_tab(self, tab):
        """Create user configuration tab for managing user paths and processing types - loads from database"""
        # Load settings from database via API
        config = self._load_settings_from_api()
        
        # Main container with scrollbar
        canvas = tk.Canvas(tab, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # --- User Settings Frame ---
        settings_frame = ttk.LabelFrame(scrollable_frame, text="Gebruiker Path Configuratie")
        settings_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Info label
        info_label = ttk.Label(
            settings_frame,
            text="Configureer gebruikers en hun Excel import paden.\nElke gebruiker kan een eigen pad hebben waar Excel bestanden automatisch worden geïmporteerd.\n\n⚠️ Deze instellingen worden opgeslagen in de database en worden automatisch gebackupt.",
            wraplength=600
        )
        info_label.pack(padx=5, pady=(5, 15))
        
        # User list frame
        self.user_list_frame = tk.Frame(settings_frame, bg="#f0f0f0")
        self.user_list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Initialize variables
        self.user_specific_paths_vars = {}
        self.user_logic_active_vars = {}
        self.scanner_panel_open_event_user_paths = config.get('scanner_panel_open_event_user_paths', {})
        self.scanner_panel_open_event_user_logic_active = config.get('scanner_panel_open_event_user_logic_active', {})
        self.scanner_user_to_processing_type_map = config.get('scanner_user_to_processing_type_map', {})
        self.available_processing_types = [
            "GEEN_PROCESSING", 
            "MDB_PROCESSING", 
            "HOPS_PROCESSING", 
            "NESTING_PROCESSING",
            "MASSIEF_PROCESSING",
            "HANDWERK_PROCESSING",
            "ACCURA_PROCESSING", 
            "BOERE_PROCESSING"
        ]
        
        # Build user list
        self._build_user_list_ui()
        
        # Add new user frame
        add_frame = ttk.LabelFrame(scrollable_frame, text="Nieuwe Gebruiker Toevoegen")
        add_frame.pack(fill='x', padx=5, pady=(10, 5))
        
        add_container = tk.Frame(add_frame, bg="#f0f0f0")
        add_container.pack(padx=10, pady=10)
        
        ttk.Label(add_container, text="Gebruikersnaam:").pack(side='left', padx=(0, 5))
        self.new_username_entry = ttk.Entry(add_container, width=20)
        self.new_username_entry.pack(side='left', padx=(0, 10))
        
        ttk.Label(add_container, text="Type:").pack(side='left', padx=(0, 5))
        self.new_user_processing_type_var = tk.StringVar()
        self.new_user_processing_type_combo = ttk.Combobox(
            add_container, 
            textvariable=self.new_user_processing_type_var, 
            values=self.available_processing_types, 
            width=20, 
            state='readonly'
        )
        if self.available_processing_types:
            self.new_user_processing_type_combo.current(0)
        self.new_user_processing_type_combo.pack(side='left', padx=(0, 10))
        
        add_btn = ttk.Button(add_container, text="Toevoegen", command=self._add_user_config)
        add_btn.pack(side='left')
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _build_user_list_ui(self):
        """Build the user list UI"""
        # Clear existing widgets
        for widget in self.user_list_frame.winfo_children():
            widget.destroy()
        
        self.user_specific_paths_vars.clear()
        self.user_logic_active_vars.clear()
        
        config = get_config()
        open_users = config.get('scanner_panel_open_event_users', [])
        
        if not open_users:
            tk.Label(self.user_list_frame, text="Geen gebruikers geconfigureerd.", bg="#f0f0f0", fg="gray").pack(pady=5)
            return
        
        # Headers
        header_frame = tk.Frame(self.user_list_frame, bg="#e0e0e0")
        header_frame.pack(fill='x', pady=(0, 5))
        tk.Label(header_frame, text="Actief", width=8, bg="#e0e0e0", font=('Arial', 9, 'bold')).pack(side='left')
        tk.Label(header_frame, text="Gebruiker", width=15, bg="#e0e0e0", font=('Arial', 9, 'bold')).pack(side='left')
        tk.Label(header_frame, text="Type", width=20, bg="#e0e0e0", font=('Arial', 9, 'bold')).pack(side='left')
        tk.Label(header_frame, text="Volgorde", width=10, bg="#e0e0e0", font=('Arial', 9, 'bold')).pack(side='left')
        tk.Label(header_frame, text="Import Pad", width=40, bg="#e0e0e0", font=('Arial', 9, 'bold')).pack(side='left', expand=True, fill='x')
        tk.Label(header_frame, text="Acties", width=20, bg="#e0e0e0", font=('Arial', 9, 'bold')).pack(side='left')
        
        # User rows
        for idx, username in enumerate(open_users):
            user_frame = tk.Frame(self.user_list_frame, bg="white" if idx % 2 == 0 else "#f8f8f8")
            user_frame.pack(fill='x', pady=1)
            
            # Active checkbox
            logic_active_var = tk.BooleanVar(value=self.scanner_panel_open_event_user_logic_active.get(username, True))
            self.user_logic_active_vars[username] = logic_active_var
            
            logic_checkbox = tk.Checkbutton(
                user_frame,
                variable=logic_active_var,
                bg="white" if idx % 2 == 0 else "#f8f8f8",
                command=lambda u=username, v=logic_active_var: self._save_user_logic_active(u, v.get())
            )
            logic_checkbox.pack(side='left', padx=10)
            
            # Username
            tk.Label(user_frame, text=username, width=15, anchor='w', bg="white" if idx % 2 == 0 else "#f8f8f8").pack(side='left')
            
            # Processing type
            processing_type = self.scanner_user_to_processing_type_map.get(username, "N/A")
            tk.Label(user_frame, text=processing_type, width=20, anchor='w', bg="white" if idx % 2 == 0 else "#f8f8f8").pack(side='left')
            
            # Order arrows
            arrow_frame = tk.Frame(user_frame, bg="white" if idx % 2 == 0 else "#f8f8f8")
            arrow_frame.pack(side='left', padx=10)
            
            up_btn = tk.Button(arrow_frame, text="↑", command=lambda u=username: self._move_user_up(u), 
                              width=2, state='normal' if idx > 0 else 'disabled')
            up_btn.pack(side='left')
            down_btn = tk.Button(arrow_frame, text="↓", command=lambda u=username: self._move_user_down(u), 
                                width=2, state='normal' if idx < len(open_users)-1 else 'disabled')
            down_btn.pack(side='left')
            
            # Path entry
            path_var = tk.StringVar(value=self.scanner_panel_open_event_user_paths.get(username, "Niet ingesteld"))
            self.user_specific_paths_vars[username] = path_var
            
            path_entry = ttk.Entry(user_frame, textvariable=path_var, state='readonly', width=40)
            path_entry.pack(side='left', expand=True, fill='x', padx=5)
            
            # Browse button
            browse_btn = ttk.Button(user_frame, text="Bladeren", 
                                   command=lambda u=username, pv=path_var: self._browse_user_path(u, pv),
                                   state='normal' if logic_active_var.get() else 'disabled')
            browse_btn.pack(side='left', padx=2)
            
            # Remove button
            remove_btn = ttk.Button(user_frame, text="Verwijderen", 
                                   command=lambda u=username: self._remove_user_config(u))
            remove_btn.pack(side='left', padx=5)
    
    def _browse_user_path(self, username, path_var):
        """Browse for user import path - saves to database"""
        directory = filedialog.askdirectory(title=f"Selecteer Import Directory voor {username}")
        if directory:
            path_var.set(directory)
            config_data = self._load_settings_from_api()
            user_paths = config_data.get('scanner_panel_open_event_user_paths', {})
            user_paths[username] = directory

            if self._save_settings_to_api({'scanner_panel_open_event_user_paths': user_paths}):
                self.scanner_panel_open_event_user_paths = user_paths
                self.log_to_queue(f"Import pad voor {username} opgeslagen in database: {directory}")
            else:
                # Fallback to config file
                save_config({'scanner_panel_open_event_user_paths': user_paths})
                self.scanner_panel_open_event_user_paths = user_paths
                self.log_to_queue(f"Import pad voor {username} opgeslagen in config (API niet beschikbaar): {directory}")
    
    def _save_user_logic_active(self, username, is_active):
        """Save user active state - saves to database"""
        config_data = self._load_settings_from_api()
        user_logic_states = config_data.get('scanner_panel_open_event_user_logic_active', {})
        user_logic_states[username] = is_active

        if self._save_settings_to_api({'scanner_panel_open_event_user_logic_active': user_logic_states}):
            self.scanner_panel_open_event_user_logic_active = user_logic_states
            status = "geactiveerd" if is_active else "gedeactiveerd"
            self.log_to_queue(f"Automatische import {status} voor {username} (opgeslagen in database)")
        else:
            # Fallback to config file
            save_config({'scanner_panel_open_event_user_logic_active': user_logic_states})
            self.scanner_panel_open_event_user_logic_active = user_logic_states
            status = "geactiveerd" if is_active else "gedeactiveerd"
            self.log_to_queue(f"Automatische import {status} voor {username} (opgeslagen in config)")
    
    def _move_user_up(self, username):
        """Move user up in the order - saves to database"""
        config = self._load_settings_from_api()
        users = config.get('scanner_panel_open_event_users', [])

        if username not in users:
            return

        current_index = users.index(username)
        if current_index > 0:
            users[current_index], users[current_index - 1] = users[current_index - 1], users[current_index]
            if self._save_settings_to_api({'scanner_panel_open_event_users': users}):
                self.log_to_queue(f"Gebruiker '{username}' omhoog verplaatst (opgeslagen in database)")
            else:
                save_config({'scanner_panel_open_event_users': users})
                self.log_to_queue(f"Gebruiker '{username}' omhoog verplaatst (opgeslagen in config)")
            self._build_user_list_ui()
    
    def _move_user_down(self, username):
        """Move user down in the order - saves to database"""
        config = self._load_settings_from_api()
        users = config.get('scanner_panel_open_event_users', [])

        if username not in users:
            return

        current_index = users.index(username)
        if current_index < len(users) - 1:
            users[current_index], users[current_index + 1] = users[current_index + 1], users[current_index]
            if self._save_settings_to_api({'scanner_panel_open_event_users': users}):
                self.log_to_queue(f"Gebruiker '{username}' omlaag verplaatst (opgeslagen in database)")
            else:
                save_config({'scanner_panel_open_event_users': users})
                self.log_to_queue(f"Gebruiker '{username}' omlaag verplaatst (opgeslagen in config)")
            self._build_user_list_ui()
    
    def _add_user_config(self):
        """Add new user configuration"""
        username = self.new_username_entry.get().strip()
        processing_type = self.new_user_processing_type_var.get()
        
        if not username:
            messagebox.showwarning("Invoer Fout", "Voer een gebruikersnaam in.")
            return
        
        config = self._load_settings_from_api()
        users = config.get('scanner_panel_open_event_users', [])

        if username in users:
            messagebox.showwarning("Dubbele Gebruiker", f"Gebruiker '{username}' bestaat al.")
            return

        # Add user to list
        users.append(username)

        # Save processing type
        type_map = config.get('scanner_user_to_processing_type_map', {})
        type_map[username] = processing_type
        self.scanner_user_to_processing_type_map = type_map

        # Set active by default
        logic_states = config.get('scanner_panel_open_event_user_logic_active', {})
        logic_states[username] = True
        self.scanner_panel_open_event_user_logic_active = logic_states

        # Save all settings to database
        settings_to_save = {
            'scanner_panel_open_event_users': users,
            'scanner_user_to_processing_type_map': type_map,
            'scanner_panel_open_event_user_logic_active': logic_states
        }

        if self._save_settings_to_api(settings_to_save):
            self.log_to_queue(f"Gebruiker '{username}' toegevoegd met type '{processing_type}' (opgeslagen in database)")
        else:
            # Fallback to config file
            save_config(settings_to_save)
            self.log_to_queue(f"Gebruiker '{username}' toegevoegd met type '{processing_type}' (opgeslagen in config)")
        
        # Clear entry fields
        self.new_username_entry.delete(0, tk.END)
        if self.available_processing_types:
            self.new_user_processing_type_combo.current(0)
        
        # Rebuild UI
        self._build_user_list_ui()
    
    def _remove_user_config(self, username):
        """Remove user configuration"""
        if not messagebox.askyesno("Bevestig Verwijdering", 
                                   f"Weet u zeker dat u gebruiker '{username}' en alle configuratie wilt verwijderen?"):
            return
        
        config = self._load_settings_from_api()

        # Remove from users list
        users = config.get('scanner_panel_open_event_users', [])
        if username in users:
            users.remove(username)

        # Remove from paths
        paths = config.get('scanner_panel_open_event_user_paths', {})
        if username in paths:
            del paths[username]
            self.scanner_panel_open_event_user_paths = paths

        # Remove from logic states
        logic_states = config.get('scanner_panel_open_event_user_logic_active', {})
        if username in logic_states:
            del logic_states[username]
            self.scanner_panel_open_event_user_logic_active = logic_states

        # Remove from processing type map
        type_map = config.get('scanner_user_to_processing_type_map', {})
        if username in type_map:
            del type_map[username]
            self.scanner_user_to_processing_type_map = type_map

        # Save all settings to database
        settings_to_save = {
            'scanner_panel_open_event_users': users,
            'scanner_panel_open_event_user_paths': paths,
            'scanner_panel_open_event_user_logic_active': logic_states,
            'scanner_user_to_processing_type_map': type_map
        }

        if self._save_settings_to_api(settings_to_save):
            self.log_to_queue(f"Gebruiker '{username}' verwijderd (opgeslagen in database)")
        else:
            # Fallback to config file
            save_config(settings_to_save)
            self.log_to_queue(f"Gebruiker '{username}' verwijderd (opgeslagen in config)")
        self._build_user_list_ui()
    # --- End of User Configuration Tab Methods ---

    def shutdown(self):
        """Gracefully shut down services managed by AdminPanel."""
        self._running = False
        self.log_to_queue("AdminPanel shutdown gestart...")
        # Stop API status checking loop
        self.api_status_thread_stop.set()
        # Stop COM Splitter if running
        self._stop_splitter()
        # Stop Backup Scheduler
        self._stop_backup_scheduler()
        # Stop DB API
        self._stop_db_api(silent=True)
        self.log_to_queue("AdminPanel shutdown voltooid.")

    def _save_db_startup_setting(self):
        value = self.db_api_startup_var.get()
        config_manager.save_startup_setting('start_db_api_on_boot', value)
        status = "ingeschakeld" if value else "uitgeschakeld"
        self.log_to_queue(f"Automatisch opstarten van DB API {status}.")

    def _save_splitter_startup_setting(self):
        value = self.splitter_startup_var.get()
        config_manager.save_startup_setting('start_com_splitter_on_boot', value)
        status = "ingeschakeld" if value else "uitgeschakeld"
        self.log_to_queue(f"Automatisch opstarten van COM Splitter {status}.")