import smtplib
import os
import json

from config_utils import update_config, get_config_path, ensure_config_exists

# Utility function to load email config from config.json
def load_email_config():
    config_file = get_config_path()
    if not os.path.exists(config_file):
        # Return default config if file is missing
        return {
            'sender': '',
            'receiver': '',
            'smtp_server': '',
            'smtp_port': 587,
            'smtp_user': '',
            'smtp_password': '',
            'email_enabled': False,
            'email_send_mode': 'per_scan'
        }
    with open(config_file, 'r') as f:
        config = json.load(f)
    return {
        'sender': config.get('email_sender', ''),
        'receiver': config.get('email_receiver', ''),
        'smtp_server': config.get('smtp_server', ''),
        'smtp_port': int(config.get('smtp_port', 587)),
        'smtp_user': config.get('smtp_user', ''),
        'smtp_password': config.get('smtp_password', ''),
        'email_enabled': config.get('email_enabled', False),
        'email_send_mode': config.get('email_send_mode', 'per_scan')
    }

# Remove any global SMTP login or test code. All email sending should use load_email_config()
import pandas as pd
import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tabs.import_tab import ImportTab
from tabs.scanner_tab import ScannerTab
from tabs.email_tab import EmailTab
from tabs.help_tab import HelpTab
from tabs.database_tab import DatabaseTab

import threading
import time
import keyboard  # For global keyboard hook
import smtplib
from email.mime.text import MIMEText
import pyodbc  # For reading .mdb files
# --- Import FileScannerGUI and dependencies from filemaker_gui.py ---
import json
from datetime import datetime

class Tooltip:
    """
    A simple tooltip that appears when hovering over a widget
    """
    def __init__(self, widget, text, absolute_position=None):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.absolute_position = absolute_position  # (x, y) tuple if provided
        self.widget.bind('<Enter>', self.showtip)
        self.widget.bind('<Leave>', self.hidetip)

    def showtip(self, event=None):
        if self.tipwindow or not self.text:
            return
        if self.absolute_position:
            x, y = self.absolute_position()
        else:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + 20
        self.tipwindow = tk.Toplevel(self.widget)
        self.tipwindow.wm_overrideredirect(1)
        self.tipwindow.wm_geometry(f"+{x}+{y}")
        try:
            self.tipwindow.wm_attributes("-toolwindow", 1)
        except tk.TclError:
            pass
        label = ttk.Label(self.tipwindow, text=self.text, justify=tk.LEFT,
                          background="white", relief=tk.SOLID, borderwidth=1,
                          font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

# FileScannerFrame moved to file_scanner_frame.py

    def __init__(self, parent):
        super().__init__(parent)
        self.root = parent  # For compatibility with original code
        self.scanning = False
        self.total_files = 0
        self.processed_files = 0
        self.files = []
        self.base_dir = ""
        self.directory_var = tk.StringVar()
        self.base_dir_var = tk.StringVar()
        # Config file path
        self.CONFIG_FILE = get_config_path()
        self.scan_mode_var = tk.StringVar(value="OPUS")  # Ensure it's initialized before load_config
        self.load_config()
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.columnconfigure(0, weight=1)


        self.directory_frame = ttk.LabelFrame(self.main_frame, text="Selecteer map", padding="5")
        self.directory_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        dir_entry = ttk.Entry(self.directory_frame, textvariable=self.directory_var, width=50)
        dir_entry.grid(row=0, column=0, padx=5)
        dir_btn = ttk.Button(self.directory_frame, text="Bladeren", command=self.browse_directory)
        dir_btn.grid(row=0, column=1, padx=5)
        self.dir_btn_tooltip = Tooltip(dir_btn, "Selecteer de map voor het scannen")
        # Add scan mode selector (OPUS/GANNOMAT)
        self.scan_mode_var = tk.StringVar(value="OPUS")
        scan_mode_combo = ttk.Combobox(self.directory_frame, textvariable=self.scan_mode_var, values=["OPUS", "GANNOMAT"], state="readonly", width=16)
        scan_mode_combo.grid(row=0, column=2, padx=5)
        scan_mode_combo_tooltip = Tooltip(scan_mode_combo, "Kies scanmodus: OPUS (.hop/.hops) of GANNOMAT (.mdb)") 
        scan_mode_combo.bind("<<ComboboxSelected>>", self.on_scan_mode_change)
        self.dir_entry = dir_entry
        self.dir_btn = dir_btn
        self.base_dir_frame = ttk.LabelFrame(self.main_frame, text="Basis map", padding="5")
        self.base_dir_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        base_entry = ttk.Entry(self.base_dir_frame, textvariable=self.base_dir_var, width=50)
        base_entry.grid(row=0, column=0, padx=5)
        base_btn = ttk.Button(self.base_dir_frame, text="Bladeren", command=self.browse_base_directory)
        base_btn.grid(row=0, column=1, padx=5)



        self.progress_frame = ttk.Frame(self.main_frame, padding="5")
        self.progress_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        self.progress_frame.columnconfigure(0, weight=1)
        self.progress_frame.columnconfigure(1, weight=0)
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100)
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.scan_button = ttk.Button(self.progress_frame, text="Map scannen", command=self.start_scan)
        self.scan_button.grid(row=0, column=1, padx=(10, 0))
        self.root.after(100, lambda: self.setup_scan_tooltip())
        self.status_label = ttk.Label(self.progress_frame, text="")
        self.status_label.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.results_frame = ttk.LabelFrame(self.main_frame, text="Resultaten", padding="5")
        self.results_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.S))
        self.results_text = tk.Text(self.results_frame, height=15, width=80)
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.S))
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)
        self.main_frame.rowconfigure(3, weight=1)

    def _open_manual(self):
        try:
            manual_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BarcodeMatch_Gebruikershandleiding.pdf")
            if os.path.exists(manual_path):
                os.startfile(manual_path)
            else:
                messagebox.showerror("Handleiding niet gevonden", "BarcodeMatch_Gebruikershandleiding.pdf is niet gevonden in de programmamap.")
        except Exception as e:
            messagebox.showerror("Fout bij openen handleiding", str(e))

    def setup_scan_tooltip(self):
        if hasattr(self, 'scan_button'):
            self.scan_button_tooltip = Tooltip(self.scan_button, "Start met scannen van de geselecteerde map voor .hop en .hops bestanden")

    def load_config(self):
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    if 'default_base_dir' in config:
                        base_dir = config['default_base_dir']
                        self.base_dir_var.set(base_dir)
                        self.base_dir = base_dir
                        if hasattr(self, 'base_dir_label'):
                            self.base_dir_label.config(text=f"Base Directory: {base_dir}")
                    if 'default_scan_mode' in config:
                        if hasattr(self, 'scan_mode_var'):
                            self.scan_mode_var.set(config['default_scan_mode'])
                    if 'default_scanner_type' in config:
                        if hasattr(self, 'scanner_type_var'):
                            self.scanner_type_var.set(config['default_scanner_type'])
                    if hasattr(self, 'default_base_label'):
                        self.default_base_label.config(text=f"(Default directory loaded from config)")
        except Exception as e:
            print(f"Error loading config: {str(e)}")

    def save_config(self):
        base_dir = self.base_dir_var.get()
        if base_dir:
            try:
                updates = {'default_base_dir': base_dir}
                if hasattr(self, 'scan_mode_var'):
                    updates['default_scan_mode'] = self.scan_mode_var.get()
                if hasattr(self, 'scanner_type_var'):
                    updates['default_scanner_type'] = self.scanner_type_var.get()
                update_config(updates)
                if hasattr(self, 'default_base_label'):
                    self.default_base_label.config(text=f"(Default directory saved to config)")
            except Exception as e:
                print(f"Error saving config: {str(e)}")



    def browse_directory(self):
        scan_mode = self.scan_mode_var.get() if hasattr(self, 'scan_mode_var') else "OPUS"
        if scan_mode == "GANNOMAT":
            mdb_file = filedialog.askopenfilename(
                filetypes=[("Access Database", "*.mdb;*.accdb")],
                title="Selecteer GANNOMAT .mdb bestand"
            )
            if mdb_file:
                self.directory_var.set(mdb_file)
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(tk.END, f"Selected file: {mdb_file}\n")
                self.results_text.see(tk.END)
        else:
            directory = filedialog.askdirectory()
            if directory:
                self.directory_var.set(directory)
                if not self.base_dir_var.get():
                    self.base_dir_var.set(directory)
                    self.base_dir = os.path.abspath(directory)
                    if hasattr(self, 'base_dir_label'):
                        self.base_dir_label.config(text=f"Base Directory: {self.base_dir}")
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(tk.END, f"Selected directory: {directory}\n")
                self.results_text.see(tk.END)

    def browse_base_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.base_dir_var.set(directory)
            self.base_dir = os.path.abspath(directory)
            if hasattr(self, 'base_dir_label'):
                self.base_dir_label.config(text=f"Base Directory: {self.base_dir}")

    def start_scan(self):
        scan_mode = self.scan_mode_var.get() if hasattr(self, 'scan_mode_var') else "OPUS"
        path = self.directory_var.get()
        if scan_mode == "GANNOMAT":
            if not path or not (path.lower().endswith('.mdb') or path.lower().endswith('.accdb')):
                messagebox.showwarning("Missing File", "Please select a .mdb file to scan.")
                return
            self.scan_button.config(state=tk.DISABLED)
            self.scanning = True
            threading.Thread(target=self._scan_thread, args=(path, scan_mode), daemon=True).start()
        else:
            if not path:
                messagebox.showwarning("Missing Directory", "Please select a directory to scan.")
                return
            self.scan_button.config(state=tk.DISABLED)
            self.scanning = True
            threading.Thread(target=self._scan_thread, args=(path, scan_mode), daemon=True).start()

    def on_scan_mode_change(self, event=None):
        # Always keep directory entry and button enabled, just change browse behavior
        self.save_scan_mode_to_config()

    def on_scanner_type_change(self, event=None):
        self.save_scanner_type_to_config()

    def save_scan_mode_to_config(self):
        try:
            updates = {'default_scan_mode': self.scan_mode_var.get()}
            if hasattr(self, 'scanner_type_var'):
                updates['default_scanner_type'] = self.scanner_type_var.get()
            update_config(updates)
        except Exception as e:
            print(f"Error saving scan mode to config: {e}")

    def save_scanner_type_to_config(self):
        try:
            updates = {'default_scanner_type': self.scanner_type_var.get()}
            if hasattr(self, 'scan_mode_var'):
                updates['default_scan_mode'] = self.scan_mode_var.get()
            update_config(updates)
        except Exception as e:
            print(f"Error saving scanner type to config: {e}")
            if scan_mode == "GANNOMAT":
                files = self.scan_mdb_files(path)
                self.files = files
                self.root.update_idletasks()
            else:
                files = self.scan_directory(path)
                self.files = files
                self.root.update_idletasks()
            self.results_text.see(tk.END)
            self.scanning = False
            if scan_mode == "GANNOMAT":
                self._create_excel(os.path.dirname(path), scan_mode)
            else:
                self._create_excel(path, scan_mode)
        except Exception as e:
            self.root.after(0, self._show_error, str(e))
        finally:
            # Always re-enable the scan button and reset progress/status
            self.scan_button.config(state=tk.NORMAL)
            self.progress_var.set(0)
            self.status_label.config(text="")


    def scan_directory(self, directory):
        self.total_files = 0
        self.processed_files = 0
        def count_files():
            total_files = 0
            for root, _, filenames in os.walk(directory):
                for filename in filenames:
                    if filename.lower().endswith(('.hop', '.hops')):
                        total_files += 1
            return total_files
        self.total_files = count_files()
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if filename.lower().endswith(('.hop', '.hops')):
                    try:
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, self.base_dir)
                        files.append({'Relative Path': relative_path})
                        self.processed_files += 1
                    except Exception as e:
                        self.results_text.insert(tk.END, f"Error processing {filename}: {str(e)}\n")
                        self.results_text.see(tk.END)
        return files

    def scan_mdb_files(self, mdb_file):
        # Scan a single .mdb file and extract ProgramNumber column, preferring 'Program' table
        self.total_files = 1
        self.processed_files = 0
        results = []
        try:
            conn_str = (
                r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
                f'DBQ={mdb_file};'
            )
            conn = pyodbc.connect(conn_str, autocommit=True)
            cursor = conn.cursor()
            # Gather all tables
            tables = [tbl_info.table_name for tbl_info in cursor.tables(tableType='TABLE')]
            program_table = None
            fallback_table = None
            # First, look for 'Program' table with ProgramNumber
            for table in tables:
                columns = [column.column_name for column in cursor.columns(table=table)]
                if table.lower() == 'program' and 'ProgramNumber' in columns:
                    program_table = table
                    break
                elif not fallback_table and 'ProgramNumber' in columns:
                    fallback_table = table
            if program_table:
                cursor.execute(f'SELECT ProgramNumber FROM [{program_table}]')
                for row in cursor.fetchall():
                    results.append({'MDB File': os.path.basename(mdb_file), 'ProgramNumber': row.ProgramNumber})
            elif fallback_table:
                cursor.execute(f'SELECT ProgramNumber FROM [{fallback_table}]')
                for row in cursor.fetchall():
                    results.append({'MDB File': os.path.basename(mdb_file), 'ProgramNumber': row.ProgramNumber})
            else:
                self.results_text.insert(tk.END, f"No table with 'ProgramNumber' column found in {os.path.basename(mdb_file)}\n")
                self.results_text.see(tk.END)
            conn.close()
            self.processed_files = 1
            self.update_progress(self.processed_files, self.total_files)
        except Exception as e:
            self.results_text.insert(tk.END, f"Error processing {os.path.basename(mdb_file)}: {str(e)}\n")
            self.results_text.see(tk.END)
        return results

    def update_progress(self, current, total):
        if total > 0:
            self.progress_var.set((current / total) * 100)
            self.status_label.config(text=f"Scanning... {current}/{total} files processed")
            self.root.update()

    def _show_error(self, error_msg):
        messagebox.showerror("Error", error_msg)

    def _create_excel(self, directory, scan_mode="OPUS"):
        if not self.files:
            self.results_text.insert(tk.END, "No files to save to Excel.\n")
            return
        df = pd.DataFrame(self.files)
        folder_name = os.path.basename(os.path.normpath(directory))
        if scan_mode == "GANNOMAT":
            # Only export ProgramNumber column if it exists
            if 'ProgramNumber' in df.columns:
                df = df[['ProgramNumber']]
            # Use the MDB filename (without extension) for export
            if hasattr(self, 'directory_var') and self.directory_var.get().lower().endswith('.mdb'):
                mdb_filename = os.path.splitext(os.path.basename(self.directory_var.get()))[0]
                excel_path = os.path.join(directory, f"{mdb_filename}_GANNOMAT.xlsx")
            else:
                excel_path = os.path.join(directory, f"{folder_name}_GANNOMAT.xlsx")
        else:
            excel_path = os.path.join(directory, f"{folder_name}_scan.xlsx")
        try:
            df.to_excel(excel_path, index=False)
            self.results_text.insert(tk.END, f"\nExcel file saved: {excel_path}\n")
        except Exception as e:
            self.results_text.insert(tk.END, f"Error saving Excel: {str(e)}\n")
        self.results_text.see(tk.END)


class COMPortComparator:
    def __init__(self, root):
        self.root = root
        # Set window title and icon
        self.root.title("BarcodeMatch")
        # Try ico.ico (Windows .ico) and ico.png (PNG) as possible icon files
        icon_set = False
        ico_dir = os.path.dirname(os.path.abspath(__file__))
        ico_ico_path = os.path.join(ico_dir, "ico.ico")
        ico_png_path = os.path.join(ico_dir, "ico.png")
        if os.path.exists(ico_ico_path):
            try:
                self.root.iconbitmap(ico_ico_path)
                icon_set = True
            except Exception as e:
                print(f"Kon ico.ico niet instellen: {e}")
        # --- Initialize daily log buffer and schedule daily email report if needed ---
        self._load_daily_log_buffer()
        self._daily_report_after_id = None  # Store after() id for cancellation
        if getattr(self, 'email_send_mode_var', None):
            mode = self.email_send_mode_var.get()
        else:
            email_cfg = load_email_config()
            mode = email_cfg.get('email_send_mode', 'per_scan')
        if mode == 'daily':
            self._send_missed_daily_reports()
            self._schedule_daily_email_report()
        if not icon_set and os.path.exists(ico_png_path):
            try:
                self.root.iconphoto(True, tk.PhotoImage(file=ico_png_path))
                icon_set = True
            except Exception as e:
                print(f"Kon ico.png niet instellen: {e}")
        if not icon_set:
            print("Geen geldig ico.ico of ico.png gevonden of kon niet worden ingesteld.")
        # Load email config from config.json at startup
        email_cfg = load_email_config()
        self.mail_sender = email_cfg['sender']
        self.mail_receiver = email_cfg['receiver']
        self.smtp_server = email_cfg['smtp_server']
        self.smtp_port = email_cfg['smtp_port']
        self.smtp_user = email_cfg['smtp_user']
        self.smtp_password = email_cfg['smtp_password']
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        # --- Modular Tab System ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.tab_frames = {}
        self.tab_icons = {}
        self.tabs = [
            {"name": "Importeren", "icon": "importeren.png", "class": ImportTab},
            {"name": "Scanner", "icon": "scanner.png", "class": ScannerTab},
            {"name": "Email", "icon": "email.png", "class": EmailTab},
            {"name": "Database", "icon": "database.png", "class": DatabaseTab},
            {"name": "Help", "icon": "help.png", "class": HelpTab}
        ]
        self.tab_instances = {}
        for idx, tab in enumerate(self.tabs):
            frame = ttk.Frame(self.notebook)
            icon = self._load_icon(tab["icon"])
            self.notebook.add(frame, text="", image=icon)
            self.tab_frames[tab["name"]] = frame
            self.tab_icons[tab["name"]] = icon  # Prevent garbage collection
            # Instantiate the tab class, passing the frame and self (main app)
            self.tab_instances[tab["name"]] = tab["class"](frame, self)
            print(f"[DEBUG] Created tab '{tab['name']}': instance={self.tab_instances[tab['name']]} type={type(self.tab_instances[tab['name']])}")
        # --- CASCADE PATCH: Ensure database_tab is accessible from main_app for other tabs (like ScannerTab) ---
        from tabs._cascade_patch_database_tab_link import apply_database_tab_patch
        apply_database_tab_patch(self)
        # Robust fallback: set attribute directly and print debug info
        if "Database" in self.tab_instances:
            self.database_tab = self.tab_instances["Database"]
            print(f"[DEBUG] main_app.database_tab set directly after patch. id(self): {id(self)}, id(self.database_tab): {id(self.database_tab)}, tab_instances keys: {list(self.tab_instances.keys())}")
        else:
            print(f"[DEBUG] main_app.database_tab NOT set: 'Database' not in tab_instances. id(self): {id(self)}, tab_instances keys: {list(self.tab_instances.keys())}")

    def _load_daily_log_buffer(self):
        # Load the daily log buffer from file if it exists
        try:
            if os.path.exists('daily_log_buffer.json'):
                with open('daily_log_buffer.json', 'r', encoding='utf-8') as f:
                    self._daily_log_buffer = json.load(f)
            else:
                self._daily_log_buffer = {}
        except Exception as e:
            print(f"Error loading daily log buffer: {e}")
            self._daily_log_buffer = {}

    def _save_daily_log_buffer(self):
        # Save the daily log buffer to a file for persistence (optional)
        try:
            with open('daily_log_buffer.json', 'w', encoding='utf-8') as f:
                json.dump(self._daily_log_buffer, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving daily log buffer: {e}")

    def _schedule_daily_email_report(self):
        """
        Schedule the daily email report to be sent at 23:59 every day.
        Stores the after() id so it can be cancelled if mode changes.
        """
        now = datetime.now()
        next_run = now.replace(hour=23, minute=59, second=0, microsecond=0)
        if now >= next_run:
            next_run = next_run + timedelta(days=1)
        delay_ms = int((next_run - now).total_seconds() * 1000)
        # Cancel any previous scheduled report
        if hasattr(self, '_daily_report_after_id') and self._daily_report_after_id is not None:
            try:
                self.root.after_cancel(self._daily_report_after_id)
            except Exception:
                pass
        self._daily_report_after_id = self.root.after(delay_ms, self._send_daily_email_report)

    def _accumulate_scan_log(self, log_line):
        """
        Accumulate scan log lines for the daily report.
        Stores them in a daily buffer keyed by date.
        """
        today = datetime.now().strftime('%Y-%m-%d')
        self._load_daily_log_buffer()
        if today not in self._daily_log_buffer:
            self._daily_log_buffer[today] = []
        self._daily_log_buffer[today].append(log_line)
        self._save_daily_log_buffer()

    def _send_daily_email_report(self):
        """
        Send all accumulated scan logs for today as a daily email report.
        Clears the buffer after sending. Schedules the next daily report if mode is still 'daily'.
        """
        today = datetime.now().strftime('%Y-%m-%d')
        self._load_daily_log_buffer()
        lines = self._daily_log_buffer.get(today, [])
        if lines:
            body = '\n'.join(lines)
            self.send_log_via_email(subject=f"Dagelijks scanrapport {today}", body_override=body)
            self._set_last_daily_report_sent(today)
            self._daily_log_buffer[today] = []
            self._save_daily_log_buffer()
        # Only reschedule if mode is still 'daily'
        email_cfg = load_email_config()
        mode = email_cfg.get('email_send_mode', 'per_scan')
        if mode == 'daily':
            self._schedule_daily_email_report()
        else:
            # Cancel any future scheduled report
            if hasattr(self, '_daily_report_after_id') and self._daily_report_after_id is not None:
                try:
                    self.root.after_cancel(self._daily_report_after_id)
                except Exception:
                    pass
                self._daily_report_after_id = None

    def _get_last_daily_report_sent(self):
        config_file = get_config_path()
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                try:
                    config = json.load(f)
                    return config.get('last_daily_report_sent', None)
                except Exception:
                    return None
        return None

    def _set_last_daily_report_sent(self, date_str):
        config_file = get_config_path()
        config = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                try:
                    config = json.load(f)
                except Exception:
                    config = {}
        config['last_daily_report_sent'] = date_str
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def _send_missed_daily_reports(self):
        """
        On startup, check for any unsent daily logs and send them as daily reports.
        """
        from datetime import datetime, timedelta
        email_cfg = load_email_config()
        if not email_cfg.get('email_enabled', False):
            return
        if email_cfg.get('email_send_mode', 'per_scan') != 'daily':
            return
        self._load_daily_log_buffer()
        last_sent = self._get_last_daily_report_sent()
        try:
            last_sent_date = datetime.strptime(last_sent, '%Y-%m-%d') if last_sent else None
        except Exception:
            last_sent_date = None
        # Gather all dates in the buffer, sorted
        all_dates = sorted(self._daily_log_buffer.keys())
        missed_dates = []
        for date_str in all_dates:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                if (last_sent_date is None) or (date_obj > last_sent_date):
                    if self._daily_log_buffer[date_str]:
                        missed_dates.append(date_str)
            except Exception:
                continue
        for date_str in missed_dates:
            lines = self._daily_log_buffer.get(date_str, [])
            if lines:
                body = '\n'.join(lines)
                try:
                    self.send_log_via_email(subject=f"Dagelijks scanrapport {date_str}", body_override=body)
                    self._set_last_daily_report_sent(date_str)
                    self._daily_log_buffer[date_str] = []
                    self._save_daily_log_buffer()
                    if hasattr(self, 'results_text'):
                        self.results_text.insert('end', f"Gemiste dagelijks rapport voor {date_str} verzonden.\n")
                        self.results_text.see('end')
                except Exception as e:
                    if hasattr(self, 'results_text'):
                        self.results_text.insert('end', f"Fout bij verzenden gemist rapport {date_str}: {e}\n")
                        self.results_text.see('end')


    def _create_email_tab(self, frame):
        # --- Email Tab Widgets ---
        email_group = ttk.LabelFrame(frame, text="Email Configuratie", padding="10")
        email_group.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
        copyright_label = tk.Label(frame, text=" 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)
        email_cfg = load_email_config()
        self.email_enabled_var = tk.BooleanVar(value=email_cfg.get('email_enabled', True))
        def on_email_enabled_change():
            enabled = self.email_enabled_var.get()
            config_file = get_config_path()
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    try:
                        config = json.load(f)
                    except Exception:
                        config = {}
            else:
                config = {}
            config['email_enabled'] = enabled
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
            state = "normal" if enabled else "disabled"
            for widget in [sender_entry, receiver_entry, smtp_entry, port_entry, user_entry, password_entry, test_btn]:
                widget.config(state=state)
        self.email_send_mode_var = tk.StringVar(value=email_cfg.get('email_send_mode', 'per_scan'))
        mode_label = ttk.Label(email_group, text="E-mail verzenden:")
        mode_label.grid(row=8, column=0, sticky=tk.W, pady=(15, 5))
        send_mode_options = [
            ("Na elke scan", "per_scan"),
            ("Dagelijks rapport", "daily")
        ]
        mode_display_names = [opt[0] for opt in send_mode_options]
        mode_value_map = {opt[0]: opt[1] for opt in send_mode_options}
        mode_display_map = {opt[1]: opt[0] for opt in send_mode_options}
        self.email_send_mode_combobox = ttk.Combobox(email_group, state="readonly", values=mode_display_names, width=25)
        current_mode = self.email_send_mode_var.get()
        self.email_send_mode_combobox.set(mode_display_map.get(current_mode, mode_display_names[0]))
        self.email_send_mode_combobox.grid(row=8, column=1, sticky=tk.W, pady=(15, 5))
        def on_email_mode_select(event=None):
            display = self.email_send_mode_combobox.get()
            value = mode_value_map.get(display, "per_scan")
            self.email_send_mode_var.set(value)
            config_file = get_config_path()
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    try:
                        config = json.load(f)
                    except Exception:
                        config = {}
            else:
                config = {}
            config['email_send_mode'] = value
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
            if value == 'daily':
                self._schedule_daily_email_report()
            else:
                if hasattr(self, '_daily_report_after_id') and self._daily_report_after_id is not None:
                    try:
                        self.root.after_cancel(self._daily_report_after_id)
                    except Exception:
                        pass
                    self._daily_report_after_id = None
        self.email_send_mode_combobox.bind("<<ComboboxSelected>>", on_email_mode_select)
        def sync_combobox_to_var(*args):
            v = self.email_send_mode_var.get()
            self.email_send_mode_combobox.set(mode_display_map.get(v, mode_display_names[0]))
        self.email_send_mode_var.trace_add('write', sync_combobox_to_var)
        email_checkbox = ttk.Checkbutton(
            email_group,
            text="E-mail inschakelen",
            variable=self.email_enabled_var,
            command=on_email_enabled_change
        )
        email_checkbox.grid(row=0, column=0, sticky=tk.W, pady=(0, 6), columnspan=2)
        ttk.Label(email_group, text="Afzender:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.sender_var = tk.StringVar(value=self.mail_sender)
        sender_entry = ttk.Entry(email_group, textvariable=self.sender_var, width=35)
        sender_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        ttk.Label(email_group, text="Ontvanger:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.receiver_var = tk.StringVar(value=self.mail_receiver)
        receiver_entry = ttk.Entry(email_group, textvariable=self.receiver_var, width=35)
        receiver_entry.grid(row=2, column=1, sticky=tk.W, pady=2)
        ttk.Label(email_group, text="SMTP server:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.smtp_var = tk.StringVar(value=self.smtp_server)
        smtp_entry = ttk.Entry(email_group, textvariable=self.smtp_var, width=35)
        smtp_entry.grid(row=3, column=1, sticky=tk.W, pady=2)
        ttk.Label(email_group, text="SMTP poort:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.port_var = tk.StringVar(value=str(self.smtp_port))
        port_entry = ttk.Entry(email_group, textvariable=self.port_var, width=10)
        port_entry.grid(row=4, column=1, sticky=tk.W, pady=2)
        ttk.Label(email_group, text="SMTP gebruiker:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.user_var = tk.StringVar(value=self.smtp_user)
        user_entry = ttk.Entry(email_group, textvariable=self.user_var, width=35)
        user_entry.grid(row=5, column=1, sticky=tk.W, pady=2)
        ttk.Label(email_group, text="SMTP wachtwoord:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.password_var = tk.StringVar(value=self.smtp_password)
        password_entry = ttk.Entry(email_group, textvariable=self.password_var, show="*", width=35)
        password_entry.grid(row=6, column=1, sticky=tk.W, pady=2)
        test_btn = ttk.Button(email_group, text="Verzend testmail", command=self._send_test_email)
        test_btn.grid(row=7, column=0, pady=10, sticky=tk.E)
        state = "normal" if self.email_enabled_var.get() else "disabled"
        for widget in [sender_entry, receiver_entry, smtp_entry, port_entry, user_entry, password_entry, test_btn]:
            widget.config(state=state)

    def _create_help_tab(self, frame):
        help_tab_btn = ttk.Button(frame, text="Open handleiding (PDF)", command=self.open_manual)
        help_tab_btn.pack(pady=20)
        copyright_label = tk.Label(frame, text=" 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)

    def open_manual(self):
        try:
            manual_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BarcodeMatch_Gebruikershandleiding.pdf")
            if os.path.exists(manual_path):
                os.startfile(manual_path)
            else:
                messagebox.showerror("Handleiding niet gevonden", "BarcodeMatch_Gebruikershandleiding.pdf is niet gevonden in de programmamap.")
        except Exception as e:
            messagebox.showerror("Fout bij openen handleiding", str(e))

    # Any other methods that use self and belong to the class should be defined here as well.

# Remove duplicate or free-floating definitions of these methods below the class.

        # Load the daily log buffer from file if it exists
        try:
            if os.path.exists('daily_log_buffer.json'):
                with open('daily_log_buffer.json', 'r', encoding='utf-8') as f:
                    self._daily_log_buffer = json.load(f)
            else:
                self._daily_log_buffer = {}
        except Exception as e:
            print(f"Error loading daily log buffer: {e}")
            self._daily_log_buffer = {}

    def _save_daily_log_buffer(self):
        # Save the daily log buffer to a file for persistence (optional)
        try:
            with open('daily_log_buffer.json', 'w', encoding='utf-8') as f:
                json.dump(self._daily_log_buffer, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving daily log buffer: {e}")

    def __init__(self, root):
        self.root = root
        # Set window title and icon
        self.root.title("BarcodeMatch")
        # Try ico.ico (Windows .ico) and ico.png (PNG) as possible icon files
        icon_set = False
        ico_dir = os.path.dirname(os.path.abspath(__file__))
        ico_ico_path = os.path.join(ico_dir, "ico.ico")
        ico_png_path = os.path.join(ico_dir, "ico.png")
        if os.path.exists(ico_ico_path):
            try:
                self.root.iconbitmap(ico_ico_path)
                icon_set = True
            except Exception as e:
                print(f"Kon ico.ico niet instellen: {e}")

        # --- Initialize daily log buffer and schedule daily email report if needed ---
        self._load_daily_log_buffer()
        self._daily_report_after_id = None  # Store after() id for cancellation
        if getattr(self, 'email_send_mode_var', None):
            mode = self.email_send_mode_var.get()
        else:
            email_cfg = load_email_config()
            mode = email_cfg.get('email_send_mode', 'per_scan')
        if mode == 'daily':
            self._schedule_daily_email_report()

        if not icon_set and os.path.exists(ico_png_path):
            try:
                self.root.iconphoto(True, tk.PhotoImage(file=ico_png_path))
                icon_set = True
            except Exception as e:
                print(f"Kon ico.png niet instellen: {e}")
        if not icon_set:
            print("Geen geldig ico.ico of ico.png gevonden of kon niet worden ingesteld.")
        # Load email config from config.json at startup
        email_cfg = load_email_config()
        self.mail_sender = email_cfg['sender']
        self.mail_receiver = email_cfg['receiver']
        self.smtp_server = email_cfg['smtp_server']
        self.smtp_port = email_cfg['smtp_port']
        self.smtp_user = email_cfg['smtp_user']
        self.smtp_password = email_cfg['smtp_password']
        # ... rest of __init__ continues as before ...
        self.root.geometry("800x600")
        self.root.minsize(800, 600)

        # --- Modular Tab System ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.tab_frames = {}
        self.tab_icons = {}

        self.tabs = [
            {"name": "Importeren", "icon": "importeren.png", "class": ImportTab},
            {"name": "Scanner", "icon": "scanner.png", "class": ScannerTab},
            {"name": "Email", "icon": "email.png", "class": EmailTab},
            {"name": "Database", "icon": "database.png", "class": DatabaseTab},
            {"name": "Help", "icon": "help.png", "class": HelpTab}
        ]

        self.tab_instances = {}
        for idx, tab in enumerate(self.tabs):
            frame = ttk.Frame(self.notebook)
            icon = self._load_icon(tab["icon"])
            self.notebook.add(frame, text="", image=icon)
            self.tab_frames[tab["name"]] = frame
            self.tab_icons[tab["name"]] = icon  # Prevent garbage collection
            # Instantiate the tab class, passing the frame and self (main app)
            self.tab_instances[tab["name"]] = tab["class"](frame, self)


    def _load_icon(self, filename, size=(75, 75)):
        try:
            from PIL import Image, ImageTk
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
            pil_img = Image.open(path).resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(pil_img)
        except Exception:
            try:
                tmp_img = tk.PhotoImage(file=path)
                return tmp_img.subsample(max(1, tmp_img.width() // size[0]), max(1, tmp_img.height() // size[1]))
            except Exception:
                return None

    # The tab creation methods are now modularized in the tabs/ directory and are no longer defined here.
        self.scanned_frame.columnconfigure(0, weight=1)
        self.scanned_frame.rowconfigure(0, weight=1)
        self.scanned_tree = ttk.Treeview(self.scanned_frame, columns=('Status', 'Item'), show='headings')
        self.scanned_tree.heading('Status', text='Status')
        self.scanned_tree.heading('Item', text='Item')
        self.scanned_tree.column('Status', width=100, stretch=True, anchor='e')
        self.scanned_tree.column('Item', width=600, stretch=True, anchor='w')
        self.tree_scroll = ttk.Scrollbar(self.scanned_frame, orient='vertical', command=self.scanned_tree.yview)
        self.scanned_tree.configure(yscrollcommand=self.tree_scroll.set)
        self.scanned_tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.tree_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree_menu = tk.Menu(self.scanned_tree, tearoff=0)
        self.tree_menu.add_command(label="Status op OK zetten", command=self.set_status_ok)
        self.tree_menu.add_command(label="Status wissen", command=self.clear_status)
        self.scanned_tree.bind("<Button-3>", self.show_tree_menu)

        # Text area for messages
        self.log_frame = ttk.Frame(self.results_paned)
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)
        self.results_text = tk.Text(self.log_frame, height=10)
        self.results_text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        # Add both panes to the PanedWindow
        self.results_paned.add(self.scanned_frame, weight=3)
        self.results_paned.add(self.log_frame, weight=1)

        # Control buttons
        self.control_frame = ttk.Frame(self.main_frame)
        self.control_frame.grid(row=3, column=0, pady=(10, 0))
        self.button_container = ttk.Frame(self.control_frame)
        self.button_container.grid(row=0, column=0)
        self.connect_button = ttk.Button(self.button_container, text="Verbinden", command=self.connect_com)
        self.connect_button.grid(row=0, column=0, padx=5)
        self.disconnect_button = ttk.Button(self.button_container, text="Verbinding verbreken", command=self.disconnect_com)

        # Progress and status
        self.progress_frame = ttk.LabelFrame(self.main_frame, text="Status", padding="5")
        self.progress_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.S), pady=(0, 10))
        self.progress_frame.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(self.progress_frame, text="Niet verbonden")
        self.status_label.grid(row=0, column=0, pady=(5, 0), sticky=tk.W)

        # Ensure correct frame is visible on startup
        self.update_scanner_type()


def _save_email_send_mode(self):
    config_file = get_config_path()
    # Read existing config
    config = {}
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            try:
                config = json.load(f)
            except Exception:
                config = {}
    config['email_send_mode'] = self.email_send_mode_var.get()
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)


    # --- Email Tab Widgets ---
    email_group = ttk.LabelFrame(frame, text="Email Configuratie", padding="10")
    email_group.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
    copyright_label = tk.Label(frame, text=" 2025 RVL", font=(None, 9), fg="#888888")
    copyright_label.pack(side=tk.BOTTOM, pady=2)

    email_cfg = load_email_config()
    self.email_enabled_var = tk.BooleanVar(value=email_cfg.get('email_enabled', True))

    def on_email_enabled_change():
        enabled = self.email_enabled_var.get()
        # Save to config.json
        config_file = get_config_path()
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                try:
                    config = json.load(f)
                except Exception:
                    config = {}
        else:
            config = {}
        config['email_enabled'] = enabled
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        state = "normal" if enabled else "disabled"
        for widget in [sender_entry, receiver_entry, smtp_entry, port_entry, user_entry, password_entry, test_btn]:
            widget.config(state=state)

    # Email send mode dropdown (Combobox)
    self.email_send_mode_var = tk.StringVar(value=email_cfg.get('email_send_mode', 'per_scan'))
    mode_label = ttk.Label(email_group, text="E-mail verzenden:")
    mode_label.grid(row=8, column=0, sticky=tk.W, pady=(15, 5))
    send_mode_options = [
        ("Na elke scan", "per_scan"),
        ("Dagelijks rapport", "daily")
    ]
    mode_display_names = [opt[0] for opt in send_mode_options]
    mode_value_map = {opt[0]: opt[1] for opt in send_mode_options}
    mode_display_map = {opt[1]: opt[0] for opt in send_mode_options}
    self.email_send_mode_combobox = ttk.Combobox(email_group, state="readonly", values=mode_display_names, width=25)
    # Set initial value
    current_mode = self.email_send_mode_var.get()
    self.email_send_mode_combobox.set(mode_display_map.get(current_mode, mode_display_names[0]))
    self.email_send_mode_combobox.grid(row=8, column=1, sticky=tk.W, pady=(15, 5))
    def on_email_mode_select(event=None):
        display = self.email_send_mode_combobox.get()
        value = mode_value_map.get(display, "per_scan")
        self.email_send_mode_var.set(value)
        config_file = get_config_path()
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                try:
                    config = json.load(f)
                except Exception:
                    config = {}
        else:
            config = {}
        config['email_send_mode'] = value
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
    self.email_send_mode_combobox.bind("<<ComboboxSelected>>", on_email_mode_select)
    # Also update combobox if var changes externally
    def sync_combobox_to_var(*args):
        v = self.email_send_mode_var.get()
        self.email_send_mode_combobox.set(mode_display_map.get(v, mode_display_names[0]))
    self.email_send_mode_var.trace_add('write', sync_combobox_to_var)

    email_checkbox = ttk.Checkbutton(
        email_group,
        text="E-mail inschakelen",
        variable=self.email_enabled_var,
        command=on_email_enabled_change
    )
    email_checkbox.grid(row=0, column=0, sticky=tk.W, pady=(0, 6), columnspan=2)

    ttk.Label(email_group, text="Afzender:").grid(row=2, column=0, sticky=tk.W, pady=2)
    self.sender_var = tk.StringVar(value=self.mail_sender)
    sender_entry = ttk.Entry(email_group, textvariable=self.sender_var, width=35)
    sender_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
    ttk.Label(email_group, text="Ontvanger:").grid(row=2, column=0, sticky=tk.W, pady=2)
    self.receiver_var = tk.StringVar(value=self.mail_receiver)
    receiver_entry = ttk.Entry(email_group, textvariable=self.receiver_var, width=35)
    receiver_entry.grid(row=2, column=1, sticky=tk.W, pady=2)
    ttk.Label(email_group, text="SMTP server:").grid(row=3, column=0, sticky=tk.W, pady=2)
    self.smtp_var = tk.StringVar(value=self.smtp_server)
    smtp_entry = ttk.Entry(email_group, textvariable=self.smtp_var, width=35)
    smtp_entry.grid(row=3, column=1, sticky=tk.W, pady=2)
    ttk.Label(email_group, text="SMTP poort:").grid(row=4, column=0, sticky=tk.W, pady=2)
    self.port_var = tk.StringVar(value=str(self.smtp_port))
    port_entry = ttk.Entry(email_group, textvariable=self.port_var, width=10)
    port_entry.grid(row=4, column=1, sticky=tk.W, pady=2)
    ttk.Label(email_group, text="SMTP gebruiker:").grid(row=5, column=0, sticky=tk.W, pady=2)
    self.user_var = tk.StringVar(value=self.smtp_user)
    user_entry = ttk.Entry(email_group, textvariable=self.user_var, width=35)
    user_entry.grid(row=5, column=1, sticky=tk.W, pady=2)
    ttk.Label(email_group, text="SMTP wachtwoord:").grid(row=6, column=0, sticky=tk.W, pady=2)
    self.password_var = tk.StringVar(value=self.smtp_password)
    password_entry = ttk.Entry(email_group, textvariable=self.password_var, show="*", width=35)
    password_entry.grid(row=6, column=1, sticky=tk.W, pady=2)
    test_btn = ttk.Button(email_group, text="Verzend testmail", command=self._send_test_email)
    test_btn.grid(row=7, column=0, pady=10, sticky=tk.E)
    state = "normal" if self.email_enabled_var.get() else "disabled"
    for widget in [sender_entry, receiver_entry, smtp_entry, port_entry, user_entry, password_entry, test_btn]:
        widget.config(state=state)

def _create_help_tab(self, frame):
    help_tab_btn = ttk.Button(frame, text="Open handleiding (PDF)", command=self.open_manual)
    help_tab_btn.pack(pady=20)
    copyright_label = tk.Label(frame, text=" 2025 RVL", font=(None, 9), fg="#888888")
    copyright_label.pack(side=tk.BOTTOM, pady=2)

def open_manual(self):
    try:
        manual_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BarcodeMatch_Gebruikershandleiding.pdf")
        if os.path.exists(manual_path):
            os.startfile(manual_path)
        else:
            messagebox.showerror("Handleiding niet gevonden", "BarcodeMatch_Gebruikershandleiding.pdf is niet gevonden in de programmamap.")
    except Exception as e:
        messagebox.showerror("Fout bij openen handleiding", str(e))

# Removed dynamic config update traces; config is saved on close via save_email_settings_to_config().


        email_checkbox.grid(row=0, column=0, sticky=tk.W, pady=(0, 6), columnspan=2)

        # Email send mode dropdown (Combobox)
        self.email_send_mode_var = tk.StringVar(value=load_email_config().get('email_send_mode', 'per_scan'))
        send_mode_options = [
            ("Na elke scan", "per_scan"),
            ("Dagelijks rapport", "daily")
        ]
        mode_display_names = [opt[0] for opt in send_mode_options]
        mode_value_map = {opt[0]: opt[1] for opt in send_mode_options}
        mode_display_map = {opt[1]: opt[0] for opt in send_mode_options}
        send_mode_label = ttk.Label(email_group, text="E-mail verzenden:")
        send_mode_label.grid(row=8, column=0, sticky=tk.W, pady=(15, 5))
        self.email_send_mode_combobox = ttk.Combobox(email_group, state="readonly", values=mode_display_names, width=25)
        current_mode = self.email_send_mode_var.get()
        self.email_send_mode_combobox.set(mode_display_map.get(current_mode, mode_display_names[0]))
        self.email_send_mode_combobox.grid(row=8, column=1, sticky=tk.W, pady=(15, 5))
        def on_email_mode_select(event=None):
            display = self.email_send_mode_combobox.get()
            value = mode_value_map.get(display, "per_scan")
            self.email_send_mode_var.set(value)
            config_file = get_config_path()
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    try:
                        config = json.load(f)
                    except Exception:
                        config = {}
            else:
                config = {}
            config['email_send_mode'] = value
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
        self.email_send_mode_combobox.bind("<<ComboboxSelected>>", on_email_mode_select)
        def sync_combobox_to_var(*args):
            v = self.email_send_mode_var.get()
            self.email_send_mode_combobox.set(mode_display_map.get(v, mode_display_names[0]))
        self.email_send_mode_var.trace_add('write', sync_combobox_to_var)

        ttk.Label(email_group, text="Afzender:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.sender_var = tk.StringVar(value=self.mail_sender)
        sender_entry = ttk.Entry(email_group, textvariable=self.sender_var, width=35)
        sender_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        ttk.Label(email_group, text="Ontvanger:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.receiver_var = tk.StringVar(value=self.mail_receiver)
        receiver_entry = ttk.Entry(email_group, textvariable=self.receiver_var, width=35)
        receiver_entry.grid(row=2, column=1, sticky=tk.W, pady=2)
        ttk.Label(email_group, text="SMTP server:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.smtp_var = tk.StringVar(value=self.smtp_server)
        smtp_entry = ttk.Entry(email_group, textvariable=self.smtp_var, width=35)
        smtp_entry.grid(row=3, column=1, sticky=tk.W, pady=2)
        ttk.Label(email_group, text="SMTP poort:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.port_var = tk.StringVar(value=str(self.smtp_port))
        port_entry = ttk.Entry(email_group, textvariable=self.port_var, width=10)
        port_entry.grid(row=4, column=1, sticky=tk.W, pady=2)
        ttk.Label(email_group, text="SMTP gebruiker:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.user_var = tk.StringVar(value=self.smtp_user)
        user_entry = ttk.Entry(email_group, textvariable=self.user_var, width=35)
        user_entry.grid(row=5, column=1, sticky=tk.W, pady=2)
        ttk.Label(email_group, text="SMTP wachtwoord:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.password_var = tk.StringVar(value=self.smtp_password)
        password_entry = ttk.Entry(email_group, textvariable=self.password_var, show="*", width=35)
        password_entry.grid(row=6, column=1, sticky=tk.W, pady=2)
        test_btn = ttk.Button(email_group, text="Verzend testmail", command=self._send_test_email)
        test_btn.grid(row=7, column=0, pady=10, sticky=tk.E)
        state = "normal" if self.email_enabled_var.get() else "disabled"
        for widget in [sender_entry, receiver_entry, smtp_entry, port_entry, user_entry, password_entry, test_btn]:
            widget.config(state=state)


    def _create_help_tab(self, frame):
        help_tab_btn = ttk.Button(frame, text="Open handleiding (PDF)", command=self.open_manual)
        help_tab_btn.pack(pady=20)
        copyright_label = tk.Label(frame, text="© 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)

    def open_manual(self):
        try:
            manual_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BarcodeMatch_Gebruikershandleiding.pdf")
            if os.path.exists(manual_path):
                os.startfile(manual_path)
            else:
                messagebox.showerror("Handleiding niet gevonden", "BarcodeMatch_Gebruikershandleiding.pdf is niet gevonden in de programmamap.")
        except Exception as e:
            messagebox.showerror("Fout bij openen handleiding", str(e))

        # Removed dynamic config update traces; config is saved on close via save_email_settings_to_config().

        # Email enabled checkbox
        email_cfg = load_email_config()
        self.email_enabled_var = tk.BooleanVar(value=email_cfg.get('email_enabled', True))

        def on_email_enabled_change():
            enabled = self.email_enabled_var.get()
            # Save to config.json
            config_file = get_config_path()
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    try:
                        config = json.load(f)
                    except Exception:
                        config = {}
            else:
                config = {}
            config['email_enabled'] = enabled
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
            state = "normal" if enabled else "disabled"
            for widget in [sender_entry, receiver_entry, smtp_entry, port_entry, user_entry, password_entry, test_btn]:
                widget.config(state=state)

        # Ensure correct frame is visible on startup
        self.update_scanner_type()

        email_checkbox = ttk.Checkbutton(
            self.email_frame,
            text="E-mail inschakelen",
            variable=self.email_enabled_var,
            command=on_email_enabled_change
        )
        email_checkbox.grid(row=6, column=0, sticky=tk.W, pady=(10, 2), columnspan=2)

        # Test email button
        test_btn = ttk.Button(self.email_frame, text="Verzend testmail", command=self._send_test_email)
        test_btn.grid(row=7, column=0, pady=10, sticky=tk.E)

        # Set initial state of widgets
        state = "normal" if self.email_enabled_var.get() else "disabled"
        for widget in [sender_entry, receiver_entry, smtp_entry, port_entry, user_entry, password_entry, test_btn]:
            widget.config(state=state)

        try:
            config_file = get_config_path()
            config = {}
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
            # Only save if the StringVar exists
            if hasattr(self, 'sender_var'):
                config['email_sender'] = self.sender_var.get()
            if hasattr(self, 'receiver_var'):
                config['email_receiver'] = self.receiver_var.get()
            if hasattr(self, 'smtp_var'):
                config['smtp_server'] = self.smtp_var.get()
            if hasattr(self, 'port_var'):
                config['smtp_port'] = self.port_var.get()
            if hasattr(self, 'user_var'):
                config['smtp_user'] = self.user_var.get()
            if hasattr(self, 'password_var'):
                config['smtp_password'] = self.password_var.get()
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving email settings to config: {e}")

    def _send_test_email(self):
        try:
            self.send_log_via_email(subject="Testmail OPUS Scan Log")
            messagebox.showinfo("Testmail", "Testmail succesvol verzonden!")
        except Exception as e:
            messagebox.showerror("Fout bij testmail", str(e))

    def send_log_via_email(self, subject="OPUS Scan Log", body_override=None):
        """Send the scan_log.txt contents as an email body using config.json settings. Optionally override body."""
        import traceback
        try:
            email_cfg = load_email_config()
            if body_override is not None:
                msg = MIMEText(body_override)
            else:
                with open("scan_log.txt", "r", encoding="utf-8") as logf:
                    lines = [line.strip() for line in logf if line.strip()]
                    last_line = lines[-1] if lines else "(Geen scan gevonden)"
                msg = MIMEText(last_line)
            msg["Subject"] = subject
            msg["From"] = email_cfg['sender']
            msg["To"] = email_cfg['receiver']

            with smtplib.SMTP(email_cfg['smtp_server'], email_cfg['smtp_port']) as server:
                server.starttls()
                server.login(email_cfg['smtp_user'], email_cfg['smtp_password'])
                server.sendmail(email_cfg['sender'], [email_cfg['receiver']], msg.as_string())
            messagebox.showinfo("E-mail verzonden", "Scan log succesvol verzonden!")
            self.results_text.insert(tk.END, "E-mail succesvol verzonden.\n")
            self.results_text.see(tk.END)
        except Exception as e:
            tb = traceback.format_exc()
            messagebox.showerror("Fout bij verzenden van e-mail", f"Er is een fout opgetreden bij het verzenden van de e-mail:\n{str(e)}")
            self.results_text.insert(tk.END, f"Fout bij verzenden van e-mail: {str(e)}\n{tb}\n")
            self.results_text.see(tk.END)


    def _save_daily_log_buffer(self):
        # Save the daily log buffer to a file for persistence (optional)
        try:
            with open('daily_log_buffer.json', 'w', encoding='utf-8') as f:
                json.dump(self._daily_log_buffer, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving daily log buffer: {e}")

    def _load_daily_log_buffer(self):
        # Load the daily log buffer from file if it exists
        try:
            if os.path.exists('daily_log_buffer.json'):
                with open('daily_log_buffer.json', 'r', encoding='utf-8') as f:
                    self._daily_log_buffer = json.load(f)
            else:
                self._daily_log_buffer = {}
        except Exception as e:
            print(f"Error loading daily log buffer: {e}")
            self._daily_log_buffer = {}

    
        """
        Schedule the daily email report to be sent at 23:59 every day.
        Stores the after() id so it can be cancelled if mode changes.
        """
        now = datetime.now()
        next_run = now.replace(hour=23, minute=59, second=0, microsecond=0)
        if now >= next_run:
            next_run = next_run + timedelta(days=1)
        delay_ms = int((next_run - now).total_seconds() * 1000)
        # Cancel any previous scheduled report
        if hasattr(self, '_daily_report_after_id') and self._daily_report_after_id is not None:
            try:
                self.root.after_cancel(self._daily_report_after_id)
            except Exception:
                pass
        self._daily_report_after_id = self.root.after(delay_ms, self._send_daily_email_report)

    
        """
        Accumulate scan log lines for the daily report.
        Stores them in a daily buffer keyed by date.
        """
        today = datetime.now().strftime('%Y-%m-%d')
        self._load_daily_log_buffer()
        if today not in self._daily_log_buffer:
            self._daily_log_buffer[today] = []
        self._daily_log_buffer[today].append(log_line)
        self._save_daily_log_buffer()

    
        """
        Send all accumulated scan logs for today as a daily email report.
        Clears the buffer after sending. Schedules the next daily report if mode is still 'daily'.
        """
        today = datetime.now().strftime('%Y-%m-%d')
        self._load_daily_log_buffer()
        lines = self._daily_log_buffer.get(today, [])
        if lines:
            body = '\n'.join(lines)
            self.send_log_via_email(subject=f"Dagelijks scanrapport {today}", body_override=body)
            self._set_last_daily_report_sent(today)
            self._daily_log_buffer[today] = []
            self._save_daily_log_buffer()
        # Only reschedule if mode is still 'daily'
        email_cfg = load_email_config()
        mode = email_cfg.get('email_send_mode', 'per_scan')
        if mode == 'daily':
            self._schedule_daily_email_report()
        else:
            # Cancel any future scheduled report
            if hasattr(self, '_daily_report_after_id') and self._daily_report_after_id is not None:
                try:
                    self.root.after_cancel(self._daily_report_after_id)
                except Exception:
                    pass
                self._daily_report_after_id = None

    
        config_file = get_config_path()
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                try:
                    config = json.load(f)
                    return config.get('last_daily_report_sent', None)
                except Exception:
                    return None
        return None

        # (Removed erroneous results_notebook usage; scanned_frame is already part of the UI)
        # Configure grid weights for proper expansion
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(2, weight=1)  # Results frame row
        
        self.results_frame.rowconfigure(0, weight=1)  # Treeview/log row
        self.results_frame.columnconfigure(0, weight=1)  # Treeview/log column
        
        self.scanned_frame.columnconfigure(0, weight=1)  # Treeview column
        self.scanned_frame.rowconfigure(0, weight=1)  # Treeview row (expand)
        

        
        # Configure text area for messages
        self.results_text.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.results_frame.rowconfigure(1, weight=1)  # Text area row
        self.results_frame.columnconfigure(0, weight=1)  # Text area column
        
        # (Removed all results_notebook references; not needed for layout)
        
        # Control buttons
        self.control_frame = ttk.Frame(self.main_frame)
        self.control_frame.grid(row=3, column=0, pady=(10, 0))
        self.button_container = ttk.Frame(self.control_frame)
        self.button_container.grid(row=0, column=0)
        self.connect_button = ttk.Button(self.button_container, text="Verbinden", command=self.connect_com)
        self.connect_button.grid(row=0, column=0, padx=5)
        self.disconnect_button = ttk.Button(self.button_container, text="Verbinding verbreken", command=self.disconnect_com)
        self.disconnect_button.grid(row=0, column=1, padx=5)
        self.disconnect_button.config(state=tk.DISABLED)
        self.control_frame.columnconfigure(0, weight=1)
        self.button_container.grid_configure(pady=5)
        
        # Progress and status
        self.progress_frame = ttk.LabelFrame(self.main_frame, text="Status", padding="5")
        self.progress_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.S), pady=(0, 10))
        
        # Configure progress frame to expand horizontally
        self.progress_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(self.progress_frame, text="Niet verbonden")
        self.status_label.grid(row=0, column=0, pady=(5, 0), sticky=tk.W)
        
        # Variables
        self.scanned_items = {}  # Dictionary to store scanned status
        
        # Initialize COM port list
        self.refresh_ports()
        self.update_scanner_type()  # Set initial UI state

        # Start background thread for keyboard scanner hook
        self.keyboard_scanner_enabled = False
        self.keyboard_thread = threading.Thread(target=self.keyboard_scanner_hook, daemon=True)
        self.keyboard_thread.start()
        
        # Initialize variables
        self.com_port = None
        self.com_thread = None
        self.com_data = []
        self.running = False
        self.last_scanned = None  # Store last scanned item
        self.consecutive_count = 0  # Count consecutive scans
        
        # Check for command line arguments
        import sys
        if len(sys.argv) > 1:
            excel_file = sys.argv[1]
            if os.path.exists(excel_file):
                self.excel_var.set(excel_file)
                self.results_text.insert(tk.END, f"Excel bestand geladen: {excel_file}\n")
                self.results_text.see(tk.END)
                try:
                    self.update_scanned_tree(excel_file)
                except Exception as e:
                    self.results_text.insert(tk.END, f"Fout bij het laden van Excel bestand: {str(e)}\n")
                    self.results_text.see(tk.END)
        
        # Configure root to update periodically
        self.root.after(100, self.update_gui)

    def update_gui(self):
        """Periodic GUI update to ensure responsiveness"""
        # Force a GUI update
        self.root.update_idletasks()
        self.root.after(100, self.update_gui)

    def update_scanner_type(self):
        """Show/hide frames and status depending on selected scanner type."""
        scanner_type = self.scanner_type_var.get()
        if scanner_type == "COM":
            self.com_frame.grid()
            self.usb_frame.grid_remove()
            self.control_frame.grid()
            self.progress_frame.grid()  # Show connection status
            self.keyboard_scanner_enabled = False
        else:
            self.com_frame.grid_remove()
            self.usb_frame.grid()
            self.control_frame.grid_remove()
            self.progress_frame.grid_remove()  # Hide connection status
            self.usb_entry.focus_set()
            self.keyboard_scanner_enabled = True
        # Optionally, clear status label if switching to USB
        if scanner_type == "USB":
            self.status_label.config(text="Niet verbonden")
        self.root.update_idletasks()

    def refresh_ports(self):
        """Refresh the list of available COM ports"""
        ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in ports]
        self.com_port_combo['values'] = port_names
        if port_names:
            self.com_port_var.set(port_names[0])

    def show_tree_menu(self, event):
        """Show the right-click menu for Treeview"""
        # Get the selected item (if needed for context menu)
        # Only context menu logic should remain here
        # All scan/Excel logic must be in tabs/scanner_tab.py
        # Send log via email
        self.send_log_via_email()

    def keyboard_scanner_hook(self):
        SCAN_TIMEOUT = 0.1  # seconds between chars to consider part of scan
        MIN_SCAN_LEN = 3    # Minimum chars to consider a scan
        while True:
            event = keyboard.read_event(suppress=False)
            if not self.keyboard_scanner_enabled:
                buffer = []
                last_time = None
                continue
            if event.event_type == keyboard.KEY_DOWN:
                now = time.time()
                if last_time is None or (now - last_time) > SCAN_TIMEOUT:
                    buffer = []
                last_time = now
                if event.name == 'enter':
                    scan_code = ''.join(buffer)
                    if len(scan_code) >= MIN_SCAN_LEN:
                        # Use Tk thread-safe call
                        self.root.after(0, self.handle_scanned_value, scan_code)
                    buffer = []
                elif len(event.name) == 1:
                    buffer.append(event.name)

                self.excluded_codes = set()
                self.results_text.insert(tk.END, f"Fout bij het laden van filtered_scans.json: {str(e)}\n")
                self.results_text.see(tk.END)
        if value in self.excluded_codes:
            return
        # This method mimics the logic in read_com for a single scan value
        self.results_text.insert(tk.END, f"Ontvangen: {value}\n")
        self.results_text.see(tk.END)
        
        if excel_file:
            try:
                updated_file = os.path.splitext(excel_file)[0] + '_updated.xlsx'
                if os.path.exists(updated_file):
                    df = pd.read_excel(updated_file)
                else:
                    df = pd.read_excel(excel_file)
                if 'Status' not in df.columns:
                    df['Status'] = ''
                item_exists = False
                matched_item = None
                for idx, row in df.iterrows():
                    excel_item = str(row.iloc[0]).lower().strip()
                    if excel_item == value.lower().strip():
                        item_exists = True
                        matched_item = excel_item
                        break
                    if not item_exists and value.lower().strip() in excel_item:
                        item_exists = True
                        matched_item = excel_item
                        break
                if item_exists:
                    # Only update if not already OK
                    for idx, row in df.iterrows():
                        if str(row.iloc[0]).lower().strip() == matched_item:
                            if str(row['Status']).strip().upper() != 'OK':
                                df.at[idx, 'Status'] = 'OK'
                                # Only update GUI status with the matched item (not the raw scan value)
                                self.root.after(0, self.update_gui_status, matched_item)
                                self.results_text.insert(tk.END, f"Item '{value}' gematcht met '{matched_item}' in Excel en gemarkeerd als OK\n")
                            else:
                                self.results_text.insert(tk.END, f"Item '{value}' is al OK in Excel, geen wijziging.\n")
                            break
                    else:
                        self.results_text.insert(tk.END, f"Waarschuwing: Item '{value}' niet gevonden in Excel bestand\n")
                        self.results_text.see(tk.END)
                    # Only save if something changed
                    df.to_excel(updated_file, index=False)
                else:
                    self.results_text.insert(tk.END, f"Waarschuwing: Item '{value}' niet gevonden in Excel bestand\n")
                    self.results_text.see(tk.END)
                self.results_text.see(tk.END)
            except Exception as e:
                self.results_text.insert(tk.END, f"Fout bij het bijwerken van status: {str(e)}\n")
                self.results_text.see(tk.END)


    def disconnect_com(self):
        """Disconnect from the COM port and update UI."""
        try:
            self.running = False
            if hasattr(self, 'com_port') and self.com_port:
                try:
                    self.com_port.close()
                except Exception:
                    pass
                self.com_port = None
            self.status_label.config(text="Niet verbonden")
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
        except Exception as e:
            self.results_text.insert(tk.END, f"Fout bij het verbreken van verbinding: {str(e)}\n")
            self.results_text.see(tk.END)
            messagebox.showerror("Fout bij verbreken", f"Verbinding kon niet worden verbroken: {str(e)}")

    def connect_com(self):
        try:
            port = self.com_port_var.get()
            baud_rate = int(self.baud_rate_var.get())
            
            self.com_port = serial.Serial(port, baud_rate, timeout=1)
            self.status_label.config(text=f"Verbonden met {port}")
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
            
            # Start reading thread
            self.running = True
            self.com_thread = threading.Thread(target=self.read_com, daemon=True)
            self.com_thread.start()
            
            # Clean up resources
            self.com_port = None
            self.com_thread = None
            self.com_data = []
            
            # Update UI
            self.status_label.config(text="Niet verbonden")
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
            
        except Exception as e:
            self.results_text.insert(tk.END, f"Fout bij het verbreken van verbinding: {str(e)}\n")
            self.results_text.see(tk.END)
            messagebox.showerror("Fout bij verbreken", f"Verbinding kon niet worden verbroken: {str(e)}")
    
    # Removed duplicate update_gui_status (use ScannerTab logic)
        """Update the GUI status in a thread-safe way"""
        try:
            # Update Treeview
            for item_id in self.scanned_tree.get_children():
                values = self.scanned_tree.item(item_id)['values']
                if values[1].lower() == matched_item.lower():  # Case-insensitive match
                    # Update status in Treeview
                    self.scanned_tree.item(item_id, values=('OK', values[1]))
                    self.scanned_items[values[1]] = 'OK'
                    self.results_text.insert(tk.END, f"Status bijgewerkt voor: {values[1]}\n")
                    self.results_text.see(tk.END)
                    break
            
            # Force a GUI update
            self.root.update_idletasks()
            
        except Exception as e:
            self.results_text.insert(tk.END, f"Fout bij het bijwerken van GUI status: {str(e)}\n")
            self.results_text.see(tk.END)
            # Force a GUI update even on error
            self.root.update_idletasks()

    def read_com(self):
        while self.running and self.com_port:
            try:
                if self.com_port.in_waiting > 0:
                    line = self.com_port.readline().decode('utf-8').strip()
                    if line:
                        self.com_data.append(line)
                        self.results_text.insert(tk.END, f"Ontvangen: {line}\n")
                        self.results_text.see(tk.END)
                        
                        # Update Treeview if Excel file is selected
                        
                        if excel_file:
                            try:
                                # Queue the GUI update using after() to ensure it runs on the main thread
                                self.root.after(0, self.update_gui_status, line)
                                
                                # Compare with Excel file and update status
                                df = pd.read_excel(excel_file)
                                if 'Status' not in df.columns:
                                    df['Status'] = ''
                                
                                # Check if item exists in Excel and update status
                                item_exists = False
                                matched_item = None
                                
                                for idx, row in df.iterrows():
                                    # Normalize Excel item
                                    excel_item = str(row.iloc[0]).lower().strip()
                                    
                                    # Try exact match first
                                    if excel_item == line.lower().strip():
                                        item_exists = True
                                        matched_item = excel_item
                                        break
                                    
                                    # Try partial match if exact match fails
                                    if not item_exists and line.lower().strip() in excel_item:
                                        item_exists = True
                                        matched_item = excel_item
                                        break
                                
                                if item_exists:
                                    # Update status for the matched item
                                    for idx, row in df.iterrows():
                                        if str(row.iloc[0]).lower().strip() == matched_item:
                                            df.at[idx, 'Status'] = 'OK'
                                            break
                                    
                                    # Update Treeview
                                    self.root.after(0, self.update_gui_status, matched_item)
                                    
                                    # Show success message
                                    self.results_text.insert(tk.END, f"Item '{line}' gematcht met '{matched_item}' in Excel en gemarkeerd als OK\n")
                                    
                                    # Check for consecutive scans
                                    if matched_item == self.last_scanned:
                                        self.consecutive_count += 1
                                        if self.consecutive_count == 3:
                                            self.consecutive_count = 0
                                            self.results_text.insert(tk.END, "\n*Easter Egg Alert*\n")
                                            self.results_text.insert(tk.END, "Je hebt hetzelfde item 3 keer achter elkaar gescand!\n")
                                            self.results_text.insert(tk.END, "Je moet dit item echt leuk vinden!\n")
                                            self.results_text.see(tk.END)
                                            messagebox.showinfo("Easter Egg!", "Wow! Je hebt hetzelfde item 3 keer achter elkaar gescand!\nJe moet dit item echt leuk vinden!")
                                    else:
                                        self.last_scanned = matched_item
                                        self.consecutive_count = 1
                                else:
                                    self.results_text.insert(tk.END, f"Waarschuwing: Item '{line}' niet gevonden in Excel bestand\n")
                                    self.results_text.see(tk.END)
                                
                                # Save updated Excel
                                output_file = os.path.splitext(excel_file)[0] + '_updated.xlsx'
                                df.to_excel(output_file, index=False)
                                
                                self.results_text.see(tk.END)
                            
                            except Exception as e:
                                self.results_text.insert(tk.END, f"Fout bij het bijwerken van status: {str(e)}\n")
                                self.results_text.see(tk.END)
                        
            except Exception as e:
                self.results_text.insert(tk.END, f"Fout bij het lezen van COM poort: {str(e)}\n")
                self.results_text.see(tk.END)
                break

            # Force a GUI update
            self.root.update_idletasks()

    # Removed duplicate update_scanned_tree (use ScannerTab.update_scanned_tree)
        """Update the Treeview with items from Excel file"""
        try:
            # Ensure Treeview is properly initialized
            if not hasattr(self, 'scanned_tree') or not self.scanned_tree.winfo_exists():
                raise Exception("Treeview niet correct geïnitialiseerd")
                
            # Clear existing items
            for item in self.scanned_tree.get_children():
                self.scanned_tree.delete(item)
            
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            # Add items to Treeview
            for idx, row in df.iterrows():
                item = str(row.iloc[0])
                # Handle NaN values by converting to empty string
                status = str(row['Status']) if 'Status' in df.columns else ''
                if status == 'nan':  # Convert pandas NaN to empty string
                    status = ''
                self.scanned_tree.insert('', 'end', values=(status, item))

                # Store in scanned_items dictionary
                self.scanned_items[item] = status

            self.results_text.insert(tk.END, "Treeview bijgewerkt met items uit Excel\n")
            self.results_text.see(tk.END)

        except Exception as e:
            self.results_text.insert(tk.END, f"Fout bij het bijwerken van Treeview: {str(e)}\n")
            self.results_text.see(tk.END)
            # Force a GUI update
            self.root.update_idletasks()

    def _compare_thread(self):
        """Thread method to compare scanned items with Excel"""
        try:
            

            if not excel_file:
                raise Exception("Selecteer eerst een Excel bestand")

            if not self.com_data:
                raise Exception("Geen data ontvangen van COM poort")

            self.results_text.insert(tk.END, "\nVergelijking gestart...\n")
            self.results_text.see(tk.END)

            # Get updated Excel data
            df = self.update_excel_with_scanned(excel_file)

            # Show results
            self.results_text.insert(tk.END, "\nVergelijkingsresultaten:\n")

            # Count items
            total_items = len(df)
            scanned_items = len(df[df['Status'] == 'OK'])

            self.results_text.insert(tk.END, f"Totaal aantal items in Excel: {total_items}\n")
            self.results_text.insert(tk.END, f"Items succesvol gescand: {scanned_items}\n")
            self.results_text.insert(tk.END, f"Items niet gescand: {total_items - scanned_items}\n")

            # Show items that weren't scanned
            if total_items > scanned_items:
                self.results_text.insert(tk.END, "\nItems die nog gescand moeten worden:\n")
                for idx, row in df[df['Status'] != 'OK'].iterrows():
                    self.results_text.insert(tk.END, f"- {row.iloc[0]}\n")
            else:
                # All items scanned successfully
                self.results_text.insert(tk.END, "\nAlle items zijn succesvol gescand!\n")
                messagebox.showinfo("Succes", "Alle items zijn succesvol gescand!")
                # Log success with Excel file name
                filename_no_ext = os.path.splitext(excel_file)[0]
                log_line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] '{filename_no_ext}' Is afgemeld op OPUS\n"
                with open("scan_log.txt", "a", encoding="utf-8") as logf:
                    logf.write(log_line)
                # Send log via email or accumulate for daily report
                email_mode = self.email_send_mode_var.get() if hasattr(self, 'email_send_mode_var') else 'per_scan'
                if email_mode == 'per_scan':
                    # Send email immediately after scan completed
                    self.send_log_via_email()
                elif email_mode == 'daily':
                    # Accumulate logs for daily report
                    self._accumulate_scan_log(log_line)
                else:
                    # Fallback to per-scan
                    self.send_log_via_email()

            self.results_text.insert(tk.END, f"\nExcel bestand opgeslagen als: {os.path.splitext(excel_file)[0]}_updated.xlsx\n")
            self.results_text.insert(tk.END, "\nVergelijking voltooid!\n")
            self.results_text.see(tk.END)

        except Exception as e:
            self.results_text.insert(tk.END, f"Fout: {str(e)}\n")
            self.results_text.see(tk.END)
        self.compare_button.config(state=tk.DISABLED)

    # Removed duplicate update_excel_with_scanned (use ScannerTab logic)
        """Update Excel file with scanned items"""
        try:
            # Read Excel file
            df = pd.read_excel(excel_file)

            # Get values from first column
            excel_values = df.iloc[:, 0].astype(str)

            # Get unique COM port values
            com_values = set(self.com_data)

            # Create a new 'Status' column if it doesn't exist
            if 'Status' not in df.columns:
                df['Status'] = ''

            # Update status for each scanned item
            for idx, row in df.iterrows():
                excel_item = str(row.iloc[0]).lower().strip()
                for com_value in com_values:
                    if excel_item == com_value.lower().strip():
                        df.at[idx, 'Status'] = 'OK'
                        break

            # Save updated Excel
            output_file = os.path.splitext(excel_file)[0] + '_updated.xlsx'
            df.to_excel(output_file, index=False)

            # Update Treeview with new status
            self.update_scanned_tree(output_file)

            return df

        except Exception as e:
            self.results_text.insert(tk.END, f"Fout bij het bijwerken van Excel: {str(e)}\n")
            self.results_text.see(tk.END)
            raise

def main():
    print("[DEBUG] main() is running. Creating COMPortComparator.")
    root = tk.Tk()
    app = COMPortComparator(root)
    print(f"[DEBUG] main() created app: {app}, type: {type(app)}, id: {id(app)}")
    def on_closing():
        # Save scan mode, scanner type, and email settings before closing
        try:
            if hasattr(app, 'file_scanner_frame') and hasattr(app.file_scanner_frame, 'save_scan_mode_to_config'):
                app.file_scanner_frame.save_scan_mode_to_config()
            if hasattr(app, 'save_scanner_type_to_config'):
                app.save_scanner_type_to_config()
            elif hasattr(app, 'scanner_type_var'):
                # Fallback: save from app
                update_config({'default_scanner_type': app.scanner_type_var.get()})
            # Save email settings
            if hasattr(app, 'save_email_settings_to_config'):
                app.save_email_settings_to_config()
        except Exception as e:
            print(f"Error saving scan mode, scanner type, or email settings on close: {e}")
        finally:
            # Always destroy the root window so the user can close the app
            if hasattr(app, 'root') and app.root:
                app.root.destroy()
    # Attach the close handler to app.root
    if hasattr(app, 'root') and app.root:
        app.root.protocol("WM_DELETE_WINDOW", on_closing)
        app.root.mainloop()
    else:
        if tk._default_root:
            tk._default_root.protocol("WM_DELETE_WINDOW", on_closing)
            tk._default_root.mainloop()


try:
    from build_info import get_build_number
except Exception as e:
    print("Error importing build_info or get_build_number:", e)
    get_build_number = lambda: "error"

def show_splash_and_start(main_callback):
    import tkinter as tk
    from tkinter import ttk
    import threading
    import time
    import sys
    try:
        print("[DEBUG] Starting splash screen...")
        splash = tk.Tk()
        splash.title("BarcodeMatch")
        splash.geometry("400x270")
        splash.overrideredirect(True)
        splash.configure(bg="white")

        # Center splash on screen
        splash.update_idletasks()
        width = 400
        height = 270
        x = (splash.winfo_screenwidth() // 2) - (width // 2)
        y = (splash.winfo_screenheight() // 2) - (height // 2)
        splash.geometry(f"{width}x{height}+{x}+{y}")

        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ico.png")
        if os.path.exists(logo_path):
            # Try to resize logo to 250x250 using PIL if available
            try:
                from PIL import Image, ImageTk
                pil_img = Image.open(logo_path).resize((350, 350), Image.LANCZOS)
                logo_img = ImageTk.PhotoImage(pil_img)
            except ImportError:
                # Fallback: use Tkinter's subsample if PIL is not available
                tmp_img = tk.PhotoImage(file=logo_path)
                w, h = tmp_img.width(), tmp_img.height()
                subsample_x = max(1, int(w / 350))
                subsample_y = max(1, int(h / 350))
                logo_img = tmp_img.subsample(subsample_x, subsample_y)
            width, height = 350, 350
            x = (splash.winfo_screenwidth() // 2) - (width // 2)
            y = (splash.winfo_screenheight() // 2) - (height // 2)
            splash.geometry(f"350x350+{x}+{y}")
            img_frame = tk.Frame(splash, width=350, height=350, bg="white")
            img_frame.pack()
            img_frame.pack_propagate(False)
            logo_label = tk.Label(img_frame, image=logo_img, bg="white", bd=0)
            logo_label.image = logo_img
            logo_label.place(x=0, y=0, relwidth=1, relheight=1)
            # Overlay build number at bottom right
            build_number = get_build_number()
            build_label = tk.Label(img_frame, text=f"Build: {build_number}", font=("Arial", 10), fg="#888888", bg="white")
            build_label.place(relx=1.0, rely=1.0, anchor="se", x=-8, y=-8)
        else:
            # Fallback: just show build number and text
            build_number = get_build_number()
            build_label = tk.Label(splash, text=f"Build: {build_number}", font=("Arial", 10), fg="#888888", bg="white")
            build_label.pack(pady=(40, 10))
            logo_label = tk.Label(splash, text="BarcodeMatch", font=("Arial", 28, "bold"), bg="white")
            logo_label.pack(pady=(10, 20))



        def close_splash_and_start_main():
            splash.destroy()
            main_callback()

        # Use after() instead of threading to avoid Tkinter threading issues
        splash.after(2000, close_splash_and_start_main)
        splash.mainloop()
    except Exception as e:
        print("[ERROR] Exception in splash screen:", e)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    def _launch_main():
        main()
    show_splash_and_start(_launch_main)
