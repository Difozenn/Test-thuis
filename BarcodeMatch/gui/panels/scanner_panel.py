import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont # Added font import as tkfont
import pandas as pd
import threading
import time
import keyboard
import serial
import serial.tools.list_ports
import os
import re
import re
import requests # Added for API calls
import os
import json
from config_utils import get_config_path, load_config as _load_full_config, update_config as _save_full_config

class ScannerPanel(ttk.Frame):
    def __init__(self, parent, main_app, **kwargs):
        super().__init__(parent, **kwargs)
        self.main_app = main_app # Store main_app for later use

        # --- Variables ---
        self.barcode_data = {}
        self.selected_item_id = None
        self.excel_file_path_var = tk.StringVar()
        self.scanner_type_var = tk.StringVar(value="USB")
        self.com_port_var = tk.StringVar()
        self.baud_rate_var = tk.StringVar(value="9600")

        # --- Threading and Serial ---
        self.ser = None
        self.is_reading_com = False
        self.com_read_thread = None
        self._usb_listener_thread = None
        self._stop_usb_listener_event = threading.Event()

        # --- USB Keyboard Scanner State ---
        self.barcode_buffer = []
        self.last_key_time = 0
        self._pending_config_updates = {} # For staging config changes

        # --- Initialization ---
        self.build_tab()
        self._load_config()
        self._on_scanner_type_change() # Set initial UI state

    def build_tab(self):
        """Gebruikersinterface voor het scannerpaneel bouwen met grid-layout."""
        self.columnconfigure(0, weight=1)
        # Row 0: top_row_frame (Scanner Type & Excel File)
        # Row 1: scanner_options_frame
        # Row 2: tree_frame (this will expand)
        # Row 3: log_frame
        self.rowconfigure(2, weight=1)  # tree_frame zal uitbreiden

        # --- Hoofdcontainer voor bovenste rij (Scannertype en Excel-bestand) ---
        top_row_frame = ttk.Frame(self)
        top_row_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        top_row_frame.columnconfigure(0, weight=1)
        top_row_frame.columnconfigure(1, weight=1)

        # --- Scannertype Frame (links in top_row_frame) ---
        scanner_type_frame = ttk.Labelframe(top_row_frame, text="Scannertype")
        scanner_type_frame.grid(row=0, column=0, sticky="nsew", padx=(10,5), pady=5)

        # --- Excel-bestand Frame (rechts in top_row_frame) ---
        excel_frame = ttk.Labelframe(top_row_frame, text="Excel-bestand")
        excel_frame.grid(row=0, column=1, sticky="nsew", padx=(5,10), pady=5)
        excel_frame.columnconfigure(1, weight=1) # Zorgt ervoor dat entry-widget uitbreidt
        
        # --- Frame voor scanner-specifieke opties (onder top_row_frame) ---
        scanner_options_frame = ttk.Frame(self)
        scanner_options_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=0)
        scanner_options_frame.columnconfigure(0, weight=1)

        # --- PanedWindow for resizable Treeview and Log Viewer ---
        main_paned_window = ttk.PanedWindow(self, orient=tk.VERTICAL)
        main_paned_window.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)

        # --- Scangegevens Frame (Treeview) in Top Pane ---
        tree_frame = ttk.Labelframe(main_paned_window, text="Scangegevens")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        main_paned_window.add(tree_frame, weight=3) # Give more initial space to treeview

        # --- Log Viewer Frame in Bottom Pane ---
        log_frame = ttk.Labelframe(main_paned_window, text="Logboek")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_paned_window.add(log_frame, weight=1) # Give less initial space to log

        # --- Inhoud Scannertype Frame ---
        ttk.Radiobutton(scanner_type_frame, text="USB-toetsenbord", variable=self.scanner_type_var, value="USB", command=self._on_scanner_type_change).pack(side="left", padx=10, pady=5)
        ttk.Radiobutton(scanner_type_frame, text="COM-poort", variable=self.scanner_type_var, value="COM", command=self._on_scanner_type_change).pack(side="left", padx=10, pady=5)

        # --- Scanner-specifieke frames (geplaatst in scanner_options_frame) ---
        self.com_frame = ttk.Frame(scanner_options_frame)
        self.com_frame.grid(row=0, column=0, sticky="ew")
        self.com_frame.columnconfigure(1, weight=1)

        self.usb_frame = ttk.Frame(scanner_options_frame)
        self.usb_frame.grid(row=0, column=0, sticky="ew")

        # --- Inhoud Excel-bestand Frame ---
        ttk.Label(excel_frame, text="Bestandspad:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        excel_entry = ttk.Entry(excel_frame, textvariable=self.excel_file_path_var, state='readonly')
        excel_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        browse_button = ttk.Button(excel_frame, text="Bladeren...", command=self._browse_excel_file)
        browse_button.grid(row=0, column=2, padx=5, pady=5)

        # --- Inhoud COM-poort Frame ---
        ttk.Label(self.com_frame, text="COM-poort:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.com_port_combo = ttk.Combobox(self.com_frame, textvariable=self.com_port_var, state='readonly', width=10)
        self.com_port_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.refresh_com_button = ttk.Button(self.com_frame, text="Vernieuwen", command=self._update_com_ports)
        self.refresh_com_button.grid(row=0, column=2, padx=5, pady=5)
        self.connect_button = ttk.Button(self.com_frame, text="Verbinden", command=self._connect_com_port)
        self.connect_button.grid(row=0, column=3, padx=5, pady=5)

        # --- Inhoud USB Frame ---
        ttk.Label(self.usb_frame, text="USB-scanner is actief indien geselecteerd. Scans worden globaal vastgelegd.").pack(padx=5, pady=5, fill="x")

        # --- Treeview ---
        self.tree = ttk.Treeview(tree_frame, columns=('Status', 'Item'), show='headings')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Item', text='Item')
        self.tree.column('Status', width=150, minwidth=150, stretch=tk.NO, anchor='center') # Status column, centered text
        self.tree.column('Item', width=300, anchor='w')   # Item (was Barcode)
        # Define a bold font for the 'OK' status
        self.bold_ok_font = None # Initialize
        try:
            # Create a bold version of the default Tk font.
            default_font_details = tkfont.nametofont("TkDefaultFont").actual()
            self.bold_ok_font = tkfont.Font(family=default_font_details["family"],
                                         size=default_font_details["size"],
                                         weight="bold")
        except tk.TclError as e:
            self._log(f"[WARN] Kon vetgedrukt lettertype niet aanmaken voor 'OK' status (TclError): {e}. Gebruikt standaard.")
        except Exception as e: # Catch any other unexpected errors
            self._log(f"[WARN] Kon vetgedrukt lettertype niet aanmaken voor 'OK' status (Algemene Fout): {e}. Gebruikt standaard.")

        # Configure OK tag (bold font removed as it applies to the whole row)
        self.tree.tag_configure('OK', background='light green')
        self.tree.tag_configure('DUPLICATE', background='orange')
        self.tree.tag_configure('NOT_FOUND', background='light coral')
        self.tree.tag_configure('NOT_OK', background='white')
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        # --- Log Viewer ---
        self.log_text = tk.Text(log_frame, height=6, wrap=tk.WORD, state='disabled')
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.grid(row=0, column=0, sticky='nsew')
        log_scroll.grid(row=0, column=1, sticky='ns')

        # --- Context Menu ---
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Markeer als OK", command=self._mark_item_ok)
        self.context_menu.add_command(label="Status wissen", command=self._clear_item_status) # Changed from Markeer als NIET OK
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Initial setup
        self._log("Scannerpaneel geïnitialiseerd.")
        self._update_com_ports()

    # --- Configuration Helper Methods ---
    def _get_config_setting(self, section, key, default_value=None):
        config = _load_full_config()
        return config.get(section, {}).get(key, default_value)

    def _set_config_setting(self, section, key, value):
        if section not in self._pending_config_updates:
            self._pending_config_updates[section] = {}
        self._pending_config_updates[section][key] = value
        # Note: This does not save immediately. save_config() will handle that.

    def _load_config(self):
        """Loads configuration settings using the new helper method."""
        self.scanner_type_var.set(self._get_config_setting('Scanner', 'type', 'USB'))
        self.com_port_var.set(self._get_config_setting('Scanner', 'com_port', ''))
        self.baud_rate_var.set(self._get_config_setting('Scanner', 'baud_rate', '9600'))
        last_file = self._get_config_setting('Paths', 'last_excel_file', '')
        if last_file and os.path.exists(last_file):
            self.excel_file_path_var.set(last_file)
            # Call _load_excel_data without triggering another config save immediately
            # The config for last_file is already loaded here.
            # _load_excel_data will still update the treeview.
            super().after(10, lambda: self._load_excel_data(last_file, update_config_path=False))

    def save_config(self):
        """Saves accumulated configuration settings and clears pending updates."""
        # Stage current values before saving everything
        self._set_config_setting('Scanner', 'type', self.scanner_type_var.get())
        self._set_config_setting('Scanner', 'com_port', self.com_port_var.get())
        self._set_config_setting('Scanner', 'baud_rate', self.baud_rate_var.get())
        # self._set_config_setting('Paths', 'last_excel_file', self.excel_file_path_var.get()) # Already handled by _load_excel_data

        if self._pending_config_updates:
            _save_full_config(self._pending_config_updates)
            self._pending_config_updates.clear()
            self._log("Configuratie opgeslagen.")
        else:
            self._log("Geen configuratiewijzigingen om op te slaan.")

    def _log(self, message):
        """Adds a message to the log viewer with a timestamp."""
        # This check prevents errors if logging is called during shutdown
        if not self.winfo_exists():
            return
        def _do_log():
            if self.log_text.winfo_exists():
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                self.log_text.config(state='normal')
                self.log_text.insert(tk.END, f"{timestamp} - {message}\n")
                self.log_text.config(state='disabled')
                self.log_text.see(tk.END)
        self.after(0, _do_log)

    def _on_scanner_type_change(self, *args):
        """Verwerkt UI-wijzigingen wanneer het scannertype wordt gewijzigd."""
        scanner_type = self.scanner_type_var.get()
        self._log(f"Scannertype gewijzigd naar {scanner_type}.")
        if scanner_type == "COM":
            self.com_frame.grid(row=0, column=0, sticky="ew")
            self.usb_frame.grid_remove()
            self._stop_usb_listener()
            self._update_com_ports()
        elif scanner_type == "USB":
            self.usb_frame.grid(row=0, column=0, sticky="ew")
            self.com_frame.grid_remove()
            self._disconnect_com_port()
            self._start_usb_listener()
        else:
            self.com_frame.grid_remove()
            self.usb_frame.grid_remove()

    def _browse_excel_file(self):
        """Opent een dialoogvenster om een Excel-bestand te selecteren."""
        file_path = filedialog.askopenfilename(
            title="Selecteer Excel-bestand",
            filetypes=(("Excel-bestanden", "*.xlsx *.xls"), ("Alle bestanden", "*.*"))
        )
        if file_path:
            self._load_excel_data(file_path)

    def _generate_updated_path(self, original_path):
        """Generates the path for the '_updated' version of an Excel file."""
        if not original_path:
            return None
        directory, filename = os.path.split(original_path)
        name, ext = os.path.splitext(filename)
        if name.endswith("_updated"):
            return original_path # Already an updated path
        updated_name = f"{name}_updated{ext}"
        return os.path.join(directory, updated_name)

    def _load_excel_data(self, file_path, update_config_path=True):
        """Laadt gegevens uit het geselecteerde Excel-bestand en vult de treeview."""
        try:
            path_to_load = file_path
            potential_updated_path = self._generate_updated_path(file_path)
            if potential_updated_path and os.path.exists(potential_updated_path):
                self._log(f"Laden van bijgewerkte versie: {potential_updated_path}")
                path_to_load = potential_updated_path
            else:
                self._log(f"Laden van origineel bestand: {file_path}")

            self._log(f"Effectief Excel-bestand laden: {path_to_load}")
            df = pd.read_excel(path_to_load)

            # Updated column check: 'Item' is required.
            if 'Item' not in df.columns:
                messagebox.showerror("Fout", "Excel-bestand moet de kolom 'Item' bevatten.")
                self._log("[FOUT] Excel-bestand mist vereiste kolom 'Item'.")
                return

            self.barcode_data.clear()
            self.tree.delete(*self.tree.get_children()) # Clear existing tree items

            for index, row in df.iterrows():
                barcode_val = str(row['Item']).strip() # Strip leading/trailing whitespace
                description_val = str(row['Omschrijving']) if 'Omschrijving' in df.columns else ""

                # --- Start of new logic for status handling ---
                raw_status_from_excel = row.get('Status', pd.NA) # Use pd.NA for missing/empty

                display_status_for_treeview = ""  # Value for Treeview display
                internal_status = 'NIET OK'       # Value for internal logic and saving
                tree_tag = 'NOT_OK'               # Default tag for Treeview

                if pd.isna(raw_status_from_excel):
                    # If Excel status is NaN (empty), display blank, internal is 'NIET OK'
                    display_status_for_treeview = ""
                    # internal_status is already 'NIET OK'
                    # tree_tag is already 'NOT_OK' (white background)
                else:
                    # If Excel status is not NaN, process it as a string
                    processed_status_str = str(raw_status_from_excel).strip().upper()

                    if processed_status_str == 'OK':
                        display_status_for_treeview = 'OK'
                        internal_status = 'OK'
                        tree_tag = 'OK'
                    elif processed_status_str == 'DUPLICAAT':
                        display_status_for_treeview = 'DUPLICAAT'
                        internal_status = 'DUPLICAAT'
                        tree_tag = 'DUPLICATE'
                    elif processed_status_str == 'NIET OK':
                        display_status_for_treeview = 'NIET OK'
                        internal_status = 'NIET OK'
                        tree_tag = 'NOT_OK'
                    else:
                        # Unrecognized string in Status column
                        self._log(f"[WARN] Ongeldige status '{processed_status_str}' (origineel: '{raw_status_from_excel}') voor item '{barcode_val}' in Excel. Standaard naar 'NIET OK'.")
                        display_status_for_treeview = 'NIET OK' # Display 'NIET OK' for unrecognized strings
                        internal_status = 'NIET OK' # Treat as 'NIET OK'
                        tree_tag = 'NOT_OK'
                # --- End of new logic for status handling ---

                # Treeview: Status, Item.
                item_id = self.tree.insert('', 'end', values=(display_status_for_treeview, barcode_val), tags=(tree_tag,))
                self.barcode_data[barcode_val] = {
                    'description': description_val,
                    'status': internal_status, # Store the determined internal_status
                    'id': item_id,
                    'item_value': barcode_val
                }

            self._log(f"{len(self.barcode_data)} items geladen uit {os.path.basename(path_to_load)}.")
            # self.excel_file_path_var should store the original path selected by the user
            # or the path that was last loaded from config, to correctly derive _updated path for saving.
            self.excel_file_path_var.set(file_path) 
            if update_config_path:
                # Save the original user-selected path to config, not the potentially loaded _updated one.
                self._set_config_setting('Paths', 'last_excel_file', file_path)
                self.save_config() 
            # After loading, immediately save to ensure the loaded data (even from original) is in an _updated file if changes occur
            # Or, only save when a change actually occurs. Let's opt for saving on change.
            # self._save_updated_excel() # Consider if initial save is needed or only on change.
        except FileNotFoundError:
            messagebox.showerror("Fout", f"Bestand niet gevonden: {file_path}")
            self._log(f"[FOUT] Bestand niet gevonden: {file_path}")
        except Exception as e:
            messagebox.showerror("Fout", f"Lezen van Excel-bestand mislukt: {e}")
            self._log(f"[FOUT] Lezen van Excel-bestand mislukt: {e}")

    def _check_barcode(self, barcode):
        """Controleert de gescande barcode aan de hand van de geladen gegevens en werkt de UI bij."""
        self._log(f"Barcode controleren: {barcode}")

        # Prioritize an exact match (fast and default)
        item = self.barcode_data.get(barcode)
        original_barcode_from_excel = barcode if item else None

        # If no exact match, try a more lenient match by ignoring all whitespace
        if not item:
            self._log(f"Exacte match niet gevonden. Poging tot een meer flexibele match...")
            # Normalize by removing all whitespace characters
            normalized_scanned = re.sub(r'\s', '', barcode)
            for key, value in self.barcode_data.items():
                normalized_key = re.sub(r'\s', '', key)
                if normalized_key == normalized_scanned:
                    item = value
                    original_barcode_from_excel = key
                    self._log(f"Flexibele match gevonden! Scanner: '{barcode}', Excel: '{original_barcode_from_excel}'")
                    break # Stop after finding the first match

        if not item:
            self._log(f"[NIET GEVONDEN] Barcode {barcode} niet in de lijst.")
            # Overweeg een optische/auditieve feedback voor niet gevonden barcodes
            return

        item_id = item['id']
        current_status = item['status']

        # Use the original barcode from Excel for logging if a lenient match was found
        log_barcode = original_barcode_from_excel

        if current_status == 'OK':
            self._log(f"[WAARSCHUWING] Item '{log_barcode}' is al gescand en gemarkeerd als OK. Dubbele scan genegeerd.")
            # No change to item['status'], no _update_treeview, item remains OK
        elif current_status == 'DUPLICAAT':
            self._log(f"[WAARSCHUWING] Item '{log_barcode}' is al eerder als DUPLICAAT gescand. Verdere scan genegeerd.")
            # No change to item['status'], no _update_treeview, item remains DUPLICATE
        else: # This implies current_status is 'NIET OK' or similar (e.g., empty from Excel)
            self._log(f"[OK] Barcode {log_barcode} komt overeen en is nu gemarkeerd als OK.")
            item['status'] = 'OK'
            self._update_treeview(item_id, 'OK')
            self._save_updated_excel() # Save changes
            self._all_items_ok_check()


    def _all_items_ok_check(self):
        """Checks if all items are OK, then triggers completion actions and optional archiving."""
        if not self.barcode_data:
            return

        all_ok = all(item['status'] in ['OK', 'DUPLICATE'] for item in self.barcode_data.values())

        if all_ok:
            self._log("Alle items zijn OK. Voltooiingsacties worden gestart.")
            
            # Perform the main completion actions (DB, email, etc.).
            # This function will show its own completion message.
            self._perform_completion_actions()

            # Now, handle archiving.
            config = {}
            config_file_path = get_config_path()
            if os.path.exists(config_file_path):
                with open(config_file_path, 'r') as f:
                    try:
                        config = json.load(f)
                    except json.JSONDecodeError:
                        self._log(f"[FOUT] Kon configuratiebestand niet lezen (JSON decode error): {config_file_path}")
                        messagebox.showerror("Configuratie Fout", f"Fout bij het lezen van het configuratiebestand.\nControleer of {config_file_path} een valide JSON-bestand is.")
                        return # Stop if config is corrupt
            else:
                self._log(f"[WAARSCHUWING] Configuratiebestand niet gevonden: {config_file_path}")
                # Allow to proceed with defaults if config file is missing, api_url will be empty

            archive_enabled = config.get('archive_on_all_ok', False)

            if archive_enabled:
                self._log("Archivering is ingeschakeld. Starten met archiveren.")
                # Use 'after' to avoid blocking the UI thread for the archiving process.
                # _archive_files will show its own message and then clear the panel.
                self.after(100, self._archive_files)
            else:
                self._log("Archivering is uitgeschakeld. Paneel wordt gereset om een nieuwe batch te starten.")
                # If not archiving, we still need to clear the panel to start a new batch.
                self._clear_panel_state()

    def _archive_files(self):
        """Archives the original and updated Excel files to an 'Archief' subfolder."""
        original_path = self.excel_file_path_var.get()
        if not original_path:
            self._log("[FOUT] Kan niet archiveren: geen Excel-bestandspad beschikbaar.")
            messagebox.showerror("Archiveringsfout", "Kan niet archiveren: geen Excel-bestandspad beschikbaar.")
            return

        updated_path = self._generate_updated_path(original_path)
        
        try:
            directory = os.path.dirname(original_path)
            archive_dir = os.path.join(directory, "Archief")
            
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
                self._log(f"Archiefmap aangemaakt: {archive_dir}")

            files_to_move = []
            if os.path.exists(original_path):
                files_to_move.append(original_path)
            if updated_path and os.path.exists(updated_path):
                files_to_move.append(updated_path)

            if not files_to_move:
                self._log("Geen bestanden gevonden om te archiveren.")
                messagebox.showwarning("Archiveren", "Kon de Excel-bestanden niet vinden om te archiveren.")
                return

            for file_path in files_to_move:
                filename = os.path.basename(file_path)
                destination = os.path.join(archive_dir, filename)
                
                if os.path.exists(destination):
                    name, ext = os.path.splitext(filename)
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    new_filename = f"{name}_{timestamp}{ext}"
                    destination = os.path.join(archive_dir, new_filename)
                    self._log(f"[WAARSCHUWING] Bestemming '{filename}' bestaat al. Hernoemen naar '{new_filename}'.")

                os.rename(file_path, destination)
                self._log(f"'{filename}' gearchiveerd naar '{destination}'")

            messagebox.showinfo("Archivering Voltooid", 
                                "Alle items zijn OK. De bestanden zijn gearchiveerd in de map 'Archief'.")
            
            self._clear_panel_state()

        except Exception as e:
            self._log(f"[FOUT] Fout tijdens archiveren: {e}")
            messagebox.showerror("Archiveringsfout", f"Er is een fout opgetreden tijdens het archiveren van de bestanden:\n{e}")

    def _clear_panel_state(self):
        """Resets the panel to its initial state after completion and/or archiving."""
        self.tree.delete(*self.tree.get_children())
        self.barcode_data.clear()
        self.excel_file_path_var.set("")
        self._log("Paneel gereset.")
        self._set_config_setting('Paths', 'last_excel_file', '')
        self.save_config()

    def _update_com_ports(self):
        """Updates the list of available COM ports."""
        try:
            ports = [port.device for port in serial.tools.list_ports.comports()]
            self.com_port_combo['values'] = ports
            if ports:
                # If current selection is not in new list, or nothing is selected, select first port
                if self.com_port_var.get() not in ports or not self.com_port_var.get():
                    self.com_port_var.set(ports[0])
            else:
                self.com_port_var.set('') # No ports available
            self._log(f"Beschikbare COM-poorten bijgewerkt: {ports if ports else 'Geen'}")
        except Exception as e:
            self._log(f"[FOUT] Kon COM-poorten niet oplijsten: {e}")
            messagebox.showerror("COM Fout", f"Fout bij het oplijsten van COM-poorten: {e}")
            self.com_port_combo['values'] = []
            self.com_port_var.set('')

    def _connect_com_port(self):
        """Connects to or disconnects from the selected COM port."""
        if self.ser and self.ser.is_open:
            self._disconnect_com_port()
            return
        port = self.com_port_var.get()
        if not port:
            messagebox.showerror("Fout", "Geen COM-poort geselecteerd.")
            self._log("[FOUT] Verbindingspoging mislukt: Geen COM-poort geselecteerd.")
            return
        try:
            self.ser = serial.Serial(port=port, baudrate=int(self.baud_rate_var.get()), timeout=1)
            self.is_reading_com = True
            self.com_read_thread = threading.Thread(target=self._read_com_port, daemon=True)
            self.com_read_thread.start()
            self.connect_button.config(text="Verbinding verbreken")
            self._log(f"Verbonden met {port}.")
            self.com_port_combo.config(state='disabled')
            self.refresh_com_button.config(state='disabled')
        except serial.SerialException as e:
            messagebox.showerror("Verbindingsfout", f"Verbinden met {port} mislukt: {e}")
            self._log(f"[FOUT] Verbinden met {port} mislukt: {e}")
            self.ser = None

    def _disconnect_com_port(self):
        """Disconnects from the serial port."""
        self.is_reading_com = False
        if self.com_read_thread and self.com_read_thread.is_alive():
            self.com_read_thread.join(timeout=1)
        if self.ser and self.ser.is_open:
            port_name = self.ser.port
            self.ser.close()
            self._log(f"Verbinding verbroken met {port_name}.")
        self.ser = None
        if self.winfo_exists():
            self.connect_button.config(text="Verbinden")
            self.com_port_combo.config(state='readonly')
            self.refresh_com_button.config(state='normal')

    def _read_com_port(self):
        """Leest gegevens van de seriële poort in een aparte thread."""
        port_name = self.ser.port # Store before thread potentially outlives self.ser validity
        self._log(f"COM-poort leesthread gestart voor {port_name}.")
        while self.is_reading_com and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        self._log(f"COM-gegevens ontvangen: {line}")
                        self.after(0, self._check_barcode, line)
            except serial.SerialException as e:
                self._log(f"[FOUT] Seriële fout: {e}")
                break # Exit thread on serial error
            except Exception as e:
                self._log(f"[FOUT] Een onverwachte fout is opgetreden in de COM-leeslus: {e}")
                break # Exit thread on other critical error
            time.sleep(0.1)
        self._log(f"COM-poort leesthread voor {port_name} beëindigd.")

    def _start_usb_listener(self):
        """Starts the USB keyboard listener thread."""
        if self.scanner_type_var.get() != "USB":
            return
        if self._usb_listener_thread and self._usb_listener_thread.is_alive():
            return
        self._stop_usb_listener_event.clear()
        self._usb_listener_thread = threading.Thread(target=self._usb_listener_loop, daemon=True)
        self._usb_listener_thread.start()

    def _stop_usb_listener(self):
        """Stops the USB keyboard listener thread."""
        if self._usb_listener_thread and self._usb_listener_thread.is_alive():
            self._stop_usb_listener_event.set()
            self._usb_listener_thread.join(timeout=1)
            self._usb_listener_thread = None
            self._log("USB listener stop signal sent.")

    def _usb_listener_loop(self):
        """De lus die luistert naar toetsenbordgebeurtenissen."""
        self._log("USB-luisterthread gestart.")
        keyboard.on_press(self._on_key_press)
        self._stop_usb_listener_event.wait()
        keyboard.unhook_all()
        self._log("USB-luisterthread gestopt.")

    def _on_key_press(self, event):
        """Callback for the keyboard listener."""
        if self._stop_usb_listener_event.is_set():
            return
        self.after(0, self._process_key_event, event)

    def _process_key_event(self, event):
        """Process the key event in the main thread."""
        if not self.winfo_exists():
            return
        current_time = time.time()
        if current_time - self.last_key_time > 0.1: # Timeout to reset buffer
            self.barcode_buffer.clear()

        self.last_key_time = current_time

        if event.name == 'enter':
            if self.barcode_buffer:
                barcode = "".join(self.barcode_buffer)
                self._log(f"USB-scan gedetecteerd: {barcode}")
                self._check_barcode(barcode)
                self.barcode_buffer.clear()
        elif len(event.name) == 1:
            self.barcode_buffer.append(event.name)

    def _update_treeview(self, item_id, status_tag, display_override=None):
        """Updates a single item in the treeview with a new status and tag."""
        original_barcode_val = None
        for barcode_key, data_dict in self.barcode_data.items():
            if data_dict.get('id') == item_id:
                original_barcode_val = data_dict.get('item_value', barcode_key)
                break
        
        if original_barcode_val is None:
            try:
                current_values = self.tree.item(item_id, 'values')
                if current_values and len(current_values) > 1:
                    original_barcode_val = current_values[1] # Item is at index 1
                else:
                    self._log(f"[FOUT] Kon originele itemwaarde niet vinden voor treeview-update (ID: {item_id}) en tree-item-waarden zijn ongeldig.")
                    return # Return if we can't get the barcode value
            except tk.TclError:
                 self._log(f"[FOUT] Kon originele itemwaarde niet vinden voor treeview-update (ID: {item_id}) en tree-item niet toegankelijk.")
                 return # Return if tree item is not accessible

        new_status_text = ''
        if display_override is not None:
            new_status_text = display_override
        elif status_tag == 'OK':
            new_status_text = 'OK'
        elif status_tag == 'DUPLICATE':
            new_status_text = 'DUPLICAAT'
        elif status_tag == 'NOT_OK':
            # If it's 'NOT_OK' and no override, it implies 'NIET OK' unless cleared
            # The previous logic in _load_excel_data already handles setting blank for initial load if status is NaN
            # For manual clearing, display_override="" is used.
            # For marking as 'NIET OK' explicitly (if that was still a feature), it would be 'NIET OK'.
            new_status_text = 'NIET OK' 
        else:
            # Fallback if an unexpected tag is passed
            new_status_text = status_tag 
            self._log(f"[WARN] Onverwachte status_tag '{status_tag}' ontvangen in _update_treeview zonder display_override.")

        try:
            self.tree.item(item_id, values=(new_status_text, original_barcode_val), tags=(status_tag,))
            self.tree.see(item_id) # Scroll to the updated item
        except tk.TclError as e:
            self._log(f"[FOUT] Kon item {item_id} niet bijwerken in de treeview: {e}")

    def _on_tree_select(self, event):
        """Handle item selection in the treeview to store the selected item ID."""
        selected_items = self.tree.selection()
        if selected_items:
            self.selected_item_id = selected_items[0]

    def _show_context_menu(self, event):
        """Display the context menu at the cursor's position."""
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            self.selected_item_id = item_id
            self.context_menu.post(event.x_root, event.y_root)

    def _clear_item_status(self):
        """Clears the status of the selected item in the treeview and data."""
        if not self.selected_item_id:
            self._log("[WARN] Poging om status te wissen zonder selectie.")
            return

        # Find the item in barcode_data using the tree item_id
        item_to_update = None
        barcode_key_of_item = None
        for key, data_dict in self.barcode_data.items():
            if data_dict.get('id') == self.selected_item_id:
                item_to_update = data_dict
                barcode_key_of_item = key
                break

        if item_to_update:
            self._log(f"Status wissen voor item: {item_to_update.get('item_value', barcode_key_of_item)}")
            item_to_update['status'] = None  # Set internal status to None for blank Excel cell
            # Update Treeview: display blank, use 'NOT_OK' tag for white background
            self._update_treeview(self.selected_item_id, 'NOT_OK', display_override="") 
            self._save_updated_excel() # Save changes
        else:
            self._log(f"[FOUT] Kon item met ID {self.selected_item_id} niet vinden in barcode_data om status te wissen.")

    def _mark_item_ok(self):
        """Manually mark the selected item as OK."""
        if not self.selected_item_id:
            self._log("[INFO] Geen item geselecteerd om als OK te markeren.")
            return
        
        # Treeview columns are ('Status', 'Item'). 'Item' (barcode value) is at index 1.
        try:
            selected_values = self.tree.item(self.selected_item_id, 'values')
            if not selected_values or len(selected_values) < 2:
                self._log(f"[FOUT] Kon item {self.selected_item_id} niet markeren als OK: ongeldige item-waarden.")
                return
            barcode = selected_values[1]
        except tk.TclError:
            self._log(f"[FOUT] Kon item {self.selected_item_id} niet markeren als OK: treeview-fout bij ophalen waarden.")
            return

        if barcode in self.barcode_data:
            self.barcode_data[barcode]['status'] = 'OK'
            self._update_treeview(self.selected_item_id, 'OK')
            self._log(f"{barcode} handmatig gemarkeerd als OK.")
            self._save_updated_excel() # Save changes
            self._all_items_ok_check()

    def _mark_item_not_ok(self):
        """Manually mark the selected item as NOT OK."""
        if not self.selected_item_id:
            self._log("[INFO] Geen item geselecteerd om als NIET OK te markeren.")
            return
        
        # Treeview columns are ('Status', 'Item'). 'Item' (barcode value) is at index 1.
        try:
            selected_values = self.tree.item(self.selected_item_id, 'values')
            if not selected_values or len(selected_values) < 2:
                self._log(f"[FOUT] Kon item {self.selected_item_id} niet markeren als NIET OK: ongeldige item-waarden.")
                return
            barcode = selected_values[1]
        except tk.TclError:
            self._log(f"[FOUT] Kon item {self.selected_item_id} niet markeren als NIET OK: treeview-fout bij ophalen waarden.")
            return

        if barcode in self.barcode_data:
            self.barcode_data[barcode]['status'] = 'NIET OK'
            self._update_treeview(self.selected_item_id, 'NOT_OK') # Use tag for consistency
            self._log(f"{barcode} handmatig gemarkeerd als NIET OK.")
            self._save_updated_excel() # Save changes

    def _save_updated_excel(self):
        """Saves the current state of barcode_data to a new Excel file with '_updated' suffix.
           Ensures that None status is written as a blank cell.
        """
        original_path = self.excel_file_path_var.get()
        if not original_path:
            self._log("[WARN] Kan status niet opslaan: geen Excel-bestandspad ingesteld.")
            return

        save_path = self._generate_updated_path(original_path)
        if not save_path:
            self._log("[FOUT] Kan geen geldig opslagpad genereren voor bijgewerkt Excel-bestand.")
            return

        if not self.barcode_data:
            self._log("[INFO] Geen data om op te slaan in bijgewerkt Excel-bestand.")
            # Optionally, if an _updated file exists, we might want to delete it or leave it.
            # For now, do nothing if no data.
            return

        try:
            data_to_save = []
            for barcode_val, item_data in self.barcode_data.items():
                data_to_save.append({
                    'Item': item_data.get('item_value', barcode_val),
                    'Status': item_data.get('status'), # Ensure None is preserved for blank cell
                    'Omschrijving': item_data.get('description', '')
                })
            
            df = pd.DataFrame(data_to_save)
            # Ensure column order, especially if Omschrijving might be missing in some items
            columns_ordered = ['Item', 'Status']
            if any('Omschrijving' in d for d in data_to_save):
                 if not df['Omschrijving'].isnull().all(): # only add if there's actual data
                    columns_ordered.append('Omschrijving')
            df = df[columns_ordered]

            df.to_excel(save_path, index=False)
            self._log(f"Status succesvol opgeslagen in {os.path.basename(save_path)}.")
        except Exception as e:
            self._log(f"[FOUT] Opslaan van bijgewerkt Excel-bestand {save_path} mislukt: {e}")
            messagebox.showerror("Opslaan Mislukt", f"Kon status niet opslaan naar {os.path.basename(save_path)}: {e}")

    def _extract_project_codes_from_filename_base(self, filename_base):
        """
        Extracts the base MO/Accura code and the full project code from a filename base.
        Strips leading date-like prefixes (e.g., MMDD_, YYYY_) from the full_project_code
        if the prefix is followed by the base_mo_code.
        Example: "MO07834" -> ("MO07834", "MO07834")
                 "0618_MO07834_Boekenkast_Rep_VL5" -> ("MO07834", "MO07834_Boekenkast_Rep_VL5")
        Returns (base_mo_code, full_project_code)
        """
        # re is imported at the module level

        full_project_code = filename_base
        base_mo_code = ""

        # Try to find MOxxxxx pattern, case-insensitive, within the full_project_code
        mo_match = re.search(r'(MO\d{5})', full_project_code, re.IGNORECASE)
        if mo_match:
            base_mo_code = mo_match.group(0).upper()
        else:
            # Fallback for ACCURA style 5-6 digit codes if MO not found
            accura_match = re.search(r'(\d{5,6})', full_project_code)
            if accura_match:
                base_mo_code = accura_match.group(0)

        # If a base_mo_code was found and the full_project_code is potentially prefixed
        if base_mo_code and len(full_project_code) > len(base_mo_code):
            try:
                # Find the starting position of base_mo_code (case-insensitive) in full_project_code
                start_index_of_base = full_project_code.upper().find(base_mo_code.upper())

                if start_index_of_base > 0:  # base_mo_code is found and it's not at the very beginning
                    potential_prefix = full_project_code[:start_index_of_base]
                    # Check if this potential_prefix is exactly a 4-digit date-like prefix (e.g., "0618_")
                    if re.fullmatch(r"\d{4}_", potential_prefix):
                        # If it matches, strip the prefix from full_project_code
                        full_project_code = full_project_code[len(potential_prefix):]
            except AttributeError:
                # This might occur if base_mo_code or full_project_code is not a string, though unlikely here.
                # Log or handle as appropriate if this case needs specific error recovery.
                pass
                
        return base_mo_code, full_project_code

    def _perform_completion_actions(self):
        """Handles all actions after all items are successfully scanned.
        This includes logging, database updates, and email notifications.
        """
        self._log("Alle items zijn succesvol gescand! Acties na voltooiing worden uitgevoerd.")
        
        excel_full_path = self.excel_file_path_var.get()
        if not excel_full_path:
            self._log("[FOUT] Kan project niet afmelden: Excel-bestandspad niet beschikbaar.")
            messagebox.showerror("Fout bij Afmelden", "Kan project niet afmelden: Excel-bestandspad niet beschikbaar.")
            return

        filename_with_ext = os.path.basename(excel_full_path)
        filename_base, _ = os.path.splitext(filename_with_ext)

        base_mo_code, full_project_code = self._extract_project_codes_from_filename_base(filename_base)

        if not full_project_code:
            self._log(f"[FOUT] Kan projectcode niet afleiden uit bestandsnaam: {filename_base}")
            messagebox.showerror("Fout bij Afmelden", f"Kan projectcode niet afleiden uit bestandsnaam: {filename_base}")
            return

        config = {}
        config_file_path = get_config_path()
        if os.path.exists(config_file_path):
            with open(config_file_path, 'r') as f:
                try:
                    config = json.load(f)
                except json.JSONDecodeError:
                    self._log(f"[FOUT] Kon configuratiebestand niet lezen (JSON decode error): {config_file_path}")
                    messagebox.showerror("Configuratie Fout", f"Fout bij het lezen van het configuratiebestand.\nControleer of {config_file_path} een valide JSON-bestand is.")
                    return # Stop if config is corrupt
        else:
            self._log(f"[WAARSCHUWING] Configuratiebestand niet gevonden: {config_file_path}")
            # Allow to proceed with defaults if config file is missing, api_url will be empty

        # Read API URL and username consistent with DatabasePanel
        api_url = config.get('api_url', '') # Reads 'api_url' from the root of the config
        current_user = config.get('user', 'BarcodeMatchUser') # Reads 'user' from the root of the config
        
        db_panel = self.main_app.get_panel_by_name("Database")
        if db_panel is not None:
            try:
                if db_panel.database_enabled_var.get():
                    self._log(f"Database logging ingeschakeld. Project '{full_project_code}' wordt als gesloten gelogd.")
                    is_rep_variant = '_REP_' in full_project_code.upper()
                    db_panel.log_project_closed(full_project_code, base_mo_code=base_mo_code, is_rep_variant=is_rep_variant)
                else:
                    self._log("Database logging is niet ingeschakeld.")
            except AttributeError:
                self._log("[FOUT] Attribuut 'database_enabled_var' of 'log_project_closed' niet gevonden op Database paneel.")
            except Exception as e:
                self._log(f"[FOUT] Kon projectstatus niet loggen naar database: {e}")
        else:
            self._log("[WARN] Database paneel niet gevonden via self.main_app.get_panel_by_name('Database'). Overslaan database logging.")

        # --- 2. Email Notification ---
        email_panel = self.main_app.get_panel_by_name("Email")
        if email_panel is not None:
            try:
                email_is_enabled = email_panel.email_enabled_var.get()
                email_mode_is_per_scan = email_panel.email_send_mode_var.get() == 'per_scan'

                if email_is_enabled and email_mode_is_per_scan:
                    self._log(f"Email-notificatie voorbereiden voor project '{full_project_code}' (emails ingeschakeld, modus 'per_scan').")
                    email_panel.send_project_complete_email(full_project_code, excel_path)
                elif not email_is_enabled:
                    self._log(f"Email notificatie overgeslagen voor project '{full_project_code}': emails zijn niet ingeschakeld in Email paneel.")
                elif not email_mode_is_per_scan:
                    current_mode = email_panel.email_send_mode_var.get()
                    self._log(f"Email notificatie overgeslagen voor project '{full_project_code}': email modus is '{current_mode}', niet 'per_scan'.")
            except AttributeError:
                self._log("[FOUT] Benodigde attributen (bv. 'email_enabled_var', 'email_send_mode_var', 'send_project_complete_email') niet gevonden op Email paneel.")
            except Exception as e:
                self._log(f"[FOUT] Fout bij verwerken email notificatie voor project '{full_project_code}': {e}")
        else:
            self._log("[WARN] Email paneel niet gevonden via self.main_app.get_panel_by_name('Email'). Overslaan email notificatie.")


    def on_close(self):
        """Verwerkt opschoning wanneer het paneel wordt gesloten."""
        self._log("Scannerpaneel sluiten...")
        self.save_config()
        self._stop_usb_listener()
        self._disconnect_com_port()
        self._log("Scannerpaneel gesloten.")
