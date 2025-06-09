import os

import time
print(f'[DIAG] scanner_panel.py import start {time.time()}')
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
from config_utils import update_config, get_config_path
import threading
import pandas as pd
import serial
import serial.tools.list_ports
import time
import keyboard  # For global keyboard hook



    # --- Scanner Panel Content ---
    # (rest of your widget setup code)

class ScannerPanel(ttk.Frame):
    def __init__(self, parent, main_app):
        print(f'[DIAG] ScannerPanel __init__ start {time.time()}')
    def get_log_state(self):
        try:
            return self.results_text.get("1.0", "end-1c")
        except Exception:
            return ""

    def set_log_state(self, log_content):
        try:
            self.results_text.delete("1.0", "end")
            if log_content:
                self.results_text.insert("end", log_content)
        except Exception:
            pass

    def build_tab(self):
        
        # --- Scanner Panel Content ---
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=0)  # Top row: Scanner Type + Excel
        self.main_frame.rowconfigure(1, weight=0)  # COM/USB row
        self.main_frame.rowconfigure(2, weight=1)  # Results row (expand)
        self.main_frame.grid_propagate(False)

        # --- Initialize config variables and StringVars ---
        config_file = get_config_path()
        default_scanner_type = "COM"
        default_base_dir = "C:/OPUS"
        default_scan_mode = "OPUS"
        default_excel_file = ""
        default_com_port = ""
        default_baud_rate = "9600"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                try:
                    config = json.load(f)
                    default_scanner_type = config.get('default_scanner_type', 'COM')
                    default_base_dir = config.get('default_base_dir', 'C:/OPUS')
                    default_scan_mode = config.get('default_scan_mode', 'OPUS')
                    default_excel_file = ''
                    default_com_port = config.get('default_com_port', '')
                    default_baud_rate = config.get('default_baud_rate', '9600')
                except Exception:
                    pass
        self.scanner_type_var = tk.StringVar(value=default_scanner_type)
        self.scanner_type_var.trace_add('write', lambda *args: self.save_scanner_type_to_config())
        self.base_dir_var = tk.StringVar(value=default_base_dir)
        self.base_dir_var.trace_add('write', lambda *args: self.save_base_dir_to_config())
        self.scan_mode_var = tk.StringVar(value=default_scan_mode)
        self.scan_mode_var.trace_add('write', lambda *args: self.save_scan_mode_to_config())
        self.excel_var = tk.StringVar(value=default_excel_file)  # Do not trace or save to config
        self.com_port_var = tk.StringVar(value=default_com_port)
        self.main_frame.rowconfigure(0, weight=0)  # Top row: Scanner Type + Excel
        self.main_frame.rowconfigure(1, weight=0)  # COM/USB row
        self.main_frame.rowconfigure(2, weight=1)  # Results row (expand)
        self.main_frame.grid_propagate(False)

        # --- Initialize config variables and StringVars ---
        config_file = get_config_path()
        default_scanner_type = "COM"
        default_base_dir = "C:/OPUS"
        default_scan_mode = "OPUS"
        default_excel_file = ""
        default_com_port = ""
        default_baud_rate = "9600"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                try:
                    config = json.load(f)
                    default_scanner_type = config.get('default_scanner_type', 'COM')
                    default_base_dir = config.get('default_base_dir', 'C:/OPUS')
                    default_scan_mode = config.get('default_scan_mode', 'OPUS')
                    default_excel_file = ''
                    default_com_port = config.get('default_com_port', '')
                    default_baud_rate = config.get('default_baud_rate', '9600')
                except Exception:
                    pass
        self.scanner_type_var = tk.StringVar(value=default_scanner_type)
        self.scanner_type_var.trace_add('write', lambda *args: self.save_scanner_type_to_config())
        self.base_dir_var = tk.StringVar(value=default_base_dir)
        self.base_dir_var.trace_add('write', lambda *args: self.save_base_dir_to_config())
        self.scan_mode_var = tk.StringVar(value=default_scan_mode)
        self.scan_mode_var.trace_add('write', lambda *args: self.save_scan_mode_to_config())
        self.excel_var = tk.StringVar(value=default_excel_file)  # Do not trace or save to config
        self.com_port_var = tk.StringVar(value=default_com_port)
        self.com_port_var.trace_add('write', lambda *args: self.save_com_port_to_config())
        self.baud_rate_var = tk.StringVar(value=default_baud_rate)
        self.baud_rate_var.trace_add('write', lambda *args: self.save_baud_rate_to_config())
        self.baud_rate_var = tk.StringVar(value=default_baud_rate)
        self.baud_rate_var.trace_add('write', lambda *args: self.save_baud_rate_to_config())

        # --- State restoration and diagnostics (after config vars are set) ---
        try:
            if hasattr(self, 'main_app') and hasattr(self, 'excel_var'):
                excel_file = getattr(self.main_app, 'scanner_excel_file', None)
                treeview_state = getattr(self.main_app, 'scanner_treeview_state', None)
                log_state = getattr(self.main_app, 'scanner_log_state', None)
                
                if excel_file and self.excel_var.get() == excel_file:
                    if treeview_state:
                        try:
                            self.set_treeview_state(treeview_state)
                            
                        except Exception as e:
                            pass
                    if log_state:
                        try:
                            self.set_log_state(log_state)
                            
                        except Exception as e:
                            pass
        except Exception as e:
            pass
        # --- Top row: Scanner Type (left) and Excel file (right) ---
        self.main_frame.columnconfigure(0, weight=1, minsize=200)
        self.main_frame.columnconfigure(1, weight=1, minsize=200)
        self.main_frame.rowconfigure(1, weight=0)

        # Scanner Type selection (left)
        self.scanner_type_frame = ttk.LabelFrame(self.main_frame, text="Scanner Type", padding="5")
        self.scanner_type_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.scanner_type_frame.columnconfigure(0, weight=0)
        self.scanner_type_frame.columnconfigure(1, weight=0)
        self.scanner_type_frame.columnconfigure(2, weight=1)
        self.com_radio = ttk.Radiobutton(self.scanner_type_frame, text="COM-poort scanner", variable=self.scanner_type_var, value="COM", command=self.update_scanner_type)
        self.com_radio.grid(row=0, column=0, sticky="w", padx=(5, 10))
        self.usb_radio = ttk.Radiobutton(self.scanner_type_frame, text="USB-toetsenbord scanner", variable=self.scanner_type_var, value="USB", command=self.update_scanner_type)
        self.usb_radio.grid(row=0, column=1, sticky="w", padx=5)

        # Excel file selection (right)
        self.excel_frame = ttk.LabelFrame(self.main_frame, text="Excel Bestand", padding="5")
        self.excel_frame.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        self.excel_frame.columnconfigure(0, weight=1)
        self.excel_frame.columnconfigure(1, weight=0)
        excel_entry = ttk.Entry(self.excel_frame, textvariable=self.excel_var)
        excel_entry.grid(row=0, column=0, sticky="ew", padx=(5, 0))
        ttk.Button(self.excel_frame, text="Excel Selecteren", command=self._browse_excel).grid(row=0, column=1, padx=(5, 5))

        # --- Scanner mode container (for toggling COM/USB) ---
        self.scanner_mode_container = ttk.Frame(self.main_frame)
        self.scanner_mode_container.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.scanner_mode_container.columnconfigure(0, weight=1)

        # --- COM section ---
        self.com_frame = ttk.LabelFrame(self.scanner_mode_container, text="COM Poort", padding="5", borderwidth=2, relief="solid")
        self.com_frame.columnconfigure(0, weight=0)
        self.com_frame.columnconfigure(1, weight=1)
        self.com_frame.columnconfigure(2, weight=0)
        self.com_frame.columnconfigure(3, weight=0)
        self.com_frame.columnconfigure(4, weight=1)
        ttk.Label(self.com_frame, text="Selecteer COM Poort:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.com_port_combo = ttk.Combobox(self.com_frame, textvariable=self.com_port_var)
        self.com_port_combo.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        ttk.Button(self.com_frame, text="Poorten Vernieuwen", command=self.refresh_ports).grid(row=0, column=2, padx=5)
        ttk.Label(self.com_frame, text="Baud Rate:").grid(row=1, column=0, padx=5, sticky=tk.W)
        ttk.Entry(self.com_frame, textvariable=self.baud_rate_var).grid(row=1, column=1, sticky="ew", padx=(0, 5))
        self.connect_button = ttk.Button(self.com_frame, text="Verbinden", command=self.connect_com_port)
        self.connect_button.grid(row=1, column=2, padx=5, sticky="ew")
        self.com_status_label = ttk.Label(self.com_frame, text="Status: Niet verbonden", foreground="red")
        self.com_status_label.grid(row=2, column=0, columnspan=3, sticky="w", padx=5, pady=(5,0))

        # --- USB section ---
        self.usb_frame = ttk.LabelFrame(self.scanner_mode_container, text="USB Keyboard Scanner", padding="5", borderwidth=2, relief="solid")
        self.usb_frame.columnconfigure(0, weight=1)
        self.usb_scan_var = tk.StringVar()
        self.usb_entry = ttk.Entry(self.usb_frame, textvariable=self.usb_scan_var)
        self.usb_entry.grid(row=0, column=0, sticky="ew", padx=5)
        self.usb_entry.bind('<Return>', self.process_usb_scan)

        # --- Show/hide COM and USB frames based on scanner type ---
        self.update_scanner_type()

        # --- Results section ---
        self.results_frame = ttk.LabelFrame(self.main_frame, text="Resultaten", padding="5")
        self.results_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=3)
        self.results_frame.rowconfigure(1, weight=1)
        self.scanned_tree = ttk.Treeview(self.results_frame, columns=('Status', 'Item'), show='headings')
        self.scanned_tree.heading('Status', text='Status')
        self.scanned_tree.heading('Item', text='Item')
        self.scanned_tree.column('Status', width=100, stretch=True, anchor='e')
        # Context menu for treeview
        self.tree_menu = tk.Menu(self.scanned_tree, tearoff=0)
        self.tree_menu.add_command(label="Status op OK zetten", command=self.set_status_ok)
        self.tree_menu.add_command(label="Status wissen", command=self.clear_status)
        self.scanned_tree.bind("<Button-3>", self.show_tree_menu)  # Windows/Linux right-click
        self.scanned_tree.bind("<Button-2>", self.show_tree_menu)  # Mac right-click
        self.tree_scroll = ttk.Scrollbar(self.results_frame, orient='vertical', command=self.scanned_tree.yview)
        self.scanned_tree.configure(yscrollcommand=self.tree_scroll.set)
        self.scanned_tree.grid(row=0, column=0, sticky="nsew")
        self.tree_scroll.grid(row=0, column=1, sticky="ns")

        self.results_text = tk.Text(self.results_frame, height=8)
        self.results_text.grid(row=1, column=0, sticky="nsew", columnspan=2)


        print(f"[DIAG] Before restore: hasattr(scanned_tree)={hasattr(self, 'scanned_tree')}, hasattr(results_text)={hasattr(self, 'results_text')}")
        print("===TEST B===")
        if not hasattr(self, 'scanned_tree') or not hasattr(self, 'results_text'):
            print(f"[DIAG] self.__dict__ keys: {list(self.__dict__.keys())}")

        # Restore treeview and log viewer state if available and Excel file matches
        try:
            if hasattr(self, 'main_app') and hasattr(self, 'excel_var'):
                excel_file = getattr(self.main_app, 'scanner_excel_file', None)
                treeview_state = getattr(self.main_app, 'scanner_treeview_state', None)
                log_state = getattr(self.main_app, 'scanner_log_state', None)
                print(f"[DIAG] build_tab restore check: main_app.scanner_excel_file={excel_file}, self.excel_var.get()={self.excel_var.get()}")
                print(f"[DIAG] build_tab restore check: treeview_state={treeview_state}")
                print(f"[DIAG] build_tab restore check: log_state={log_state[:60] if log_state else log_state}")
                # Remove hasattr check so errors surface
                if excel_file and self.excel_var.get() == excel_file:
                    if treeview_state:
                        try:
                            self.set_treeview_state(treeview_state)
                            
                        except Exception as e:
                            pass
                    if log_state:
                        try:
                            self.set_log_state(log_state)
                            
                        except Exception as e:
                            pass
        except Exception as e:
            pass



        copyright_label = tk.Label(self, text=" 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)
        print('[DIAG] ScannerPanel.build_tab completed successfully')

        # Returns a list of (status, item) for all rows
        state = []
        for item_id in self.scanned_tree.get_children():
            values = self.scanned_tree.item(item_id, 'values')
            state.append(tuple(values))
        return state

    def get_treeview_state(self):
        # Returns a list of (status, item) for all rows
        state = []
        for item_id in self.scanned_tree.get_children():
            values = self.scanned_tree.item(item_id, 'values')
            state.append(tuple(values))
        return state

    def set_treeview_state(self, state):
        # Clear and repopulate the treeview from a list of (status, item)
        for item in self.scanned_tree.get_children():
            self.scanned_tree.delete(item)
        for row in state:
            self.scanned_tree.insert('', 'end', values=row)



    def __init__(self, parent, main_app):
        super().__init__(parent)

        self.parent = parent
        self.main_app = main_app
        self.scanned_items = {}
        self.selected_item = None
        self.keyboard_scanner_enabled = False
        self._usb_scan_buffer = ''
        self._usb_listener_thread = None
        self._usb_listener_running = False
        self.build_tab()

    def save_scanner_type_to_config(self):
        try:
            updates = {'default_scanner_type': self.scanner_type_var.get()}
            update_config(updates)
        except Exception as e:
            print(f"Error saving scanner type to config (ScannerPanel): {e}")

    def save_base_dir_to_config(self):
        try:
            updates = {'default_base_dir': self.base_dir_var.get()}
            update_config(updates)
        except Exception as e:
            print(f"Error saving base dir to config (ScannerPanel): {e}")

    def save_scan_mode_to_config(self):
        try:
            updates = {'default_scan_mode': self.scan_mode_var.get()}
            update_config(updates)
        except Exception as e:
            print(f"Error saving scan mode to config (ScannerPanel): {e}")

    def save_excel_file_to_config(self):
        # Project rule: Excel file path should NOT be saved to config.json
        pass

    def save_com_port_to_config(self):
        try:
            updates = {'default_com_port': self.com_port_var.get()}
            update_config(updates)
        except Exception as e:
            print(f"Error saving com port to config (ScannerPanel): {e}")

    def save_baud_rate_to_config(self):
        try:
            updates = {'default_baud_rate': self.baud_rate_var.get()}
            update_config(updates)
        except Exception as e:
            print(f"Error saving baud rate to config (ScannerPanel): {e}")

    def build_tab(self):
        
        # --- Scanner Panel Content ---
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=0)  # Top row: Scanner Type + Excel
        self.main_frame.rowconfigure(1, weight=0)  # COM/USB row
        self.main_frame.rowconfigure(2, weight=1)  # Results row (expand)
        self.main_frame.grid_propagate(False)

        # --- Initialize config variables and StringVars ---
        config_file = get_config_path()
        default_scanner_type = "COM"
        default_base_dir = "C:/OPUS"
        default_scan_mode = "OPUS"
        default_excel_file = ""
        default_com_port = ""
        default_baud_rate = "9600"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                try:
                    config = json.load(f)
                    default_scanner_type = config.get('default_scanner_type', 'COM')
                    default_base_dir = config.get('default_base_dir', 'C:/OPUS')
                    default_scan_mode = config.get('default_scan_mode', 'OPUS')
                    default_excel_file = ''
                    default_com_port = config.get('default_com_port', '')
                    default_baud_rate = config.get('default_baud_rate', '9600')
                except Exception:
                    pass
        self.scanner_type_var = tk.StringVar(value=default_scanner_type)
        self.scanner_type_var.trace_add('write', lambda *args: self.save_scanner_type_to_config())
        self.base_dir_var = tk.StringVar(value=default_base_dir)
        self.base_dir_var.trace_add('write', lambda *args: self.save_base_dir_to_config())
        self.scan_mode_var = tk.StringVar(value=default_scan_mode)
        self.scan_mode_var.trace_add('write', lambda *args: self.save_scan_mode_to_config())
        self.excel_var = tk.StringVar(value=default_excel_file)  # Do not trace or save to config
        self.com_port_var = tk.StringVar(value=default_com_port)
        self.com_port_var.trace_add('write', lambda *args: self.save_com_port_to_config())
        self.baud_rate_var = tk.StringVar(value=default_baud_rate)
        self.baud_rate_var.trace_add('write', lambda *args: self.save_baud_rate_to_config())
        self.baud_rate_var = tk.StringVar(value=default_baud_rate)
        self.baud_rate_var.trace_add('write', lambda *args: self.save_baud_rate_to_config())

        # --- State restoration and diagnostics (after config vars are set) ---
        try:
            if hasattr(self, 'main_app') and hasattr(self, 'excel_var'):
                excel_file = getattr(self.main_app, 'scanner_excel_file', None)
                treeview_state = getattr(self.main_app, 'scanner_treeview_state', None)
                log_state = getattr(self.main_app, 'scanner_log_state', None)
                
                if excel_file and self.excel_var.get() == excel_file:
                    if treeview_state:
                        try:
                            self.set_treeview_state(treeview_state)
                            
                        except Exception as e:
                            pass
                    if log_state:
                        try:
                            self.set_log_state(log_state)
                            
                        except Exception as e:
                            pass
        except Exception as e:
            pass
        # --- Top row: Scanner Type (left) and Excel file (right) ---
        self.main_frame.columnconfigure(0, weight=1, minsize=200)
        self.main_frame.columnconfigure(1, weight=1, minsize=200)
        self.main_frame.rowconfigure(1, weight=0)

        # Scanner Type selection (left)
        self.scanner_type_frame = ttk.LabelFrame(self.main_frame, text="Scanner Type", padding="5")
        self.scanner_type_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.scanner_type_frame.columnconfigure(0, weight=0)
        self.scanner_type_frame.columnconfigure(1, weight=0)
        self.scanner_type_frame.columnconfigure(2, weight=1)
        self.com_radio = ttk.Radiobutton(self.scanner_type_frame, text="COM-poort scanner", variable=self.scanner_type_var, value="COM", command=self.update_scanner_type)
        self.com_radio.grid(row=0, column=0, sticky="w", padx=(5, 10))
        self.usb_radio = ttk.Radiobutton(self.scanner_type_frame, text="USB-toetsenbord scanner", variable=self.scanner_type_var, value="USB", command=self.update_scanner_type)
        self.usb_radio.grid(row=0, column=1, sticky="w", padx=5)

        # Excel file selection (right)
        self.excel_frame = ttk.LabelFrame(self.main_frame, text="Excel Bestand", padding="5")
        self.excel_frame.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        self.excel_frame.columnconfigure(0, weight=1)
        self.excel_frame.columnconfigure(1, weight=0)
        excel_entry = ttk.Entry(self.excel_frame, textvariable=self.excel_var)
        excel_entry.grid(row=0, column=0, sticky="ew", padx=(5, 0))
        ttk.Button(self.excel_frame, text="Excel Selecteren", command=self._browse_excel).grid(row=0, column=1, padx=(5, 5))

        # --- Scanner mode container (for toggling COM/USB) ---
        self.scanner_mode_container = ttk.Frame(self.main_frame)
        self.scanner_mode_container.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.scanner_mode_container.columnconfigure(0, weight=1)

        # --- COM section ---
        self.com_frame = ttk.LabelFrame(self.scanner_mode_container, text="COM Poort", padding="5", borderwidth=2, relief="solid")
        self.com_frame.columnconfigure(0, weight=0)
        self.com_frame.columnconfigure(1, weight=1)
        self.com_frame.columnconfigure(2, weight=0)
        self.com_frame.columnconfigure(3, weight=0)
        self.com_frame.columnconfigure(4, weight=1)
        ttk.Label(self.com_frame, text="Selecteer COM Poort:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.com_port_combo = ttk.Combobox(self.com_frame, textvariable=self.com_port_var)
        self.com_port_combo.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        ttk.Button(self.com_frame, text="Poorten Vernieuwen", command=self.refresh_ports).grid(row=0, column=2, padx=5)
        ttk.Label(self.com_frame, text="Baud Rate:").grid(row=1, column=0, padx=5, sticky=tk.W)
        ttk.Entry(self.com_frame, textvariable=self.baud_rate_var).grid(row=1, column=1, sticky="ew", padx=(0, 5))
        self.connect_button = ttk.Button(self.com_frame, text="Verbinden", command=self.connect_com_port)
        self.connect_button.grid(row=1, column=2, padx=5, sticky="ew")
        self.com_status_label = ttk.Label(self.com_frame, text="Status: Niet verbonden", foreground="red")
        self.com_status_label.grid(row=2, column=0, columnspan=3, sticky="w", padx=5, pady=(5,0))

        # --- USB section ---
        self.usb_frame = ttk.LabelFrame(self.scanner_mode_container, text="USB Keyboard Scanner", padding="5", borderwidth=2, relief="solid")
        self.usb_frame.columnconfigure(0, weight=1)
        self.usb_scan_var = tk.StringVar()
        self.usb_entry = ttk.Entry(self.usb_frame, textvariable=self.usb_scan_var)
        self.usb_entry.grid(row=0, column=0, sticky="ew", padx=5)
        self.usb_entry.bind('<Return>', self.process_usb_scan)

        # --- Show/hide COM and USB frames based on scanner type ---
        self.update_scanner_type()

        # --- Results section ---
        self.results_frame = ttk.LabelFrame(self.main_frame, text="Resultaten", padding="5")
        self.results_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=3)
        self.results_frame.rowconfigure(1, weight=1)
        self.scanned_tree = ttk.Treeview(self.results_frame, columns=('Status', 'Item'), show='headings')
        self.scanned_tree.heading('Status', text='Status')
        self.scanned_tree.heading('Item', text='Item')
        self.scanned_tree.column('Status', width=100, stretch=True, anchor='e')
        # Context menu for treeview
        self.tree_menu = tk.Menu(self.scanned_tree, tearoff=0)
        self.tree_menu.add_command(label="Status op OK zetten", command=self.set_status_ok)
        self.tree_menu.add_command(label="Status wissen", command=self.clear_status)
        self.scanned_tree.bind("<Button-3>", self.show_tree_menu)  # Windows/Linux right-click
        self.scanned_tree.bind("<Button-2>", self.show_tree_menu)  # Mac right-click
        self.tree_scroll = ttk.Scrollbar(self.results_frame, orient='vertical', command=self.scanned_tree.yview)
        self.scanned_tree.configure(yscrollcommand=self.tree_scroll.set)
        self.scanned_tree.grid(row=0, column=0, sticky="nsew")
        self.tree_scroll.grid(row=0, column=1, sticky="ns")

        self.results_text = tk.Text(self.results_frame, height=8)
        self.results_text.grid(row=1, column=0, sticky="nsew", columnspan=2)

        copyright_label = tk.Label(self, text=" 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)

    def update_scanner_type(self):
        # Robust toggling for keyboard logger
        if hasattr(self, 'com_frame') and hasattr(self, 'usb_frame'):
            self.com_frame.pack_forget()
            self.usb_frame.pack_forget()
            if self.scanner_type_var.get() == 'USB':
                self.usb_frame.pack(fill="x", expand=True)
                self.usb_listener_enabled = True
                # Start USB listener thread if not already running
                if not getattr(self, '_usb_listener_running', False):
                    self._usb_listener_thread = threading.Thread(target=self._start_usb_listener, daemon=True)
                    self._usb_listener_thread.start()
                    self._usb_listener_running = True
            else:
                self.com_frame.pack(fill="x", expand=True)
                self.usb_listener_enabled = False

    def _start_usb_listener(self):
        # Runs in a background thread
        keyboard.on_press(self._on_key_event)
        keyboard.wait()  # Keeps the thread alive

    def _on_key_event(self, event):
        # Only process if USB mode is selected, the frame is visible, and the listener is enabled
        try:
            if not getattr(self, 'usb_listener_enabled', False):
                return
            if not hasattr(self, 'scanner_type_var') or self.scanner_type_var.get() != 'USB':
                return
            if hasattr(self, 'usb_frame') and not self.usb_frame.winfo_ismapped():
                return
            # Ignore modifier keys
            if event.event_type != 'down' or event.name in ['shift', 'ctrl', 'alt', 'caps lock', 'tab', 'esc', 'windows', 'left windows', 'right windows']:
                return
            if event.name == 'enter':
                scan = self._usb_scan_buffer
                self._usb_scan_buffer = ''
                if scan:
                    # Schedule processing in the Tkinter main thread
                    self.after(0, self.process_usb_scan, scan)
            elif len(event.name) == 1:
                self._usb_scan_buffer += event.name
            elif event.name == 'space':
                self._usb_scan_buffer += ' '
        except Exception as e:
            print(f"[USB Keylogger Error]: {e}")

    def process_usb_scan(self, scan=None):
        # If called from Entry, scan is None and use the Entry value
        if scan is None:
            scan = self.usb_scan_var.get()
        self.results_text.see('end')

    def process_com_scan(self, scan):
        # Compare COM scan value to Excel list, set status OK if found, update Excel
        found = False
        for item_id in self.scanned_tree.get_children():
            values = list(self.scanned_tree.item(item_id, 'values'))
            if len(values) >= 2 and str(values[1]).strip() == str(scan).strip():
                found = True
                if values[0] == 'OK':
                    self.results_text.insert('end', f"COM-scan al op OK: {scan}\n")
                    self.results_text.see('end')
                else:
                    values[0] = 'OK'
                    self.scanned_tree.item(item_id, values=values)
                    self.results_text.insert('end', f"COM-scan gevonden en op OK gezet: {scan}\n")
                    self.results_text.see('end')
                    self._save_treeview_to_excel()
                    if all(self.scanned_tree.item(i, 'values')[0] == 'OK' for i in self.scanned_tree.get_children()):
                        self._on_all_items_ok()
                break
        if not found:
            self.results_text.insert('end', f"[WAARSCHUWING] COM-scan niet gevonden in Excel: {scan}\n")
            self.results_text.see('end')

    def _on_all_items_ok(self):
        # Show popup immediately
        messagebox.showinfo("Alle items OK", "Alle items zijn gescand en op OK gezet.")
        log_msg = "[LOG] Alle items gescand en op OK gezet."
        self.results_text.insert('end', log_msg + " (verwerken...)\n")
        self.results_text.see('end')

        def background_success_logic():
            import requests
            import json
            import os
            sent_to_db = False
            sent_email = False
            sent_closed = False
            closed_error = None
            config_file = get_config_path()
            project_name = None
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    excel_path = ''
                    project_name = os.path.splitext(os.path.basename(excel_path))[0] if excel_path else 'Onbekend project'
                    # Only send CLOSED event if an OPEN event exists
                    if config.get('database_enabled', False):
                        try:
                            api_url = config.get('api_url', 'http://localhost:5000/log')
                            user = config.get('user', 'user')
                            # Query logs for this project (GET /logs), look for an OPEN event
                            found_open = True
                            if found_open:
                                closed_payload = {
                                    "event": "CLOSED",
                                    "details": "Project gesloten na alle items OK.",
                                    "project": project_name,
                                    "user": user
                                }
                                closed_resp = requests.post(api_url, json=closed_payload, timeout=5)
                                if closed_resp.status_code == 200:
                                    closed_json = closed_resp.json()
                                    if closed_json.get('success'):
                                        sent_closed = True
                                    elif closed_json.get('already_closed'):
                                        closed_error = "[INFO] Project was already closed (CLOSED event not added again)."
                                    else:
                                        closed_error = f"[FOUT] CLOSED event niet gelukt: {closed_resp.text}"
                                else:
                                    closed_error = f"[FOUT] CLOSED event niet gelukt: {closed_resp.text}"
                            else:
                                closed_error = "[INFO] Geen OPEN event gevonden voor dit project, geen CLOSED event verzonden."
                        except Exception as e:
                            pass
                    # Email sending
                    if config.get('email_enabled', False):
                        try:
                            from email.mime.text import MIMEText
                            sender = config.get('email_sender', '')
                            receiver = config.get('email_receiver', '')
                            msg = MIMEText("Alle items zijn gescand en op OK gezet.")
                            msg['Subject'] = "Alle items OK"
                            # Place your email sending logic here
                            # Example: send_email(sender, receiver, msg)
                            sent_email = True
                        except Exception as e:
                            pass
                except Exception as e:
                    def ui_config_error():
                        self.results_text.insert('end', f"[FOUT] Config lezen: {e}\n")
                        self.results_text.see('end')
                    self.after(0, ui_config_error)
            # Always log the result in the log viewer
            def ui_update():
                status_parts = []
                if sent_to_db:
                    status_parts.append("(naar database gestuurd)")
                if sent_closed:
                    status_parts.append("(CLOSED event verzonden)")
                if sent_email:
                    status_parts.append("(e-mail verzonden)")
                if not status_parts:
                    status_parts.append("(niet verzonden)")
                log_full = f"{log_msg} {' '.join(status_parts)}\n"
                self.results_text.insert('end', log_full)
                if closed_error:
                    self.results_text.insert('end', f"{closed_error}\n")
                self.results_text.see('end')
            self.after(0, ui_update)
        import threading
        threading.Thread(target=background_success_logic, daemon=True).start()


    def _browse_directory(self):
        scan_mode = self.scan_mode_var.get()
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
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(tk.END, f"Selected directory: {directory}\n")
                self.results_text.see(tk.END)

    def _browse_base_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.base_dir_var.set(directory)

    def _start_scan(self):
        scan_mode = self.scan_mode_var.get()
        path = self.directory_var.get()
        if scan_mode == "GANNOMAT":
            if not path or not (path.lower().endswith('.mdb') or path.lower().endswith('.accdb')):
                messagebox.showwarning("Missing File", "Please select a .mdb file to scan.")
                return
            self.scan_button.config(state=tk.DISABLED)
            threading.Thread(target=self._scan_thread, args=(path, scan_mode), daemon=True).start()
        else:
            if not path:
                messagebox.showwarning("Missing Directory", "Please select a directory to scan.")
                return
            self.scan_button.config(state=tk.DISABLED)
            threading.Thread(target=self._scan_thread, args=(path, scan_mode), daemon=True).start()

    def _on_scan_mode_change(self, event=None):
        self.save_scan_mode_to_config()

    def _scan_thread(self, path, scan_mode):
        try:
            self.progress_var.set(0)
            self.status_label.config(text="Scannen gestart...")
            if scan_mode == "GANNOMAT" and (path.lower().endswith('.mdb') or path.lower().endswith('.accdb')):
                try:
                    import pyodbc
                except ImportError:
                    self.results_text.insert('end', 'pyodbc is niet geïnstalleerd. Kan MDB-bestanden niet scannen.\n')
                    self.scan_button.config(state=tk.NORMAL)
                    messagebox.showerror("Scanfout", "pyodbc is niet geïnstalleerd. Kan MDB-bestanden niet scannen.")
                    return
                results = []
                try:
                    conn_str = (
                        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
                        f'DBQ={path};'
                    )
                    conn = pyodbc.connect(conn_str, autocommit=True)
                    cursor = conn.cursor()
                    tables = [tbl_info.table_name for tbl_info in cursor.tables(tableType='TABLE')]
                    program_table = None
                    fallback_table = None
                    for table in tables:
                        columns = [column.column_name for column in cursor.columns(table=table)]
                        if table.lower() == 'program' and 'ProgramNumber' in columns:
                            program_table = table
                    # ... Add logic to extract and display data ...
                    self.results_text.insert('end', f"Scanned {len(results)} items from MDB.\n")
                except Exception as e:
                    self.results_text.insert('end', f"Error scanning MDB: {e}\n")
                finally:
                    self.scan_button.config(state=tk.NORMAL)
            else:
                # Directory scan logic (OPUS mode)
                self.results_text.insert('end', f"Scanning directory: {path}\n")
                # ... Add directory scanning logic ...
                self.scan_button.config(state=tk.NORMAL)
        except Exception as e:
            self.results_text.insert('end', f"Scan error: {e}\n")
            self.scan_button.config(state=tk.NORMAL)

    def process_usb_scan(self, event=None):
        # Get scan value from entry or argument
        scan = self.usb_scan_var.get() if event is None else event
        if event is None:
            self.usb_scan_var.set('')
        found = False
        for item_id in self.scanned_tree.get_children():
            values = list(self.scanned_tree.item(item_id, 'values'))
            if len(values) >= 2 and str(values[1]).strip() == str(scan).strip():
                found = True
                if values[0] == 'OK':
                    self.results_text.insert('end', f"Scan al op OK: {scan}\n")
                    self.results_text.see('end')
                else:
                    values[0] = 'OK'
                    self.scanned_tree.item(item_id, values=values)
                    self.results_text.insert('end', f"Scan gevonden en op OK gezet: {scan}\n")
                    self.results_text.see('end')
                    self._save_treeview_to_excel()
                    if all(self.scanned_tree.item(i, 'values')[0] == 'OK' for i in self.scanned_tree.get_children()):
                        self._on_all_items_ok()
                break
        if not found:
            self.results_text.insert('end', f"[WAARSCHUWING] Scan niet gevonden in Excel: {scan}\n")
            self.results_text.see('end')

    def connect_com_port(self):
        # Add logic to connect to COM port
        pass

    def disconnect_com(self):
        # Add logic to disconnect from COM port
        pass

    def update_scanner_type(self):
        scanner_type = self.scanner_type_var.get()
        if scanner_type == "COM":
            self.com_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
            self.usb_frame.grid_forget()
        elif scanner_type == "USB":
            self.usb_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
            self.com_frame.grid_forget()

    def _browse_excel(self):
        # Logic to browse for Excel file
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Selecteer Excel-bestand",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")]
        )
        if file_path:
            self.excel_var.set(file_path)
            self.load_excel_to_treeview(file_path)
            # Persist selection to config
            if hasattr(self, 'save_excel_file_to_config'):
                self.save_excel_file_to_config()

    def load_excel_to_treeview(self, file_path):
        """Load Excel data and populate the scanned_tree widget."""
        try:
            print(f'[DIAG] importing pandas in scanner_panel.py {time.time()}')
            import pandas as pd
            print(f'[DIAG] pandas imported in scanner_panel.py {time.time()}')
            import os
            # Prefer _updated.xlsx if it exists
            base, ext = os.path.splitext(file_path)
            updated_path = f"{base}_updated.xlsx"
            actual_file = file_path
            if os.path.exists(updated_path):
                actual_file = updated_path
            df = pd.read_excel(actual_file)
            # Clear existing treeview
            for item in self.scanned_tree.get_children():
                self.scanned_tree.delete(item)
            # Determine columns
            import os
            import math
            if 'Status' in df.columns and 'Item' in df.columns:
                for _, row in df.iterrows():
                    status = row.get('Status', '')
                    item = row.get('Item', '')
                    # Convert NaN or 'nan' to blank
                    if isinstance(status, float) and math.isnan(status):
                        status = ''
                    elif isinstance(status, str) and status.lower() == 'nan':
                        status = ''
                    if isinstance(item, float) and math.isnan(item):
                        item = ''
                    elif isinstance(item, str) and item.lower() == 'nan':
                        item = ''
                    if isinstance(item, str):
                        item = os.path.splitext(item)[0]
                    self.scanned_tree.insert('', 'end', values=(status, item))
            else:
                # Fallback: ensure Status is leftmost if present, and strip extensions from string values
                for _, row in df.iterrows():
                    row_dict = row.to_dict() if hasattr(row, 'to_dict') else dict(row)
                    # Try to find 'Status' and move to front
                    status_val = row_dict.pop('Status', '') if 'Status' in row_dict else ''
                    # Convert NaN or 'nan' to blank for status
                    if isinstance(status_val, float) and math.isnan(status_val):
                        status_val = ''
                    elif isinstance(status_val, str) and status_val.lower() == 'nan':
                        status_val = ''
                    # Remove extension and convert NaN for all string/float values
                    row_values = []
                    for v in row_dict.values():
                        if isinstance(v, float) and math.isnan(v):
                            row_values.append('')
                        elif isinstance(v, str) and v.lower() == 'nan':
                            row_values.append('')
                        elif isinstance(v, str) and '.' in v:
                            row_values.append(os.path.splitext(v)[0])
                        else:
                            row_values.append(v)
                    self.scanned_tree.insert('', 'end', values=(status_val, *row_values))
            self.results_text.insert('end', f"Excel geladen: {file_path}\n")
            self.results_text.see('end')
            # Check if all items are OK after loading
            if all(self.scanned_tree.item(i, 'values')[0] == 'OK' for i in self.scanned_tree.get_children() if len(self.scanned_tree.item(i, 'values')) > 0):
                self._on_all_items_ok()
        except Exception as e:
            self.results_text.insert('end', f"[FOUT] Kan Excel niet laden: {e}\n")
            self.results_text.see('end')


    def refresh_ports(self):
        # Add logic to refresh COM ports
        pass

    def set_status_ok(self):
        # Set the selected item's status to 'OK' in the treeview and update Excel
        if self.selected_item:
            values = list(self.scanned_tree.item(self.selected_item, 'values'))
            if len(values) >= 2:
                values[0] = 'OK'
                self.scanned_tree.item(self.selected_item, values=values)
                self.results_text.insert('end', f"Status op OK gezet voor: {values[1]}\n")
                self.results_text.see('end')
                self._save_treeview_to_excel()
                # Check if all items are OK after manual edit
                if all(self.scanned_tree.item(i, 'values')[0] == 'OK' for i in self.scanned_tree.get_children() if len(self.scanned_tree.item(i, 'values')) > 0):
                    self._on_all_items_ok()

    def clear_status(self):
        # Clear the selected item's status in the treeview and update Excel
        if self.selected_item:
            values = list(self.scanned_tree.item(self.selected_item, 'values'))
            if len(values) >= 2:
                values[0] = ''
                self.scanned_tree.item(self.selected_item, values=values)
                self.results_text.insert('end', f"Status gewist voor: {values[1]}\n")
                self.results_text.see('end')
                self._save_treeview_to_excel()

    def _save_treeview_to_excel(self):
        # Save the current treeview to an _updated.xlsx file
        excel_path = self.excel_var.get()
        if not excel_path or not os.path.exists(excel_path):
            self.results_text.insert('end', "Geen geldig Excel-bestand geladen. Kan wijzigingen niet opslaan.\n")
            self.results_text.see('end')
            return
        import pandas as pd
        items = []
        for item_id in self.scanned_tree.get_children():
            values = self.scanned_tree.item(item_id, 'values')
            if len(values) >= 2:
                items.append({'Status': values[0], 'Item': values[1]})
        # Try to preserve the original column name for 'Item'
        try:
            df_orig = pd.read_excel(excel_path)
            if 'ProgramNumber' in df_orig.columns:
                item_col = 'ProgramNumber'
            elif 'Relative Path' in df_orig.columns:
                item_col = 'Relative Path'
            else:
                item_col = df_orig.columns[0]
            # Map items back to original columns
            new_rows = []
            for item in items:
                row = {col: '' for col in df_orig.columns}
                row['Status'] = item['Status']
                row[item_col] = item['Item']
                new_rows.append(row)
            df_new = pd.DataFrame(new_rows, columns=df_orig.columns)
        except Exception as e:
            # Fallback: just save Status and Item
            df_new = pd.DataFrame(items)
        updated_path = os.path.splitext(excel_path)[0] + "_updated.xlsx"
        try:
            df_new.to_excel(updated_path, index=False)
            self.results_text.insert('end', f"Wijzigingen opgeslagen in: {updated_path}\n")
            self.results_text.see('end')
        except Exception as e:
            self.results_text.insert('end', f"Fout bij opslaan van wijzigingen: {e}\n")
            self.results_text.see('end')

    def show_tree_menu(self, event):
        # Select the row under the mouse and show the context menu
        item_id = self.scanned_tree.identify_row(event.y)
        if item_id:
            self.scanned_tree.selection_set(item_id)
            self.selected_item = item_id
            try:
                self.tree_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.tree_menu.grab_release()
        else:
            self.scanned_tree.selection_remove(self.scanned_tree.selection())
            self.selected_item = None

    def update_scanned_tree(self):
        # Add logic to update scanned tree
        pass
