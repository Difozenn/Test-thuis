import time
import tkinter as tk
import re
from tkinter import ttk, messagebox, filedialog
import serial.tools.list_ports
import serial
import threading
import os
from datetime import datetime
from config_utils import get_config, save_config
from ..utils import Tooltip

class ScannerPanel(tk.Frame):
    
    app_has_focus_var = None
    
    def __init__(self, master, app, app_has_focus_var=None, background_service_instance=None):
        super().__init__(master, bg="#f0f0f0")
        self.master = master
        self.app = app
        self.app_has_focus_var = app_has_focus_var
        self.background_import_service = background_service_instance
        
        # Register callback for background service logs
        if self.background_import_service:
            self.background_import_service.log_callback = self.log_message_from_service
        
        config = get_config()
        
        # --- USB Keyboard Frame ---
        self.usb_frame = tk.LabelFrame(self, text="USB Keyboard Scanner", bg="#f0f0f0", padx=10, pady=5)
        self.usb_frame.columnconfigure(0, weight=1)
        self.usb_code_var = tk.StringVar()
        self.usb_entry = tk.Entry(self.usb_frame, textvariable=self.usb_code_var)
        self.usb_entry.grid(row=0, column=0, padx=5, pady=10, sticky='ew')
        self.usb_entry.bind('<Return>', self.on_usb_scan)
        
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
        self.event_frame = tk.LabelFrame(self, text="Event Type", bg="#f0f0f0", padx=10, pady=5)
        self.event_frame.pack(pady=(0, 10), fill='x', padx=20)

        # --- Log Viewer Frame ---
        self.log_viewer_frame = tk.LabelFrame(self, text="Activiteitenlog", bg="#f0f0f0", padx=10, pady=5)
        self.log_viewer_frame.pack(pady=(0, 10), fill='both', expand=True, padx=20)

        # Add clear button
        log_button_frame = tk.Frame(self.log_viewer_frame, bg="#f0f0f0")
        log_button_frame.pack(fill='x', pady=(0, 5))
        tk.Button(log_button_frame, text="Log wissen", command=self.clear_log).pack(side='right')

        self.log_text = tk.Text(self.log_viewer_frame, height=10, bg="white", fg="black", state='disabled', wrap=tk.WORD)
        self.log_scroll = tk.Scrollbar(self.log_viewer_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=self.log_scroll.set)

        self.log_scroll.pack(side='right', fill='y')
        self.log_text.pack(side='left', fill='both', expand=True)

        # Configure text tags for different message types
        self.log_text.tag_config("info", foreground="black")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("debug", foreground="gray")

        # Frame for radio buttons and lock button
        self.radio_lock_frame = tk.Frame(self.event_frame, bg="#f0f0f0")
        self.radio_lock_frame.pack(fill='x', anchor='nw')

        # Frame for user-specific path settings
        self.user_paths_frame = tk.Frame(self.event_frame, bg="#f0f0f0")

        self.event_type_locked = config.get('scanner_panel_event_type_locked', False)
        self.open_radio = tk.Radiobutton(self.radio_lock_frame, text="OPEN", variable=self.event_type_var, value="OPEN", bg="#f0f0f0", command=self._on_event_type_radio_change)
        self.closed_radio = tk.Radiobutton(self.radio_lock_frame, text="AFGEMELD", variable=self.event_type_var, value="AFGEMELD", bg="#f0f0f0", command=self._on_event_type_radio_change)
        self.open_radio.pack(side='left', padx=10, pady=(0,5))
        self.closed_radio.pack(side='left', padx=10, pady=(0,5))
        self.lock_btn = tk.Button(self.radio_lock_frame, text="Lock" if not self.event_type_locked else "Unlock", command=self.toggle_event_type_lock, width=7)

        # Load user-specific paths from config
        self.user_specific_paths_vars = {}
        self.remove_user_buttons = []
        self.user_browse_buttons = []
        self.user_logic_checkboxes = []
        self.add_user_frame_widget = None
        self.scanner_panel_open_event_user_paths = config.get('scanner_panel_open_event_user_paths', {})
        self.user_logic_active_vars = {}
        self.scanner_panel_open_event_user_logic_active = config.get('scanner_panel_open_event_user_logic_active', {})
        self.scanner_user_to_processing_type_map = config.get('scanner_user_to_processing_type_map', {})

        # Serial port attributes
        self.ser = None
        self.is_reading = False
        self.read_thread = None

        self.open_projects = set()

        self.load_config_values()
        
        if hasattr(self.app, 'admin_config_locked_var') and isinstance(self.app.admin_config_locked_var, tk.BooleanVar):
            self.app.admin_config_locked_var.trace_add('write', self._update_admin_dependent_ui)
            self._update_admin_dependent_ui()
        else:
            self.log_message("Admin configuratie vergrendeld", "warning")
            self._update_admin_dependent_ui()

        self.update_frame_visibility()
        self.apply_event_type_lock_ui()
        self._update_open_event_ui_visibility()

        self._previous_scanner_type = self.scanner_type_var.get()

        # Auto-connect if enabled
        config = get_config()
        if config.get('scanner_panel_com_auto_connect', False) and self.scanner_type_var.get() == 'COM':
            self.log_message("Automatisch verbinden is ingeschakeld", "info")
            self.after(100, self.connect_com)

        self._create_lock_button()

    def log_message(self, message, level="info", show_timestamp=True):
        """Adds a user-friendly message to the log viewer."""
        if level == "debug":
            return
            
        formatted_message = self._format_user_message(message)
        if not formatted_message:
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S") if show_timestamp else ""
        full_message = f"[{timestamp}] {formatted_message}\n" if timestamp else f"{formatted_message}\n"
        
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, full_message, level)
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def log_message_from_service(self, message):
        """Handle log messages from background service with special formatting."""
        if "BACKGROUND_PROJECT_OPENED:" in message:
            parts = message.split(":")
            if len(parts) >= 3:
                project = parts[1]
                user = parts[2]
                self.log_message(f"✓ Project {project} geopend voor {user}", "success")
        elif "BACKGROUND_PROJECT_OPEN_FAILED:" in message:
            parts = message.split(":")
            if len(parts) >= 3:
                project = parts[1]
                user = parts[2]
                self.log_message(f"✗ Kan project {project} niet openen voor {user}", "error")
        elif "BACKGROUND_IO_ERROR:" in message:
            parts = message.split(":")
            if len(parts) >= 3:
                project = parts[1]
                user = parts[2]
                self.log_message(f"⚠️ Map toegangsfout voor {user}", "warning")
        elif "BACKGROUND_PROCESSING_COMPLETE:" in message:
            project = message.split(":")[1] if ":" in message else ""
            self.log_message(f"✓ Verwerking voltooid voor {project}", "success")
        elif "BACKGROUND_FATAL_ERROR:" in message:
            project = message.split(":")[1] if ":" in message else ""
            self.log_message(f"❌ Kritieke fout bij verwerken {project}", "error")
        elif "HOPS import gestart" in message:
            self.log_message("📊 HOPS import gestart", "info")
        elif "MDB import gestart" in message:
            self.log_message("📊 MDB import gestart", "info")
        elif "Excel rapport succesvol opgeslagen" in message:
            if "HOPS" in message:
                self.log_message("✓ HOPS Excel rapport aangemaakt", "success")
            elif "MDB" in message:
                self.log_message("✓ MDB Excel rapport aangemaakt", "success")
        elif "import thread voltooid" in message:
            if "Totaal HOPS:" in message or "Totaal MDB:" in message:
                self.log_message("✓ Import succesvol afgerond", "success")
        elif "OPEN event updated with Excel path" in message:
            self.log_message("✓ Excel bestand gekoppeld aan project", "success")

    def _format_user_message(self, message):
        """Convert technical messages to user-friendly Dutch messages."""
        skip_patterns = [
            "Debug:", "DEBUG", "_extract_", "log_scan_event called",
            "Config loaded", "Configuratie succesvol geladen",
            "[BG_TASK]", "Event ontvangen:", "[db_log_api]",
            "Background task started", "Checking dir", "Match found",
            "Waiting for", "Successfully posted", "API URL",
            "OPEN LOGIC", "Pre-emptive", "Initiating background"
        ]
        
        if any(pattern in message for pattern in skip_patterns):
            return None
            
        conversions = {
            "Verbinden met": "Verbinding maken met scanner op",
            "Verbonden met": "✓ Scanner verbonden op",
            "COM poort": "Scanner poort",
            "Niet verbonden": "Scanner niet verbonden",
            "Verbreek": "Verbinding verbroken",
            "Auto-connect is ON": "Automatisch verbinden ingeschakeld",
            "Project": "Project",
            "is al OPEN": "is al geopend",
            "AFGEMELD": "afgesloten",
            "OPEN": "geopend",
            "import overgeslagen": "verwerking overgeslagen",
            "Geen overeenkomende projectmap gevonden": "Project map niet gevonden",
            "Set path for": "Map ingesteld voor",
            "Path selection cancelled": "Map selectie geannuleerd",
            "Gebruiker": "Gebruiker",
            "toegevoegd": "toegevoegd",
            "verwijderd": "verwijderd",
            "Error": "Fout",
            "Failed": "Mislukt"
        }
        
        result = message
        for eng, nl in conversions.items():
            result = result.replace(eng, nl)
            
        return result

    def clear_log(self):
        """Clear the log viewer."""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.log_message("Log gewist", "info")

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
        else:
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
        self.scanner_user_to_processing_type_map = config.get('scanner_user_to_processing_type_map', {})
        self.available_processing_types = ["GEEN_PROCESSING", "MDB_PROCESSING", "HOPS_PROCESSING"]

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
        self._apply_event_type_lock_to_user_controls()

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
        self.scanner_panel_open_event_user_logic_active = user_logic_states
        status = "geactiveerd" if is_active else "gedeactiveerd"
        self.log_message(f"Mappen-check {status} voor {username}", "info")

    def _build_open_event_user_paths_ui(self):
        for widget in self.user_paths_frame.winfo_children():
            widget.destroy()
        self.user_specific_paths_vars.clear()
        self.user_logic_active_vars.clear()
        self.remove_user_buttons.clear()
        self.user_browse_buttons.clear()
        self.user_logic_checkboxes.clear()
        self.add_user_frame_widget = None

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
            Tooltip(logic_checkbox, "Activeer/Deactiveer automatische import voor deze gebruiker.")
            user_label = tk.Label(user_frame, text=f"{username}:", width=15, anchor='w', bg="#f0f0f0")
            
            processing_type = self.scanner_user_to_processing_type_map.get(username, "N/A")
            processing_type_label = tk.Label(user_frame, text=f"Type: {processing_type}", width=20, anchor='w', bg="#f0f0f0")

            remove_button = tk.Button(user_frame, text="Verwijderen", command=lambda u=username: self._remove_user_config(u), bg="#ffdddd", fg="#990000")
            self.remove_user_buttons.append(remove_button)

            logic_checkbox.pack(side='left', padx=(0, 2))
            user_label.pack(side='left', padx=(0, 5)) 
            processing_type_label.pack(side='left', padx=(0,10)) 
            path_display_entry.pack(side='left', expand=True, fill='x', padx=(0,5))
            browse_button.pack(side='left', padx=(0, 2))
            remove_button.pack(side='left', padx=(0,0)) 

            is_initially_checked = logic_active_var.get()
            path_display_entry.config(state='readonly' if is_initially_checked else 'disabled')
            browse_button.config(state='normal' if is_initially_checked else 'disabled')
            if not is_initially_checked:
                path_var.set("Niet ingesteld")

        self._update_admin_dependent_ui()
        self._apply_event_type_lock_to_user_controls()

        self.add_user_frame_widget = tk.Frame(self.user_paths_frame, bg="#e0e0e0", pady=10)

        tk.Label(self.add_user_frame_widget, text="Nieuwe Gebruiker:", bg="#e0e0e0").pack(side='left', padx=(5,2))
        self.new_username_entry = tk.Entry(self.add_user_frame_widget, width=15)
        self.new_username_entry.pack(side='left', padx=2)

        tk.Label(self.add_user_frame_widget, text="Type:", bg="#e0e0e0").pack(side='left', padx=(5,2))
        self.new_user_processing_type_var = tk.StringVar()
        self.new_user_processing_type_combo = ttk.Combobox(self.add_user_frame_widget, textvariable=self.new_user_processing_type_var, values=self.available_processing_types, width=20, state='readonly')
        if self.available_processing_types:
            self.new_user_processing_type_combo.current(0)
        self.new_user_processing_type_combo.pack(side='left', padx=2)

        add_button = tk.Button(self.add_user_frame_widget, text="Toevoegen", command=self._add_user_config, bg="#d0e0d0", fg="#006600")
        add_button.pack(side='left', padx=(5,5))

    def _browse_user_path(self, username, path_var):
        directory = filedialog.askdirectory(title=f"Select Directory for {username}")
        if directory:
            path_var.set(directory)
            config_data = get_config()
            user_paths = config_data.get('scanner_panel_open_event_user_paths', {})
            user_paths[username] = directory
            save_config({'scanner_panel_open_event_user_paths': user_paths})
            self.scanner_panel_open_event_user_paths = user_paths
            self.log_message(f"Map ingesteld voor {username}: {directory}", "success")
        else:
            self.log_message(f"Map selectie geannuleerd voor {username}", "info")

    def _remove_user_config(self, username_to_remove):
        if not messagebox.askyesno("Bevestig Verwijdering", f"Weet u zeker dat u gebruiker '{username_to_remove}' en alle bijbehorende configuraties wilt verwijderen?"):
            return

        config_data = get_config()

        open_users = config_data.get('scanner_panel_open_event_users', [])
        if username_to_remove in open_users:
            open_users.remove(username_to_remove)
            config_data['scanner_panel_open_event_users'] = open_users

        processing_map = config_data.get('scanner_user_to_processing_type_map', {})
        if username_to_remove in processing_map:
            del processing_map[username_to_remove]
            config_data['scanner_user_to_processing_type_map'] = processing_map

        logic_active_map = config_data.get('scanner_panel_open_event_user_logic_active', {})
        if username_to_remove in logic_active_map:
            del logic_active_map[username_to_remove]
            config_data['scanner_panel_open_event_user_logic_active'] = logic_active_map

        paths_map = config_data.get('scanner_panel_open_event_user_paths', {})
        if username_to_remove in paths_map:
            del paths_map[username_to_remove]
            config_data['scanner_panel_open_event_user_paths'] = paths_map
        
        save_config(config_data)
        self.log_message(f"Gebruiker '{username_to_remove}' verwijderd", "success")

        self.load_config_values()
        self._build_open_event_user_paths_ui()
        self._update_admin_dependent_ui()

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

        open_users.append(new_username)
        config_data['scanner_panel_open_event_users'] = open_users

        processing_map = config_data.get('scanner_user_to_processing_type_map', {})
        processing_map[new_username] = selected_processing_type
        config_data['scanner_user_to_processing_type_map'] = processing_map

        logic_active_map = config_data.get('scanner_panel_open_event_user_logic_active', {})
        logic_active_map[new_username] = True
        config_data['scanner_panel_open_event_user_logic_active'] = logic_active_map

        paths_map = config_data.get('scanner_panel_open_event_user_paths', {})
        paths_map[new_username] = "Niet ingesteld"
        config_data['scanner_panel_open_event_user_paths'] = paths_map
        
        save_config(config_data)
        self.log_message(f"Gebruiker '{new_username}' ({selected_processing_type}) toegevoegd", "success")

        self.new_username_entry.delete(0, tk.END)
        if self.available_processing_types:
            self.new_user_processing_type_combo.current(0)

        self.load_config_values()
        self._build_open_event_user_paths_ui()
        self._update_admin_dependent_ui()

    def _update_admin_dependent_ui(self, *args):
        is_locked = True
        if hasattr(self.app, 'admin_config_locked_var') and isinstance(self.app.admin_config_locked_var, tk.BooleanVar):
            try:
                is_locked = self.app.admin_config_locked_var.get()
            except tk.TclError:
                self.log_message("Admin lock status onbekend", "warning")
                is_locked = True

        for btn in self.remove_user_buttons:
            if btn.winfo_exists():
                if is_locked:
                    btn.pack_forget()
                else:
                    if not btn.winfo_manager(): 
                        btn.pack(side='left', padx=(5,0))

        if hasattr(self, 'add_user_frame_widget') and self.add_user_frame_widget and self.add_user_frame_widget.winfo_exists():
            if is_locked:
                self.add_user_frame_widget.pack_forget()
            else:
                if not self.add_user_frame_widget.winfo_manager():
                    self.add_user_frame_widget.pack(fill='x', side='bottom', pady=(10,0), ipady=5)
        elif not is_locked and hasattr(self, 'add_user_frame_widget') and self.add_user_frame_widget:
            if not self.add_user_frame_widget.winfo_manager():
                 self.add_user_frame_widget.pack(fill='x', side='bottom', pady=(10,0), ipady=5)

    def _apply_event_type_lock_to_user_controls(self):
        event_locked = self.event_type_locked
        open_users = sorted(self.scanner_panel_open_event_user_paths.keys())

        for checkbox in self.user_logic_checkboxes:
            if checkbox.winfo_exists():
                checkbox.config(state=tk.DISABLED if event_locked else tk.NORMAL)
        
        open_users = sorted(self.scanner_panel_open_event_user_paths.keys())
        for i, browse_btn in enumerate(self.user_browse_buttons):
            if browse_btn.winfo_exists():
                is_corresponding_logic_active = False
                if i < len(self.user_logic_checkboxes) and self.user_logic_checkboxes[i].winfo_exists():
                    username_for_logic_check = ""
                    if i < len(open_users):
                        username_for_logic_check = open_users[i]
                    
                    if username_for_logic_check and username_for_logic_check in self.user_logic_active_vars:
                        logic_var = self.user_logic_active_vars[username_for_logic_check]
                        if self.user_logic_checkboxes[i].cget('state') != tk.DISABLED and logic_var.get():
                            is_corresponding_logic_active = True

                if event_locked:
                    browse_btn.config(state=tk.DISABLED)
                else:
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

        if event_type == 'OPEN' and project_code_to_log and project_code_to_log in self.open_projects:
            self.log_message(f"ℹ️ Project {project_code_to_log} is al geopend", "warning")
            self.usb_entry.config(bg='light green')
            self.after(2000, lambda: self.usb_entry.config(bg='white'))
            return

        if not api_url:
            self.log_message("❌ API URL niet geconfigureerd", "error")
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
                'base_mo_code': base_project_code,
                'is_rep_variant': bool(re.search(r'_REP_?', project_code_to_log, re.IGNORECASE)),
                'user': current_user
            }
            try:
                resp_afgemeld = requests.post(api_url, json=data_afgemeld, timeout=3)
                if resp_afgemeld.ok:
                    if project_code_to_log:
                        self.open_projects.discard(project_code_to_log)
                else:
                    all_ok = False
            except Exception:
                self.log_message(f"⚠️ Kon bestaand project niet sluiten", "warning")
                all_ok = False

            self.log_message(f"🔄 Project {project_code_to_log} wordt verwerkt voor alle gebruikers...", "info")
            self.background_import_service.process_scan_for_open_event_async(
                project_code_to_log=project_code_to_log,
                base_project_code=base_project_code,
                scanned_code=code,
                current_user_scanner=current_user,
                api_url=api_url,
                config_data=config
            )
            
            if all_ok:
                self.open_projects.add(project_code_to_log)
                self.usb_entry.config(bg='light green')
            else:
                self.usb_entry.config(bg='red')
            self.after(2000, lambda: self.usb_entry.config(bg='white'))
        else:
            data = {
                'event': event_type,
                'details': code,
                'project': project_code_to_log,
                'base_mo_code': base_project_code,
                'is_rep_variant': bool(re.search(r'_REP_?', project_code_to_log, re.IGNORECASE)),
                'user': current_user
            }
            try:
                response = requests.post(api_url, json=data, timeout=3)
                if response.ok:
                    if event_type == 'AFGEMELD' and project_code_to_log:
                        self.open_projects.discard(project_code_to_log)
                        self.log_message(f"✓ Project {project_code_to_log} afgesloten", "success")
                    self.usb_entry.config(bg='light green')
                else:
                    self.log_message(f"❌ Fout bij afsluiten project", "error")
                    self.usb_entry.config(bg='red')
            except Exception as e:
                self.log_message(f"❌ Netwerkfout bij afsluiten", "error")
                self.usb_entry.config(bg='red')
            self.after(2000, lambda: self.usb_entry.config(bg='white'))

    def _extract_full_project_name(self, scan_data):
        """
        Extracts the full project name from scan data if it's a REP file path.
        """
        if re.search(r'_REP_?', scan_data, re.IGNORECASE):
            try:
                path_part = scan_data.split(';', 1)[1].strip()
                directory_path = os.path.dirname(path_part)
                project_name = os.path.basename(directory_path)
                if re.search(r'_REP_?', project_name, re.IGNORECASE):
                    return project_name
            except (IndexError, TypeError):
                return None
        return None

    def _extract_project_code(self, code_input):
        import re
        import os

        base_project_code = ""
        mo_match = re.search(r'(MO\d{4,6})', code_input, re.IGNORECASE)
        if mo_match:
            base_project_code = mo_match.group(0).upper()
        else:
            accura_match = re.search(r'(\d{5,6})', code_input)
            if accura_match:
                base_project_code = accura_match.group(0)
        
        if not base_project_code:
            return "", ""

        full_project_code = base_project_code
        
        try:
            path_components = os.path.normpath(code_input).split(os.sep)
            project_folder_name = ""
            for component in path_components:
                if base_project_code in component.upper():
                    project_folder_name = component
                    break
            
            if project_folder_name:
                prefix_match = re.match(r'^(\d{4}_)', project_folder_name)
                if prefix_match:
                    prefix = prefix_match.group(1)
                    if project_folder_name.upper().startswith(prefix + base_project_code):
                        full_project_code = project_folder_name[len(prefix):]
                    else:
                        full_project_code = project_folder_name
                else:
                    full_project_code = project_folder_name
        except Exception as e:
            full_project_code = base_project_code

        return base_project_code, full_project_code

    def _set_dbpanel_connection_status(self, connected, error_reason=None):
        parent = self.master
        while parent is not None:
            for child in parent.winfo_children():
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
            self.log_message("Scanner is al verbonden", "info")
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
            self.log_message(f"Verbinding maken met scanner op {port}...", "info")
            self.ser = serial.Serial(port, baud_rate, timeout=1)
            
            if self.ser.is_open:
                self.com_status_label.config(text="Verbonden", fg="green")
                self.connect_btn.config(state=tk.DISABLED)
                self.disconnect_btn.config(state=tk.NORMAL)
                self.com_port_combo.config(state='disabled')
                if hasattr(self, 'baud_rate_entry'):
                    self.baud_rate_entry.config(state='disabled')

                save_config({'scanner_panel_com_auto_connect': True})
                self.is_reading = True
                self.read_thread = threading.Thread(target=self._read_com_port_loop, daemon=True)
                self.read_thread.start()
                self.log_message(f"✓ Scanner verbonden op {port}", "success")

        except serial.SerialException as e:
            self.log_message(f"❌ Kan niet verbinden met {port}", "error")
            self.com_status_label.config(text="Verbindfout", fg="red")
            messagebox.showerror("COM Fout", f"Fout bij verbinden met {port}:\n{e}")
            self.ser = None
        except Exception as e:
            self.log_message(f"❌ Onbekende fout bij verbinden", "error")
            self.com_status_label.config(text="Onbekende fout", fg="red")
            messagebox.showerror("COM Fout", f"Algemene fout: {e}")
            self.ser = None

    def disconnect_com(self):
        self.log_message("Scanner verbinding wordt verbroken...", "info")
        self.is_reading = False
        if hasattr(self, 'read_thread') and self.read_thread and self.read_thread.is_alive():
            self.read_thread.join()
        self.read_thread = None

        if hasattr(self, 'ser') and self.ser and self.ser.is_open:
            try:
                self.ser.close()
                self.log_message(f"✓ Scanner verbinding verbroken", "success")
            except Exception as e:
                self.log_message(f"⚠️ Fout bij verbreken verbinding", "warning")
        
        self.ser = None

        if self.winfo_exists():
            self.com_status_label.config(text="Niet verbonden", fg="red")
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.com_port_combo.config(state='readonly')
            if hasattr(self, 'baud_rate_entry'):
                self.baud_rate_entry.config(state=tk.NORMAL)
        
        save_config({'scanner_panel_com_auto_connect': False})

    def _read_com_port_loop(self):
        print("[ScannerPanel] COM poort leeslus gestart.")
        try:
            while self.is_reading:
                if self.ser and self.ser.is_open:
                    if self.ser.in_waiting > 0:
                        try:
                            line = self.ser.readline().decode('utf-8', errors='ignore')
                            if line:
                                line_stripped = line.strip()
                                if self.app_has_focus_var and not self.app_has_focus_var.get():
                                    print(f"[ScannerPanel COM Read] Window not focused. Ignoring data: {line_stripped}")
                                    time.sleep(0.1)
                                    continue

                                print(f"[ScannerPanel COM Read] Raw data: {line_stripped}")
                                self.master.after(0, self.process_com_data, line_stripped)
                        except serial.SerialTimeoutException:
                            continue
                        except serial.SerialException as e:
                            print(f"[ScannerPanel COM Read] Serial error: {e}")
                            if hasattr(self.master, 'after'):
                                self.master.after(0, self.disconnect_com)
                            else:
                                self.disconnect_com()
                            break
                        except Exception as e:
                            print(f"[ScannerPanel COM Read] Error reading from COM port: {e}")
                            time.sleep(1)
                    else:
                        if self.app_has_focus_var and not self.app_has_focus_var.get():
                            time.sleep(0.2)
                        else:
                            time.sleep(0.05)
                else:
                    if self.app_has_focus_var and not self.app_has_focus_var.get():
                        time.sleep(0.5)
                    else:
                        time.sleep(0.1)
                
                if not self.is_reading:
                    break
        except Exception as e:
            print(f"[ScannerPanel] Externe fout in _read_com_port_loop: {e}")
        finally:
            print("[ScannerPanel] COM poort leeslus beëindigd.")
            if self.is_reading:
                self.is_reading = False
                self.after(0, self.disconnect_com)

    def shutdown(self):
        """Gracefully disconnect COM port on app shutdown without changing auto-connect config."""
        print("[ScannerPanel] Shutdown called. Disconnecting COM port.")
        self.is_reading = False
        if hasattr(self, 'read_thread') and self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)
        
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
        event_type = self.event_type_var.get()
        if event_type == 'OPEN':
            self.log_message(f"📋 Project {data} wordt geopend...", "info")
        else:
            self.log_message(f"📋 Project {data} wordt afgesloten...", "info")
        
        import threading
        threading.Thread(target=self.log_scan_event, args=(data,), daemon=True).start()

    def on_usb_scan(self, event):
        code = self.usb_code_var.get().strip()
        if code:
            self.usb_code_var.set('')
            
            event_type = self.event_type_var.get()
            if event_type == 'OPEN':
                self.log_message(f"📋 Project {code} wordt geopend...", "info")
            else:
                self.log_message(f"📋 Project {code} wordt afgesloten...", "info")
            
            import threading
            threading.Thread(target=self.log_scan_event, args=(code,), daemon=True).start()

    def save_com_port(self, *args):
        save_config({'scanner_panel_com_port': self.com_port_var.get()})

    def save_baud_rate(self, *args):
        save_config({'scanner_panel_baud_rate': self.baud_rate_var.get()})