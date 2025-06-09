import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
from config_utils import update_config, get_config_path
import pandas as pd
import serial
import serial.tools.list_ports
import time
from . import scanner_tab_utils

class ScannerTab:
    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        self.scanned_items = {}
        self.selected_item = None
        self.keyboard_scanner_enabled = False
        self.build_tab()

    def save_scanner_type_to_config(self):
        try:
            updates = {'default_scanner_type': self.scanner_type_var.get()}
            update_config(updates)
        except Exception as e:
            print(f"Error saving scanner type to config (ScannerTab): {e}")

    def save_base_dir_to_config(self):
        try:
            updates = {'default_base_dir': self.base_dir_var.get()}
            update_config(updates)
        except Exception as e:
            print(f"Error saving base dir to config (ScannerTab): {e}")

    def save_scan_mode_to_config(self):
        try:
            updates = {'default_scan_mode': self.scan_mode_var.get()}
            update_config(updates)
        except Exception as e:
            print(f"Error saving scan mode to config (ScannerTab): {e}")


    def build_tab(self):
        # --- Scanner Tab Content ---
        self.main_frame = ttk.Frame(self.parent, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(2, weight=1)
        copyright_label = tk.Label(self.parent, text="© 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)

        # Scanner type and Excel file selection
        config_file = get_config_path()
        default_scanner_type = "COM"
        default_base_dir = "C:/OPUS"
        default_scan_mode = "OPUS"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                try:
                    config = json.load(f)
                    default_scanner_type = config.get('default_scanner_type', 'COM')
                    default_base_dir = config.get('default_base_dir', 'C:/OPUS')
                    default_scan_mode = config.get('default_scan_mode', 'OPUS')
                except Exception:
                    pass
        else:
            default_scanner_type = "COM"
            default_base_dir = "C:/OPUS"
            default_scan_mode = "OPUS"
        self.scanner_type_var = tk.StringVar(value=default_scanner_type)
        self.scanner_type_var.trace_add('write', lambda *args: self.save_scanner_type_to_config())
        self.base_dir_var = tk.StringVar(value=default_base_dir)
        self.base_dir_var.trace_add('write', lambda *args: self.save_base_dir_to_config())
        self.scan_mode_var = tk.StringVar(value=default_scan_mode)
        self.scan_mode_var.trace_add('write', lambda *args: self.save_scan_mode_to_config())

        # --- Ensure results_frame/results_text are created before Excel/file dialogs ---
        self.results_frame = ttk.LabelFrame(self.main_frame, text="Resultaten", padding="5")
        self.results_frame.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=3)
        self.results_frame.rowconfigure(1, weight=1)

        # Treeview for scanned items
        self.scanned_tree = ttk.Treeview(self.results_frame, columns=('Status', 'Item'), show='headings')
        self.scanned_tree.heading('Status', text='Status')
        self.scanned_tree.heading('Item', text='Item')
        self.scanned_tree.column('Status', width=100, stretch=True, anchor='e')
        self.scanned_tree.column('Item', width=600, stretch=True, anchor='w')
        self.tree_scroll = ttk.Scrollbar(self.results_frame, orient='vertical', command=self.scanned_tree.yview)
        self.scanned_tree.configure(yscrollcommand=self.tree_scroll.set)
        self.scanned_tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.tree_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree_menu = tk.Menu(self.scanned_tree, tearoff=0)
        self.tree_menu.add_command(label="Status op OK zetten", command=self.set_status_ok)
        self.tree_menu.add_command(label="Status wissen", command=self.clear_status)
        self.scanned_tree.bind("<Button-3>", self.show_tree_menu)

        # Log window below
        self.results_text = tk.Text(self.results_frame, height=8)
        self.results_text.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), columnspan=2)

        # --- Excel frame and scanner type selection after results_text is created ---
        self.scanner_excel_frame = ttk.Frame(self.main_frame, padding="5")
        self.scanner_excel_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.scanner_excel_frame.columnconfigure(0, weight=1)
        self.scanner_excel_frame.columnconfigure(1, weight=1)

        scanner_type_frame = ttk.LabelFrame(self.scanner_excel_frame, text="Scanner Type", padding="5")
        scanner_type_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.com_radio = ttk.Radiobutton(scanner_type_frame, text="COM Port Scanner", variable=self.scanner_type_var, value="COM", command=self.update_scanner_type)
        self.com_radio.grid(row=0, column=0, padx=5, sticky=tk.W)
        self.usb_radio = ttk.Radiobutton(scanner_type_frame, text="USB Keyboard Scanner", variable=self.scanner_type_var, value="USB", command=self.update_scanner_type)
        self.usb_radio.grid(row=0, column=1, padx=5, sticky=tk.W)

        self.excel_frame = ttk.LabelFrame(self.scanner_excel_frame, text="Excel Bestand", padding="5")
        self.excel_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.excel_frame.columnconfigure(0, weight=1)
        self.excel_frame.columnconfigure(1, weight=0)
        self.excel_var = tk.StringVar()
        excel_entry = ttk.Entry(self.excel_frame, textvariable=self.excel_var)
        excel_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(5, 0))
        ttk.Button(self.excel_frame, text="Excel Selecteren", command=self.browse_excel).grid(row=0, column=1, padx=(5, 5))

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

        self.usb_frame = ttk.LabelFrame(self.main_frame, text="USB Keyboard Scanner", padding="5")
        self.usb_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.usb_frame.columnconfigure(0, weight=1)
        self.usb_scan_var = tk.StringVar()
        self.usb_entry = ttk.Entry(self.usb_frame, textvariable=self.usb_scan_var)
        self.usb_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        self.usb_entry.bind('<Return>', self.process_usb_scan)
        # Remove all initial grid/grid_remove calls for com_frame and usb_frame here
        # Instead, ensure the correct frame is visible based on the default scanner type at the end

        # Ensure the correct scanner frame is visible on startup
        self.update_scanner_type()

    def show_tree_menu(self, event):
        # Select the row under the mouse and show the context menu
        item_id = self.scanned_tree.identify_row(event.y)
        if item_id:
            self.scanned_tree.selection_set(item_id)
            self.selected_item = item_id
            self.tree_menu.tk_popup(event.x_root, event.y_root)
        else:
            self.scanned_tree.selection_remove(self.scanned_tree.selection())
            self.selected_item = None
        # Do not recreate or re-add frames here!

        # Control frame (must be created before update_scanner_type)
        self.control_frame = ttk.Frame(self.main_frame)
        self.control_frame.grid(row=3, column=0, pady=(10, 0))
        self.button_container = ttk.Frame(self.control_frame)
        self.button_container.grid(row=0, column=0)
        self.connect_button = ttk.Button(self.button_container, text="Verbinden", command=self.connect_com)
        self.connect_button.grid(row=0, column=0, padx=5)
        self.disconnect_button = ttk.Button(self.button_container, text="Verbinding verbreken", command=self.disconnect_com)

        # Progress frame (must be created before update_scanner_type)
        self.progress_frame = ttk.LabelFrame(self.main_frame, text="Status", padding="5")
        self.progress_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.S), pady=(0, 10))
        self.progress_frame.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(self.progress_frame, text="Niet verbonden")
        self.status_label.grid(row=0, column=0, pady=(5, 0), sticky=tk.W)

        # Ensure correct frame is visible on startup
        self.update_scanner_type()

    def process_usb_scan(self, event):
        value = self.usb_scan_var.get().strip()
        if value:
            self.handle_scanned_value(value)
            self.usb_scan_var.set("")

    def connect_com(self):
        # TODO: Implement COM port connection logic
        self.results_text.insert(tk.END, "[STUB] Verbinden met COM-poort...\n")
        self.results_text.see(tk.END)

    def disconnect_com(self):
        # TODO: Implement COM port disconnection logic
        self.results_text.insert(tk.END, "[STUB] Verbinding met COM-poort verbreken...\n")
        self.results_text.see(tk.END)

    def update_scanner_type(self):
        scanner_type = self.scanner_type_var.get()
        # Only access control_frame and progress_frame if they exist
        has_control = hasattr(self, 'control_frame')
        has_progress = hasattr(self, 'progress_frame')
        if scanner_type == "COM":
            self.com_frame.grid()
            self.usb_frame.grid_remove()
            if has_control:
                self.control_frame.grid()
            if has_progress:
                self.progress_frame.grid()
            self.keyboard_scanner_enabled = False
        else:
            self.com_frame.grid_remove()
            self.usb_frame.grid()
            if has_control:
                self.control_frame.grid_remove()
            if has_progress:
                self.progress_frame.grid_remove()
            self.usb_entry.focus_set()

    def browse_excel(self):
        excel_file = filedialog.askopenfilename(
            filetypes=[("Excel bestanden", "*.xlsx")],
            title="Selecteer Excel Bestand"
        )
        if excel_file:
            self.excel_var.set(excel_file)
            self.results_text.insert(tk.END, f"Excel bestand geselecteerd: {excel_file}\n")
            self.results_text.see(tk.END)
            try:
                updated_file = os.path.splitext(excel_file)[0] + "_updated.xlsx"
                if os.path.exists(updated_file):
                    self.update_scanned_tree(updated_file)
                    self.results_text.insert(tk.END, f"Bestaande scanresultaten geladen uit: {updated_file}\n")
                    self.results_text.see(tk.END)
                else:
                    self.update_scanned_tree(excel_file)
            except Exception as e:
                self.results_text.insert(tk.END, f"Fout bij het laden van Excel bestand: {str(e)}\n")
                self.results_text.see(tk.END)

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in ports]
        self.com_port_combo['values'] = port_names
        if port_names:
            self.com_port_var.set(port_names[0])

    def set_status_ok(self):
        if self.selected_item:
            status = self.scanned_tree.set(self.selected_item, 'Status')
            if status != 'OK':
                item = self.scanned_tree.set(self.selected_item, 'Item')
                self.scanned_tree.set(self.selected_item, 'Status', 'OK')
                self.scanned_items[item] = 'OK'
                if self.excel_var.get():
                    try:
                        updated_file = os.path.splitext(self.excel_var.get())[0] + "_updated.xlsx"
                        import pandas as pd
                        if os.path.exists(updated_file):
                            df = pd.read_excel(updated_file)
                        else:
                            df = pd.read_excel(self.excel_var.get())
                        if 'Status' not in df.columns:
                            df['Status'] = ''
                        # Explicitly cast Status column to str to avoid dtype warnings
                        df['Status'] = df['Status'].astype(str)
                        df.loc[df.iloc[:, 0].astype(str) == item, 'Status'] = 'OK'
                        df.to_excel(updated_file, index=False)
                        self.results_text.insert(tk.END, f"Status OK gezet voor: {item}\n")
                        self.results_text.see(tk.END)
                    except Exception as e:
                        error_message = f"Fout bij het bijwerken van status: {str(e)}"
                        self.results_text.insert(tk.END, error_message + "\n")
                        self.results_text.see(tk.END)
        # --- All OK check and database logging ---
        all_ok = all(self.scanned_tree.set(item_id, 'Status') == 'OK' for item_id in self.scanned_tree.get_children())
        if all_ok:
            self.results_text.insert(tk.END, "\nAlle items zijn succesvol gescand!\n")
            self.results_text.see(tk.END)
            # Print all item statuses for debugging
            status_debug = []
            for item_id in self.scanned_tree.get_children():
                item = self.scanned_tree.set(item_id, 'Item')
                status = self.scanned_tree.set(item_id, 'Status')
                status_debug.append(f"{item}: {status}")
            debug_str = "[DEBUG] Statuses: " + ", ".join(status_debug)
            print(debug_str)
            self.results_text.insert(tk.END, debug_str + "\n")
            self.results_text.see(tk.END)
            messagebox.showinfo("Succes", "Alle items zijn succesvol gescand!")
            project_name = self.excel_var.get()
            database_tab = getattr(self.main_app, 'database_tab', None)
            if not database_tab and hasattr(self.main_app, 'tab_instances'):
                database_tab = self.main_app.tab_instances.get('Database')
                if database_tab:
                    self.main_app.database_tab = database_tab
            if database_tab:
                print(f"[DEBUG] Calling log_project_closed for project: {project_name}")
                self.results_text.insert(tk.END, f"[DEBUG] Calling log_project_closed for project: {project_name}\n")
                self.results_text.see(tk.END)
                result = database_tab.log_project_closed(project_name)
                print(f"[DEBUG] log_project_closed result: {result}")
                self.results_text.insert(tk.END, f"[DEBUG] log_project_closed result: {result}\n")
                self.results_text.see(tk.END)
            else:
                print("[DEBUG] self.main_app.database_tab does not exist!")
                print(f"[DEBUG] id(self.main_app): {id(self.main_app)}")
                print(f"[DEBUG] self.main_app.__dict__.keys(): {list(self.main_app.__dict__.keys())}")
                print(f"[DEBUG] id(self): {id(self)} (ScannerTab instance)")
                # Print tab_instances keys and types
                tab_keys = list(getattr(self.main_app, 'tab_instances', {}).keys())
                print(f"[DEBUG] self.main_app.tab_instances keys: {tab_keys}")
                tab_types = {k: str(type(v)) for k,v in getattr(self.main_app, 'tab_instances', {}).items()}
                print(f"[DEBUG] self.main_app.tab_instances types: {tab_types}")
                db_tab = getattr(self.main_app, 'tab_instances', {}).get('Database', None)
                print(f"[DEBUG] self.main_app.tab_instances['Database']: {db_tab}, type: {type(db_tab)}")
                self.results_text.insert(tk.END, "[DEBUG] self.main_app.database_tab does not exist!\n")
                self.results_text.insert(tk.END, f"[DEBUG] id(self.main_app): {id(self.main_app)}\n")
                self.results_text.insert(tk.END, f"[DEBUG] self.main_app.__dict__.keys(): {list(self.main_app.__dict__.keys())}\n")
                self.results_text.insert(tk.END, f"[DEBUG] id(self): {id(self)} (ScannerTab instance)\n")
                self.results_text.insert(tk.END, f"[DEBUG] self.main_app.tab_instances keys: {tab_keys}\n")
                self.results_text.insert(tk.END, f"[DEBUG] self.main_app.tab_instances types: {tab_types}\n")
                self.results_text.insert(tk.END, f"[DEBUG] self.main_app.tab_instances['Database']: {db_tab}, type: {type(db_tab)}\n")
                self.results_text.see(tk.END)
            self.usb_scan_var.set("")

    def clear_status(self):
        if self.selected_item:
            item = self.scanned_tree.set(self.selected_item, 'Item')
            self.scanned_tree.set(self.selected_item, 'Status', '')
            self.scanned_items[item] = ''
            excel_file = self.excel_var.get()
            if excel_file:
                try:
                    updated_file = os.path.splitext(excel_file)[0] + "_updated.xlsx"
                    import pandas as pd
                    if os.path.exists(updated_file):
                        df = pd.read_excel(updated_file)
                    else:
                        df = pd.read_excel(excel_file)
                    if 'Status' not in df.columns:
                        df['Status'] = ''
                    df.loc[df.iloc[:, 0].astype(str) == item, 'Status'] = ''
                    df.to_excel(updated_file, index=False)
                    self.results_text.insert(tk.END, f"Status handmatig gewist voor: {item}\n")
                    self.results_text.see(tk.END)
                    self.update_scanned_tree(excel_file)
                except Exception as e:
                    self.results_text.insert(tk.END, f"Fout bij het wissen van status: {str(e)}\n")
                    self.results_text.see(tk.END)

    def update_scanned_tree(self, excel_file):

        try:
            updated_file = os.path.splitext(excel_file)[0] + "_updated.xlsx"
            file_to_load = updated_file if os.path.exists(updated_file) else excel_file
            import pandas as pd
            df = pd.read_excel(file_to_load)
            # Ensure 'Status' column exists
            if 'Status' not in df.columns:
                df['Status'] = ''
            # Clear existing items to prevent duplicates
            for item_id in self.scanned_tree.get_children():
                self.scanned_tree.delete(item_id)
            self.scanned_items.clear()

            # Determine which column to use as 'Item': prefer 'ProgramNumber', else 'Relative Path', else first column
            if 'ProgramNumber' in df.columns:
                item_col = 'ProgramNumber'
            elif 'Relative Path' in df.columns:
                item_col = 'Relative Path'
            else:
                item_col = df.columns[0]
            inserted_count = 0
            for idx, row in df.iterrows():
                item = str(row[item_col])
                status = str(row['Status']) if 'Status' in row else ''
                if status == 'nan':
                    status = ''

                self.scanned_tree.insert('', 'end', values=(status, item))
                self.scanned_items[item] = status
                inserted_count += 1

            self.results_text.insert(tk.END, f"Treeview bijgewerkt met items uit {'_updated.xlsx' if os.path.exists(updated_file) else 'Excel'}\n")
            self.results_text.see(tk.END)
            self.scanned_tree.focus_set()
            self.scanned_tree.update_idletasks()
            self.scanned_tree.tkraise()

        except Exception as e:
            self.results_text.insert(tk.END, f"Fout bij het bijwerken van Treeview: {str(e)}\n")
            self.results_text.see(tk.END)
            self.main_app.root.update_idletasks()

    def scan_directory(self, directory):
        # Use the utility function for scanning directories
        return scanner_tab_utils.scan_directory(directory, self.base_dir, self.results_text)

    # ... (rest of the code remains the same)
        # Use the utility function for scanning mdb files
        return scanner_tab_utils.scan_mdb_files(mdb_file, self.results_text)

    def _create_excel(self, directory, scan_mode="OPUS"):
        # Use the utility function for creating Excel files
        scanner_tab_utils.create_excel(self.files, directory, scan_mode, self.results_text)

    def handle_scanned_value(self, value):
        if not hasattr(self, 'excluded_codes'):
            try:
                with open(os.path.join(os.path.dirname(__file__), 'filtered_scans.json'), 'r', encoding='utf-8') as f:
                    self.excluded_codes = set(json.load(f))
            except Exception as e:
                self.excluded_codes = set()
                self.results_text.insert(tk.END, f"Fout bij het laden van filtered_scans.json: {str(e)}\n")
                self.results_text.see(tk.END)
        if value in self.excluded_codes:
            return
        found = False
        for item_id in self.scanned_tree.get_children():
            item = self.scanned_tree.set(item_id, 'Item')
            if item == value:
                self.scanned_tree.selection_set(item_id)
                self.scanned_tree.see(item_id)
                self.selected_item = item_id
                self.set_status_ok()
                found = True
                break
        if not found:
            self.results_text.insert(tk.END, f"Waarschuwing: Item '{value}' niet gevonden in Excel bestand\n")
            self.results_text.see(tk.END)
