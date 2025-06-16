import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial.tools.list_ports
import threading
import queue
import os
import subprocess
import requests
import socket
import webbrowser
import psutil
import sys
from BarcodeMaster.config_utils import get_config, save_config
from BarcodeMaster import config_manager
from BarcodeMaster.com_splitter import ComSplitter

PANEL_BG = "#f0f0f0"

class AdminPanel(tk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.app = app
        self.splitter_instance = None
        self.log_queue = queue.Queue()
        self.api_status_thread_stop = threading.Event()

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

        self._create_lock_button()

        self.process_log_queue()

    def _create_db_tab(self, tab):
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'central_logging.sqlite'))
        self.db_log_path = os.path.abspath(os.path.join(os.path.dirname(self.db_path), 'db_log_api.log'))
        self.api_script_path = os.path.abspath(os.path.join(os.path.dirname(self.db_path), 'db_log_api.py'))
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

        self.start_api_btn = ttk.Button(control_frame, text="Start API", command=self._start_db_api)
        self.start_api_btn.pack(side='left', padx=5, pady=5)

        self.stop_api_btn = ttk.Button(control_frame, text="Stop API", command=self._stop_db_api)
        self.stop_api_btn.pack(side='left', padx=5, pady=5)

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
        self._update_api_status_label()
        # Start the background thread for continuous updates
        self.start_api_status_thread()

    def _create_info_row(self, parent, text, value, row):
        ttk.Label(parent, text=text).grid(row=row, column=0, sticky='w', padx=5, pady=2)
        label = ttk.Label(parent, text=value, anchor='w', wraplength=400)
        label.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
        return label

    def _detect_lan_ip(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                self.lan_ip = s.getsockname()[0]
        except Exception as e:
            self.lan_ip = f"Fout: {e}"
        if self.winfo_exists():
            self.after(0, self.update_db_info)

    def update_db_info(self):
        if self.winfo_exists():
            self.lan_ip_label.config(text=self.lan_ip)

    def start_api_status_thread(self):
        threading.Thread(target=self._check_api_status_loop, daemon=True).start()

    def _update_api_status_label(self):
        # Diagnostic print
        
        # Update API Status Label
        api_status_str = self.app.service_status.services.get('db_api', 'INACTIEF').upper()
        is_active = "RUNNING" in api_status_str
        status_text = "Actief" if is_active else "Inactief"
        status_color = 'green' if is_active else 'red'
        
        if self.winfo_exists() and hasattr(self, 'api_status_label'):
            self.api_status_label.config(text=status_text, foreground=status_color)

        # Update Log Count Label
        log_count_text = "N/A"
        if is_active:
            try:
                base_url = self.api_url.split('/log')[0]
                count_url = f"{base_url}/logs/count"
                response = requests.get(count_url, timeout=2)
                response.raise_for_status()
                result = response.json()
                if result.get('success'):
                    log_count_text = str(result.get('count', 'Fout'))
                else:
                    log_count_text = "API Fout"
            except requests.exceptions.RequestException:
                log_count_text = "Onbereikbaar" # Unreachable
        
        if self.winfo_exists() and hasattr(self, 'log_count_label'):
            self.log_count_label.config(text=log_count_text)

    def _check_api_status_loop(self):
        while not self.api_status_thread_stop.is_set():
            self._update_api_status_label()
            # Wait for 1 second before the next check, but allow interruption
            self.api_status_thread_stop.wait(1) # Corrected from time.sleep(1)

    def _start_db_api(self):
        try:
            subprocess.Popen([sys.executable, self.api_script_path])
            messagebox.showinfo("API Beheer", "Database API is gestart.")
        except Exception as e:
            messagebox.showerror("API Fout", f"Kon de API niet starten:\n{e}")

    def _stop_db_api(self, silent=False):
        stopped = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['cmdline'] and self.api_script_path in proc.info['cmdline']:
                try:
                    p = psutil.Process(proc.info['pid'])
                    p.terminate()
                    stopped = True
                except psutil.Error as e:
                    if not silent:
                        messagebox.showerror("Fout bij Stoppen", f"Kon proces {proc.info['pid']} niet stoppen: {e}")
        if not silent:
            if stopped:
                messagebox.showinfo("API Beheer", "Database API proces gestopt.")
            else:
                messagebox.showwarning("API Beheer", "Geen actief Database API proces gevonden.")

    def _view_db_log(self):
        try:
            os.startfile(self.db_log_path)
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
            api_status_str = self.app.service_status.services.get('db_api', 'INACTIEF').upper()
            if "RUNNING" not in api_status_str:
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
                self._update_api_status_label() 
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

    def shutdown(self):
        """Graceful shutdown method to be called on application close."""
        self.log_to_queue("Applicatie wordt afgesloten, services stoppen...")
        if hasattr(self, 'api_status_thread_stop'):
            self.api_status_thread_stop.set()
        self._stop_splitter()
        self._stop_db_api(silent=True)
