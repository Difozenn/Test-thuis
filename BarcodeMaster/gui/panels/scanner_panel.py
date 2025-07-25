import time
import tkinter as tk
import re
from tkinter import ttk, messagebox, filedialog
import serial.tools.list_ports
import serial
import threading
import os
from datetime import datetime, timedelta
from config_utils import get_config, save_config
from ..utils import Tooltip
import requests
import json

class ScannerPanel(tk.Frame):
    
    app_has_focus_var = None
    
    def __init__(self, master, app, app_has_focus_var=None, background_service_instance=None):
        super().__init__(master, bg="#f0f0f0")
        self.master = master
        self.app = app
        self.app_has_focus_var = app_has_focus_var
        self.background_import_service = background_service_instance
        
        # Register callback with db_log_api for forwarding (only one callback needed)
        try:
            from database.db_log_api import register_scanner_callback
            register_scanner_callback(self.log_message_from_service)
            print("[SCANNER] Successfully registered callback with db_log_api")
        except Exception as e:
            print(f"[SCANNER] Could not register callback with db_log_api: {e}")
        
        config = get_config()
        
        # Add session tracking
        self.current_session_id = None
        self.session_start_time = None
        
        # Initialize work hours cache
        self._work_hours_cache = None
        
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

        # --- User Configuration ---
        self.event_frame = tk.LabelFrame(self, text="Gebruiker Configuratie", bg="#f0f0f0", padx=10, pady=5)
        self.event_frame.pack(pady=(0, 10), fill='x', padx=20)
        
        # Add START button frame after event type frame
        self._create_session_controls()

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

        # Frame for user-specific path settings
        self.user_paths_frame = tk.Frame(self.event_frame, bg="#f0f0f0")

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
        # Always show user configuration UI
        self._build_open_event_user_paths_ui()
        self.user_paths_frame.pack(fill='x', padx=5, pady=(5,0))

        self._previous_scanner_type = self.scanner_type_var.get()

        # Auto-connect if enabled
        config = get_config()
        if config.get('scanner_panel_com_auto_connect', False) and self.scanner_type_var.get() == 'COM':
            self.log_message("Automatisch verbinden is ingeschakeld", "info")
            self.after(100, self.connect_com)

        self._create_lock_button()

    def _create_session_controls(self):
        """Create session START button and status display with work hours indicator"""
        self.session_frame = tk.LabelFrame(self, text="Werk Sessie", bg="#f0f0f0", padx=10, pady=5)
        self.session_frame.pack(pady=(0, 10), fill='x', padx=20, after=self.event_frame)
        
        # Work hours status
        work_status_frame = tk.Frame(self.session_frame, bg="#f0f0f0")
        work_status_frame.pack(fill='x', pady=(0, 5))
        
        self.work_hours_label = tk.Label(
            work_status_frame,
            text="",
            bg="#f0f0f0",
            font=('Arial', 9)
        )
        self.work_hours_label.pack(side='left', padx=10)
        
        # Session controls frame
        controls_frame = tk.Frame(self.session_frame, bg="#f0f0f0")
        controls_frame.pack(fill='x', pady=5)
        
        # START button
        self.start_button = tk.Button(
            controls_frame, 
            text="START NIEUWE SESSIE", 
            command=self.start_new_session,
            bg="#4CAF50", 
            fg="white", 
            font=('Arial', 12, 'bold'),
            padx=20, 
            pady=10
        )
        self.start_button.pack(side='left', padx=10)
        
        # Session status label
        self.session_status_label = tk.Label(
            controls_frame, 
            text="Geen actieve sessie", 
            bg="#f0f0f0", 
            font=('Arial', 10)
        )
        self.session_status_label.pack(side='left', padx=20)
        
        # Session timer removed per user request
        
        # Load work hours asynchronously after panel is shown
        self._initial_work_hours_display()
        self.after(100, self.async_update_work_hours_status)
        
        # Start periodic work hours status updates (30 seconds)
        self.after(30000, self.update_work_hours_status)

    def _initial_work_hours_display(self):
        """Show initial work hours display without API call"""
        now = datetime.now()
        self.work_hours_label.config(
            text=f"⏳ Werktijd laden... {now.strftime('%H:%M')}",
            fg="orange"
        )

    def async_update_work_hours_status(self):
        """Load work hours asynchronously in background thread"""
        import threading
        import time
        
        def _load_work_hours():
            try:
                # Load work hours in background
                work_hours = self.get_work_hours_from_api()
                self._work_hours_cache = work_hours
                self._last_cache_refresh = time.time()
                
                # Update UI in main thread
                self.after(0, lambda: self._update_work_hours_display(work_hours))
            except Exception as e:
                print(f"Error loading work hours asynchronously: {e}")
                # Use defaults and update UI
                defaults = {
                    'monday': {'start': 7.5, 'end': 16},
                    'tuesday': {'start': 7.5, 'end': 16},
                    'wednesday': {'start': 7.5, 'end': 16},
                    'thursday': {'start': 7.5, 'end': 16},
                    'friday': {'start': 7.5, 'end': 15},
                    'break_start': 12.0,
                    'break_end': 12.5,
                    'work_days': [0, 1, 2, 3, 4]
                }
                self._work_hours_cache = defaults
                self._last_cache_refresh = time.time()
                self.after(0, lambda: self._update_work_hours_display(defaults))
        
        # Start background thread
        threading.Thread(target=_load_work_hours, daemon=True).start()

    def _update_work_hours_display(self, work_hours):
        """Update work hours display with loaded data"""
        now = datetime.now()
        is_work_time, message = self._check_work_status(work_hours)
        
        if is_work_time:
            # Get current day's work hours
            day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            day_name = day_names[now.weekday()]
            day_config = work_hours.get(day_name, {'start': 7.5, 'end': 16})
            
            start_time = f"{int(day_config['start'])}:{int((day_config['start'] % 1) * 60):02d}"
            end_time = f"{int(day_config['end'])}:{int((day_config['end'] % 1) * 60):02d}"
            
            self.work_hours_label.config(
                text=f"✓ Werktijd: {now.strftime('%H:%M')} ({start_time}-{end_time})",
                fg="green"
            )
            if hasattr(self, 'start_button'):
                self.start_button.config(state='normal')
        else:
            self.work_hours_label.config(
                text=f"✗ {message}",
                fg="red"
            )
            if hasattr(self, 'start_button') and not self.current_session_id:
                self.start_button.config(state='disabled')

    def refresh_work_hours_cache(self):
        """Force refresh of work hours cache from API"""
        print("Refreshing work hours cache from API...")
        self._work_hours_cache = None
        if hasattr(self, '_last_cache_refresh'):
            delattr(self, '_last_cache_refresh')
        self.async_update_work_hours_status()

    def force_refresh_work_hours(self):
        """Public method to force immediate work hours refresh (for external calls)"""
        self.refresh_work_hours_cache()

    def update_work_hours_status(self):
        """Update work hours status display (called periodically)"""
        # Refresh cache every 30 seconds to pick up settings changes quickly
        if hasattr(self, '_last_cache_refresh'):
            import time
            if time.time() - self._last_cache_refresh > 30:  # 30 seconds
                self.refresh_work_hours_cache()
                # Don't return here - continue to schedule next update
        
        if self._work_hours_cache:
            # Use cached work hours for regular updates
            self._update_work_hours_display(self._work_hours_cache)
        else:
            # If cache not available, trigger async load
            self.async_update_work_hours_status()
        
        # Update every 30 seconds for faster settings pickup
        self.after(30000, self.update_work_hours_status)

    def get_work_hours_from_api(self):
        """Fetch work hours configuration from API with fallback handling"""
        defaults = {
            'monday': {'start': 7.5, 'end': 16},
            'tuesday': {'start': 7.5, 'end': 16},
            'wednesday': {'start': 7.5, 'end': 16},
            'thursday': {'start': 7.5, 'end': 16},
            'friday': {'start': 7.5, 'end': 15},
            'break_start': 12.0,
            'break_end': 12.5,
            'work_days': [0, 1, 2, 3, 4]
        }
        
        try:
            config = get_config()
            api_url = config.get('api_url', '').rstrip('/')
            if not api_url:
                return defaults
            
            # Use shorter timeout and handle connection issues gracefully
            response = requests.get(
                api_url.replace('/log', '/api/settings/work-hours'), 
                timeout=2  # Reduced timeout
            )
            
            if response.ok:
                data = response.json()
                if data.get('success') and 'settings' in data:
                    settings = data['settings']
                    
                    # Handle new per-day format
                    result = {
                        'break_start': float(settings.get('break_start', 12)),
                        'break_end': float(settings.get('break_end', 12.5)),
                        'work_days': settings.get('work_days', [0, 1, 2, 3, 4])
                    }
                    
                    # Extract per-day configurations
                    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                    for day in days:
                        if day in settings and isinstance(settings[day], dict):
                            result[day] = {
                                'start': float(settings[day].get('start', 7.5)),
                                'end': float(settings[day].get('end', 16))
                            }
                        else:
                            # Fallback for weekend or missing days
                            result[day] = {'start': 0, 'end': 0}
                    
                    print(f"Work hours loaded from API: {result}")
                    return result
            else:
                print(f"API returned error status: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("Work hours API timeout - using defaults")
        except requests.exceptions.ConnectionError:
            print("Work hours API connection error - using defaults")
        except ValueError as e:
            print(f"Work hours API data conversion error: {e} - using defaults")
        except Exception as e:
            print(f"Unexpected error fetching work hours from API: {e} - using defaults")
        
        return defaults

    def _check_work_status(self, work_hours):
        """Check if current time is within work hours using provided work hours data"""
        now = datetime.now()
        
        # Holiday check first (most important)
        try:
            import requests
            response = requests.get('http://localhost:5001/api/holidays', timeout=2)
            if response.status_code == 200:
                holidays_data = response.json()
                today_str = now.strftime('%Y-%m-%d')
                for holiday in holidays_data.get('holidays', []):
                    if holiday.get('date') == today_str:
                        return False, f"Feestdag - {holiday.get('name', 'Kantoor gesloten')}"
        except:
            # If holiday check fails, continue with other validations
            pass
        
        # Weekend check
        if now.weekday() not in work_hours['work_days']:
            return False, "Weekend - kantoor gesloten"
        
        # Get day-specific work hours
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        day_name = day_names[now.weekday()]
        day_config = work_hours.get(day_name, {'start': 7.5, 'end': 16})
        
        # Time check with per-day configuration
        hour = now.hour + now.minute / 60
        
        if hour < day_config['start']:
            start_time = f"{int(day_config['start'])}:{int((day_config['start'] % 1) * 60):02d}"
            return False, f"Te vroeg - werk begint om {start_time}"
        
        if hour > day_config['end']:
            end_time = f"{int(day_config['end'])}:{int((day_config['end'] % 1) * 60):02d}"
            return False, f"Te laat - werk eindigt om {end_time}"
        
        # Break time check
        if work_hours['break_start'] <= hour <= work_hours['break_end']:
            return False, f"Pauze - van {int(work_hours['break_start']):02d}:{int((work_hours['break_start'] % 1) * 60):02d} tot {int(work_hours['break_end']):02d}:{int((work_hours['break_end'] % 1) * 60):02d}"
        
        return True, "Werktijd"

    def get_current_work_status(self):
        """Check if current time is within work hours using cached or API configuration"""
        if self._work_hours_cache:
            return self._check_work_status(self._work_hours_cache)
        else:
            # Fallback to API call if cache not available
            work_hours = self.get_work_hours_from_api()
            return self._check_work_status(work_hours)

    def start_new_session(self):
        """Start a new work session for current user or close existing session"""
        if self.current_session_id:
            # If there's an active session, stop it
            self.close_current_session()
            return
            
        config = get_config()
        current_user = config.get('user', 'NESTING')
        api_url = config.get('api_url', '').rstrip('/')
        
        if not api_url:
            self.log_message("❌ API URL niet geconfigureerd", "error")
            return
        
        # Check if within work hours
        is_work_time, message = self.get_current_work_status()
        if not is_work_time:
            self.log_message(f"❌ {message}", "error")
            messagebox.showwarning("Buiten Werktijd", f"Kan geen sessie starten: {message}")
            return
        
        # Create new session
        self.session_start_time = datetime.now()
        self.current_session_id = f"{current_user}_{self.session_start_time.strftime('%Y%m%d_%H%M%S')}"
        
        data = {
            'event': 'SESSION_START',
            'user': current_user,
            'session_id': self.current_session_id,
            'timestamp': self.session_start_time.isoformat(),
            'session_type': 'SCANNER'  # Scanner panel sessions
        }
        
        try:
            response = requests.post(api_url.replace('/log', '/session/start'), json=data, timeout=3)
            if response.ok:
                # Also create global project session for production time tracking
                project_session_data = {
                    'event': 'PROJECT_SESSION_START',
                    'user': current_user,
                    'session_id': self.current_session_id,
                    'timestamp': self.session_start_time.isoformat(),
                    'details': 'Global project session started'
                }
                
                try:
                    project_response = requests.post(api_url.replace('/log', '/project_session/start'), json=project_session_data, timeout=3)
                    if project_response.ok:
                        self.log_message(f"✓ Werk sessie gestart voor {current_user}", "success")
                        self.session_status_label.config(text=f"Actieve sessie: {current_user}", fg="green")
                        self.start_button.config(text="STOP SESSIE", bg="#f44336")
                    else:
                        self.log_message("⚠️ Sessie gestart, maar project tracking mislukt", "warning")
                        self.session_status_label.config(text=f"Actieve sessie: {current_user}", fg="green")
                        self.start_button.config(text="STOP SESSIE", bg="#f44336")
                except Exception as pe:
                    self.log_message("⚠️ Sessie gestart, maar project tracking mislukt", "warning")
                    self.session_status_label.config(text=f"Actieve sessie: {current_user}", fg="green")
                    self.start_button.config(text="STOP SESSIE", bg="#f44336")
            else:
                self.log_message("❌ Kon sessie niet starten", "error")
                self.current_session_id = None
                self.session_start_time = None
        except Exception as e:
            self.log_message(f"❌ Fout bij starten sessie: {e}", "error")
            self.current_session_id = None
            self.session_start_time = None

    def close_current_session(self):
        """Close the current active session and AFGEMELD all open projects"""
        if not self.current_session_id:
            return
        
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')
        current_user = config.get('user', 'NESTING')
        timestamp = datetime.now().isoformat()
        
        # First, AFGEMELD all open projects for this user
        if self.open_projects:
            self.log_message(f"🔄 Afsluiten van {len(self.open_projects)} open projecten...", "info")
            
            for project in list(self.open_projects):  # Copy to avoid modification during iteration
                # Item counts now come from Excel files automatically, no manual input needed
                item_count = 0
                
                # Send AFGEMELD for this project
                data_afgemeld = {
                    'event': 'AFGEMELD',
                    'details': f"Auto-close on session end",
                    'project': project,
                    'user': current_user,
                    'item_count': item_count,
                    'session_id': self.current_session_id,
                    'timestamp': timestamp
                }
                
                try:
                    response = requests.post(api_url, json=data_afgemeld, timeout=3)
                    if response.ok:
                        self.log_message(f"✓ Project {project} afgesloten", "success")
                        self.open_projects.discard(project)
                    else:
                        self.log_message(f"⚠️ Fout bij afsluiten project {project}", "warning")
                except Exception as e:
                    self.log_message(f"⚠️ Netwerkfout bij afsluiten project {project}: {e}", "warning")
        
        # Then close the session
        data = {
            'session_id': self.current_session_id,
            'timestamp': timestamp
        }
        
        try:
            response = requests.post(api_url.replace('/log', '/session/end'), json=data, timeout=3)
            if response.ok:
                end_time = datetime.now()
                # Use work minutes calculation that excludes breaks
                work_minutes = int(self.calculate_work_minutes_local(self.session_start_time, end_time))
                self.log_message(f"✓ Sessie afgesloten. Duur: {work_minutes} minuten", "success")
        except Exception as e:
            self.log_message(f"⚠️ Fout bij afsluiten sessie: {e}", "warning")
        
        self.current_session_id = None
        self.session_start_time = None
        self.session_status_label.config(text="Geen actieve sessie", fg="black")
        self.start_button.config(text="START NIEUWE SESSIE", bg="#4CAF50")
    

    # update_session_timer function removed - timer no longer displayed

    def calculate_work_minutes_local(self, start_time, end_time):
        """Calculate work minutes locally for display using dynamic work hours from settings"""
        total_minutes = 0
        current = start_time
        
        # Get work hours from cache or fallback to API
        work_hours = self._work_hours_cache if self._work_hours_cache else self.get_work_hours_from_api()
        
        # Day name mapping
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        while current < end_time:
            # Skip weekends (or non-work days)
            if current.weekday() not in work_hours.get('work_days', [0, 1, 2, 3, 4]):
                current = current.replace(hour=0, minute=0, second=0) + timedelta(days=1)
                continue
            
            # Get work hours for current day
            day_name = day_names[current.weekday()]
            day_config = work_hours.get(day_name, {'start': 7.5, 'end': 16})
            
            # Work hours for current day
            day_start_hour = day_config['start']
            day_end_hour = day_config['end']
            day_start = current.replace(hour=int(day_start_hour), minute=int((day_start_hour % 1) * 60), second=0)
            day_end = current.replace(hour=int(day_end_hour), minute=int((day_end_hour % 1) * 60), second=0)
            
            # Break hours
            break_start_hour = work_hours.get('break_start', 12)
            break_end_hour = work_hours.get('break_end', 12.5)
            break_start = current.replace(hour=int(break_start_hour), minute=int((break_start_hour % 1) * 60), second=0)
            break_end = current.replace(hour=int(break_end_hour), minute=int((break_end_hour % 1) * 60), second=0)
            
            # Actual work period
            actual_start = max(current, day_start)
            actual_end = min(end_time, day_end)
            
            if actual_start < actual_end:
                # Morning
                if actual_start < break_start:
                    morning_end = min(actual_end, break_start)
                    total_minutes += (morning_end - actual_start).total_seconds() / 60
                
                # Afternoon
                if actual_end > break_end:
                    afternoon_start = max(actual_start, break_end)
                    total_minutes += (actual_end - afternoon_start).total_seconds() / 60
            
            # Next day
            current = current.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        
        return round(total_minutes)

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
        if "BACKGROUND_PROCESSING_STARTED:" in message:
            parts = message.split(":")
            if len(parts) >= 2:
                project = parts[1]
                self.log_message(f"🔄 Verwerking gestart voor project {project}", "info")
        elif "BACKGROUND_WORK_FOUND:" in message:
            parts = message.split(":")
            if len(parts) >= 4:
                project = parts[1]
                user = parts[2]
                count = parts[3]
                item_text = "items" if int(count) != 1 else "item"
                self.log_message(f"✓ {user}: {count} {item_text} gevonden en verwerkt", "success")
        elif "BACKGROUND_NO_WORK_ITEMS:" in message:
            parts = message.split(":")
            if len(parts) >= 4:
                project = parts[1]
                user = parts[2]
                count = parts[3]
                self.log_message(f"○ {user}: {count} items gevonden (geen actie vereist)", "info")
        elif "BACKGROUND_NO_EXCEL_FILE:" in message:
            parts = message.split(":")
            if len(parts) >= 3:
                project = parts[1]
                user = parts[2]
                self.log_message(f"○ {user}: Geen Excel bestand beschikbaar", "info")
        elif "BACKGROUND_PROJECT_OPENED:" in message:
            parts = message.split(":")
            if len(parts) >= 3:
                project = parts[1]
                user = parts[2]
                self.log_message(f"🔄 {user}: Project {project} wordt geopend...", "info")
        elif "BACKGROUND_NO_WORK_FOUND:" in message:
            parts = message.split(":")
            if len(parts) >= 3:
                project = parts[1]
                user = parts[2]
                self.log_message(f"○ {user}: Geen werk beschikbaar", "info")
        elif "BACKGROUND_PROJECT_OPEN_FAILED:" in message:
            parts = message.split(":")
            if len(parts) >= 3:
                project = parts[1]
                user = parts[2]
                self.log_message(f"❌ {user}: Kon project {project} niet openen", "error")
        elif "BACKGROUND_IO_ERROR:" in message:
            parts = message.split(":")
            if len(parts) >= 3:
                project = parts[1]
                user = parts[2]
                self.log_message(f"⚠️ {user}: Map toegangsfout", "warning")
        elif "BACKGROUND_PROCESSING_COMPLETE:" in message:
            project = message.split(":")[1] if ":" in message else ""
            self.log_message(f"✓ Alle verwerking voltooid voor project {project}", "success")
        elif "BACKGROUND_FATAL_ERROR:" in message:
            project = message.split(":")[1] if ":" in message else ""
            self.log_message(f"❌ Kritieke fout bij verwerken project {project}", "error")
        elif "Excel rapport succesvol opgeslagen" in message:
            # Skip these - they're now handled by BACKGROUND_WORK_FOUND messages
            pass
        elif "import thread voltooid" in message:
            # Skip these - they're redundant with Excel rapport messages
            pass
        elif "OPEN event updated with Excel path" in message:
            # Skip these - they're internal file path updates
            pass

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
        self.scanner_panel_open_event_user_paths = config.get('scanner_panel_open_event_user_paths', {})
        self.scanner_panel_open_event_user_logic_active = config.get('scanner_panel_open_event_user_logic_active', {})
        self.scanner_user_to_processing_type_map = config.get('scanner_user_to_processing_type_map', {})
        self.available_processing_types = ["GEEN_PROCESSING", "MDB_PROCESSING", "HOPS_PROCESSING", "NESTING_PROCESSING", "ACCURA_PROCESSING", "BOERE_PROCESSING"]

    def on_scanner_type_change(self):
        """Handles scanner type changes without auto-connecting/disconnecting."""
        self.save_scanner_type()
        self.update_frame_visibility()
        self._previous_scanner_type = self.scanner_type_var.get()

    def save_scanner_type(self):
        save_config({'scanner_panel_type': self.scanner_type_var.get()})


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
        open_users = config.get('scanner_panel_open_event_users', [])
        self.scanner_panel_open_event_user_paths = config.get('scanner_panel_open_event_user_paths', {})
        self.scanner_panel_open_event_user_logic_active = config.get('scanner_panel_open_event_user_logic_active', {})

        if not open_users:
            tk.Label(self.user_paths_frame, text="Geen gebruikers geconfigureerd voor OPEN event paden.", bg="#f0f0f0", fg="gray").pack(pady=5)

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

            # Arrow buttons for reordering
            user_index = open_users.index(username)
            arrow_frame = tk.Frame(user_frame, bg="#f0f0f0")
            
            up_button = tk.Button(arrow_frame, text="↑", command=lambda u=username: self._move_user_up(u), 
                                width=2, state='normal' if user_index > 0 else 'disabled')
            down_button = tk.Button(arrow_frame, text="↓", command=lambda u=username: self._move_user_down(u), 
                                  width=2, state='normal' if user_index < len(open_users)-1 else 'disabled')
            
            up_button.pack(side='top')
            down_button.pack(side='top')

            remove_button = tk.Button(user_frame, text="Verwijderen", command=lambda u=username: self._remove_user_config(u), bg="#ffdddd", fg="#990000")
            self.remove_user_buttons.append(remove_button)

            logic_checkbox.pack(side='left', padx=(0, 2))
            user_label.pack(side='left', padx=(0, 5)) 
            processing_type_label.pack(side='left', padx=(0,10)) 
            arrow_frame.pack(side='left', padx=(0, 5))
            path_display_entry.pack(side='left', expand=True, fill='x', padx=(0,5))
            browse_button.pack(side='left', padx=(0, 2))
            remove_button.pack(side='left', padx=(0,0)) 

            is_initially_checked = logic_active_var.get()
            path_display_entry.config(state='readonly' if is_initially_checked else 'disabled')
            browse_button.config(state='normal' if is_initially_checked else 'disabled')
            if not is_initially_checked:
                path_var.set("Niet ingesteld")

        self._update_admin_dependent_ui()

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

    def _move_user_up(self, username):
        """Move user up in the order"""
        config = get_config()
        users = config.get('scanner_panel_open_event_users', [])
        
        if username not in users:
            return
            
        current_index = users.index(username)
        if current_index > 0:
            # Swap with previous user
            users[current_index], users[current_index - 1] = users[current_index - 1], users[current_index]
            save_config({'scanner_panel_open_event_users': users})
            self.log_message(f"Gebruiker '{username}' omhoog verplaatst", "info")
            self._build_open_event_user_paths_ui()

    def _move_user_down(self, username):
        """Move user down in the order"""
        config = get_config()
        users = config.get('scanner_panel_open_event_users', [])
        
        if username not in users:
            return
            
        current_index = users.index(username)
        if current_index < len(users) - 1:
            # Swap with next user
            users[current_index], users[current_index + 1] = users[current_index + 1], users[current_index]
            save_config({'scanner_panel_open_event_users': users})
            self.log_message(f"Gebruiker '{username}' omlaag verplaatst", "info")
            self._build_open_event_user_paths_ui()

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

    def _update_browse_button_states(self):
        """Update browse button states based on checkbox state"""
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
                        if logic_var.get():
                            is_corresponding_logic_active = True

                browse_btn.config(state=tk.NORMAL if is_corresponding_logic_active else tk.DISABLED)

    # get_item_count_dialog function removed - item counts now come from Excel files automatically

    def log_scan_event(self, code):
        import requests
        from config_utils import get_config
        import traceback
        import re

        event_type = 'OPEN'  # Always use OPEN event type
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')

        base_project_code, full_project_code = self._extract_project_code(code)
        project_code_to_log = full_project_code


        if not api_url:
            self.log_message("❌ API URL niet geconfigureerd", "error")
            self.usb_entry.config(bg='red')
            self.after(2000, lambda: self.usb_entry.config(bg='white'))
            return

        all_ok = True
        current_user = config.get('user', 'unknown')

        # Add session_id to data if available
        session_data = {}
        if self.current_session_id:
            session_data['session_id'] = self.current_session_id

        # Check if project is already open
        if project_code_to_log in self.open_projects:
            self.log_message(f"ℹ️ Project {project_code_to_log} is al geopend", "warning")
            self.usb_entry.config(bg='light green')
            self.after(2000, lambda: self.usb_entry.config(bg='white'))
            return

        # Use session start time if available, otherwise current time
        scan_timestamp = self.session_start_time.isoformat() if self.session_start_time else None
        
        # Now send OPEN event for the current user
        data_open = {
            'event': 'OPEN',
            'details': code,
            'project': project_code_to_log,
            'base_mo_code': base_project_code,
            'is_rep_variant': bool(re.search(r'_REP_?', project_code_to_log, re.IGNORECASE)),
            'user': current_user,
            **session_data
        }
        
        # Add timestamp if available
        if scan_timestamp:
            data_open['timestamp'] = scan_timestamp
        
        try:
            resp_open = requests.post(api_url, json=data_open, timeout=3)
            if not resp_open.ok:
                all_ok = False
                self.log_message(f"❌ Fout bij openen project voor {current_user}", "error")
        except Exception:
            self.log_message(f"❌ Netwerkfout bij openen project", "error")
            all_ok = False

        # Don't duplicate the processing message - it's already shown via callback
        
        # Show immediate feedback for the current user
        self.log_message(f"✓ Project {project_code_to_log} geopend door {current_user}", "success")
        
        # If current user is an Excel processor, show unified processing message
        excel_processors = ['NESTING', 'ACCURA', 'BOERE']
        if current_user in excel_processors:
            # Show unified processing message for Excel processors
            self.after(500, lambda: self.log_message(f"🔄 Excel verwerking wordt gestart voor alle gebruikers...", "info"))
        
        # Trigger background service for other users
        self.background_import_service.process_scan_for_open_event_async(
            project_code_to_log=project_code_to_log,
            base_project_code=base_project_code,
            scanned_code=code,
            current_user_scanner=current_user,
            api_url=api_url,
            config_data=config,
            timestamp=scan_timestamp
        )
        
        if all_ok:
            self.open_projects.add(project_code_to_log)
            self.usb_entry.config(bg='light green')
        else:
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
        # Look for MOxxxxx pattern (exactly 5 digits to match BarcodeMatch)
        mo_match = re.search(r'(MO\d{5})', code_input, re.IGNORECASE)
        if mo_match:
            base_project_code = mo_match.group(0).upper()
        
        if not base_project_code:
            # Use full code_input as fallback when no MO code found
            return code_input, code_input

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
        # Close session if active
        if self.current_session_id:
            self.close_current_session()
        
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
        event_type = 'OPEN'  # Always use OPEN event type
        
        import threading
        threading.Thread(target=self.log_scan_event, args=(data,), daemon=True).start()

    def on_usb_scan(self, event):
        code = self.usb_code_var.get().strip()
        if code:
            self.usb_code_var.set('')
            
            event_type = 'OPEN'  # Always use OPEN event type
            
            import threading
            threading.Thread(target=self.log_scan_event, args=(code,), daemon=True).start()

    def save_com_port(self, *args):
        save_config({'scanner_panel_com_port': self.com_port_var.get()})

    def save_baud_rate(self, *args):
        save_config({'scanner_panel_baud_rate': self.baud_rate_var.get()})