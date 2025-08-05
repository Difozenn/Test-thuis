import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont
import pandas as pd
import threading
import time
import keyboard
import serial
import serial.tools.list_ports
import os
import re
import requests
import json
from datetime import datetime
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
        
        # --- Session Tracking ---
        self.current_session_id = None
        self.session_start_time = None
        self.session_item_count = 0
        self.session_paused = False
        self.pause_start_time = None
        self.total_pause_duration = 0

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
        self.tree.bind("<Double-1>", self._on_tree_double_click)

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

    def _log(self, message, level="info", show_timestamp=True):
        """Enterprise-grade logging with professional formatting."""
        # This check prevents errors if logging is called during shutdown
        if not self.winfo_exists():
            return
            
        # Filter out technical noise - keep only user-relevant messages
        formatted_message = self._format_user_message(message)
        if not formatted_message:
            return
            
        def _do_log():
            if self.log_text.winfo_exists():
                timestamp = datetime.now().strftime("%H:%M:%S") if show_timestamp else ""
                full_message = f"[{timestamp}] {formatted_message}" if timestamp else formatted_message
                self.log_text.config(state='normal')
                self.log_text.insert(tk.END, f"{full_message}\n")
                self.log_text.config(state='disabled')
                self.log_text.see(tk.END)
        self.after(0, _do_log)
    
    def _ensure_url_protocol(self, url):
        """Ensure URL has http:// or https:// protocol"""
        if url and not url.startswith(('http://', 'https://')):
            return f'http://{url}'
        return url
    
    def _format_user_message(self, message):
        """Convert technical messages to clean, professional Dutch messages."""
        # Skip technical noise
        skip_patterns = [
            "Debug:", "DEBUG", "_extract_", "Effectief Excel-bestand laden:",
            "Background task", "API call", "non-blocking", "Laden van origineel bestand:",
            "Laden van bijgewerkte versie:", "Session started for", "Session ended:",
            "Failed to start session", "Failed to end session", "failed with status:"
        ]
        
        if any(pattern in message for pattern in skip_patterns):
            return None
            
        # Convert technical messages to user-friendly messages with icons
        conversions = {
            # File operations
            "Barcode controleren:": None,  # Too technical
            "Exacte match niet gevonden. Poging tot een meer flexibele match...": None,  # Too technical
            
            # Success messages
            "items geladen uit": lambda m: f"✓ Excel bestand geladen: {m.split('items geladen uit')[0].strip()} items uit {m.split('items geladen uit')[1].strip()}",
            "Flexibele match gevonden!": lambda m: f"✓ Barcode gevonden (flexibele matching)",
            "[OK] Barcode": lambda m: f"✓ Item gescand: {m.split('komt overeen')[0].replace('[OK] Barcode ', '').strip()}",
            "handmatig gemarkeerd als OK": lambda m: f"✓ Item handmatig gemarkeerd: {m.split('Item')[1].split('handmatig')[0].strip()}",
            "[VOLTOOID] Alle items zijn nu OK!": "🎉 Scan voltooid - alle items gescand!",
            "Excel-bestand opgeslagen als:": lambda m: f"✓ Voortgang opgeslagen: {m.split('als:')[1].strip()}",
            
            # Warning messages  
            "[WAARSCHUWING] Item": lambda m: f"⚠️ Dubbele scan: {m.split('Item')[1].split('is al')[0].strip().strip(chr(39))} al gescand",
            "[WARN]": lambda m: f"⚠️ {m.split('[WARN]')[1].strip()}",
            
            # Error messages
            "[NIET GEVONDEN] Barcode": lambda m: f"❌ Barcode niet gevonden: {m.split('Barcode')[1].split('niet in')[0].strip()}",
            "[FOUT]": lambda m: f"❌ {m.split('[FOUT]')[1].strip()}",
            "Geen toestemming om bestand te overschrijven": "❌ Geen schrijfrechten voor bestand",
            
            # Info messages
            "Scannertype gewijzigd naar": lambda m: f"ℹ️ Scanner: {m.split('naar')[1].strip()}",
            "Scannerpaneel geïnitialiseerd": "ℹ️ Scanner panel gereed",
            "Configuratie opgeslagen": "ℹ️ Instellingen opgeslagen",
            "USB-luisteraar gestart": "ℹ️ USB scanner actief",
            "USB-luisteraar gestopt": "ℹ️ USB scanner gestopt",
            "COM-poort verbonden": lambda m: f"ℹ️ Scanner verbonden: {m.split('op')[1].strip() if 'op' in m else 'COM poort'}",
            "COM-poort verbroken": "ℹ️ Scanner verbinding verbroken"
        }
        
        # Apply conversions
        for pattern, replacement in conversions.items():
            if pattern in message:
                if replacement is None:
                    return None
                elif callable(replacement):
                    return replacement(message)
                else:
                    return replacement
        
        # For messages that don't match patterns, apply basic cleanup
        cleaned = message.strip()
        
        # Skip empty or very technical messages
        if not cleaned or len(cleaned) < 3:
            return None
            
        return cleaned

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

    def load_project_excel(self, excel_file_path):
        """Public method to load a project's Excel file into the scanner panel."""
        self._log(f"Laden van project Excel via externe aanroep: {excel_file_path}")
        if excel_file_path and os.path.exists(excel_file_path):
            self._load_excel_data(excel_file_path, update_config_path=True)
        elif excel_file_path:
            messagebox.showerror("Bestand niet gevonden", f"Het opgegeven Excel-bestand kon niet worden gevonden:\n{excel_file_path}")
            self._log(f"[FOUT] Extern opgegeven Excel-bestand niet gevonden: {excel_file_path}")
        else:
            messagebox.showerror("Geen bestand opgegeven", "Geen Excel-bestandspad opgegeven om te laden.")
            self._log("[FOUT] Geen Excel-bestandspad opgegeven voor externe lading.")

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
            # Log current session state
            self._log(f"[DEBUG] _load_excel_data - current session: {self.current_session_id}, paused: {self.session_paused}")
            
            # Start session when Excel file is loaded (user begins working)
            self._start_session_for_excel_work(file_path)
            
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
                self._log("[FOUT] Excel-bestand mist vereiste kolom 'Item'.", "error")
                return

            self.barcode_data.clear()
            self.tree.delete(*self.tree.get_children()) # Clear existing tree items

            for index, row in df.iterrows():
                barcode_val = str(row['Item']).strip() # Strip leading/trailing whitespace
                description_val = str(row['Omschrijving']) if 'Omschrijving' in df.columns else ""

                # --- Start of new logic for status handling ---
                raw_status_from_excel = row.get('Status', pd.NA) # Use pd.NA for missing/empty

                display_status_for_treeview = ""  # Value for Treeview display (default empty)
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
                    elif processed_status_str == 'DUPLICAAT' or processed_status_str == 'NIET OK' or processed_status_str == 'DUPLICATE':
                        # For DUPLICAAT or NIET OK, show empty in treeview but keep internal status
                        display_status_for_treeview = "" 
                        internal_status = processed_status_str
                        tree_tag = 'NOT_OK'
                    else:
                        # Unrecognized string in Status column
                        self._log(f"[WARN] Ongeldige status '{processed_status_str}' (origineel: '{raw_status_from_excel}') voor item '{barcode_val}' in Excel. Standaard naar leeg in treeview.", "warning")
                        display_status_for_treeview = "" # Display empty for unrecognized strings
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
            self._log(f"[FOUT] Bestand niet gevonden: {file_path}", "error")
        except Exception as e:
            messagebox.showerror("Fout", f"Lezen van Excel-bestand mislukt: {e}")
            self._log(f"[FOUT] Lezen van Excel-bestand mislukt: {e}", "error")

    def _start_session_for_excel_work(self, excel_file_path):
        """Start a session when user begins working on Excel file"""
        self._log(f"[DEBUG] _start_session_for_excel_work - existing session: {self.current_session_id}")
        
        # If we already have a session, don't create a new one
        if self.current_session_id:
            self._log(f"[DEBUG] Session already exists: {self.current_session_id}, not creating new one")
            # If paused, resume it
            if self.session_paused:
                self._resume_session()
            return
            
        try:
            config_file_path = get_config_path()
            if os.path.exists(config_file_path):
                with open(config_file_path, 'r') as f:
                    config = json.load(f)
                    
                api_url = self._ensure_url_protocol(config.get('api_url', ''))
                if not api_url:
                    return
                
                # Determine user from file path (e.g., C:/BOERE/... -> BOERE)
                user = self._determine_user_from_path(excel_file_path)
                if not user:
                    user = config.get('user', 'NESTING')  # Fallback
                
                # Extract project from filename
                project_name = self._extract_project_from_filename(excel_file_path)
                
                # Generate session ID
                self.session_start_time = datetime.now()
                self.current_session_id = f"{user}_{self.session_start_time.strftime('%Y%m%d_%H%M%S')}"
                self.session_item_count = 0
                self.session_paused = False
                self.pause_start_time = None
                self.total_pause_duration = 0
                
                self._log(f"[DEBUG] Created session: {self.current_session_id}")
                
                # Send session start event
                data = {
                    'session_id': self.current_session_id,
                    'user': user,
                    'timestamp': self.session_start_time.isoformat(),
                    'session_type': 'XLSX_UPDATED',
                    'item_count': len(getattr(self, 'barcode_data', {}))  # Number of items in Excel
                }
                
                if project_name:
                    data['project'] = project_name
                
                # Make API call in background thread
                def start_session_api():
                    try:
                        response = requests.post(api_url.replace('/log', '/session/xlsx_updated'), 
                                               json=data, timeout=1)
                        if response.ok:
                            self._log(f"Started XLSX session for {user}: {self.current_session_id} - Status: BEZIG")
                    except Exception as e:
                        self._log(f"Failed to start XLSX session: {e}")
                
                threading.Thread(target=start_session_api, daemon=True).start()
                        
        except Exception as e:
            self._log(f"Error starting session: {e}")
    
    def _determine_user_from_path(self, file_path):
        """Extract user from file path"""
        if not file_path:
            return None
        
        # Get valid users from logs
        valid_users = self._get_valid_users_from_logs()
        
        # Extract user from file path
        path_parts = file_path.replace('\\', '/').split('/')
        for part in path_parts:
            if part.upper() in valid_users:
                return part.upper()
        
        return None
    
    def _extract_project_from_filename(self, file_path):
        """Extract project name from filename dynamically"""
        if not file_path:
            return None
        
        filename = os.path.basename(file_path)
        
        # Priority 1: Look up project from database using file path
        try:
            config_file_path = get_config_path()
            if os.path.exists(config_file_path):
                with open(config_file_path, 'r') as f:
                    config = json.load(f)
                    
                api_url = self._ensure_url_protocol(config.get('api_url', ''))
                if api_url:
                    # Get logs to find project by file path
                    logs_response = requests.get(f"{api_url.replace('/log', '/logs')}", timeout=0.5)
                    if logs_response.ok:
                        logs_data = logs_response.json()
                        if isinstance(logs_data, list):
                            # Find project by matching file path (Windows path normalization)
                            normalized_file_path = file_path.replace('\\', '/')
                            for log_entry in logs_data:
                                if isinstance(log_entry, dict) and 'file_path' in log_entry and 'project' in log_entry:
                                    log_file_path = log_entry['file_path']
                                    if log_file_path:
                                        normalized_log_path = log_file_path.replace('\\', '/')
                                        if normalized_log_path == normalized_file_path:
                                            return log_entry['project']
                                            
                            # Priority 2: Match by filename in file_path field
                            for log_entry in logs_data:
                                if isinstance(log_entry, dict) and 'file_path' in log_entry and 'project' in log_entry:
                                    log_file_path = log_entry['file_path']
                                    if log_file_path and filename in log_file_path:
                                        return log_entry['project']
        except:
            pass
        
        # Priority 3: Try to get project names from logs data and match against filename
        try:
            config_file_path = get_config_path()
            if os.path.exists(config_file_path):
                with open(config_file_path, 'r') as f:
                    config = json.load(f)
                    
                api_url = self._ensure_url_protocol(config.get('api_url', ''))
                if api_url:
                    # Get logs to extract project information
                    logs_response = requests.get(f"{api_url.replace('/log', '/logs')}", timeout=0.5)
                    if logs_response.ok:
                        logs_data = logs_response.json()
                        if isinstance(logs_data, list):
                            # Find projects from logs and match against filename
                            for log_entry in logs_data:
                                if isinstance(log_entry, dict) and 'project' in log_entry:
                                    project = log_entry['project']
                                    if project and project in filename:
                                        return project
        except:
            pass
        
        # Priority 4: Fallback - extract MO code dynamically
        import re
        mo_match = re.search(r'(MO\d{5})', filename)
        if mo_match:
            # Try to extract full project name from filename structure
            project_parts = filename.split('_')
            if len(project_parts) >= 2:
                # Build project name by removing timestamp and extension
                project_name = filename
                # Remove timestamp pattern
                project_name = re.sub(r'_\d{8}_\d{6}\.xlsx?$', '', project_name)
                # Remove file extension if still present
                project_name = re.sub(r'\.xlsx?$', '', project_name)
                return project_name
            else:
                return mo_match.group(1)
        
        return None
    
    def _get_valid_users_from_logs(self):
        """Get valid users from BarcodeMaster logs"""
        valid_users = set()
        
        try:
            config_file_path = get_config_path()
            if os.path.exists(config_file_path):
                with open(config_file_path, 'r') as f:
                    config = json.load(f)
                    
                api_url = self._ensure_url_protocol(config.get('api_url', ''))
                if api_url:
                    # Get logs to extract user information
                    logs_response = requests.get(f"{api_url.replace('/log', '/logs')}", timeout=0.5)
                    if logs_response.ok:
                        logs_data = logs_response.json()
                        if isinstance(logs_data, list):
                            for log_entry in logs_data:
                                if isinstance(log_entry, dict) and 'user' in log_entry:
                                    user = log_entry['user']
                                    if user and user.strip():
                                        valid_users.add(user.upper())
        except:
            pass
        
        # Fallback: try to get users from BarcodeMaster config dynamically
        if not valid_users:
            try:
                # Look for BarcodeMaster config file dynamically
                import glob
                
                # Search for config files in possible locations
                config_search_paths = [
                    '/home/*/Projects/BarcodeMaster/config.json',
                    '../*/config.json',
                    '../../*/config.json',
                    'config.json'
                ]
                
                for search_path in config_search_paths:
                    config_files = glob.glob(search_path)
                    for config_file in config_files:
                        if os.path.exists(config_file):
                            with open(config_file, 'r') as f:
                                bm_config = json.load(f)
                                open_event_users = bm_config.get('scanner_panel_open_event_users', [])
                                if open_event_users:
                                    valid_users.update([user.upper() for user in open_event_users])
                                    break
                    if valid_users:
                        break
            except:
                pass
        
        # Final fallback: scan directory names if still no users found
        if not valid_users:
            try:
                # Get common directory names from file paths in logs
                config_file_path = get_config_path()
                if os.path.exists(config_file_path):
                    with open(config_file_path, 'r') as f:
                        config = json.load(f)
                        api_url = self._ensure_url_protocol(config.get('api_url', ''))
                        if api_url:
                            logs_response = requests.get(f"{api_url.replace('/log', '/logs')}", timeout=0.5)
                            if logs_response.ok:
                                logs_data = logs_response.json()
                                if isinstance(logs_data, list):
                                    for log_entry in logs_data:
                                        if isinstance(log_entry, dict) and 'details' in log_entry:
                                            details = log_entry['details']
                                            if details and ('C:/' in details or 'C:\\' in details):
                                                # Extract potential user names from file paths
                                                import re
                                                path_match = re.search(r'[C]:[/\\]([A-Z\s]+)[/\\]', details)
                                                if path_match:
                                                    potential_user = path_match.group(1).strip()
                                                    if potential_user and len(potential_user) > 2:
                                                        valid_users.add(potential_user.upper())
            except:
                pass
        
        return valid_users

    def _pause_session(self):
        """Pause the current session when panel is hidden"""
        self._log(f"[DEBUG] _pause_session called - session_id: {self.current_session_id}, paused: {self.session_paused}")
        if self.current_session_id and not self.session_paused:
            # Mark as paused immediately to prevent duplicate pause attempts
            self.session_paused = True
            self.pause_start_time = datetime.now()
            
            try:
                config_file_path = get_config_path()
                if os.path.exists(config_file_path):
                    with open(config_file_path, 'r') as f:
                        config = json.load(f)
                        
                    api_url = config.get('api_url', '')
                    if api_url:
                        data = {
                            'session_id': self.current_session_id,
                            'timestamp': self.pause_start_time.isoformat()
                        }
                        
                        def pause_session_api():
                            try:
                                response = requests.post(api_url.replace('/log', '/session/pause'), 
                                                       json=data, timeout=1)
                                if response.ok:
                                    self._log(f"Session paused: {self.current_session_id}")
                                else:
                                    # Reset flag if pause failed
                                    self.session_paused = False
                            except Exception as e:
                                self._log(f"Failed to pause session: {e}")
                                # Reset flag if pause failed
                                self.session_paused = False
                        
                        threading.Thread(target=pause_session_api, daemon=True).start()
                        
            except Exception as e:
                self._log(f"Error pausing session: {e}")
    
    def _resume_session(self):
        """Resume the current session when panel is shown"""
        if self.current_session_id and self.session_paused:
            # Calculate pause duration
            if self.pause_start_time:
                pause_duration = (datetime.now() - self.pause_start_time).total_seconds()
                self.total_pause_duration += pause_duration
            
            try:
                config_file_path = get_config_path()
                if os.path.exists(config_file_path):
                    with open(config_file_path, 'r') as f:
                        config = json.load(f)
                        
                    api_url = config.get('api_url', '')
                    if api_url:
                        data = {
                            'session_id': self.current_session_id,
                            'timestamp': datetime.now().isoformat(),
                            'total_pause_duration': self.total_pause_duration
                        }
                        
                        def resume_session_api():
                            try:
                                response = requests.post(api_url.replace('/log', '/session/resume'), 
                                                       json=data, timeout=1)
                                if response.ok:
                                    self._log(f"Session resumed: {self.current_session_id}")
                                    self.session_paused = False
                                    self.pause_start_time = None
                            except Exception as e:
                                self._log(f"Failed to resume session: {e}")
                        
                        threading.Thread(target=resume_session_api, daemon=True).start()
                        
            except Exception as e:
                self._log(f"Error resuming session: {e}")
    
    def pack(self, **kwargs):
        """Override pack to detect when panel is shown"""
        super().pack(**kwargs)
        self._resume_session()
    
    def pack_forget(self):
        """Override pack_forget to detect when panel is hidden"""
        self._log("[DEBUG] pack_forget called")
        self._pause_session()
        super().pack_forget()

    def _end_session(self):
        """End the current session"""
        if not self.current_session_id:
            return
            
        try:
            config_file_path = get_config_path()
            if os.path.exists(config_file_path):
                with open(config_file_path, 'r') as f:
                    config = json.load(f)
                    
                api_url = self._ensure_url_protocol(config.get('api_url', ''))
                
                if api_url:
                    # If session is paused, calculate final pause duration
                    if self.session_paused and self.pause_start_time:
                        pause_duration = (datetime.now() - self.pause_start_time).total_seconds()
                        self.total_pause_duration += pause_duration
                    
                    # Send session end event
                    data = {
                        'session_id': self.current_session_id,
                        'timestamp': datetime.now().isoformat(),
                        'item_count': self.session_item_count,
                        'total_pause_duration': self.total_pause_duration
                    }
                    
                    # Make API call in background thread to avoid blocking UI
                    def end_session_api():
                        try:
                            response = requests.post(api_url.replace('/log', '/session/end'), 
                                                   json=data, timeout=1)  # Reduced timeout
                            if response.ok:
                                self._log(f"Session ended: {self.current_session_id}")
                        except Exception as e:
                            self._log(f"Failed to end session (non-blocking): {e}")
                    
                    threading.Thread(target=end_session_api, daemon=True).start()
                        
            self.current_session_id = None
            self.session_start_time = None
            self.session_item_count = 0
            self.session_paused = False
            self.pause_start_time = None
            self.total_pause_duration = 0
                        
        except Exception as e:
            self._log(f"Error ending session: {e}")

    def _check_barcode(self, barcode):
        """Controleert de gescande barcode aan de hand van de geladen gegevens en werkt de UI bij."""
        self._log(f"Barcode controleren: {barcode}")

        # Prioritize an exact match (fast and default)
        item = self.barcode_data.get(barcode)
        original_barcode_from_excel = barcode if item else None

        # If no exact match, try a more lenient match by ignoring all whitespace and normalizing path separators
        if not item:
            self._log(f"Exacte match niet gevonden. Poging tot een meer flexibele match...")
            # Normalize by removing all whitespace characters and standardizing path separators
            normalized_scanned = re.sub(r'\s', '', os.path.normpath(barcode))
            for key, value in self.barcode_data.items():
                normalized_key = re.sub(r'\s', '', os.path.normpath(key))
                if normalized_key == normalized_scanned:
                    item = value
                    original_barcode_from_excel = key
                    self._log(f"Flexibele match gevonden! Scanner: '{barcode}', Excel: '{original_barcode_from_excel}'")
                    break # Stop after finding the first match

        if not item:
            self._log(f"[NIET GEVONDEN] Barcode {barcode} niet in de lijst.", "error")
            # Overweeg een optische/auditieve feedback voor niet gevonden barcodes
            return

        item_id = item['id']
        current_status = item['status']

        # Use the original barcode from Excel for logging if a lenient match was found
        log_barcode = original_barcode_from_excel

        if current_status == 'OK':
            # Item already scanned - just log a message
            self._log(f"[WAARSCHUWING] Item '{log_barcode}' is al gescand. Dubbele scan gedetecteerd.", "warning")
            # No change to item['status'], no _update_treeview, item remains OK
        else: # This implies current_status is anything other than 'OK'
            self._log(f"[OK] Barcode {log_barcode} komt overeen en is nu gemarkeerd als OK.", "success")
            item['status'] = 'OK'
            self._update_treeview(item_id, 'OK')
            self._save_updated_excel() # Save changes
            self.session_item_count += 1  # Increment session item count
            self._all_items_ok_check()

    def _all_items_ok_check(self):
        """Checks if all items are OK, then triggers completion actions."""
        if not self.barcode_data:
            return

        all_ok = all(item['status'] == 'OK' for item in self.barcode_data.values())

        if all_ok:
            self._log("[VOLTOOID] Alle items zijn nu OK!", "success")
            
            # End the current session before completion actions
            self._end_session()
            
            # Perform the completion actions
            self._perform_completion_actions()
            
            # Show completion message
            messagebox.showinfo("Scan Voltooid", "Alle items zijn nu gescand en gemarkeerd als OK!")

    def _extract_project_info_from_excel(self, excel_path):
        """
        Extract project information from Excel metadata.
        First tries to read from _ProjectInfo sheet, then falls back to filename.
        Returns (project_name, mo_number) tuple.
        """
        try:
            # Try to read metadata sheet
            excel_file = pd.ExcelFile(excel_path)
            if '_ProjectInfo' in excel_file.sheet_names:
                metadata_df = pd.read_excel(excel_path, sheet_name='_ProjectInfo')
                if not metadata_df.empty:
                    # Convert to dictionary for easy access
                    metadata = dict(zip(metadata_df['Property'], metadata_df['Value']))
                    project_name = metadata.get('project_name', '')
                    mo_number = metadata.get('mo_number', '')
                    if project_name:
                        self._log(f"[METADATA] Found project name from metadata: {project_name}")
                        return mo_number, project_name
        except Exception as e:
            self._log(f"[METADATA] Error reading metadata: {e}")
        
        # Fallback to filename extraction
        filename_base = os.path.splitext(os.path.basename(excel_path))[0]
        # Strip "_updated" suffix if present before extracting project codes
        if filename_base.endswith("_updated"):
            filename_base = filename_base[:-8]  # Remove last 8 characters ("_updated")
        return self._extract_project_codes_from_filename_base(filename_base)
    
    def _extract_project_codes_from_filename_base(self, filename_base):
        """
        Extracts the base MO/Accura code and the full project code from a filename base.
        Strips leading date-like prefixes (e.g., MMDD_, YYYY_) from the full_project_code
        if the prefix is followed by the base_mo_code.
        Example: "MO07834" -> ("MO07834", "MO07834")
                 "0618_MO07834_Boekenkast_Rep_VL5" -> ("MO07834", "MO07834_Boekenkast_Rep_VL5")
        Returns (base_mo_code, full_project_code)
        """
        full_project_code = filename_base
        base_mo_code = ""

        # Try to find MOxxxxx pattern, case-insensitive, within the full_project_code
        mo_match = re.search(r'(MO\d{5})', full_project_code, re.IGNORECASE)
        if mo_match:
            base_mo_code = mo_match.group(0).upper()
        else:
            # Use full project name when no MO code found
            base_mo_code = full_project_code

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

        # Extract project info from Excel metadata or filename
        base_mo_code, full_project_code = self._extract_project_info_from_excel(excel_full_path)

        if not full_project_code:
            self._log(f"[FOUT] Kan projectcode niet afleiden uit Excel bestand: {excel_full_path}")
            messagebox.showerror("Fout bij Afmelden", f"Kan projectcode niet afleiden uit Excel bestand: {os.path.basename(excel_full_path)}")
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
        api_url = self._ensure_url_protocol(config.get('api_url', '')) # Reads 'api_url' from the root of the config
        current_user = config.get('user', 'BarcodeMatchUser') # Reads 'user' from the root of the config
        
        # Include session_id in AFGEMELD event
        db_panel = self.main_app.get_panel_by_name("Database")
        if db_panel is not None:
            try:
                if db_panel.database_enabled_var.get():
                    self._log(f"Database logging ingeschakeld. Project '{full_project_code}' wordt als gesloten gelogd.")
                    is_rep_variant = '_REP_' in full_project_code.upper()
                    # Pass session_id if available
                    db_panel.log_project_closed(full_project_code, base_mo_code=base_mo_code, 
                                              is_rep_variant=is_rep_variant)
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
                    email_panel.send_project_complete_email(full_project_code, excel_full_path)
                elif not email_is_enabled:
                    self._log(f"Email notificatie overgeslagen voor project '{full_project_code}': emails zijn niet ingeschakeld in Email paneel.")
                elif not email_mode_is_per_scan:
                    current_mode = email_panel.email_send_mode_var.get()
                    self._log(f"Email notificatie overgeslagen voor project '{full_project_code}': email modus is '{current_mode}', niet 'per_scan'.")
            except AttributeError:
                self._log("[FOUT] Benodigde attributen (bv. 'email_enabled_var', 'email_send_mode_var', 'send_project_complete_email') niet gevonden op Email paneel.")
            except Exception as e:
                self._log(f"[FOUT] Fout bij verwerken email notificatie voor project '{full_project_code}': {e}")

    def _update_treeview(self, item_id, new_status):
        """Werkt de status van een item in de treeview bij.
        Toont alleen 'OK' of leeg in de treeview."""
        # Map internal status to display status and tag
        if new_status == 'OK':
            display_status = 'OK'
            tag = 'OK'
        else:
            # For all other statuses (DUPLICAAT, NIET OK, etc.), show blank in treeview
            display_status = ''
            tag = 'NOT_OK'
        
        current_values = self.tree.item(item_id)['values']
        if current_values:
            new_values = (display_status, current_values[1])  # Update only the status column
            self.tree.item(item_id, values=new_values, tags=(tag,))

    def _save_updated_excel(self):
        """Modified to send XLSX_UPDATED event for session tracking"""
        original_file_path = self.excel_file_path_var.get()
        if not original_file_path:
            self._log("[FOUT] Geen Excel-bestand geladen om op te slaan.")
            return

        updated_file_path = self._generate_updated_path(original_file_path)
        if not updated_file_path:
            self._log("[FOUT] Kon bijgewerkt bestandspad niet genereren.")
            return
            
        save_successful = False
        save_path = ""
        
        try:
            # Read the original file again to preserve all columns
            df = pd.read_excel(original_file_path)
            
            # Update the status column with the in-memory data
            for barcode, data in self.barcode_data.items():
                mask = df['Item'] == barcode
                if mask.any():
                    # Map internal status to Excel status
                    if data['status'] == 'OK':
                        excel_status = 'OK'
                    elif data['status'] == 'DUPLICAAT':
                        excel_status = 'DUPLICAAT'
                    elif data['status'] == 'NIET OK':
                        excel_status = 'NIET OK'
                    else:
                        excel_status = 'NIET OK'  # Default for unknown
                    
                    df.loc[mask, 'Status'] = excel_status

            # Save to the updated file
            df.to_excel(updated_file_path, index=False)
            self._log(f"Excel-bestand opgeslagen als: {os.path.basename(updated_file_path)}")
            
            save_successful = True
            save_path = updated_file_path
            
            if save_successful:  # After successful save
                # Use the SAME extraction logic as _perform_completion_actions
                base_mo_code, full_project_code = self._extract_project_info_from_excel(save_path)
                
                # Send XLSX_UPDATED event
                config_file_path = get_config_path()
                if os.path.exists(config_file_path):
                    with open(config_file_path, 'r') as f:
                        config = json.load(f)
                        
                    api_url = config.get('api_url', '')
                    if api_url:
                        # Determine which user this is for based on file path
                        user = self._determine_user_from_path(save_path)
                        
                        if user and full_project_code:
                            data = {
                                'event': 'XLSX_UPDATED',
                                'user': user,
                                'project': full_project_code,  # Use the FULL project code
                                'file_path': save_path,
                                'item_count': len(self.barcode_data),
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # Make API call in background thread to avoid blocking UI
                            def send_api_call():
                                try:
                                    response = requests.post(api_url.replace('/log', '/session/xlsx_updated'), 
                                                           json=data, timeout=1)  # Reduced timeout
                                    if response.ok:
                                        self._log(f"Session started for {user} via XLSX update")
                                    else:
                                        self._log(f"API call failed with status: {response.status_code}")
                                except Exception as e:
                                    self._log(f"API call failed (non-blocking): {e}")
                            
                            # Run API call in background thread so it doesn't block scanning
                            threading.Thread(target=send_api_call, daemon=True).start()
            
        except PermissionError:
            self._log(f"[FOUT] Geen toestemming om bestand te overschrijven: {updated_file_path}")
            messagebox.showerror("Opslagfout", f"Geen toestemming om bestand te overschrijven:\n{updated_file_path}")
        except Exception as e:
            self._log(f"[FOUT] Fout bij opslaan: {e}")
            messagebox.showerror("Opslagfout", f"Kon Excel-bestand niet opslaan:\n{e}")

    def _determine_user_from_path(self, file_path):
        """Determine which user based on file path"""
        # Logic to determine if this is OPUS or GANNOMAT based on path
        # This is a simplified version - adjust based on your actual path structure
        if 'OPUS' in file_path.upper():
            return 'OPUS'
        elif 'GANNOMAT' in file_path.upper():
            return 'KL GANNOMAT'
        return None

    def _extract_project_from_path(self, file_path):
        """Extract project code from file path"""
        # Look for patterns like MO123456 in the path
        import re
        
        # Try to find MO code
        mo_match = re.search(r'(MO\d{4,6})', file_path, re.IGNORECASE)
        if mo_match:
            return mo_match.group(0).upper()
        
        # Try to find numeric code
        accura_match = re.search(r'(\d{5,6})', file_path)
        if accura_match:
            return accura_match.group(0)
        
        return None

    def _show_context_menu(self, event):
        """Toont het contextmenu bij rechtermuisklik."""
        # Select the item under the cursor
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            self.selected_item_id = item_id
            self.context_menu.post(event.x_root, event.y_root)

    def _on_tree_select(self, event):
        """Behandelt de selectie van een item in de treeview."""
        selection = self.tree.selection()
        if selection:
            self.selected_item_id = selection[0]

    def _mark_item_ok(self):
        """Markeert het geselecteerde item als OK."""
        if self.selected_item_id:
            barcode = self.tree.item(self.selected_item_id)['values'][1]  # Item column
            if barcode in self.barcode_data:
                self.barcode_data[barcode]['status'] = 'OK'
                self._update_treeview(self.selected_item_id, 'OK')
                self._save_updated_excel()
                self._log(f"Item '{barcode}' handmatig gemarkeerd als OK.")
                self.session_item_count += 1  # Increment session item count
                self._all_items_ok_check()

    def _clear_item_status(self):
        """Clears the status of the selected item (sets to NIET OK)."""
        if self.selected_item_id:
            barcode = self.tree.item(self.selected_item_id)['values'][1]  # Item column
            if barcode in self.barcode_data:
                self.barcode_data[barcode]['status'] = 'NIET OK'
                self._update_treeview(self.selected_item_id, 'NIET OK')
                self._save_updated_excel()
                self._log(f"Status gewist voor item '{barcode}'.")

    def _start_usb_listener(self):
        """Start luisteren naar USB-toetsenbordscans."""
        if self._usb_listener_thread and self._usb_listener_thread.is_alive():
            self._log("USB-luisteraar is al actief.")
            return
        
        self._stop_usb_listener_event.clear()
        self._usb_listener_thread = threading.Thread(target=self._usb_listener_worker, daemon=True)
        self._usb_listener_thread.start()
        self._log("USB-luisteraar gestart.")

    def _stop_usb_listener(self):
        """Stop luisteren naar USB-toetsenbordscans."""
        if self._usb_listener_thread and self._usb_listener_thread.is_alive():
            self._stop_usb_listener_event.set()
            keyboard.unhook_all()  # Remove all keyboard hooks
            self._usb_listener_thread.join(timeout=2)
            self._log("USB-luisteraar gestopt.")

    def _usb_listener_worker(self):
        """Worker thread voor USB-toetsenbordscans."""
        def on_key_event(e):
            if e.event_type == keyboard.KEY_DOWN:
                current_time = time.time()
                
                # Reset buffer if too much time has passed
                if current_time - self.last_key_time > 0.5:  # 500ms timeout
                    self.barcode_buffer.clear()
                
                self.last_key_time = current_time
                
                if e.name == 'enter':
                    if self.barcode_buffer:
                        barcode = ''.join(self.barcode_buffer)
                        self.barcode_buffer.clear()
                        # Schedule the barcode check in the main thread
                        self.after(0, self._check_barcode, barcode)
                elif len(e.name) == 1:  # Single character
                    self.barcode_buffer.append(e.name)
        
        keyboard.hook(on_key_event)
        
        # Keep the thread alive
        while not self._stop_usb_listener_event.is_set():
            time.sleep(0.1)

    def _update_com_ports(self):
        """Vernieuwt de lijst met beschikbare COM-poorten."""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.com_port_combo['values'] = ports
        if ports and not self.com_port_var.get():
            self.com_port_var.set(ports[0])
        self._log(f"COM-poorten vernieuwd: {ports}")

    def _connect_com_port(self):
        """Verbindt met de geselecteerde COM-poort."""
        if self.ser and self.ser.is_open:
            self._log("COM-poort is al verbonden.")
            return
        
        port = self.com_port_var.get()
        baud_rate = int(self.baud_rate_var.get())
        
        try:
            self.ser = serial.Serial(port, baud_rate, timeout=0.1)
            self.is_reading_com = True
            self.com_read_thread = threading.Thread(target=self._read_com_port, daemon=True)
            self.com_read_thread.start()
            self._log(f"Verbonden met {port} op {baud_rate} baud.")
            self.connect_button.config(text="Verbreken", command=self._disconnect_com_port)
        except Exception as e:
            messagebox.showerror("Verbindingsfout", f"Kon niet verbinden met {port}:\n{e}")
            self._log(f"[FOUT] Kon niet verbinden met {port}: {e}")

    def _disconnect_com_port(self):
        """Verbreekt de verbinding met de COM-poort."""
        self.is_reading_com = False
        if self.com_read_thread and self.com_read_thread.is_alive():
            self.com_read_thread.join(timeout=2)
        
        if self.ser and self.ser.is_open:
            self.ser.close()
            self._log("COM-poort verbinding verbroken.")
        
        self.connect_button.config(text="Verbinden", command=self._connect_com_port)

    def _read_com_port(self):
        """Leest gegevens van de COM-poort."""
        buffer = ""
        while self.is_reading_com and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting:
                    data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                    
                    # Check for line endings
                    while '\r\n' in buffer or '\n' in buffer:
                        if '\r\n' in buffer:
                            line, buffer = buffer.split('\r\n', 1)
                        else:
                            line, buffer = buffer.split('\n', 1)
                        
                        line = line.strip()
                        if line:
                            # Schedule the barcode check in the main thread
                            self.after(0, self._check_barcode, line)
                
                time.sleep(0.01)  # Small delay to prevent high CPU usage
            except Exception as e:
                self._log(f"[FOUT] Fout bij lezen van COM-poort: {e}")
                break

    def _on_tree_double_click(self, event):
        """Handles double-click events on the treeview to open .HOP/.HOPS files."""
        try:
            # Get the selected item
            selected_item = self.tree.selection()
            if not selected_item:
                return
            
            # Get the item data
            item_data = self.tree.item(selected_item[0])
            if not item_data or 'values' not in item_data:
                return
            
            values = item_data['values']
            if len(values) < 2:  # Need at least Status and Item columns
                return
            
            item_content = str(values[1])  # Item column is the second column
            
            # Check if the item content contains a file path with .HOP or .HOPS extension
            if not item_content:
                return
            
            # Check if it's a .HOP or .HOPS file
            if not (item_content.lower().endswith('.hop') or item_content.lower().endswith('.hops')):
                self._log(f"Item '{item_content}' is geen .HOP/.HOPS bestand")
                return
            
            # Normalize the path to handle different path formats
            # Replace forward slashes with backslashes on Windows
            normalized_path = item_content.replace('/', os.sep).replace('\\', os.sep)
            
            # Try to resolve the path
            if os.path.isabs(normalized_path):
                # It's an absolute path
                final_path = os.path.normpath(normalized_path)
            else:
                # It's a relative path - try relative to the Excel file location
                excel_path = self.excel_file_path_var.get()
                if excel_path:
                    excel_dir = os.path.dirname(excel_path)
                    final_path = os.path.normpath(os.path.join(excel_dir, normalized_path))
                else:
                    final_path = os.path.normpath(normalized_path)
            
            # Check if the file exists
            if not os.path.exists(final_path):
                self._log(f"Bestand niet gevonden: {final_path}")
                self._log(f"Origineel pad: {item_content}")
                messagebox.showwarning("Bestand niet gevonden", 
                                     f"Het bestand kon niet worden gevonden:\n{final_path}\n\nOrigineel pad:\n{item_content}")
                return
            
            # Try to open the file with the default associated program
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(final_path)
                else:  # macOS/Linux
                    import subprocess
                    if sys.platform == 'darwin':  # macOS
                        subprocess.run(['open', final_path])
                    else:  # Linux
                        subprocess.run(['xdg-open', final_path])
                
                self._log(f"Bestand geopend: {os.path.basename(final_path)}")
                
            except Exception as e:
                self._log(f"Fout bij openen van bestand: {e}")
                messagebox.showerror("Fout bij openen", 
                                   f"Kon het bestand niet openen:\n{final_path}\n\nFout: {e}")
                
        except Exception as e:
            self._log(f"Fout bij dubbelklik verwerking: {e}")
            print(f"[ERROR] Double-click handler error: {e}")
    
    def shutdown(self):
        """Ruimt resources op bij het afsluiten van de applicatie."""
        self._stop_usb_listener()
        self._disconnect_com_port()
        # Do NOT end session - sessions should persist across application restarts
        # self._end_session()  # Removed - sessions continue next day
        self._log("Scannerpaneel afgesloten.")