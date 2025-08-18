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
import signal
import weakref
import atexit
from PIL import Image, ImageTk
from path_utils import get_resource_path

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
        
        # Track two independent sessions
        # Session 1
        self.session1_id = None
        self.session1_start_time = None
        self.session1_paused = False
        self.session1_pause_start = None
        self.session1_total_pause = 0
        
        # Session 2  
        self.session2_id = None
        self.session2_start_time = None
        self.session2_paused = False
        self.session2_pause_start = None
        self.session2_total_pause = 0
        
        # Track which session receives scans (1 or 2)
        self.active_scan_session = 1  # Default to Session 1
        
        # For backward compatibility during transition
        self.current_session_id = None  # Will point to session1_id
        self.background_session_id = None  # Will point to session2_id
        
        # Initialize work hours cache
        self._work_hours_cache = None
        
        # Check for and cleanup any orphaned sessions on startup
        self.check_and_cleanup_orphaned_sessions()
        
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

        # Create enhanced session display
        self._create_enhanced_session_display()

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

        # User configuration moved to admin panel
        # self.user_paths_frame = tk.Frame(self.event_frame, bg="#f0f0f0")

        # Load user configuration from config (still needed for processing)
        self.user_specific_paths_vars = {}
        self.scanner_panel_open_event_user_paths = config.get('scanner_panel_open_event_user_paths', {})
        self.user_logic_active_vars = {}
        self.scanner_panel_open_event_user_logic_active = config.get('scanner_panel_open_event_user_logic_active', {})
        self.scanner_user_to_processing_type_map = config.get('scanner_user_to_processing_type_map', {})

        # Serial port attributes
        self.ser = None
        self.is_reading = False
        self.read_thread = None

        self.open_projects = set()
        self.session1_project = None  # Current/last project for Session 1
        self.session2_project = None  # Current/last project for Session 2
        self.session1_projects = []  # All projects in Session 1 batch
        self.session2_projects = []  # All projects in Session 2 batch
        
        # Separate pause states for each session
        self.session1_paused = False
        self.session2_paused = False
        self.session1_pause_start = None
        self.session2_pause_start = None
        self.session1_total_pause = 0
        self.session2_total_pause = 0

        self.load_config_values()
        
        if hasattr(self.app, 'admin_config_locked_var') and isinstance(self.app.admin_config_locked_var, tk.BooleanVar):
            self.app.admin_config_locked_var.trace_add('write', self._update_admin_dependent_ui)
            self._update_admin_dependent_ui()
        else:
            self.log_message("Admin configuratie vergrendeld", "warning")
            self._update_admin_dependent_ui()

        self.update_frame_visibility()
        # User configuration now in admin panel
        # self._build_open_event_user_paths_ui()
        # self.user_paths_frame.pack(fill='x', padx=5, pady=(5,0))

        self._previous_scanner_type = self.scanner_type_var.get()

        # Auto-connect if enabled
        config = get_config()
        if config.get('scanner_panel_com_auto_connect', False) and self.scanner_type_var.get() == 'COM':
            self.log_message("Automatisch verbinden is ingeschakeld", "info")
            self.after(100, self.connect_com)

        self._create_lock_button()

    def _create_enhanced_session_display(self):
        """Create larger, more intuitive session display with timing information"""
        # Load button images first
        try:
            # Load images for buttons
            start_img_path = get_resource_path('assets/start.png')
            stop_img_path = get_resource_path('assets/stop.png')
            pauze_img_path = get_resource_path('assets/pauze.png')
            
            # Load and resize images to appropriate button size (75x75)
            self.start_img = Image.open(start_img_path).resize((75, 75), Image.Resampling.LANCZOS)
            self.start_photo = ImageTk.PhotoImage(self.start_img)
            
            self.stop_img = Image.open(stop_img_path).resize((75, 75), Image.Resampling.LANCZOS)
            self.stop_photo = ImageTk.PhotoImage(self.stop_img)
            
            self.pauze_img = Image.open(pauze_img_path).resize((75, 75), Image.Resampling.LANCZOS)
            self.pauze_photo = ImageTk.PhotoImage(self.pauze_img)
            
            images_loaded = True
        except Exception as e:
            print(f"Warning: Could not load button images: {e}")
            images_loaded = False
            # Fallback to text if images fail to load
            self.start_photo = None
            self.stop_photo = None
            self.pauze_photo = None
        
        # Main session container - much larger and clearer
        self.session_frame = tk.LabelFrame(
            self,
            text="Werk Sessie Beheer",
            bg="#f0f0f0",
            padx=10,
            pady=5
        )
        self.session_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Work hours indicator at top
        self.work_hours_frame = tk.Frame(self.session_frame, bg="#f0f0f0")
        self.work_hours_frame.pack(fill='x', pady=(0, 10))
        
        self.work_hours_label = tk.Label(
            self.work_hours_frame,
            text="⏰ Werktijd laden...",
            bg="#f0f0f0",
            fg="#27ae60",
            font=('Segoe UI', 10)
        )
        self.work_hours_label.pack(side='left')
        
        # Scan target selector - which session receives scanned projects
        scan_selector_frame = tk.Frame(self.session_frame, bg="#f0f0f0")
        scan_selector_frame.pack(fill='x', pady=(5, 10))
        
        tk.Label(
            scan_selector_frame,
            text="Scan naar:",
            bg="#f0f0f0",
            font=('Segoe UI', 11, 'bold'),
            fg="#2c3e50"
        ).pack(side='left', padx=(0, 10))
        
        self.scan_session_var = tk.IntVar(value=1)  # Default to Session 1
        
        self.scan_radio1 = tk.Radiobutton(
            scan_selector_frame,
            text="Sessie 1",
            variable=self.scan_session_var,
            value=1,
            bg="#f0f0f0",
            font=('Segoe UI', 10),
            fg="#2980b9",  # Blue when selected (will be set in set_active_scan_session)
            selectcolor="#f0f0f0",
            activebackground="#f0f0f0",
            state='disabled',  # Disabled until session is started
            command=lambda: self.set_active_scan_session(1)
        )
        self.scan_radio1.pack(side='left', padx=5)
        
        self.scan_radio2 = tk.Radiobutton(
            scan_selector_frame,
            text="Sessie 2",
            variable=self.scan_session_var,
            value=2,
            bg="#f0f0f0",
            font=('Segoe UI', 10),
            fg="#2c3e50",  # Black when not selected
            selectcolor="#f0f0f0",
            activebackground="#f0f0f0",
            state='disabled',  # Disabled until session is started
            command=lambda: self.set_active_scan_session(2)
        )
        self.scan_radio2.pack(side='left', padx=5)
        
        # Main content area with two columns for sessions
        content_frame = tk.Frame(self.session_frame, bg="#f0f0f0")
        content_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # LEFT COLUMN - Active Session
        left_frame = tk.Frame(content_frame, bg="#f0f0f0")
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Session 1 card
        self.active_session_card = tk.LabelFrame(
            left_frame,
            text="Sessie 1",
            bg="#f0f0f0",
            fg="#2980b9",  # Blue - selected by default
            font=('Segoe UI', 11, 'bold'),
            padx=15,
            pady=10,
            relief=tk.SOLID,
            borderwidth=2  # Thicker border for selected
        )
        self.active_session_card.pack(fill='both', expand=True)
        
        # Active session info
        self.active_session_id = tk.Label(
            self.active_session_card,
            text="Geen actieve sessie",
            bg="#f0f0f0",
            fg="#7f8c8d",
            font=('Segoe UI', 10)
        )
        self.active_session_id.pack(anchor='w', pady=2)
        
        self.active_session_start = tk.Label(
            self.active_session_card,
            text="Start tijd: --:--",
            bg="#f0f0f0",
            fg="#7f8c8d",
            font=('Segoe UI', 10)
        )
        self.active_session_start.pack(anchor='w', pady=2)
        
        self.active_session_duration = tk.Label(
            self.active_session_card,
            text="Duur: 0h 0m",
            bg="#f0f0f0",
            fg="#2c3e50",
            font=('Segoe UI', 11, 'bold')
        )
        self.active_session_duration.pack(anchor='w', pady=5)
        
        # Active project display for Session 1
        self.active_project_label = tk.Label(
            self.active_session_card,
            text="Project: --",
            bg="#f0f0f0",
            fg="#2980b9",
            font=('Segoe UI', 11, 'bold')
        )
        self.active_project_label.pack(anchor='w', pady=2)
        
        # Active session status indicator
        self.active_status_frame = tk.Frame(self.active_session_card, bg="#f0f0f0")
        self.active_status_frame.pack(fill='x', pady=5)
        
        self.active_status_indicator = tk.Label(
            self.active_status_frame,
            text="● INACTIEF",
            bg="#f0f0f0",
            fg="#7f8c8d",
            font=('Segoe UI', 10, 'bold')
        )
        self.active_status_indicator.pack(side='left')
        
        # Session 1 control buttons
        session1_button_frame = tk.Frame(self.active_session_card, bg="#f0f0f0")
        session1_button_frame.pack(fill='x', pady=(10, 5))
        
        # Container for Session 1 buttons
        session1_buttons_container = tk.Frame(session1_button_frame, bg="#f0f0f0")
        session1_buttons_container.pack()
        
        # START/STOP button for Session 1
        self.start_button_frame = tk.Frame(session1_buttons_container, bg="#f0f0f0")
        self.start_button_frame.pack(side='left', padx=5)
        
        if hasattr(self, 'start_photo') and self.start_photo:
            self.start_button = tk.Button(
                self.start_button_frame,
                image=self.start_photo,
                bg="#f0f0f0",
                relief=tk.FLAT,
                cursor="hand2",
                bd=0,
                command=self.start_session1
            )
        else:
            # Fallback to text button
            self.start_button = tk.Button(
                self.start_button_frame,
                text="▶",
                font=('Arial', 28, 'bold'),
                bg="#27ae60",
                fg="white",
                width=4,
                height=2,
                relief=tk.FLAT,
                cursor="hand2",
                activebackground="#229954",
                bd=2,
                command=self.start_session1
            )
        self.start_button.pack()
        
        self.start_label = tk.Label(
            self.start_button_frame,
            text="Start Sessie 1",
            bg="#f0f0f0",
            font=('Segoe UI', 10)
        )
        self.start_label.pack()
        
        # PAUSE button for Session 1
        self.pause_button_frame = tk.Frame(session1_buttons_container, bg="#f0f0f0")
        self.pause_button_frame.pack(side='left', padx=5)
        
        if images_loaded and self.pauze_photo:
            self.pause_button = tk.Button(
                self.pause_button_frame,
                image=self.pauze_photo,
                bg="#f0f0f0",
                relief=tk.FLAT,
                cursor="hand2",
                bd=0,
                state='disabled',
                command=self.toggle_pause_session
            )
        else:
            # Fallback to text button
            self.pause_button = tk.Button(
                self.pause_button_frame,
                text="⏸",
                font=('Arial', 20, 'bold'),
                bg="#95a5a6",
                fg="white",
                width=3,
                height=1,
                relief=tk.FLAT,
                cursor="hand2",
                activebackground="#7f8c8d",
                bd=2,
                state='disabled',
                command=self.toggle_pause_session
            )
        self.pause_button.pack()
        
        self.pause_label = tk.Label(
            self.pause_button_frame,
            text="Pauzeer S1",
            bg="#f0f0f0",
            font=('Segoe UI', 10)
        )
        self.pause_label.pack()
        
        # RIGHT COLUMN - Background Session
        right_frame = tk.Frame(content_frame, bg="#f0f0f0")
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        # Session 2 card
        self.background_session_card = tk.LabelFrame(
            right_frame,
            text="Sessie 2",
            bg="#f0f0f0",
            fg="#2c3e50",  # Black - not selected by default
            font=('Segoe UI', 11, 'bold'),
            padx=15,
            pady=10,
            relief=tk.SOLID,
            borderwidth=1  # Thinner border for unselected
        )
        self.background_session_card.pack(fill='both', expand=True)
        
        # Background session info
        self.background_session_id_label = tk.Label(
            self.background_session_card,
            text="Geen achtergrond sessie",
            bg="#f0f0f0",
            fg="#bdc3c7",
            font=('Segoe UI', 10)
        )
        self.background_session_id_label.pack(anchor='w', pady=2)
        
        self.background_session_start = tk.Label(
            self.background_session_card,
            text="Start tijd: --:--",
            bg="#f0f0f0",
            fg="#bdc3c7",
            font=('Segoe UI', 10)
        )
        self.background_session_start.pack(anchor='w', pady=2)
        
        self.background_session_duration = tk.Label(
            self.background_session_card,
            text="Duur: 0h 0m",
            bg="#f0f0f0",
            fg="#7f8c8d",
            font=('Segoe UI', 11, 'bold')
        )
        self.background_session_duration.pack(anchor='w', pady=5)
        
        # Active project display for Session 2
        self.background_project_label = tk.Label(
            self.background_session_card,
            text="Project: --",
            bg="#f0f0f0",
            fg="#2c3e50",  # Black instead of purple
            font=('Segoe UI', 11, 'bold')
        )
        self.background_project_label.pack(anchor='w', pady=2)
        
        # Background session status
        self.background_status_frame = tk.Frame(self.background_session_card, bg="#f0f0f0")
        self.background_status_frame.pack(fill='x', pady=5)
        
        self.background_status_indicator = tk.Label(
            self.background_status_frame,
            text="● INACTIEF",
            bg="#f0f0f0",
            fg="#bdc3c7",
            font=('Segoe UI', 10, 'bold')
        )
        self.background_status_indicator.pack(side='left')
        
        # Session 2 control buttons
        session2_button_frame = tk.Frame(self.background_session_card, bg="#f0f0f0")
        session2_button_frame.pack(fill='x', pady=(10, 5))
        
        # Container for Session 2 buttons
        session2_buttons_container = tk.Frame(session2_button_frame, bg="#f0f0f0")
        session2_buttons_container.pack()
        
        # START/STOP button for Session 2
        self.start_button2_frame = tk.Frame(session2_buttons_container, bg="#f0f0f0")
        self.start_button2_frame.pack(side='left', padx=5)
        
        if hasattr(self, 'start_photo') and self.start_photo:
            self.start_button2 = tk.Button(
                self.start_button2_frame,
                image=self.start_photo,
                bg="#f0f0f0",
                relief=tk.FLAT,
                cursor="hand2",
                bd=0,
                state='disabled',
                command=self.start_session2
            )
        else:
            # Fallback to text button
            self.start_button2 = tk.Button(
                self.start_button2_frame,
                text="▶",
                font=('Arial', 28, 'bold'),
                bg="#27ae60",
                fg="white",
                width=4,
                height=2,
                relief=tk.FLAT,
                cursor="hand2",
                activebackground="#229954",
                bd=2,
                state='disabled',
                command=self.start_session2
            )
        self.start_button2.pack()
        
        self.start_label2 = tk.Label(
            self.start_button2_frame,
            text="Start Sessie 2",
            bg="#f0f0f0",
            font=('Segoe UI', 10)
        )
        self.start_label2.pack()
        
        # PAUSE button for Session 2
        self.pause_button2_frame = tk.Frame(session2_buttons_container, bg="#f0f0f0")
        self.pause_button2_frame.pack(side='left', padx=5)
        
        if images_loaded and self.pauze_photo:
            self.pause_button2 = tk.Button(
                self.pause_button2_frame,
                image=self.pauze_photo,
                bg="#f0f0f0",
                relief=tk.FLAT,
                cursor="hand2",
                bd=0,
                state='disabled',
                command=self.toggle_pause_session2
            )
        else:
            # Fallback to text button
            self.pause_button2 = tk.Button(
                self.pause_button2_frame,
                text="⏸",
                font=('Arial', 20, 'bold'),
                bg="#95a5a6",
                fg="white",
                width=3,
                height=1,
                relief=tk.FLAT,
                cursor="hand2",
                activebackground="#7f8c8d",
                bd=2,
                state='disabled',
                command=self.toggle_pause_session2
            )
        self.pause_button2.pack()
        
        self.pause_label2 = tk.Label(
            self.pause_button2_frame,
            text="Pauzeer S2",
            bg="#f0f0f0",
            font=('Segoe UI', 10)
        )
        self.pause_label2.pack()
        
        # No more control buttons at the bottom - they're now in the session cards
        
        # Hidden status label - not needed with new design
        self.session_status_label = tk.Label(
            self.session_frame,
            text="",
            fg="#2C3E50"
        )
        # Don't pack it - just create for compatibility
        
        # Start session timer updates
        self.update_session_timers()
        
        # Load work hours asynchronously after panel is shown
        self._initial_work_hours_display()
        self.after(100, self.async_update_work_hours_status)
        
        # Start periodic work hours status updates (30 seconds)
        self.after(30000, self.update_work_hours_status)
        
        # Register signal handlers for better shutdown handling
        self._register_shutdown_handlers()

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
                fg="#27AE60"
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

    def check_and_cleanup_orphaned_sessions(self):
        """Check for orphaned sessions from this user and close them on startup"""
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')
        current_user = config.get('user', 'NESTING')
        
        try:
            # Query database directly for active sessions from this user
            response = requests.get(f"{api_url}/api/user/{current_user}/active-sessions", timeout=5)
            if response.ok and response.json().get('success'):
                active_sessions = response.json().get('sessions', [])
                for session in active_sessions:
                    # Close orphaned session
                    end_data = {
                        'session_id': session['session_id'],
                        'timestamp': datetime.now().isoformat()
                    }
                    close_response = requests.post(api_url.replace('/log', '/session/end'), json=end_data, timeout=1)
                    if close_response.ok:
                        print(f"[ScannerPanel] Cleaned up orphaned session: {session['session_id']}")
                    else:
                        print(f"[ScannerPanel] Failed to clean up session: {session['session_id']}")
            elif response.status_code == 404:
                # Endpoint doesn't exist yet, fallback to manual check
                print("[ScannerPanel] Active sessions endpoint not available, skipping cleanup")
        except requests.exceptions.RequestException as e:
            print(f"[ScannerPanel] Error checking for orphaned sessions: {e}")
        except Exception as e:
            print(f"[ScannerPanel] Unexpected error during session cleanup: {e}")

    def _register_shutdown_handlers(self):
        """Register signal handlers to ensure sessions are closed on shutdown"""
        # Store weak reference to avoid circular reference issues
        weak_self = weakref.ref(self)
        
        def signal_handler(signum, frame):
            """Handle shutdown signals"""
            panel = weak_self()
            if panel and panel.current_session_id:
                print(f"[ScannerPanel] Caught signal {signum}, closing session...")
                try:
                    panel.close_current_session()
                except Exception as e:
                    print(f"[ScannerPanel] Error closing session on signal: {e}")
        
        def atexit_handler():
            """Handle normal exit"""
            panel = weak_self()
            if panel and panel.current_session_id:
                print("[ScannerPanel] Application exiting, closing session...")
                try:
                    panel.close_current_session()
                except Exception as e:
                    print(f"[ScannerPanel] Error closing session on exit: {e}")
        
        # Register signal handlers for various shutdown scenarios
        try:
            signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
            signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
            if hasattr(signal, 'SIGBREAK'):
                signal.signal(signal.SIGBREAK, signal_handler)  # Windows Ctrl+Break
        except Exception as e:
            print(f"[ScannerPanel] Warning: Could not register signal handlers: {e}")
        
        # Register atexit handler for normal exits
        atexit.register(atexit_handler)

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

    def set_active_scan_session(self, session_number):
        """Set which session (1 or 2) receives scanned projects"""
        self.active_scan_session = session_number
        
        # Update radio button colors and session card borders
        if session_number == 1:
            # Radio buttons - Session 1 blue, Session 2 black
            self.scan_radio1.config(fg="#2980b9")  # Blue for selected
            self.scan_radio2.config(fg="#2c3e50")  # Black for unselected
            
            # Session cards - highlight Session 1
            self.active_session_card.config(fg="#2980b9", relief=tk.SOLID, borderwidth=2)
            self.background_session_card.config(fg="#2c3e50", relief=tk.SOLID, borderwidth=1)
            
            # Project labels - Session 1 blue, Session 2 black
            self.active_project_label.config(fg="#2980b9")
            self.background_project_label.config(fg="#2c3e50")
            
            self.log_message("✓ Scans gaan nu naar Sessie 1", "info")
        else:
            # Radio buttons - Session 2 blue, Session 1 black
            self.scan_radio1.config(fg="#2c3e50")  # Black for unselected
            self.scan_radio2.config(fg="#2980b9")  # Blue for selected
            
            # Session cards - highlight Session 2
            self.active_session_card.config(fg="#2c3e50", relief=tk.SOLID, borderwidth=1)
            self.background_session_card.config(fg="#2980b9", relief=tk.SOLID, borderwidth=2)
            
            # Project labels - Session 2 blue, Session 1 black
            self.active_project_label.config(fg="#2c3e50")
            self.background_project_label.config(fg="#2980b9")
            
            self.log_message("✓ Scans gaan nu naar Sessie 2", "info")
    
    def start_session1(self):
        """Start or stop Session 1"""
        if self.session1_id:
            self.stop_session1()
        else:
            self.start_new_session1()
    
    def start_session2(self):
        """Start or stop Session 2"""
        if self.session2_id:
            self.stop_session2()
        else:
            self.start_new_session2()
    
    def start_new_session1(self):
        """Start a new Session 1"""
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')
        current_user = config.get('user', 'NESTING')
        
        if not api_url:
            self.log_message("❌ API URL niet geconfigureerd", "error")
            return
        
        # Create unique session ID
        self.session1_start_time = datetime.now()
        self.session1_id = f"{current_user}_S1_{self.session1_start_time.strftime('%Y%m%d_%H%M%S')}"
        
        # Reset session state
        self.session1_paused = False
        self.session1_pause_start = None
        self.session1_total_pause = 0
        self.session1_project = None
        self.session1_projects = []
        
        # Update compatibility pointers
        self.current_session_id = self.session1_id
        self.session_start_time = self.session1_start_time
        
        # Start session in database
        data = {
            'event': 'SESSION_START',
            'user': current_user,
            'session_id': self.session1_id,
            'timestamp': self.session1_start_time.isoformat(),
            'session_type': 'SCANNER',
            'session_number': 1
        }
        
        try:
            response = requests.post(api_url.replace('/log', '/session/start'), json=data, timeout=1)
            if response.ok:
                self.log_message(f"✓ Sessie 1 gestart: {self.session1_id}", "success")
                self.update_session_display()
            else:
                self.log_message(f"❌ Kon Sessie 1 niet starten: {response.text}", "error")
                self.session1_id = None
                self.session1_start_time = None
                self.current_session_id = None
        except Exception as e:
            self.log_message(f"❌ Fout bij starten Sessie 1: {e}", "error")
            self.session1_id = None
            self.session1_start_time = None
            self.current_session_id = None
    
    def start_new_session2(self):
        """Start a new Session 2"""
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')
        current_user = config.get('user', 'NESTING')
        
        if not api_url:
            self.log_message("❌ API URL niet geconfigureerd", "error")
            return
        
        # Create unique session ID
        self.session2_start_time = datetime.now()
        self.session2_id = f"{current_user}_S2_{self.session2_start_time.strftime('%Y%m%d_%H%M%S')}"
        
        # Reset session state
        self.session2_paused = False
        self.session2_pause_start = None
        self.session2_total_pause = 0
        self.session2_project = None
        self.session2_projects = []
        
        # Update compatibility pointer
        self.background_session_id = self.session2_id
        
        # Start session in database
        data = {
            'event': 'SESSION_START',
            'user': current_user,
            'session_id': self.session2_id,
            'timestamp': self.session2_start_time.isoformat(),
            'session_type': 'SCANNER',
            'session_number': 2,
            'is_new_batch': True,  # Keep Session 1 active when starting Session 2
            'background_session': self.session1_id if self.session1_id else None
        }
        
        try:
            response = requests.post(api_url.replace('/log', '/session/start'), json=data, timeout=1)
            if response.ok:
                self.log_message(f"✓ Sessie 2 gestart: {self.session2_id}", "success")
                self.update_session_display()
            else:
                self.log_message(f"❌ Kon Sessie 2 niet starten: {response.text}", "error")
                self.session2_id = None
                self.session2_start_time = None
                self.background_session_id = None
        except Exception as e:
            self.log_message(f"❌ Fout bij starten Sessie 2: {e}", "error")
            self.session2_id = None
            self.session2_start_time = None
            self.background_session_id = None
    
    def stop_session1(self):
        """Stop Session 1"""
        if not self.session1_id:
            return
        
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')
        current_user = config.get('user', 'NESTING')
        
        # Send AFGEMELD for all projects in Session 1
        for project in self.session1_projects:
            try:
                afgemeld_data = {
                    'event': 'AFGEMELD',
                    'user': current_user,
                    'project': project,
                    'session_id': self.session1_id,
                    'timestamp': datetime.now().isoformat()
                }
                # Ensure we use the correct /log endpoint for AFGEMELD
                log_url = api_url if api_url.endswith('/log') else f"{api_url}/log"
                requests.post(log_url, json=afgemeld_data, timeout=1)
            except:
                pass
        
        # End session
        try:
            end_data = {
                'session_id': self.session1_id,
                'timestamp': datetime.now().isoformat(),
                'user': current_user
            }
            base_url = api_url if not api_url.endswith('/log') else api_url.replace('/log', '')
            session_end_url = f"{base_url}/session/end"
            response = requests.post(session_end_url, json=end_data, timeout=1)
            if response.ok:
                self.log_message(f"✓ Sessie 1 gestopt: {self.session1_id}", "success")
            else:
                error_msg = response.text if response.text else f"Status: {response.status_code}"
                self.log_message(f"⚠️ Kon Sessie 1 niet netjes afsluiten: {error_msg}", "warning")
        except Exception as e:
            self.log_message(f"⚠️ Fout bij stoppen Sessie 1: {e}", "warning")
        
        # Clear session state
        self.session1_id = None
        self.session1_start_time = None
        self.session1_paused = False
        self.session1_pause_start = None
        self.session1_total_pause = 0
        self.session1_project = None
        self.session1_projects = []
        self.current_session_id = None
        
        self.update_session_display()
    
    def stop_session2(self):
        """Stop Session 2"""
        if not self.session2_id:
            return
        
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')
        current_user = config.get('user', 'NESTING')
        
        # Send AFGEMELD for all projects in Session 2
        for project in self.session2_projects:
            try:
                afgemeld_data = {
                    'event': 'AFGEMELD',
                    'user': current_user,
                    'project': project,
                    'session_id': self.session2_id,
                    'timestamp': datetime.now().isoformat()
                }
                # Ensure we use the correct /log endpoint for AFGEMELD
                log_url = api_url if api_url.endswith('/log') else f"{api_url}/log"
                requests.post(log_url, json=afgemeld_data, timeout=1)
            except:
                pass
        
        # End session
        try:
            end_data = {
                'session_id': self.session2_id,
                'timestamp': datetime.now().isoformat(),
                'user': current_user
            }
            base_url = api_url if not api_url.endswith('/log') else api_url.replace('/log', '')
            session_end_url = f"{base_url}/session/end"
            response = requests.post(session_end_url, json=end_data, timeout=1)
            if response.ok:
                self.log_message(f"✓ Sessie 2 gestopt: {self.session2_id}", "success")
            else:
                error_msg = response.text if response.text else f"Status: {response.status_code}"
                self.log_message(f"⚠️ Kon Sessie 2 niet netjes afsluiten: {error_msg}", "warning")
        except Exception as e:
            self.log_message(f"⚠️ Fout bij stoppen Sessie 2: {e}", "warning")
        
        # Clear session state
        self.session2_id = None
        self.session2_start_time = None
        self.session2_paused = False
        self.session2_pause_start = None
        self.session2_total_pause = 0
        self.session2_project = None
        self.session2_projects = []
        self.background_session_id = None
        
        self.update_session_display()
    
    def update_session_display(self):
        """Update the enhanced UI to show current session status with timing"""
        config = get_config()
        current_user = config.get('user', 'NESTING')
        
        # Update radio button states based on active sessions
        if self.session1_id:
            self.scan_radio1.config(state='normal')
        else:
            self.scan_radio1.config(state='disabled')
            # If Session 1 not active and currently selected, switch to Session 2 if available
            if self.active_scan_session == 1 and self.session2_id:
                self.scan_session_var.set(2)
                self.set_active_scan_session(2)
        
        if self.session2_id:
            self.scan_radio2.config(state='normal')
        else:
            self.scan_radio2.config(state='disabled')
            # If Session 2 not active and currently selected, switch to Session 1 if available
            if self.active_scan_session == 2 and self.session1_id:
                self.scan_session_var.set(1)
                self.set_active_scan_session(1)
        
        # Update Session 1 card
        if self.session1_id:
            self.active_session_id.config(
                text=f"Sessie ID: {self.session1_id[-8:]}",
                fg="#2c3e50"
            )
            if self.session1_start_time:
                self.active_session_start.config(
                    text=f"Start tijd: {self.session1_start_time.strftime('%H:%M')}",
                    fg="#2c3e50"
                )
                # Calculate duration
                duration = datetime.now() - self.session1_start_time
                hours = int(duration.total_seconds() // 3600)
                minutes = int((duration.total_seconds() % 3600) // 60)
                self.active_session_duration.config(
                    text=f"Duur: {hours}h {minutes}m",
                    fg="#2c3e50"
                )
            
            if self.session1_paused:
                self.active_status_indicator.config(
                    text="● GEPAUZEERD",
                    fg="#f39c12"
                )
            else:
                self.active_status_indicator.config(
                    text="● ACTIEF",
                    fg="#27ae60"
                )
            
            # Update buttons for active session
            if hasattr(self, 'stop_photo') and self.stop_photo:
                self.start_button.config(image=self.stop_photo)
            else:
                self.start_button.config(text="⏹", bg="#e74c3c", activebackground="#c0392b")  # Stop icon
            self.start_label.config(text="Stop Sessie 1")
            self.pause_button.config(state='normal')  # Enable pause button for Session 1
            
            # Session 2 button is always enabled (independent sessions)
            self.start_button2.config(state='normal')
        else:
            # No active session
            self.active_session_id.config(
                text="Geen actieve sessie",
                fg="#7f8c8d"
            )
            self.active_session_start.config(
                text="Start tijd: --:--",
                fg="#7f8c8d"
            )
            self.active_session_duration.config(
                text="Duur: 0h 0m",
                fg="#7f8c8d"
            )
            self.active_status_indicator.config(
                text="● INACTIEF",
                fg="#7f8c8d"
            )
            # Clear project when session ends
            self.session1_project = None
            self.session1_projects = []  # Clear batch list
            self.active_project_label.config(text="Project: --")
            
            # Update buttons for no session
            if hasattr(self, 'start_photo') and self.start_photo:
                self.start_button.config(image=self.start_photo)
            else:
                self.start_button.config(text="▶", bg="#27ae60", activebackground="#229954")  # Play icon
            self.start_label.config(text="Start Sessie 1")
            # Session 2 button is always enabled (independent sessions)
            self.start_button2.config(state='normal')
            self.pause_button.config(state='disabled')  # Disable pause button when no Session 1
        
        # Update Session 2 card
        if self.session2_id:
            self.background_session_id_label.config(
                text=f"Sessie ID: {self.session2_id[-8:]}",
                fg="#2c3e50"
            )
            if self.session2_start_time:
                self.background_session_start.config(
                    text=f"Start tijd: {self.session2_start_time.strftime('%H:%M')}",
                    fg="#2c3e50"
                )
                # Calculate duration
                duration = datetime.now() - self.session2_start_time
                hours = int(duration.total_seconds() // 3600)
                minutes = int((duration.total_seconds() % 3600) // 60)
                self.background_session_duration.config(
                    text=f"Duur: {hours}h {minutes}m",
                    fg="#2c3e50"
                )
            
            if self.session2_paused:
                self.background_status_indicator.config(
                    text="● GEPAUZEERD",
                    fg="#f39c12"
                )
            else:
                self.background_status_indicator.config(
                    text="● ACTIEF",
                    fg="#27ae60"  # Green for active instead of purple
                )
            # Update Session 2 button to show stop
            if hasattr(self, 'stop_photo') and self.stop_photo:
                self.start_button2.config(image=self.stop_photo, state='normal')
            else:
                self.start_button2.config(text="⏹", bg="#e74c3c", activebackground="#c0392b", state='normal')
            self.start_label2.config(text="Stop Sessie 2")
            self.pause_button2.config(state='normal')  # Enable pause button for Session 2
        else:
            # No background session
            self.background_session_id_label.config(
                text="Geen sessie 2",
                fg="#bdc3c7"
            )
            self.background_session_start.config(
                text="Start tijd: --:--",
                fg="#bdc3c7"
            )
            self.background_session_duration.config(
                text="Duur: 0h 0m",
                fg="#7f8c8d"
            )
            self.background_status_indicator.config(
                text="● INACTIEF",
                fg="#bdc3c7"
            )
            # Update Session 2 button to show start (always enabled for independent sessions)
            if hasattr(self, 'start_photo') and self.start_photo:
                self.start_button2.config(image=self.start_photo, state='normal')
            else:
                self.start_button2.config(text="▶", bg="#27ae60", activebackground="#229954", state='normal')
            self.start_label2.config(text="Start Sessie 2")
            self.pause_button2.config(state='disabled')  # Disable pause button when no Session 2
            # Clear project when session ends
            self.session2_project = None
            self.session2_projects = []  # Clear batch list
            self.background_project_label.config(text="Project: --")
    
    def update_session_timers(self):
        """Update session duration displays every minute"""
        if self.session1_id and self.session1_start_time:
            duration = datetime.now() - self.session1_start_time
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            self.active_session_duration.config(
                text=f"Duur: {hours}h {minutes}m"
            )
        
        if self.session2_id and self.session2_start_time:
            duration = datetime.now() - self.session2_start_time
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            self.background_session_duration.config(
                text=f"Duur: {hours}h {minutes}m"
            )
        
        # Schedule next update in 30 seconds
        self.after(30000, self.update_session_timers)
    
    def stop_background_session(self):
        """Stop the background session (opdeelzaag work completed)"""
        if not self.background_session_id:
            return
        
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')
        current_user = config.get('user', 'NESTING')
        
        # Confirm with user
        result = messagebox.askyesno(
            "Stop Achtergrond Sessie",
            f"Wilt u de achtergrond sessie {self.background_session_id} stoppen?\n\n"
            "Dit betekent dat het opdeelzaag werk is afgerond.",
            icon='question'
        )
        
        if not result:
            return
        
        try:
            # First send AFGEMELD for all projects in Session 2
            if self.session2_projects:
                for project in self.session2_projects:
                    afgemeld_data = {
                        'event': 'AFGEMELD',
                        'user': current_user,
                        'project': project,
                        'timestamp': datetime.now().isoformat(),
                        'details': 'Achtergrond sessie voltooid'
                    }
                    try:
                        requests.post(api_url, json=afgemeld_data, timeout=1)
                        self.log_message(f"✓ Project {project} afgemeld", "info")
                    except:
                        pass  # Don't fail if one AFGEMELD fails
            
            # End the background session
            end_data = {
                'session_id': self.background_session_id,
                'timestamp': datetime.now().isoformat(),
                'keep_projects_active': False  # Projects are AFGEMELD, session can close
            }
            
            response = requests.post(api_url.replace('/log', '/session/end'), json=end_data, timeout=1)
            if response.ok:
                self.log_message(f"✓ Achtergrond sessie {self.background_session_id} gestopt", "success")
                self.background_session_id = None
                self.session2_start_time = None
                self.session2_project = None  # Clear Session 2 project
                self.session2_projects = []  # Clear Session 2 batch list
                
                # Update display
                self.update_session_display()
            else:
                self.log_message(f"❌ Kon achtergrond sessie niet stoppen: {response.text}", "error")
                
        except Exception as e:
            self.log_message(f"❌ Fout bij stoppen achtergrond sessie: {e}", "error")
    
    def start_new_batch_session(self):
        """Start a new batch session while keeping the old session running in background"""
        # Run in background thread to prevent GUI freeze
        threading.Thread(target=self._start_new_batch_session_async, daemon=True).start()
    
    def _start_new_batch_session_async(self):
        """Async version of start_new_batch_session to prevent GUI blocking"""
        if not self.current_session_id:
            # No active session, just start a new one
            self._start_new_session_async()
            return
        
        # Check if we already have a background session
        if self.background_session_id:
            self.after(0, lambda: messagebox.showwarning(
                "Achtergrond Sessie Actief",
                f"Er is al een achtergrond sessie actief: {self.background_session_id}\n\n"
                "Stop eerst de achtergrond sessie voordat u een nieuwe batch start.",
                icon='warning'
            ))
            return
        
        # Check if within work hours
        is_work_time, message = self.get_current_work_status()
        if not is_work_time:
            self.log_message(f"❌ {message}", "error")
            messagebox.showwarning("Buiten Werktijd", f"Kan geen nieuwe batch starten: {message}")
            return
        
        # Confirm with user
        result = messagebox.askyesno(
            "Nieuwe Batch Starten",
            "Dit zal:\n"
            "1. De huidige sessie naar de achtergrond verplaatsen (voor opdeelzaag werk)\n"
            "2. Een nieuwe sessie starten voor de nieuwe batch (nesting machine)\n\n"
            "Beide sessies blijven actief en moeten handmatig gestopt worden.\n"
            "Barcode scans gaan naar de nieuwe sessie.\n\n"
            "Wilt u doorgaan?",
            icon='question'
        )
        
        if not result:
            return
        
        config = get_config()
        current_user = config.get('user', 'NESTING')
        api_url = config.get('api_url', '').rstrip('/')
        
        if not api_url:
            self.log_message("❌ API URL niet geconfigureerd", "error")
            return
        
        # Move current session to background (don't end it!)
        # For now, keep the same session ID to avoid complications
        # The API update endpoint would need to be available to change the ID
        self.background_session_id = self.current_session_id
        self.session2_start_time = self.session_start_time
        
        # Move Session 1 projects to Session 2
        self.session2_project = self.session1_project
        self.session2_projects = self.session1_projects.copy()  # Copy batch list
        self.session1_project = None
        self.session1_projects = []  # Clear Session 1 batch list
        if self.session2_projects:
            if len(self.session2_projects) > 1:
                self.background_project_label.config(text=f"Batch: {len(self.session2_projects)} projecten")
            else:
                self.background_project_label.config(text=f"Project: {self.session2_project}")
        self.active_project_label.config(text="Project: --")
        
        self.log_message(f"↔️ Sessie {self.background_session_id} naar achtergrond verplaatst", "info")
        
        # Reset current session variables for new session
        self.current_session_id = None
        self.session_start_time = None
        self.session_paused = False
        self.pause_start_time = None
        self.total_pause_duration = 0
        
        # Start a new session for the new batch
        self.session_start_time = datetime.now()
        self.current_session_id = f"{current_user}_{self.session_start_time.strftime('%Y%m%d_%H%M%S')}"
        
        data = {
            'event': 'SESSION_START',
            'user': current_user,
            'session_id': self.current_session_id,
            'timestamp': self.session_start_time.isoformat(),
            'session_type': 'SCANNER',
            'is_new_batch': True,
            'background_session': self.background_session_id  # Track relationship
        }
        
        try:
            response = requests.post(api_url.replace('/log', '/session/start'), json=data, timeout=1)
            if response.ok:
                # Also create global project session
                project_session_data = {
                    'event': 'PROJECT_SESSION_START',
                    'user': current_user,
                    'session_id': self.current_session_id,
                    'timestamp': self.session_start_time.isoformat(),
                    'details': f'New batch session started (background: {self.background_session_id})'
                }
                
                try:
                    project_response = requests.post(api_url.replace('/log', '/project_session/start'), json=project_session_data, timeout=1)
                    if project_response.ok:
                        self.log_message(f"✓ Nieuwe batch sessie gestart: {self.current_session_id}", "success")
                except Exception as e:
                    self.log_message(f"⚠ Project sessie registratie mislukt: {e}", "warning")
                
                # Update UI to show both sessions
                self.update_session_display()
                
                # Log the batch transition
                log_data = {
                    'event': 'BATCH_TRANSITION',
                    'user': current_user,
                    'session_id': self.current_session_id,
                    'background_session': self.background_session_id,
                    'details': 'Nieuwe batch gestart, vorige sessie loopt door in achtergrond',
                    'timestamp': datetime.now().isoformat()
                }
                
                try:
                    requests.post(api_url, json=log_data, timeout=1)
                except:
                    pass  # Don't fail on logging error
                
            else:
                self.log_message(f"❌ Kon nieuwe batch sessie niet starten: {response.text}", "error")
                # Restore background session as current
                self.current_session_id = self.background_session_id
                self.session_start_time = self.session2_start_time
                self.background_session_id = None
                self.session2_start_time = None
                
        except Exception as e:
            self.log_message(f"❌ Fout bij starten nieuwe batch: {e}", "error")
            # Restore background session as current
            self.current_session_id = self.background_session_id
            self.session_start_time = self.session2_start_time
            self.background_session_id = None
            self.session2_start_time = None
    
    def start_new_session(self):
        """Start a new work session for current user or close existing session"""
        if self.current_session_id:
            # If there's an active session, stop it (async)
            threading.Thread(target=self._close_current_session_async, daemon=True).start()
            return
        
        # Start session in background thread to prevent GUI freeze
        threading.Thread(target=self._start_new_session_async, daemon=True).start()
    
    def _start_new_session_async(self):
        """Async version of start_new_session to prevent GUI blocking"""
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
            response = requests.post(api_url.replace('/log', '/session/start'), json=data, timeout=1)
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
                    project_response = requests.post(api_url.replace('/log', '/project_session/start'), json=project_session_data, timeout=1)
                    if project_response.ok:
                        self.log_message(f"✓ Werk sessie gestart voor {current_user}", "success")
                        self.update_session_display()
                    else:
                        self.log_message("⚠️ Sessie gestart, maar project tracking mislukt", "warning")
                        self.update_session_display()
                except Exception as pe:
                    self.log_message("⚠️ Sessie gestart, maar project tracking mislukt", "warning")
                    self.update_session_display()
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
        # Run in background thread to prevent GUI freeze
        threading.Thread(target=self._close_current_session_async, daemon=True).start()
    
    def _close_current_session_async(self):
        """Async version of close_current_session to prevent GUI blocking"""
        if not self.current_session_id:
            return
        
        # Check if we have a background session - if so, handle differently
        if self.background_session_id:
            # We have both sessions active
            result = messagebox.askyesno(
                "Stop Huidige Sessie",
                f"Wilt u de huidige sessie {self.current_session_id} stoppen?\n\n"
                f"De achtergrond sessie {self.background_session_id} blijft actief.\n"
                f"Projecten worden NIET afgemeld (achtergrond sessie loopt nog).",
                icon='question'
            )
            
            if not result:
                return
            
            # Stop current session but keep projects active
            config = get_config()
            api_url = config.get('api_url', '').rstrip('/')
            
            try:
                end_data = {
                    'session_id': self.current_session_id,
                    'timestamp': datetime.now().isoformat(),
                    'keep_projects_active': True  # Background session still needs projects
                }
                
                response = requests.post(api_url.replace('/log', '/session/end'), json=end_data, timeout=1)
                if response.ok:
                    self.log_message(f"✓ Huidige sessie {self.current_session_id} gestopt", "success")
                    
                    # Move background session to current
                    self.current_session_id = self.background_session_id
                    self.session_start_time = self.session2_start_time
                    self.background_session_id = None
                    self.session2_start_time = None
                    
                    # Reset pause states for the now-current session
                    self.session_paused = False
                    self.pause_start_time = None
                    self.total_pause_duration = 0
                    
                    self.log_message(f"↔️ Achtergrond sessie {self.current_session_id} is nu actief", "info")
                    
                    # Update display
                    self.update_session_display()
                else:
                    self.log_message(f"❌ Kon huidige sessie niet stoppen: {response.text}", "error")
            except Exception as e:
                self.log_message(f"❌ Fout bij stoppen huidige sessie: {e}", "error")
            
            return
        
        # Normal case - no background session, so we can AFGEMELD projects
        # If session is paused, just clear the pause state without sending resume event
        # (we're stopping the session, so no need to log a resume)
        if self.session1_paused:
            self.session1_paused = False
            self.session1_pause_start = None
        
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
                    response = requests.post(api_url, json=data_afgemeld, timeout=1)
                    if response.ok:
                        self.log_message(f"✓ Project {project} afgesloten", "success")
                        self.open_projects.discard(project)
                    else:
                        error_msg = response.text[:200] if response.text else f"Status: {response.status_code}"
                        self.log_message(f"⚠️ Fout bij afsluiten project {project}: {error_msg}", "warning")
                except Exception as e:
                    self.log_message(f"⚠️ Netwerkfout bij afsluiten project {project}: {e}", "warning")
        
        # Then close the session
        data = {
            'session_id': self.current_session_id,
            'timestamp': timestamp,
            'total_pause_duration': self.total_pause_duration  # Include pause duration for accurate work time calculation
        }
        
        try:
            response = requests.post(api_url.replace('/log', '/session/end'), json=data, timeout=1)
            if response.ok:
                end_time = datetime.now()
                # Use work minutes calculation that excludes breaks
                work_minutes = int(self.calculate_work_minutes_local(self.session_start_time, end_time))
                self.log_message(f"✓ Sessie afgesloten. Duur: {work_minutes} minuten", "success")
        except Exception as e:
            self.log_message(f"⚠️ Fout bij afsluiten sessie: {e}", "warning")
        
        self.current_session_id = None
        self.session_start_time = None
        self.session_paused = False
        self.pause_start_time = None
        self.total_pause_duration = 0
        self.session1_project = None  # Clear Session 1 project
        self.session1_projects = []  # Clear batch list
        self.update_session_display()
        if hasattr(self, 'pauze_photo') and self.pauze_photo:
            self.pause_button.config(image=self.pauze_photo)
        else:
            self.pause_button.config(text="⏸", bg="#34495E", activebackground="#2C3E50")  # Pause icon, gray
        self.pause_label.config(text="Pauzeer")
    

    # update_session_timer function removed - timer no longer displayed
    
    def toggle_pause_session(self):
        """Toggle between pausing and resuming Session 1"""
        if not self.current_session_id:
            return
        
        if self.session1_paused:
            self.resume_session1()
        else:
            self.pause_session1()
    
    def toggle_pause_session2(self):
        """Toggle between pausing and resuming Session 2"""
        if not self.background_session_id:
            return
        
        if self.session2_paused:
            self.resume_session2()
        else:
            self.pause_session2()
    
    def pause_session1(self):
        """Pause Session 1 only"""
        if not self.current_session_id or self.session1_paused:
            return
        
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')
        current_user = config.get('user', 'NESTING')
        
        # Set pause state for Session 1
        self.session1_paused = True
        self.session1_pause_start = datetime.now()
        
        # Get current project for Session 1
        current_project = self.session1_project
        
        # Pause Session 1
        data = {
            'session_id': self.current_session_id,
            'timestamp': self.session1_pause_start.isoformat(),
            'user': current_user,
            'project': current_project
        }
        
        try:
            # Send pause event to session endpoint
            response = requests.post(api_url.replace('/log', '/session/pause'), json=data, timeout=1)
            if response.ok:
                self.log_message(f"⏸️ Actieve sessie gepauzeerd voor {current_user}", "info")
                
                # Also log SESSION_PAUSE event for tracking
                log_data = {
                    'event': 'SESSION_PAUSE',
                    'user': current_user,
                    'project': current_project,
                    'session_id': self.current_session_id,
                    'details': 'Sessie 1 gepauzeerd',
                    'timestamp': self.session1_pause_start.isoformat()
                }
                try:
                    requests.post(api_url, json=log_data, timeout=1)
                except:
                    pass  # Don't fail the pause if event logging fails
                
                # Update UI for Session 1 pause
                self.session_status_label.config(text=f"Sessie 1 gepauzeerd: {current_user}", fg="#F39C12")
                    
                # Change pause button to show resume (we'll use start image for resume)
                if hasattr(self, 'start_photo') and self.start_photo:
                    self.pause_button.config(image=self.start_photo)
                else:
                    self.pause_button.config(text="▶", bg="#27AE60", activebackground="#229954")  # Play icon, green
                self.pause_label.config(text="Hervat S1")
                
            else:
                self.log_message("❌ Kon sessie 1 niet pauzeren", "error")
                # Revert pause state on failure
                self.session1_paused = False
                self.session1_pause_start = None
        except Exception as e:
            self.log_message(f"❌ Fout bij pauzeren sessie 1: {e}", "error")
            # Revert pause state on failure
            self.session1_paused = False
            self.session1_pause_start = None
    
    def pause_session2(self):
        """Pause Session 2 only"""
        if not self.background_session_id or self.session2_paused:
            return
        
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')
        current_user = config.get('user', 'NESTING')
        
        # Set pause state for Session 2
        self.session2_paused = True
        self.session2_pause_start = datetime.now()
        
        # Get current project for Session 2
        current_project = self.session2_project
        
        # Pause Session 2
        data = {
            'session_id': self.background_session_id,
            'timestamp': self.session2_pause_start.isoformat(),
            'user': current_user,
            'project': current_project
        }
        
        try:
            # Send pause event to session endpoint
            response = requests.post(api_url.replace('/log', '/session/pause'), json=data, timeout=1)
            if response.ok:
                self.log_message(f"⏸️ Achtergrond sessie gepauzeerd voor {current_user}", "info")
                
                # Also log SESSION_PAUSE event for tracking
                log_data = {
                    'event': 'SESSION_PAUSE',
                    'user': current_user,
                    'project': current_project,
                    'session_id': self.background_session_id,
                    'details': 'Sessie 2 gepauzeerd',
                    'timestamp': self.session2_pause_start.isoformat()
                }
                try:
                    requests.post(api_url, json=log_data, timeout=1)
                except:
                    pass  # Don't fail the pause if event logging fails
                
                # Update UI for Session 2 pause
                # Change pause button to show resume
                if hasattr(self, 'start_photo') and self.start_photo:
                    self.pause_button2.config(image=self.start_photo)
                else:
                    self.pause_button2.config(text="▶", bg="#27AE60", activebackground="#229954")  # Play icon, green
                self.pause_label2.config(text="Hervat S2")
                
            else:
                self.log_message("❌ Kon sessie 2 niet pauzeren", "error")
                # Revert pause state on failure
                self.session2_paused = False
                self.session2_pause_start = None
        except Exception as e:
            self.log_message(f"❌ Fout bij pauzeren sessie 2: {e}", "error")
            # Revert pause state on failure
            self.session2_paused = False
            self.session2_pause_start = None
    
    def resume_session1(self):
        """Resume paused Session 1"""
        threading.Thread(target=self._resume_session1_async, daemon=True).start()
    
    def _resume_session1_async(self):
        """Async version of resume_session1 to prevent GUI blocking"""
        if not self.current_session_id or not self.session1_paused:
            return
        
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')
        current_user = config.get('user', 'NESTING')
        
        # Calculate pause duration for Session 1
        pause_duration_seconds = 0
        if self.session1_pause_start:
            # Don't calculate pause duration locally - let the API do it with work-hours awareness
            pause_duration_seconds = (datetime.now() - self.session1_pause_start).total_seconds()
            # Don't add to total - the API will track the correct work-hours-aware total
        
        # Get current project for Session 1
        current_project = self.session1_project
        
        data = {
            'session_id': self.current_session_id,
            'timestamp': datetime.now().isoformat(),
            'total_pause_duration': self.session1_total_pause,
            'user': current_user,
            'project': current_project
        }
        
        try:
            response = requests.post(api_url.replace('/log', '/session/resume'), json=data, timeout=1)
            if response.ok:
                self.log_message(f"▶️ Actieve sessie hervat voor {current_user}", "success")
                
                # Also log SESSION_RESUME event for tracking
                pause_minutes = round(pause_duration_seconds / 60, 1)
                log_data = {
                    'event': 'SESSION_RESUME',
                    'user': current_user,
                    'project': current_project,
                    'session_id': self.current_session_id,
                    'details': f'Sessie 1 hervat - pauze duur: {pause_minutes} minuten',
                    'status': 'BEZIG',  # Show that work is continuing
                    'timestamp': datetime.now().isoformat()
                }
                try:
                    requests.post(api_url, json=log_data, timeout=1)
                except:
                    pass  # Don't fail the resume if event logging fails
                
                # Update UI for Session 1 resume
                self.session_status_label.config(text=f"Sessie 1 actief: {current_user}", fg="#27AE60")
                
                # Change pause button back to pause icon
                if hasattr(self, 'pauze_photo') and self.pauze_photo:
                    self.pause_button.config(image=self.pauze_photo)
                else:
                    self.pause_button.config(text="⏸", bg="#34495E", activebackground="#2C3E50")  # Pause icon, gray
                self.pause_label.config(text="Pauzeer S1")
                
                # Clear pause state for Session 1
                self.session1_paused = False
                self.session1_pause_start = None
            else:
                self.log_message("❌ Kon sessie 1 niet hervatten", "error")
        except Exception as e:
            self.log_message(f"❌ Fout bij hervatten sessie 1: {e}", "error")
    
    def resume_session2(self):
        """Resume paused Session 2"""
        threading.Thread(target=self._resume_session2_async, daemon=True).start()
    
    def _resume_session2_async(self):
        """Async version of resume_session2 to prevent GUI blocking"""
        if not self.background_session_id or not self.session2_paused:
            return
        
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')
        current_user = config.get('user', 'NESTING')
        
        # Calculate pause duration for Session 2
        pause_duration_seconds = 0
        if self.session2_pause_start:
            # Don't calculate pause duration locally - let the API do it with work-hours awareness
            pause_duration_seconds = (datetime.now() - self.session2_pause_start).total_seconds()
            # Don't add to total - the API will track the correct work-hours-aware total
        
        # Get current project for Session 2
        current_project = self.session2_project
        
        data = {
            'session_id': self.background_session_id,
            'timestamp': datetime.now().isoformat(),
            'total_pause_duration': self.session2_total_pause,
            'user': current_user,
            'project': current_project
        }
        
        try:
            response = requests.post(api_url.replace('/log', '/session/resume'), json=data, timeout=1)
            if response.ok:
                self.log_message(f"▶️ Achtergrond sessie hervat voor {current_user}", "success")
                
                # Also log SESSION_RESUME event for tracking
                pause_minutes = round(pause_duration_seconds / 60, 1)
                log_data = {
                    'event': 'SESSION_RESUME',
                    'user': current_user,
                    'project': current_project,
                    'session_id': self.background_session_id,
                    'details': f'Sessie 2 hervat - pauze duur: {pause_minutes} minuten',
                    'status': 'BEZIG',  # Show that work is continuing
                    'timestamp': datetime.now().isoformat()
                }
                try:
                    requests.post(api_url, json=log_data, timeout=1)
                except:
                    pass  # Don't fail the resume if event logging fails
                    
                # Update UI for Session 2 resume
                # Change pause button back to pause icon
                if hasattr(self, 'pauze_photo') and self.pauze_photo:
                    self.pause_button2.config(image=self.pauze_photo)
                else:
                    self.pause_button2.config(text="⏸", bg="#95a5a6", activebackground="#7f8c8d")  # Pause icon, gray
                self.pause_label2.config(text="Pauzeer S2")
                
                # Clear pause state for Session 2
                self.session2_paused = False
                self.session2_pause_start = None
                
            else:
                self.log_message("❌ Kon sessie 2 niet hervatten", "error")
        except Exception as e:
            self.log_message(f"❌ Fout bij hervatten sessie 2: {e}", "error")

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

    def _update_session_project_items(self, project, item_count):
        """Update the item count for a project in session_projects table"""
        try:
            config = get_config()
            api_url = config.get('api_url', '').rstrip('/')
            
            # Determine which session this project belongs to
            session_to_update = None
            if project in self.session1_projects:
                session_to_update = self.current_session_id
            elif project in self.session2_projects:
                session_to_update = self.background_session_id
            
            if session_to_update and api_url:
                # Update the session_projects entry with actual item count
                update_data = {
                    'session_id': session_to_update,
                    'project': project,
                    'item_count': item_count,
                    'timestamp': datetime.now().isoformat()
                }
                # Build the correct URL - api_url is base URL, not the /log endpoint
                base_url = api_url.replace('/log', '') if '/log' in api_url else api_url
                update_url = f"{base_url}/session/update_project_items"
                response = requests.post(update_url, json=update_data, timeout=1)
                if response.ok:
                    self.log_message(f"✓ Items bijgewerkt voor {project}: {item_count}", "debug")
        except Exception as e:
            # Don't fail if update fails
            self.log_message(f"⚠️ Kon items niet bijwerken: {e}", "debug")
    
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
                
                # Update session_projects with actual item count if this is current user
                config = get_config()
                current_user = config.get('user', 'NESTING')
                if user == current_user:
                    self._update_session_project_items(project, int(count))
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
            self.com_frame.pack(fill='x', padx=20, pady=5, before=self.session_frame)
            self.usb_frame.pack_forget()
        else:
            self.usb_frame.pack(fill='x', padx=20, pady=5, before=self.session_frame)
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
        # This method is now a stub - UI moved to admin panel
        pass
    
    def _update_admin_dependent_ui(self, *args):
        # This method is now a stub - UI moved to admin panel
        pass
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
        # Use the correct session based on which one is the scan target
        if self.active_scan_session == 2 and self.session2_id:
            session_data['session_id'] = self.session2_id
        elif self.active_scan_session == 1 and self.session1_id:
            session_data['session_id'] = self.session1_id
        elif self.current_session_id:
            # Fallback to current_session_id for backward compatibility
            session_data['session_id'] = self.current_session_id

        # Check if project is already open
        if project_code_to_log in self.open_projects:
            self.log_message(f"ℹ️ Project {project_code_to_log} is al geopend", "warning")
            self.usb_entry.config(bg='light green')
            self.after(2000, lambda: self.usb_entry.config(bg='white'))
            return

        # Use current time for the scan timestamp
        scan_timestamp = datetime.now().isoformat()
        
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
            resp_open = requests.post(api_url, json=data_open, timeout=3)  # Increased timeout
            if not resp_open.ok:
                # Log the error but don't fail the operation - OPEN should always be recorded
                self.log_message(f"⚠️ Waarschuwing: Project open event niet geregistreerd (HTTP {resp_open.status_code})", "warning")
            
            # Always show project opened and update session display
            # Even if logging failed, the user DID open/scan the project
            self.log_message(f"✓ Project {project_code_to_log} geopend door {current_user}", "success")
            # Store current project for session tracking
            self.current_project = project_code_to_log
            
            # Update project in session display - add to the selected session
            session_to_update = None
            
            if self.active_scan_session == 1 and self.session1_id:
                session_to_update = self.session1_id
                self.session1_project = project_code_to_log  # Keep track of last project
                if project_code_to_log not in self.session1_projects:
                    self.session1_projects.append(project_code_to_log)
                # Show multiple projects if batch
                if len(self.session1_projects) > 1:
                    self.active_project_label.config(text=f"Batch: {len(self.session1_projects)} projecten")
                else:
                    self.active_project_label.config(text=f"Project: {project_code_to_log}")
            elif self.active_scan_session == 2 and self.session2_id:
                session_to_update = self.session2_id
                self.session2_project = project_code_to_log  # Keep track of last project
                if project_code_to_log not in self.session2_projects:
                    self.session2_projects.append(project_code_to_log)
                # Show multiple projects if batch
                if len(self.session2_projects) > 1:
                    self.background_project_label.config(text=f"Batch: {len(self.session2_projects)} projecten")
                else:
                    self.background_project_label.config(text=f"Project: {project_code_to_log}")
            else:
                # No session active for the selected scan target
                self.log_message(f"⚠️ Sessie {self.active_scan_session} is niet actief. Start eerst de sessie.", "warning")
                return
            
            # Link project to session in database
            if session_to_update and api_url:
                try:
                    # Item count is 0 when project opens, will be updated when items are scanned
                    initial_item_count = 0
                    link_data = {
                        'session_id': session_to_update,
                        'project': project_code_to_log,
                        'item_count': initial_item_count,
                        'timestamp': scan_timestamp
                    }
                    # Build the correct URL - api_url is base URL, not the /log endpoint
                    base_url = api_url.replace('/log', '') if '/log' in api_url else api_url
                    link_url = f"{base_url}/session/add_project"
                    response = requests.post(link_url, json=link_data, timeout=1)
                    if response.ok:
                        self.log_message(f"✓ Project {project_code_to_log} gekoppeld aan sessie {session_to_update}", "debug")
                    else:
                        self.log_message(f"⚠️ Kon project niet koppelen: {response.text}", "warning")
                except Exception as e:
                    # Don't fail the scan if linking fails
                    self.log_message(f"⚠️ Kon project niet koppelen aan sessie: {e}", "warning")
                
        except requests.exceptions.Timeout:
            # Timeout - log warning but continue
            self.log_message(f"⚠️ Waarschuwing: Project open event timeout - werk wordt nog steeds verwerkt", "warning")
            self.log_message(f"✓ Project {project_code_to_log} geopend door {current_user}", "success")
            # Still update project tracking - respect active_scan_session
            self.current_project = project_code_to_log
            if self.active_scan_session == 1 and self.session1_id:
                self.session1_project = project_code_to_log
                if project_code_to_log not in self.session1_projects:
                    self.session1_projects.append(project_code_to_log)
                if len(self.session1_projects) > 1:
                    self.active_project_label.config(text=f"Batch: {len(self.session1_projects)} projecten")
                else:
                    self.active_project_label.config(text=f"Project: {project_code_to_log}")
            elif self.active_scan_session == 2 and self.session2_id:
                self.session2_project = project_code_to_log
                if project_code_to_log not in self.session2_projects:
                    self.session2_projects.append(project_code_to_log)
                if len(self.session2_projects) > 1:
                    self.background_project_label.config(text=f"Batch: {len(self.session2_projects)} projecten")
                else:
                    self.background_project_label.config(text=f"Project: {project_code_to_log}")
        except Exception as e:
            # Other network error - log but continue
            self.log_message(f"⚠️ Netwerkwaarschuwing: {str(e)[:50]}", "warning")
            self.log_message(f"✓ Project {project_code_to_log} geopend door {current_user}", "success")
            # Still update project tracking - respect active_scan_session
            self.current_project = project_code_to_log
            if self.active_scan_session == 1 and self.session1_id:
                self.session1_project = project_code_to_log
                if project_code_to_log not in self.session1_projects:
                    self.session1_projects.append(project_code_to_log)
                if len(self.session1_projects) > 1:
                    self.active_project_label.config(text=f"Batch: {len(self.session1_projects)} projecten")
                else:
                    self.active_project_label.config(text=f"Project: {project_code_to_log}")
            elif self.active_scan_session == 2 and self.session2_id:
                self.session2_project = project_code_to_log
                if project_code_to_log not in self.session2_projects:
                    self.session2_projects.append(project_code_to_log)
                if len(self.session2_projects) > 1:
                    self.background_project_label.config(text=f"Batch: {len(self.session2_projects)} projecten")
                else:
                    self.background_project_label.config(text=f"Project: {project_code_to_log}")

        # Don't duplicate the processing message - it's already shown via callback
        
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
            
            # Assign project to the active scan session - respect active_scan_session
            if self.active_scan_session == 1 and self.session1_id:
                self.session1_project = project_code_to_log  # Keep track of last project
                if project_code_to_log not in self.session1_projects:
                    self.session1_projects.append(project_code_to_log)
                # Show multiple projects if batch
                if len(self.session1_projects) > 1:
                    self.active_project_label.config(text=f"Batch: {len(self.session1_projects)} projecten")
                else:
                    self.active_project_label.config(text=f"Project: {project_code_to_log}")
            elif self.active_scan_session == 2 and self.session2_id:
                self.session2_project = project_code_to_log  # Keep track of last project
                if project_code_to_log not in self.session2_projects:
                    self.session2_projects.append(project_code_to_log)
                # Show multiple projects if batch
                if len(self.session2_projects) > 1:
                    self.background_project_label.config(text=f"Batch: {len(self.session2_projects)} projecten")
                else:
                    self.background_project_label.config(text=f"Project: {project_code_to_log}")
            
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
                self.com_status_label.config(text="VERBONDEN", fg="#27AE60")
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