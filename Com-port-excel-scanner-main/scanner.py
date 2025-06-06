import os
import pandas as pd
import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import keyboard  # For global keyboard hook
import smtplib
from email.mime.text import MIMEText

# --- Import FileScannerGUI and dependencies from filemaker_gui.py ---
import json
from datetime import datetime

class Tooltip:
    """
    A simple tooltip that appears when hovering over a widget
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind('<Enter>', self.showtip)
        self.widget.bind('<Leave>', self.hidetip)

    def showtip(self, event=None):
        if self.tipwindow or not self.text:
            return
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

class FileScannerFrame(ttk.Frame):
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
        self.CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self.load_config()
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.columnconfigure(0, weight=1)
        self.directory_frame = ttk.LabelFrame(self.main_frame, text="Select Directory", padding="5")
        self.directory_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        dir_entry = ttk.Entry(self.directory_frame, textvariable=self.directory_var, width=50)
        dir_entry.grid(row=0, column=0, padx=5)
        dir_btn = ttk.Button(self.directory_frame, text="Browse", command=self.browse_directory)
        dir_btn.grid(row=0, column=1, padx=5)
        self.dir_btn_tooltip = Tooltip(dir_btn, "Selecteer de maatkast map")
        self.base_dir_frame = ttk.LabelFrame(self.main_frame, text="Base Directory", padding="5")
        self.base_dir_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        base_entry = ttk.Entry(self.base_dir_frame, textvariable=self.base_dir_var, width=50)
        base_entry.grid(row=0, column=0, padx=5)
        base_btn = ttk.Button(self.base_dir_frame, text="Browse Base", command=self.browse_base_directory)
        base_btn.grid(row=0, column=1, padx=5)
        self.base_btn_tooltip = Tooltip(base_btn, "Browse for base directory")
        self.base_dir_label = ttk.Label(self.base_dir_frame, text="")
        self.base_dir_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5)
        self.default_base_label = ttk.Label(self.base_dir_frame, text="")
        self.default_base_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5)
        save_default_btn = ttk.Button(self.base_dir_frame, text="Set as Default", command=self.save_config)
        save_default_btn.grid(row=2, column=2, padx=5)
        self.save_default_btn_tooltip = Tooltip(save_default_btn, "Sla deze map op als standaard basisdirectory")
        if isinstance(self.root, tk.Tk):
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.progress_frame = ttk.Frame(self.main_frame, padding="5")
        self.progress_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        self.progress_frame.columnconfigure(0, weight=1)
        self.progress_frame.columnconfigure(1, weight=0)
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100)
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.scan_button = ttk.Button(self.progress_frame, text="Scan Directory", command=self.start_scan)
        self.scan_button.grid(row=0, column=1, padx=(10, 0))
        self.root.after(100, lambda: self.setup_scan_tooltip())
        self.status_label = ttk.Label(self.progress_frame, text="")
        self.status_label.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.results_frame = ttk.LabelFrame(self.main_frame, text="Results", padding="5")
        self.results_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.S))
        self.results_text = tk.Text(self.results_frame, height=15, width=80)
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.S))
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)
        self.main_frame.rowconfigure(3, weight=1)

    def setup_scan_tooltip(self):
        if hasattr(self, 'scan_button'):
            self.scan_button_tooltip = Tooltip(self.scan_button, "Start scanning the selected directory for .hop and .hops files")

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
                        if hasattr(self, 'default_base_label'):
                            self.default_base_label.config(text=f"(Default directory loaded from config)")
        except Exception as e:
            print(f"Error loading config: {str(e)}")

    def save_config(self):
        base_dir = self.base_dir_var.get()
        if base_dir:
            try:
                config = {'default_base_dir': base_dir}
                with open(self.CONFIG_FILE, 'w') as f:
                    json.dump(config, f, indent=4)
                if hasattr(self, 'default_base_label'):
                    self.default_base_label.config(text=f"(Default directory saved to config)")
            except Exception as e:
                print(f"Error saving config: {str(e)}")

    def on_closing(self):
        self.save_config()
        self.root.destroy()

    def browse_directory(self):
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
        directory = self.directory_var.get()
        if not directory:
            messagebox.showwarning("Missing Directory", "Please select a directory to scan.")
            return
        self.scan_button.config(state=tk.DISABLED)
        self.scanning = True
        threading.Thread(target=self._scan_thread, args=(directory,), daemon=True).start()

    def _scan_thread(self, directory):
        try:
            files = self.scan_directory(directory)
            self.files = files
            self._update_gui(directory, len(files))
        except Exception as e:
            self.root.after(0, self._show_error, str(e))
            return
        self.results_text.see(tk.END)
        self.scanning = False
        self.scan_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_label.config(text="")
        self._create_excel(directory)

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
                        self.update_progress(self.processed_files, self.total_files)
                    except Exception as e:
                        self.results_text.insert(tk.END, f"Error processing {filename}: {str(e)}\n")
                        self.results_text.see(tk.END)
        return files

    def update_progress(self, current, total):
        if total > 0:
            self.progress_var.set((current / total) * 100)
            self.status_label.config(text=f"Scanning... {current}/{total} files processed")
            self.root.update()

    def _update_gui(self, directory, file_count):
        self.results_text.insert(tk.END, f"\nScan complete! Found {file_count} files\n")
        self.results_text.insert(tk.END, "\nFiles found:\n")
        for file_info in self.files:
            self.results_text.insert(tk.END, f"- {file_info['Relative Path']}\n")
        self.results_text.see(tk.END)

    def _show_error(self, error_msg):
        messagebox.showerror("Error", error_msg)

    def _create_excel(self, directory):
        if not self.files:
            self.results_text.insert(tk.END, "No files to save to Excel.\n")
            return
        df = pd.DataFrame(self.files)
        # Use the last part of the selected directory as the file name
        folder_name = os.path.basename(os.path.normpath(directory))
        excel_path = os.path.join(directory, f"{folder_name}_scan.xlsx")
        try:
            df.to_excel(excel_path, index=False)
            self.results_text.insert(tk.END, f"\nExcel file saved: {excel_path}\n")
        except Exception as e:
            self.results_text.insert(tk.END, f"Error saving Excel: {str(e)}\n")
        self.results_text.see(tk.END)


class COMPortComparator:
    def __init__(self, root):
        # Default sender and receiver, can be changed
        self.mail_sender = "Rob_vanlooy@hotmail.com"
        self.mail_receiver = "Rob_vanlooy@hotmail.com"
        self.smtp_server = "smtp.office365.com"
        self.smtp_port = 587
        self.smtp_user = self.mail_sender
        self.smtp_password = "YOUR_PASSWORD_HERE"  # Replace or prompt securely

        self.root = root
        self.root.title("COM Port Comparator")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)

        # --- Tabs ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # --- Initialize scanned_items dictionary ---
        self.scanned_items = {}

        # --- Start USB keyboard scanner background thread ---
        self.keyboard_scanner_enabled = False
        self.keyboard_thread = threading.Thread(target=self.keyboard_scanner_hook, daemon=True)
        self.keyboard_thread.start()

        # Add Importeren tab with embedded FileScannerFrame
        self.importeren_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.importeren_tab, text="Importeren")
        self.file_scanner_frame = FileScannerFrame(self.importeren_tab)
        self.file_scanner_frame.pack(fill=tk.BOTH, expand=True)

        # --- Scanner Tab ---
        self.scanner_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.scanner_tab, text="Scanner")

        # --- Email Tab ---
        self.email_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.email_tab, text="Email")

        # Move all main widgets to scanner_tab instead of root
        self.main_frame = ttk.Frame(self.scanner_tab, padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.scanner_tab.rowconfigure(0, weight=1)
        self.scanner_tab.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(2, weight=1)

        # --- Scanner Tab Widgets ---
        # Scanner type and Excel file selection
        self.scanner_excel_frame = ttk.Frame(self.main_frame, padding="5")
        self.scanner_excel_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.scanner_excel_frame.columnconfigure(0, weight=1)
        self.scanner_excel_frame.columnconfigure(1, weight=1)

        # Scanner type
        self.scanner_type_var = tk.StringVar(value="COM")
        scanner_type_frame = ttk.LabelFrame(self.scanner_excel_frame, text="Scanner Type", padding="5")
        scanner_type_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.com_radio = ttk.Radiobutton(scanner_type_frame, text="COM Port Scanner", variable=self.scanner_type_var, value="COM", command=self.update_scanner_type)
        self.com_radio.grid(row=0, column=0, padx=5, sticky=tk.W)
        self.usb_radio = ttk.Radiobutton(scanner_type_frame, text="USB Keyboard Scanner", variable=self.scanner_type_var, value="USB", command=self.update_scanner_type)
        self.usb_radio.grid(row=0, column=1, padx=5, sticky=tk.W)

        # Excel file selection
        self.excel_frame = ttk.LabelFrame(self.scanner_excel_frame, text="Excel Bestand", padding="5")
        self.excel_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.excel_frame.columnconfigure(0, weight=1)
        self.excel_frame.columnconfigure(1, weight=0)
        self.excel_var = tk.StringVar()
        excel_entry = ttk.Entry(self.excel_frame, textvariable=self.excel_var)
        excel_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(5, 0))
        ttk.Button(self.excel_frame, text="Excel Selecteren", command=self.browse_excel).grid(row=0, column=1, padx=(5, 5))

        # COM Port selection
        self.com_frame = ttk.LabelFrame(self.main_frame, text="COM Poort", padding="5")
        self.com_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.com_frame.columnconfigure(0, weight=0)
        self.com_frame.columnconfigure(1, weight=1)
        self.com_frame.columnconfigure(2, weight=0)
        self.com_port_var = tk.StringVar()
        ttk.Label(self.com_frame, text="Selecteer COM Poort:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.com_port_combo = ttk.Combobox(self.com_frame, textvariable=self.com_port_var)
        self.com_port_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(self.com_frame, text="Poorten Vernieuwen", command=self.refresh_ports).grid(row=0, column=2, padx=5)
        ttk.Label(self.com_frame, text="Baud Rate:").grid(row=1, column=0, padx=5, sticky=tk.W)
        self.baud_rate_var = tk.StringVar(value="9600")
        ttk.Entry(self.com_frame, textvariable=self.baud_rate_var).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 5))

        # USB Keyboard scanner entry (hidden by default)
        self.usb_frame = ttk.LabelFrame(self.main_frame, text="USB Keyboard Scanner", padding="5")
        self.usb_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.usb_frame.columnconfigure(0, weight=1)
        self.usb_scan_var = tk.StringVar()
        self.usb_entry = ttk.Entry(self.usb_frame, textvariable=self.usb_scan_var)
        self.usb_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        self.usb_entry.bind('<Return>', self.process_usb_scan)
        self.usb_frame.grid_remove()  # Hide initially

        # Results frame
        self.results_frame = ttk.LabelFrame(self.main_frame, text="Resultaten", padding="5")
        self.results_frame.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)
        self.results_frame.rowconfigure(1, weight=0)

        # Create a notebook (tabbed interface) for results
        self.results_notebook = ttk.Notebook(self.results_frame)
        self.results_notebook.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        # Treeview for scanned items
        self.scanned_frame = ttk.Frame(self.results_notebook)
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
        self.results_notebook.add(self.scanned_frame, text='Gescande Items')

        # Text area for messages
        self.results_text = tk.Text(self.results_frame, height=10)
        self.results_text.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

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
        self.progress_frame.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(self.progress_frame, text="Niet verbonden")
        self.status_label.grid(row=0, column=0, pady=(5, 0), sticky=tk.W)

        # --- Email Config Widgets ---
        self.email_frame = ttk.LabelFrame(self.email_tab, text="E-mail Configuratie", padding="10")
        self.email_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Sender
        ttk.Label(self.email_frame, text="Afzender:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.sender_var = tk.StringVar(value=self.mail_sender)
        sender_entry = ttk.Entry(self.email_frame, textvariable=self.sender_var, width=35)
        sender_entry.grid(row=0, column=1, sticky=tk.W, pady=2)
        # Receiver
        ttk.Label(self.email_frame, text="Ontvanger:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.receiver_var = tk.StringVar(value=self.mail_receiver)
        receiver_entry = ttk.Entry(self.email_frame, textvariable=self.receiver_var, width=35)
        receiver_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        # SMTP Server
        ttk.Label(self.email_frame, text="SMTP server:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.smtp_var = tk.StringVar(value=self.smtp_server)
        smtp_entry = ttk.Entry(self.email_frame, textvariable=self.smtp_var, width=35)
        smtp_entry.grid(row=2, column=1, sticky=tk.W, pady=2)
        # SMTP Port
        ttk.Label(self.email_frame, text="SMTP poort:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.port_var = tk.StringVar(value=str(self.smtp_port))
        port_entry = ttk.Entry(self.email_frame, textvariable=self.port_var, width=10)
        port_entry.grid(row=3, column=1, sticky=tk.W, pady=2)
        # SMTP User
        ttk.Label(self.email_frame, text="SMTP gebruiker:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.user_var = tk.StringVar(value=self.smtp_user)
        user_entry = ttk.Entry(self.email_frame, textvariable=self.user_var, width=35)
        user_entry.grid(row=4, column=1, sticky=tk.W, pady=2)
        # SMTP Password
        ttk.Label(self.email_frame, text="SMTP wachtwoord:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.password_var = tk.StringVar(value=self.smtp_password)
        password_entry = ttk.Entry(self.email_frame, textvariable=self.password_var, show="*", width=35)
        password_entry.grid(row=5, column=1, sticky=tk.W, pady=2)

        # Update config on entry change
        self.sender_var.trace_add('write', lambda *a: self._update_email_config())
        self.receiver_var.trace_add('write', lambda *a: self._update_email_config())
        self.smtp_var.trace_add('write', lambda *a: self._update_email_config())
        self.port_var.trace_add('write', lambda *a: self._update_email_config())
        self.user_var.trace_add('write', lambda *a: self._update_email_config())
        self.password_var.trace_add('write', lambda *a: self._update_email_config())

        # Test email button
        test_btn = ttk.Button(self.email_frame, text="Verzend testmail", command=self._send_test_email)
        test_btn.grid(row=6, column=0, columnspan=2, pady=10)

    def _update_email_config(self):
        self.mail_sender = self.sender_var.get()
        self.mail_receiver = self.receiver_var.get()
        self.smtp_server = self.smtp_var.get()
        try:
            self.smtp_port = int(self.port_var.get())
        except ValueError:
            self.smtp_port = 587
        self.smtp_user = self.user_var.get()
        self.smtp_password = self.password_var.get()

    def _send_test_email(self):
        try:
            self.send_log_via_email(subject="Testmail OPUS Scan Log")
            messagebox.showinfo("Testmail", "Testmail succesvol verzonden!")
        except Exception as e:
            messagebox.showerror("Fout bij testmail", str(e))

    def send_log_via_email(self, subject="OPUS Scan Log"):
        """Send the scan_log.txt contents as an email body."""
        import traceback
        try:
            with open("scan_log.txt", "r", encoding="utf-8") as logf:
                log_content = logf.read()
            msg = MIMEText(log_content)
            msg["Subject"] = subject
            msg["From"] = self.mail_sender
            msg["To"] = self.mail_receiver

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.mail_sender, [self.mail_receiver], msg.as_string())
            messagebox.showinfo("E-mail verzonden", "Scan log succesvol verzonden!")
            self.results_text.insert(tk.END, "E-mail succesvol verzonden.\n")
            self.results_text.see(tk.END)
        except Exception as e:
            tb = traceback.format_exc()
            messagebox.showerror("Fout bij verzenden van e-mail", f"Er is een fout opgetreden bij het verzenden van de e-mail:\n{str(e)}")
            self.results_text.insert(tk.END, f"Fout bij verzenden van e-mail: {str(e)}\n{tb}\n")
            self.results_text.see(tk.END)

        self.results_notebook.add(self.scanned_frame, text='Gescande Items')
        
        # Configure grid weights for proper expansion
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(2, weight=1)  # Results frame row
        
        self.results_frame.rowconfigure(0, weight=1)  # Notebook row
        self.results_frame.columnconfigure(0, weight=1)  # Notebook column
        
        self.scanned_frame.columnconfigure(0, weight=1)  # Treeview column
        self.scanned_frame.rowconfigure(0, weight=1)  # Treeview row (expand)
        

        
        # Configure text area for messages
        self.results_text.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.results_frame.rowconfigure(1, weight=1)  # Text area row
        self.results_frame.columnconfigure(0, weight=1)  # Text area column
        
        # Configure notebook for proper expansion
        self.results_notebook.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.results_notebook.columnconfigure(0, weight=1)
        self.results_notebook.rowconfigure(0, weight=1)
        
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
        
    def browse_excel(self):
        """Handle Excel file selection and update Treeview"""
        excel_file = filedialog.askopenfilename(
            filetypes=[("Excel bestanden", "*.xlsx")],
            title="Selecteer Excel Bestand"
        )
        if excel_file:
            self.excel_var.set(excel_file)
            self.results_text.insert(tk.END, f"Excel bestand geselecteerd: {excel_file}\n")
            self.results_text.see(tk.END)
            
            # Update Treeview with all items from Excel
            try:
                self.update_scanned_tree(excel_file)
                # Check if there's an updated version of the file
                updated_file = os.path.splitext(excel_file)[0] + '_updated.xlsx'
                if os.path.exists(updated_file):
                    try:
                        self.update_scanned_tree(updated_file)
                        self.results_text.insert(tk.END, f"Bestaande scanresultaten geladen uit: {updated_file}\n")
                        self.results_text.see(tk.END)
                    except Exception as e:
                        self.results_text.insert(tk.END, f"Fout bij het laden van bijgewerkt Excel bestand: {str(e)}\n")
                        self.results_text.see(tk.END)
            except Exception as e:
                self.results_text.insert(tk.END, f"Fout bij het laden van Excel bestand: {str(e)}\n")
                self.results_text.see(tk.END)
    
    def refresh_ports(self):
        """Refresh the list of available COM ports"""
        ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in ports]
        self.com_port_combo['values'] = port_names
        if port_names:
            self.com_port_var.set(port_names[0])

    def show_tree_menu(self, event):
        """Show the right-click menu for Treeview"""
        # Get the selected item
        self.selected_item = self.scanned_tree.identify_row(event.y)
        if self.selected_item:
            # Position the menu at the mouse cursor
            self.tree_menu.post(event.x_root, event.y_root)

    def set_status_ok(self):
        """Set the selected item's status to OK"""
        if self.selected_item:
            status = self.scanned_tree.set(self.selected_item, 'Status')
            if status != 'OK':
                # Get the item text
                item = self.scanned_tree.set(self.selected_item, 'Item')
                
                # Update Treeview
                self.scanned_tree.set(self.selected_item, 'Status', 'OK')
                
                # Update dictionary
                self.scanned_items[item] = 'OK'
                
                # Update Excel file if one is selected
                excel_file = self.excel_var.get()
                if excel_file:
                    try:
                        # Read Excel file
                        df = pd.read_excel(excel_file)
                        
                        # Find the row with this item
                        for idx, row in df.iterrows():
                            if str(row.iloc[0]).strip() == item.strip():
                                df.at[idx, 'Status'] = 'OK'
                                break
                        
                        # Save updated Excel
                        df.to_excel(excel_file, index=False)
                        
                        # Also update the _updated.xlsx file if it exists
                        updated_file = os.path.splitext(excel_file)[0] + '_updated.xlsx'
                        if os.path.exists(updated_file):
                            df.to_excel(updated_file, index=False)
                        
                    except Exception as e:
                        self.results_text.insert(tk.END, f"Fout bij het bijwerken van Excel bestand: {str(e)}\n")
                        self.results_text.see(tk.END)
                
                self.results_text.insert(tk.END, f"Status handmatig op OK gezet voor: {item}\n")
                self.results_text.see(tk.END)
                
                # Check if all items are now OK
                all_ok = True
                for item_id in self.scanned_tree.get_children():
                    if self.scanned_tree.set(item_id, 'Status') != 'OK':
                        all_ok = False
                        break
                
                if all_ok:
                    self.results_text.insert(tk.END, "\nAlle items zijn succesvol gescand!\n")
                    self.results_text.see(tk.END)
                    messagebox.showinfo("Succes", "Alle items zijn succesvol gescand!")
                    # Log success with Excel file name
                    excel_file = self.excel_var.get()
                    filename_no_ext = os.path.splitext(excel_file)[0]
                    with open("scan_log.txt", "a", encoding="utf-8") as logf:
                        logf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] '{filename_no_ext}' Is afgemeld op OPUS\n")
                    # Send log via email
                    self.send_log_via_email()

    def clear_status(self):
        """Clear the selected item's status"""
        if self.selected_item:
            # Get the item text
            item = self.scanned_tree.set(self.selected_item, 'Item')
            
            # Update Treeview
            self.scanned_tree.set(self.selected_item, 'Status', '')
            
            # Update dictionary
            self.scanned_items[item] = ''
            
            # Update Excel file if one is selected
            excel_file = self.excel_var.get()
            if excel_file:
                try:
                    # Always work with the latest updated file if it exists
                    updated_file = os.path.splitext(excel_file)[0] + '_updated.xlsx'
                    df = None
                    if os.path.exists(updated_file):
                        df = pd.read_excel(updated_file)
                    else:
                        df = pd.read_excel(excel_file)
                    # Update status in DataFrame
                    for idx, row in df.iterrows():
                        excel_item = str(row.iloc[0])
                        if excel_item == item:
                            df.at[idx, 'Status'] = ''
                            break
                    # Save updated Excel
                    df.to_excel(updated_file, index=False)
                    self.results_text.insert(tk.END, f"Status gewist in Excel voor: {item}\n")
                    self.results_text.see(tk.END)
                except Exception as e:
                    self.results_text.insert(tk.END, f"Fout bij het bijwerken van status: {str(e)}\n")
                    self.results_text.see(tk.END)
            
            self.results_text.insert(tk.END, f"Status handmatig gewist voor: {item}\n")
            self.results_text.see(tk.END)
            
            # Check if all items are now OK
            all_ok = True
            for item_id in self.scanned_tree.get_children():
                if self.scanned_tree.set(item_id, 'Status') != 'OK':
                    all_ok = False
                    break
            
            if all_ok:
                self.results_text.insert(tk.END, "\nAlle items zijn succesvol gescand!\n")
            self.usb_scan_var.set("")

    def process_usb_scan(self, event=None):
        """Handle Enter key in USB entry: process the scanned value."""
        scan_value = self.usb_scan_var.get().strip()
        if scan_value:
            self.handle_scanned_value(scan_value)
            self.usb_scan_var.set("")

    def keyboard_scanner_hook(self):
        """Background hook to detect fast keyboard input ending with Enter as a scan."""
        buffer = []
        last_time = None
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


    def handle_scanned_value(self, value):
        # Exclude specific codes from being shown in the status window (read from JSON)
        if not hasattr(self, 'excluded_codes'):
            try:
                import json
                with open(os.path.join(os.path.dirname(__file__), 'filtered_scans.json'), 'r', encoding='utf-8') as f:
                    self.excluded_codes = set(json.load(f))
            except Exception as e:
                self.excluded_codes = set()
                self.results_text.insert(tk.END, f"Fout bij het laden van filtered_scans.json: {str(e)}\n")
                self.results_text.see(tk.END)
        if value in self.excluded_codes:
            return
        # This method mimics the logic in read_com for a single scan value
        self.results_text.insert(tk.END, f"Ontvangen: {value}\n")
        self.results_text.see(tk.END)
        excel_file = self.excel_var.get()
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
    
    def update_gui_status(self, matched_item):
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
                        excel_file = self.excel_var.get()
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

    def update_scanned_tree(self, excel_file):
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
            excel_file = self.excel_var.get()

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
                with open("scan_log.txt", "a", encoding="utf-8") as logf:
                    logf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] '{filename_no_ext}' Is afgemeld op OPUS\n")
                # Send log via email
                self.send_log_via_email()

            self.results_text.insert(tk.END, f"\nExcel bestand opgeslagen als: {os.path.splitext(excel_file)[0]}_updated.xlsx\n")
            self.results_text.insert(tk.END, "\nVergelijking voltooid!\n")
            self.results_text.see(tk.END)

        except Exception as e:
            self.results_text.insert(tk.END, f"Fout: {str(e)}\n")
            self.results_text.see(tk.END)
        self.compare_button.config(state=tk.DISABLED)

    def update_excel_with_scanned(self, excel_file):
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
    root = tk.Tk()
    app = COMPortComparator(root)
    root.mainloop()

if __name__ == "__main__":
    main()
