import time
import tkinter as tk
import re
from tkinter import ttk, messagebox, filedialog
import serial.tools.list_ports
import serial
import threading
import os # Added for os.path.isdir
from datetime import datetime # Added for timestamp
from config_utils import get_config, save_config # Ensure these are correctly imported
from ..utils import Tooltip
# BackgroundImportService is now passed in, so direct import might only be needed for type hinting if used.
# from BarcodeMaster.services.background_import_service import BackgroundImportService 

class ScannerPanel(tk.Frame):
    
    # To prevent processing COM data when the main app window is not focused
    # This BooleanVar will be passed from the MainApp instance
    app_has_focus_var = None
    def __init__(self, master, app, app_has_focus_var=None, background_service_instance=None):
        super().__init__(master, bg="#f0f0f0")
        self.master = master # master is the content_frame from MainApp
        self.app = app
        self.app_has_focus_var = app_has_focus_var # Passed from MainApp
        self.background_import_service = background_service_instance # Use shared instance
        config = get_config()
        # --- USB Keyboard Frame ---
        self.usb_frame = tk.LabelFrame(self, text="USB Keyboard Scanner", bg="#f0f0f0", padx=10, pady=5)
        self.usb_frame.columnconfigure(0, weight=1)
        self.usb_code_var = tk.StringVar()
        self.usb_entry = tk.Entry(self.usb_frame, textvariable=self.usb_code_var)
        self.usb_entry.grid(row=0, column=0, padx=5, pady=10, sticky='ew')
        self.usb_entry.bind('<Return>', self.on_usb_scan)
        # Initial visibility handled by update_frame_visibility()
        # --- Scanner Type Selection ---
        scanner_type = config.get('scanner_panel_type', 'COM')
        self.scanner_type_var = tk.StringVar(value=scanner_type)
        type_frame = tk.LabelFrame(self, text="Scanner Type", bg="#f0f0f0", padx=10, pady=5)
        type_frame.pack(pady=(5, 10), fill='x', padx=20)
        com_radio = tk.Radiobutton(type_frame, text="COM Port Scanner", variable=self.scanner_type_var, value="COM", bg="#f0f0f0", command=self.on_scanner_type_change)
        usb_radio = tk.Radiobutton(type_frame, text="USB Keyboard Scanner", variable=self.scanner_type_var, value="USB", bg="#f0f0f0", command=self.on_scanner_type_change)
        com_radio.pack(side='left', padx=10)
        usb_radio.pack(side='left', padx=10)

        # --- COM Port Frame ---
        self.com_frame = tk.LabelFrame(self, text="COM Port Scanner", bg="#f0f0f0", padx=10, pady=5)
        # The com_frame is packed/unpacked in update_frame_visibility, not here.

        self.com_port_var = tk.StringVar()
        self.com_port_var.trace_add('write', self.save_com_port)
        tk.Label(self.com_frame, text="Selecteer COM Poort:", bg="#f0f0f0").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.com_port_combo = ttk.Combobox(self.com_frame, textvariable=self.com_port_var, width=15, state='readonly')
        self.com_port_combo.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        tk.Button(self.com_frame, text="Vernieuw", command=self.refresh_ports).grid(row=0, column=2, padx=5, pady=5)
        
        self.baud_rate_var = tk.StringVar()
        self.baud_rate_var.trace_add('write', self.save_baud_rate)
        tk.Label(self.com_frame, text="Baud Rate:", bg="#f0f0f0").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.baud_rate_entry = tk.Entry(self.com_frame, textvariable=self.baud_rate_var, width=10)
        self.baud_rate_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        
        self.connect_btn = tk.Button(self.com_frame, text="Verbinden", command=self.connect_com)
        self.connect_btn.grid(row=2, column=0, padx=5, pady=10, sticky='w')
        self.disconnect_btn = tk.Button(self.com_frame, text="Verbreek", command=self.disconnect_com, state=tk.DISABLED)
        self.disconnect_btn.grid(row=2, column=1, padx=5, pady=10, sticky='w')
        
        self.com_status_label = tk.Label(self.com_frame, text="Niet verbonden", fg="red", bg="#f0f0f0")
        self.com_status_label.grid(row=2, column=2, padx=5, pady=10, sticky='w')

        # --- Event Type Selection ---
        event_type = config.get('scanner_panel_event_type', 'OPEN')
        self.event_type_var = tk.StringVar(value=event_type)
        # Make event_frame an attribute of self for easier access by helper methods
        self.event_frame = tk.LabelFrame(self, text="Event Type", bg="#f0f0f0", padx=10, pady=5)
        self.event_frame.pack(pady=(0, 10), fill='x', padx=20)

        # --- Log Viewer Frame ---
        self.log_viewer_frame = tk.LabelFrame(self, text="Log Viewer", bg="#f0f0f0", padx=10, pady=5)
        self.log_viewer_frame.pack(pady=(0, 10), fill='both', expand=True, padx=20)

        self.log_text = tk.Text(self.log_viewer_frame, height=10, bg="white", fg="black", state='disabled', wrap=tk.WORD)
        self.log_scroll = tk.Scrollbar(self.log_viewer_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=self.log_scroll.set)

        self.log_scroll.pack(side='right', fill='y')
        self.log_text.pack(side='left', fill='both', expand=True)

        # Frame for radio buttons and lock button (direct child of self.event_frame)
        self.radio_lock_frame = tk.Frame(self.event_frame, bg="#f0f0f0")
        self.radio_lock_frame.pack(fill='x', anchor='nw') # Anchor to keep it at the top

        # Frame for user-specific path settings, packed/unpacked dynamically
        self.user_paths_frame = tk.Frame(self.event_frame, bg="#f0f0f0")

        self.event_type_locked = config.get('scanner_panel_event_type_locked', False)
        self.open_radio = tk.Radiobutton(self.radio_lock_frame, text="OPEN", variable=self.event_type_var, value="OPEN", bg="#f0f0f0", command=self._on_event_type_radio_change)
        self.closed_radio = tk.Radiobutton(self.radio_lock_frame, text="AFGEMELD", variable=self.event_type_var, value="AFGEMELD", bg="#f0f0f0", command=self._on_event_type_radio_change)
        self.open_radio.pack(side='left', padx=10, pady=(0,5)) # pady to ensure it's above user_paths_frame
        self.closed_radio.pack(side='left', padx=10, pady=(0,5))
        self.lock_btn = tk.Button(self.radio_lock_frame, text="Lock" if not self.event_type_locked else "Unlock", command=self.toggle_event_type_lock, width=7)

        # Load user-specific paths from config
        self.user_specific_paths_vars = {} # To hold StringVar for each user path entry
        self.remove_user_buttons = [] # To store references to remove buttons
        self.user_browse_buttons = [] # To store references to browse buttons
        self.user_logic_checkboxes = [] # To store references to user logic checkboxes
        self.add_user_frame_widget = None # To store the 'Add User' frame widget
        self.scanner_panel_open_event_user_paths = config.get('scanner_panel_open_event_user_paths', {})
        # Load user-specific logic active states
        self.user_logic_active_vars = {} # To hold BooleanVar for each user logic checkbox
        self.scanner_panel_open_event_user_logic_active = config.get('scanner_panel_open_event_user_logic_active', {})
        self.scanner_user_to_processing_type_map = config.get('scanner_user_to_processing_type_map', {})

        # Serial port attributes
        self.ser = None
        self.is_reading = False
        self.read_thread = None

        self.open_projects = set() # To track open projects and prevent duplicates

        self.load_config_values() # Load saved settings
        # Listen to admin lock changes if the var is provided by MainApp
        if hasattr(self.app, 'admin_config_locked_var') and isinstance(self.app.admin_config_locked_var, tk.BooleanVar):
            self.app.admin_config_locked_var.trace_add('write', self._update_admin_dependent_ui)
            # Initial call to set UI state based on admin lock, 
            # _build_open_event_user_paths_ui will also call it if OPEN event is selected.
            # Call it here to ensure state is set even if OPEN event is not default.
            self._update_admin_dependent_ui() 
        else:
            self.log_message("Warning: app.admin_config_locked_var not found or not a BooleanVar. User management UI might not reflect admin lock state correctly. Assuming locked.")
            # Default to locked state if var is missing, _update_admin_dependent_ui handles this
            self._update_admin_dependent_ui()

        self.update_frame_visibility() # Initial visibility based on scanner type
        self.apply_event_type_lock_ui() # Apply lock state from config
        self._update_open_event_ui_visibility() # Ensure event type specific UI is also updated

        # Store initial type to handle connect/disconnect logic correctly on first change
        self._previous_scanner_type = self.scanner_type_var.get()

        # Auto-connect if enabled in config
        config = get_config()
        if config.get('scanner_panel_com_auto_connect', False) and self.scanner_type_var.get() == 'COM':
            self.log_message("Auto-connect is ON. Attempting connection...")
            # Use 'after' to ensure the main window is fully initialized before connecting
            self.after(100, self.connect_com)

        self._create_lock_button()

    def log_message(self, message):
        """Adds a timestamped message to the log viewer."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def _create_lock_button(self):
        self.lock_button_frame = tk.Frame(self, bg="#f0f0f0")
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

    def set_config_lock_visibility(self, visible):
        """Shows or hides the event type lock button based on admin lock state."""
        if visible and self.winfo_exists():
            self.lock_btn.pack(side=tk.RIGHT, padx=(5,0))
        elif self.winfo_exists():
            self.lock_btn.pack_forget()

    def update_frame_visibility(self):
        if self.scanner_type_var.get() == 'COM':
            self.com_frame.pack(fill='x', padx=20, pady=5, before=self.event_frame)
            self.usb_frame.pack_forget()
        else: # USB
            self.usb_frame.pack(fill='x', padx=20, pady=5, before=self.event_frame)
            self.com_frame.pack_forget()

    def load_config_values(self):
        config = get_config()
        self.scanner_type_var.set(config.get('scanner_panel_type', 'COM'))
        self.com_port_var.set(config.get('scanner_panel_com_port', ''))
        self.baud_rate_var.set(config.get('scanner_panel_baud_rate', '9600'))
        self.event_type_var.set(config.get('scanner_panel_event_type', 'AFGEMELD'))
        self.scanner_panel_open_event_user_paths = config.get('scanner_panel_open_event_user_paths', {})
        self.scanner_panel_open_event_user_logic_active = config.get('scanner_panel_open_event_user_logic_active', {})
        self.scanner_user_to_processing_type_map = config.get('scanner_user_to_processing_type_map', {}) # Ensure this is loaded for config reloads
        self.available_processing_types = ["GEEN_PROCESSING", "MDB_PROCESSING", "HOPS_PROCESSING"] # Define available types, including no processing

    def on_scanner_type_change(self):
        """Handles scanner type changes without auto-connecting/disconnecting."""
        self.save_scanner_type()
        self.update_frame_visibility()
        self._previous_scanner_type = self.scanner_type_var.get()

    def save_scanner_type(self):
        save_config({'scanner_panel_type': self.scanner_type_var.get()})

    def save_event_type(self):
        save_config({'scanner_panel_event_type': self.event_type_var.get()})

    def toggle_event_type_lock(self):
        self.event_type_locked = not self.event_type_locked
        save_config({'scanner_panel_event_type_locked': self.event_type_locked})
        self.apply_event_type_lock_ui()

    def apply_event_type_lock_ui(self):
        if self.event_type_locked:
            self.open_radio.config(fg='#888888', state='disabled')
            self.closed_radio.config(fg='#888888', state='disabled')
            self.lock_btn.config(text='Unlock')
        else:
            self.open_radio.config(fg='black', state='normal')
            self.closed_radio.config(fg='black', state='normal')
            self.lock_btn.config(text='Lock')
        self._apply_event_type_lock_to_user_controls() # Update user controls based on new lock state

    def _on_event_type_radio_change(self):
        save_config({'scanner_panel_event_type': self.event_type_var.get()})
        self._update_open_event_ui_visibility()

    def _update_open_event_ui_visibility(self):
        if self.event_type_var.get() == 'OPEN':
            self._build_open_event_user_paths_ui()
            self.user_paths_frame.pack(fill='x', padx=5, pady=(5,0), after=self.radio_lock_frame)
        else:
            self.user_paths_frame.pack_forget()

    def _save_user_logic_active_state(self, username, is_active):
        config_data = get_config()
        user_logic_states = config_data.get('scanner_panel_open_event_user_logic_active', {})
        user_logic_states[username] = is_active
        save_config({'scanner_panel_open_event_user_logic_active': user_logic_states})
        self.scanner_panel_open_event_user_logic_active = user_logic_states # Update local cache
        self.log_message(f"Mappen-check actief voor {username} ingesteld op {is_active}")

    def _build_open_event_user_paths_ui(self):
        for widget in self.user_paths_frame.winfo_children():
            widget.destroy()
        self.user_specific_paths_vars.clear()
        self.user_logic_active_vars.clear()
        self.remove_user_buttons.clear() # Clear old button references
        self.user_browse_buttons.clear()
        self.user_logic_checkboxes.clear()
        self.add_user_frame_widget = None # Reset add user frame reference

        config = get_config()
        open_users = config.get('scanner_panel_open_event_users', ['GANNOMAT', 'OPUS'])
        self.scanner_panel_open_event_user_paths = config.get('scanner_panel_open_event_user_paths', {})
        self.scanner_panel_open_event_user_logic_active = config.get('scanner_panel_open_event_user_logic_active', {})

        if not open_users:
            tk.Label(self.user_paths_frame, text="Geen gebruikers geconfigureerd voor OPEN event paden.", bg="#f0f0f0", fg="gray").pack(pady=5)
            return

        for username in open_users:
            user_frame = tk.Frame(self.user_paths_frame, bg="#f0f0f0")
            user_frame.pack(fill='x', pady=2)

            # --- Define variables and widgets ---
            logic_active_var = tk.BooleanVar(value=self.scanner_panel_open_event_user_logic_active.get(username, True))
            self.user_logic_active_vars[username] = logic_active_var

            path_var = tk.StringVar(value=self.scanner_panel_open_event_user_paths.get(username, "Niet ingesteld"))
            self.user_specific_paths_vars[username] = path_var

            path_display_entry = tk.Entry(user_frame, textvariable=path_var, width=30)
            browse_button = tk.Button(user_frame, text="Bladeren...", command=lambda u=username, pv=path_var: self._browse_user_path(u, pv))
            self.user_browse_buttons.append(browse_button)

            def create_checkbox_command(u, lav, pde, bb, pv_for_clear):
                def command():
                    self._save_user_logic_active_state(u, lav.get())
                    is_checked = lav.get()
                    pde.config(state='readonly' if is_checked else 'disabled')
                    bb.config(state='normal' if is_checked else 'disabled')
                    if not is_checked:
                        pv_for_clear.set("Niet ingesteld")
                        current_paths_config = get_config().get('scanner_panel_open_event_user_paths', {})
                        if u in current_paths_config:
                            del current_paths_config[u]
                            save_config({'scanner_panel_open_event_user_paths': current_paths_config})
                            self.scanner_panel_open_event_user_paths = current_paths_config
                return command

            logic_checkbox = tk.Checkbutton(
                user_frame,
                variable=logic_active_var,
                bg="#f0f0f0",
                command=create_checkbox_command(username, logic_active_var, path_display_entry, browse_button, path_var)
            )
            self.user_logic_checkboxes.append(logic_checkbox)
            Tooltip(logic_checkbox, "Activeer/Deactiveer automatische import voor deze gebruiker.") # Added Tooltip
            user_label = tk.Label(user_frame, text=f"{username}:", width=15, anchor='w', bg="#f0f0f0")
            
            processing_type = self.scanner_user_to_processing_type_map.get(username, "N/A")
            processing_type_label = tk.Label(user_frame, text=f"Type: {processing_type}", width=20, anchor='w', bg="#f0f0f0")

            remove_button = tk.Button(user_frame, text="Verwijderen", command=lambda u=username: self._remove_user_config(u), bg="#ffdddd", fg="#990000")
            self.remove_user_buttons.append(remove_button)

            # --- Pack widgets in the new order ---
            logic_checkbox.pack(side='left', padx=(0, 2))
            user_label.pack(side='left', padx=(0, 5)) 
            processing_type_label.pack(side='left', padx=(0,10)) 
            path_display_entry.pack(side='left', expand=True, fill='x', padx=(0,5))
            browse_button.pack(side='left', padx=(0, 2))
            remove_button.pack(side='left', padx=(0,0)) 

            # --- Set initial state based on checkbox ---
            is_initially_checked = logic_active_var.get()
            path_display_entry.config(state='readonly' if is_initially_checked else 'disabled')
            browse_button.config(state='normal' if is_initially_checked else 'disabled')
            if not is_initially_checked:
                path_var.set("Niet ingesteld")

        # After building all user UI, apply admin lock state and event type lock state
        self._update_admin_dependent_ui()
        self._apply_event_type_lock_to_user_controls()

        # --- UI for Adding a new user ---
        self.add_user_frame_widget = tk.Frame(self.user_paths_frame, bg="#e0e0e0", pady=10)
        # Packing is handled by _update_admin_dependent_ui
        # self.add_user_frame_widget.pack(fill='x', side='bottom', pady=(10,0), ipady=5) # Initial packing deferred

        tk.Label(self.add_user_frame_widget, text="Nieuwe Gebruiker:", bg="#e0e0e0").pack(side='left', padx=(5,2))
        self.new_username_entry = tk.Entry(self.add_user_frame_widget, width=15)
        self.new_username_entry.pack(side='left', padx=2)

        tk.Label(self.add_user_frame_widget, text="Type:", bg="#e0e0e0").pack(side='left', padx=(5,2))
        self.new_user_processing_type_var = tk.StringVar()
        self.new_user_processing_type_combo = ttk.Combobox(self.add_user_frame_widget, textvariable=self.new_user_processing_type_var, values=self.available_processing_types, width=20, state='readonly')
        if self.available_processing_types:
            self.new_user_processing_type_combo.current(0) # Default to first type
        self.new_user_processing_type_combo.pack(side='left', padx=2)

        add_button = tk.Button(self.add_user_frame_widget, text="Toevoegen", command=self._add_user_config, bg="#d0e0d0", fg="#006600")
        add_button.pack(side='left', padx=(5,5))

    def _browse_user_path(self, username, path_var):
        directory = filedialog.askdirectory(title=f"Select Directory for {username}")
        if directory:
            path_var.set(directory)
            # Update and save the configuration
            config_data = get_config() # Use a different name to avoid conflict with module
            user_paths = config_data.get('scanner_panel_open_event_user_paths', {})
            user_paths[username] = directory
            save_config({'scanner_panel_open_event_user_paths': user_paths})
            # Update the main storage attribute as well
            self.scanner_panel_open_event_user_paths = user_paths
            # self._log(f"Set path for {username} to {directory}") # _log method might not exist, use print
            self.log_message(f"Set path for {username} to {directory}")
        else:
            # self._log(f"Path selection cancelled for {username}")
            self.log_message(f"Path selection cancelled for {username}")

    def _remove_user_config(self, username_to_remove):
        if not messagebox.askyesno("Bevestig Verwijdering", f"Weet u zeker dat u gebruiker '{username_to_remove}' en alle bijbehorende configuraties wilt verwijderen?"):
            return

        config_data = get_config()

        # 1. Remove from scanner_panel_open_event_users
        open_users = config_data.get('scanner_panel_open_event_users', [])
        if username_to_remove in open_users:
            open_users.remove(username_to_remove)
            config_data['scanner_panel_open_event_users'] = open_users

        # 2. Remove from scanner_user_to_processing_type_map
        processing_map = config_data.get('scanner_user_to_processing_type_map', {})
        if username_to_remove in processing_map:
            del processing_map[username_to_remove]
            config_data['scanner_user_to_processing_type_map'] = processing_map

        # 3. Remove from scanner_panel_open_event_user_logic_active
        logic_active_map = config_data.get('scanner_panel_open_event_user_logic_active', {})
        if username_to_remove in logic_active_map:
            del logic_active_map[username_to_remove]
            config_data['scanner_panel_open_event_user_logic_active'] = logic_active_map

        # 4. Remove from scanner_panel_open_event_user_paths
        paths_map = config_data.get('scanner_panel_open_event_user_paths', {})
        if username_to_remove in paths_map:
            del paths_map[username_to_remove]
            config_data['scanner_panel_open_event_user_paths'] = paths_map
        
        save_config(config_data) # Save the entire modified config_data dictionary
        self.log_message(f"Gebruiker '{username_to_remove}' verwijderd.")

        # Refresh local cache and UI
        self.load_config_values() # Reload all config values, including the map
        self._build_open_event_user_paths_ui() # Rebuild the UI to reflect changes
        self._update_admin_dependent_ui() # Explicitly call after rebuild to ensure visibility

    def _add_user_config(self):
        new_username = self.new_username_entry.get().strip()
        selected_processing_type = self.new_user_processing_type_var.get()

        if not new_username:
            messagebox.showerror("Fout", "Gebruikersnaam mag niet leeg zijn.")
            return

        if not selected_processing_type:
            messagebox.showerror("Fout", "Selecteer een processing type.")
            return

        config_data = get_config()
        open_users = config_data.get('scanner_panel_open_event_users', [])

        if new_username in open_users:
            messagebox.showerror("Fout", f"Gebruiker '{new_username}' bestaat al.")
            return

        # 1. Add to scanner_panel_open_event_users
        open_users.append(new_username)
        config_data['scanner_panel_open_event_users'] = open_users

        # 2. Add to scanner_user_to_processing_type_map
        processing_map = config_data.get('scanner_user_to_processing_type_map', {})
        processing_map[new_username] = selected_processing_type
        config_data['scanner_user_to_processing_type_map'] = processing_map

        # 3. Add to scanner_panel_open_event_user_logic_active (default to True)
        logic_active_map = config_data.get('scanner_panel_open_event_user_logic_active', {})
        logic_active_map[new_username] = True
        config_data['scanner_panel_open_event_user_logic_active'] = logic_active_map

        # 4. Add to scanner_panel_open_event_user_paths (default to "Niet ingesteld")
        paths_map = config_data.get('scanner_panel_open_event_user_paths', {})
        paths_map[new_username] = "Niet ingesteld"
        config_data['scanner_panel_open_event_user_paths'] = paths_map
        
        save_config(config_data)
        log_message = f"Gebruiker '{new_username}' ({selected_processing_type}) toegevoegd."
        self.log_message(log_message)
        # self._log_to_widget(log_message) # Replaced with print, as _log_to_widget doesn't exist

        # Clear input fields
        self.new_username_entry.delete(0, tk.END)
        if self.available_processing_types:
            self.new_user_processing_type_combo.current(0)

        # Refresh local cache and UI
        self.load_config_values()
        self._build_open_event_user_paths_ui() # This will rebuild and re-apply admin UI states
        self._update_admin_dependent_ui() # Explicitly call after rebuild to ensure visibility

    def _update_admin_dependent_ui(self, *args): # *args for trace callback
        is_locked = True # Default to locked if admin_config_locked_var is not available or not set up
        if hasattr(self.app, 'admin_config_locked_var') and isinstance(self.app.admin_config_locked_var, tk.BooleanVar):
            try:
                is_locked = self.app.admin_config_locked_var.get()
            except tk.TclError: # Can happen if the variable is being destroyed
                self.log_message("Warning: TclError reading admin_config_locked_var. Assuming locked.")
                is_locked = True
        else:
            # This case is handled by the warning in __init__ as well.
            # For safety, if the variable isn't set up, assume admin functions should be restricted.
            pass # Keeps is_locked = True from its initialization

        # Update remove buttons visibility based on admin lock
        for btn in self.remove_user_buttons:
            if btn.winfo_exists(): # Ensure widget hasn't been destroyed
                if is_locked: # Admin lock
                    btn.pack_forget()
                else:
                    # If admin unlocked, ensure button is visible (packed)
                    if not btn.winfo_manager(): 
                        btn.pack(side='left', padx=(5,0)) # Original packing options

        # Update 'Add User' frame visibility
        if hasattr(self, 'add_user_frame_widget') and self.add_user_frame_widget and self.add_user_frame_widget.winfo_exists():
            if is_locked:
                self.add_user_frame_widget.pack_forget()
            else:
                # Ensure it's packed correctly if it was previously forgotten
                # Check if it's already packed to avoid issues if called multiple times
                if not self.add_user_frame_widget.winfo_manager(): # Checks if widget is being managed by a geometry manager
                    self.add_user_frame_widget.pack(fill='x', side='bottom', pady=(10,0), ipady=5)
        elif not is_locked and hasattr(self, 'add_user_frame_widget') and self.add_user_frame_widget:
            # This case might occur if _build_open_event_user_paths_ui hasn't been called yet but admin is unlocked
            # or if the frame was somehow destroyed. If it exists but isn't packed, pack it.
            if not self.add_user_frame_widget.winfo_manager():
                 self.add_user_frame_widget.pack(fill='x', side='bottom', pady=(10,0), ipady=5)

    def _apply_event_type_lock_to_user_controls(self):
        event_locked = self.event_type_locked
        open_users = sorted(self.scanner_panel_open_event_user_paths.keys())

        for checkbox in self.user_logic_checkboxes:
            if checkbox.winfo_exists():
                checkbox.config(state=tk.DISABLED if event_locked else tk.NORMAL)
        
        # Re-define open_users here as a defensive measure against NameError
        open_users = sorted(self.scanner_panel_open_event_user_paths.keys())
        for i, browse_btn in enumerate(self.user_browse_buttons):
            if browse_btn.winfo_exists():
                # Corresponding logic checkbox must exist and be checked for browse to be active
                can_be_active = False
                if i < len(self.user_logic_checkboxes) and self.user_logic_checkboxes[i].winfo_exists():
                    # Get the BooleanVar associated with the checkbox
                    # Assuming user_logic_active_vars keys match the order or can be mapped
                    # This part is a bit tricky as we only stored the widget, not the var directly in this list
                    # A safer way would be to iterate open_users and get var from self.user_logic_active_vars
                    # For now, let's assume the checkbox's own variable reflects its state for enabling browse
                    # A better approach: check the variable directly from self.user_logic_active_vars[username_of_this_row]
                    # This current implementation might not perfectly get the corresponding checkbox state easily.
                    # Let's simplify: if event is locked, disable. If event is unlocked, enable if checkbox is checked.
                    # The checkbox's own command already handles path_entry and browse_button state based on its check.
                    # So, we primarily just need to disable the checkbox itself if event_locked.
                    # The browse button's state will be managed by the checkbox's command.
                    # However, the request was to disable browse button *also* when event frame is locked.
                    
                    # Get the associated username for this browse button/checkbox row
                    # This requires that _build_open_event_user_paths_ui iterates users in a fixed order
                    # and that self.user_browse_buttons and self.user_logic_active_vars are aligned.
                    # This is fragile. A better way would be to store (username, widget) tuples.
                    # For now, we rely on the checkbox's command to manage the browse button based on its own state.
                    # The event_type_lock will disable the checkbox, which in turn (via its command) should disable browse.
                    # Let's add an explicit disable here if event_locked for the browse button too.
                    is_corresponding_logic_active = False
                    # This is a simplification; proper linking is needed for full robustness
                    # We'd need to find the username for this row to check self.user_logic_active_vars[username].get()
                    # For now, just disable if event_locked, otherwise let checkbox command handle it.
                    if i < len(self.user_logic_checkboxes) and self.user_logic_checkboxes[i].winfo_exists():
                        # This is not ideal, as it reads the state of the var from the widget, not the source of truth
                        # It's better to get the username and then self.user_logic_active_vars[username].get()
                        # For now, let's assume the checkbox's state is what we need
                        # CORRECTED: Use username to get the BooleanVar from self.user_logic_active_vars
                        username_for_logic_check = ""
                        if i < len(open_users): # open_users is defined at the start of the method
                            username_for_logic_check = open_users[i]
                        
                        if username_for_logic_check and username_for_logic_check in self.user_logic_active_vars:
                            logic_var = self.user_logic_active_vars[username_for_logic_check]
                            if self.user_logic_checkboxes[i].cget('state') != tk.DISABLED and logic_var.get():
                                is_corresponding_logic_active = True
                        # else: if username not found or var not in dict, is_corresponding_logic_active remains False

                if event_locked: # Event type frame lock
                    browse_btn.config(state=tk.DISABLED)
                else:
                    # If event frame is not locked, browse button state depends on its associated logic checkbox's state.
                    # The checkbox's command already handles this dynamically when the checkbox is clicked.
                    # Here, we just ensure initial state consistency when the event_type_lock itself changes.
                    browse_btn.config(state=tk.NORMAL if is_corresponding_logic_active else tk.DISABLED)

    def log_scan_event(self, code):
        import requests
        from config_utils import get_config
        import traceback
        import re

        event_type = self.event_type_var.get()
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')

        base_project_code, full_project_code = self._extract_project_code(code)
        project_code_to_log = full_project_code

        if event_type == 'OPEN' and '_REP' not in full_project_code and base_project_code and base_project_code in self.open_projects:
            self.log_message(f"Warning: Project {base_project_code} is al OPEN.")
            self.usb_entry.config(bg='yellow')
            self.after(2000, lambda: self.usb_entry.config(bg='white'))
            return

        self.log_message("log_scan_event called")
        self.log_message(f"  Code: {code}")
        self.log_message(f"  Base Project: {base_project_code}, Full Project: {project_code_to_log}")
        self.log_message(f"  Event type: {event_type}")

        if not api_url:
            self.log_message("  [ERROR] API URL not configured, cannot log event.")
            self.usb_entry.config(bg='red')
            self.after(2000, lambda: self.usb_entry.config(bg='white'))
            return

        all_ok = True
        current_user = config.get('user', 'unknown')

        if event_type == 'OPEN':
            data_afgemeld = {
                'event': 'AFGEMELD',
                'details': code,
                'project': project_code_to_log,
                'user': current_user
            }
            self.log_message(f"  [OPEN LOGIC] Payload for current user (AFGEMELD): {data_afgemeld}")
            try:
                resp_afgemeld = requests.post(api_url, json=data_afgemeld, timeout=3)
                if resp_afgemeld.ok:
                    if base_project_code:
                        self.open_projects.discard(base_project_code)
                else:
                    all_ok = False
            except Exception:
                self.log_message(f"    [EXCEPTION] AFGEMELD request failed for user {current_user}!")
                self.log_message(traceback.format_exc())
                all_ok = False

            open_users = config.get('scanner_panel_open_event_users', [])
            user_logic_active_states = config.get('scanner_panel_open_event_user_logic_active', {})

            for user in open_users:
                if user == current_user:
                    continue

                if user_logic_active_states.get(user, True):
                    user_dir = self.scanner_panel_open_event_user_paths.get(user)
                    match_found = False
                    if user_dir and os.path.isdir(user_dir):
                        try:
                            if base_project_code and base_project_code.strip():
                                for item_name in os.listdir(user_dir):
                                    item_base_name, _ = os.path.splitext(item_name)
                                    is_rep_scan = bool(re.search(r'_REP_?', full_project_code, re.IGNORECASE))
                                    if is_rep_scan:
                                        # For REP scans, match the full dynamic code
                                        if item_base_name.upper() == full_project_code.upper():
                                            match_found = True
                                            break
                                    else:
                                        # For standard scans, match base code but exclude REP items
                                        if item_base_name.upper() == base_project_code.upper() and '_REP_' not in item_name.upper():
                                            match_found = True
                                            break
                        except OSError as e_os:
                            self.log_message(f"  [OPEN LOGIC] Error accessing dir {user_dir} for {user}: {e_os}")
                            continue

                    if match_found:
                        self.log_message(f"  [OPEN LOGIC] Match found for '{project_code_to_log}' in '{user_dir}' for user '{user}'.")
                        data_open = {
                            'event': 'OPEN',
                            'details': f"Match found for {project_code_to_log} in {user_dir}",
                            'project': project_code_to_log,
                            'user': user
                        }
                        try:
                            resp_open = requests.post(api_url, json=data_open, timeout=3)
                            if resp_open.ok:
                                if base_project_code:
                                    self.open_projects.add(base_project_code)
                                self.background_import_service.trigger_import_for_event(
                                    user_type=user,
                                    project_code=project_code_to_log,
                                    event_details=f"Scan event: {code}",
                                    timestamp=datetime.now().isoformat()
                                )
                            else:
                                all_ok = False
                        except Exception:
                            self.log_message(f"    [EXCEPTION] OPEN request failed for user {user}!")
                            self.log_message(traceback.format_exc())
                            all_ok = False
                    else:
                        self.log_message(f"  [OPEN LOGIC] No match for '{project_code_to_log}' in '{user_dir}' for user '{user}'.")
                else:
                    self.log_message(f"  [OPEN LOGIC] Logic inactive for user '{user}'. Skipping OPEN event.")

            if all_ok:
                self.usb_entry.config(bg='light green')
            else:
                self.usb_entry.config(bg='red')
            self.after(2000, lambda: self.usb_entry.config(bg='white'))
        else:
            data = {
                'event': event_type,
                'details': code,
                'project': project_code_to_log,
                'user': current_user
            }
            try:
                response = requests.post(api_url, json=data, timeout=3)
                if response.ok:
                    if event_type == 'AFGEMELD' and base_project_code:
                        self.open_projects.discard(base_project_code)
                    self.usb_entry.config(bg='light green')
                else:
                    self.usb_entry.config(bg='red')
            except Exception as e:
                self.log_message(f"    [EXCEPTION] Default request failed!")
                self.log_message(traceback.format_exc())
                self.usb_entry.config(bg='red')
            self.after(2000, lambda: self.usb_entry.config(bg='white'))

    def _extract_project_code(self, code):
        import re
        base_project_code = ""
        full_project_code = ""
        
        # Find base project code (MOxxxxx or 5-6 digits)
        mo_match = re.search(r'(MO\d{5})', code)
        if mo_match:
            base_project_code = mo_match.group(1)
        else:
            accura_match = re.search(r'(\d{5,6})', code)
            if accura_match:
                base_project_code = accura_match.group(1)

        if not base_project_code:
            return "", "" # No project code found

        # Now find the full project code including the dynamic _REP_ part
        rep_match = re.search(f'({re.escape(base_project_code)}_REP(?:_\\S*)?)', code, re.IGNORECASE)
        if rep_match:
            full_project_code = rep_match.group(1)
        else:
            full_project_code = base_project_code
            
        return base_project_code, full_project_code

    def _set_dbpanel_connection_status(self, connected, error_reason=None):
        # Try to find and update DatabasePanel connection status label
        parent = self.master
        while parent is not None:
            for child in parent.winfo_children():
                # DatabasePanel is a sibling panel
                if child.__class__.__name__ == 'DatabasePanel':
                    try:
                        child.set_connection_status(connected, error_reason)
                    except Exception:
                        pass
            parent = getattr(parent, 'master', None)

    def refresh_ports(self):
        try:
            import serial.tools.list_ports
            ports = [port.device for port in serial.tools.list_ports.comports()]
            self.com_port_combo['values'] = ports
            if self.com_port_var.get() not in ports:
                self.com_port_var.set(ports[0] if ports else '')
        except Exception as e:
            self.com_port_combo['values'] = []
            self.com_port_var.set('')

    def connect_com(self):
        if self.ser and self.ser.is_open:
            self.log_message("COM port already connected.")
            return

        port = self.com_port_var.get()
        baud_rate_str = self.baud_rate_var.get()

        if not port:
            messagebox.showerror("COM Fout", "Selecteer aub een COM poort.")
            self.com_status_label.config(text="Geen poort", fg="red")
            return

        if not baud_rate_str.isdigit():
            messagebox.showerror("COM Fout", "Baud rate moet een getal zijn.")
            self.com_status_label.config(text="Baud ongeldig", fg="red")
            return
        
        baud_rate = int(baud_rate_str)

        try:
            self.log_message(f"Verbinden met {port} op {baud_rate} baud...")
            self.ser = serial.Serial(port, baud_rate, timeout=1)
            
            if self.ser.is_open:
                self.com_status_label.config(text="Verbonden", fg="green")
                self.connect_btn.config(state=tk.DISABLED)
                self.disconnect_btn.config(state=tk.NORMAL)
                self.com_port_combo.config(state='disabled')
                if hasattr(self, 'baud_rate_entry'):
                    self.baud_rate_entry.config(state='disabled')

                # On successful connection, save the auto-connect preference
                save_config({'scanner_panel_com_auto_connect': True})
                self.is_reading = True
                self.read_thread = threading.Thread(target=self._read_com_port_loop, daemon=True)
                self.read_thread.start()
                self.log_message(f"Verbonden met {port}. Lees thread gestart.")

        except serial.SerialException as e:
            self.log_message(f"SerialException: {e}")
            self.com_status_label.config(text="Verbindfout", fg="red")
            messagebox.showerror("COM Fout", f"Fout bij verbinden met {port}:\n{e}")
            self.ser = None
        except Exception as e:
            self.log_message(f"Algemene fout bij verbinden: {e}")
            self.com_status_label.config(text="Onbekende fout", fg="red")
            messagebox.showerror("COM Fout", f"Algemene fout: {e}")
            self.ser = None

    def disconnect_com(self):
        self.log_message("Poging tot verbreken COM poort...")
        self.is_reading = False  # Signal thread to stop
        if hasattr(self, 'read_thread') and self.read_thread and self.read_thread.is_alive():
            self.log_message("Wachten tot lees thread stopt...")
            self.read_thread.join()  # Wait indefinitely for the thread to finish
            self.log_message("Lees thread succesvol gestopt.")
        self.read_thread = None

        if hasattr(self, 'ser') and self.ser and self.ser.is_open:
            try:
                self.ser.close()
                self.log_message(f"COM poort {self.ser.portstr} gesloten.")
            except Exception as e:
                self.log_message(f"Fout bij sluiten COM poort: {e}")
        
        self.ser = None

        # Update UI only if the panel's widgets still exist.
        # This prevents TclError if the panel is destroyed right after this call.
        if self.winfo_exists():
            self.com_status_label.config(text="Niet verbonden", fg="red")
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.com_port_combo.config(state='readonly')
            if hasattr(self, 'baud_rate_entry'):
                self.baud_rate_entry.config(state=tk.NORMAL)
        
        # On manual disconnect, save the preference to not auto-connect next time
        save_config({'scanner_panel_com_auto_connect': False})

    def _read_com_port_loop(self):
        print("[ScannerPanel] COM poort leeslus gestart.")
        try:
            while self.is_reading:
                if self.ser and self.ser.is_open:  # Check if port is configured and open
                    if self.ser.in_waiting > 0:  # Check if data is available
                        try:
                            line = self.ser.readline().decode('utf-8', errors='ignore')
                            if line:
                                line_stripped = line.strip()
                                if self.app_has_focus_var and not self.app_has_focus_var.get():
                                    print(f"[ScannerPanel COM Read] Window not focused. Ignoring data: {line_stripped}")
                                    time.sleep(0.1)  # Don't busy-wait if window not focused but data is coming
                                    continue  # Skip processing

                                print(f"[ScannerPanel COM Read] Raw data: {line_stripped}")
                                self.master.after(0, self.process_com_data, line_stripped)
                        except serial.SerialTimeoutException:  # Handle timeout specifically if it occurs
                            continue  # Just continue the loop, no data received
                        except serial.SerialException as e:
                            print(f"[ScannerPanel COM Read] Serial error: {e}")
                            # Schedule disconnect_com to run in main thread to avoid UI issues from thread
                            if hasattr(self.master, 'after'): # Ensure master has 'after' (it should as a Tk widget)
                                self.master.after(0, self.disconnect_com)
                            else: # Fallback if master is not what we expect, though unlikely
                                self.disconnect_com()
                            break  # Exit the while self.is_reading loop
                        except Exception as e:
                            print(f"[ScannerPanel COM Read] Error reading from COM port: {e}")
                            # import traceback
                            # traceback.print_exc()
                            time.sleep(1)  # Wait a bit before retrying
                    else:  # No data in waiting on the open port
                        if self.app_has_focus_var and not self.app_has_focus_var.get():
                            time.sleep(0.2)  # Slightly longer sleep if no data and not focused
                        else:
                            time.sleep(0.05)  # Shorter sleep if focused but no data
                else:  # Port is not open or not configured (self.ser is None)
                    if self.app_has_focus_var and not self.app_has_focus_var.get():
                        time.sleep(0.5)  # Longer sleep if not focused and port not open/configured
                    else:
                        time.sleep(0.1)  # Check port status periodically
                
                # Crucial check: if disconnect_com was called (e.g., by user button press or error handler),
                # self.is_reading would be False. Exit loop immediately.
                if not self.is_reading:
                    break
        except Exception as e:
            print(f"[ScannerPanel] Externe fout in _read_com_port_loop: {e}")
        finally:
            print("[ScannerPanel] COM poort leeslus beëindigd.")
            # Ensure disconnect UI updates if loop exits unexpectedly
            if self.is_reading: # If loop exited but we were supposed to be reading
                self.is_reading = False # Ensure flag is false
                self.after(0, self.disconnect_com) # Attempt a full disconnect sequence from main thread

    def shutdown(self):
        """Gracefully disconnect COM port on app shutdown without changing auto-connect config."""
        print("[ScannerPanel] Shutdown called. Disconnecting COM port.")
        self.is_reading = False  # Signal thread to stop
        if hasattr(self, 'read_thread') and self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)  # Wait for thread to finish
        
        if hasattr(self, 'ser') and self.ser and self.ser.is_open:
            try:
                self.ser.close()
                print("[ScannerPanel] COM port successfully closed on shutdown.")
            except Exception as e:
                print(f"[ScannerPanel] Error closing COM port on shutdown: {e}")
        self.ser = None

    def process_com_data(self, data):
        """Process data received from COM port. Runs in main Tkinter thread."""
        print(f"[ScannerPanel] Verwerken van COM data: {data}")
        # Assuming the data is the barcode itself, log it
        # You might need to clear an entry field or update UI based on this data
        self.log_scan_event(data)
        # Example: if you have an entry for COM data to be displayed:
        # self.com_received_data_var.set(data)



    def on_usb_scan(self, event):
        code = self.usb_code_var.get().strip()
        if code:
            
            # Send to database log API
            import threading
            threading.Thread(target=self.log_scan_event, args=(code,), daemon=True).start()

    def save_com_port(self, *args):
        save_config({'scanner_panel_com_port': self.com_port_var.get()})

    def save_baud_rate(self, *args):
        save_config({'scanner_panel_baud_rate': self.baud_rate_var.get()})
