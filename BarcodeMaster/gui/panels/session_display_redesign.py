"""
Redesigned Session Display for BarcodeMaster Scanner Panel
A larger, more intuitive interface for managing dual work sessions
"""

import tkinter as tk
from datetime import datetime, timedelta

class SessionDisplay:
    """
    Large, clear session display showing:
    - Session ID and start time
    - Duration timer
    - Status (Active/Paused/Background)
    - Clear visual distinction between sessions
    """
    
    def create_session_display(self, parent_frame):
        """Create the enhanced session display UI"""
        
        # Main session container - much larger
        self.session_container = tk.LabelFrame(
            parent_frame,
            text="WERK SESSIE BEHEER",
            bg="#f8f9fa",
            fg="#2c3e50",
            font=('Segoe UI', 12, 'bold'),
            padx=20,
            pady=15,
            relief=tk.RIDGE,
            borderwidth=2
        )
        self.session_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Work hours indicator at top
        self.work_hours_frame = tk.Frame(self.session_container, bg="#f8f9fa")
        self.work_hours_frame.pack(fill='x', pady=(0, 10))
        
        self.work_hours_indicator = tk.Label(
            self.work_hours_frame,
            text="⏰ Werktijd: 07:30 - 16:00",
            bg="#f8f9fa",
            fg="#27ae60",
            font=('Segoe UI', 10)
        )
        self.work_hours_indicator.pack(side='left')
        
        # Main content area with two columns
        content_frame = tk.Frame(self.session_container, bg="#f8f9fa")
        content_frame.pack(fill='both', expand=True)
        
        # LEFT COLUMN - Active Session
        left_frame = tk.Frame(content_frame, bg="#f8f9fa")
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Active session card
        self.active_session_card = tk.LabelFrame(
            left_frame,
            text="ACTIEVE SESSIE",
            bg="#ffffff",
            fg="#2980b9",
            font=('Segoe UI', 11, 'bold'),
            padx=15,
            pady=10,
            relief=tk.SOLID,
            borderwidth=2
        )
        self.active_session_card.pack(fill='both', expand=True)
        
        # Session info
        self.active_session_id = tk.Label(
            self.active_session_card,
            text="Geen actieve sessie",
            bg="#ffffff",
            fg="#7f8c8d",
            font=('Segoe UI', 10)
        )
        self.active_session_id.pack(anchor='w', pady=2)
        
        self.active_session_start = tk.Label(
            self.active_session_card,
            text="Start tijd: --:--",
            bg="#ffffff",
            fg="#7f8c8d",
            font=('Segoe UI', 10)
        )
        self.active_session_start.pack(anchor='w', pady=2)
        
        self.active_session_duration = tk.Label(
            self.active_session_card,
            text="Duur: 0h 0m",
            bg="#ffffff",
            fg="#2c3e50",
            font=('Segoe UI', 11, 'bold')
        )
        self.active_session_duration.pack(anchor='w', pady=5)
        
        # Active session status indicator
        self.active_status_frame = tk.Frame(self.active_session_card, bg="#ffffff")
        self.active_status_frame.pack(fill='x', pady=5)
        
        self.active_status_indicator = tk.Label(
            self.active_status_frame,
            text="● ACTIEF",
            bg="#ffffff",
            fg="#27ae60",
            font=('Segoe UI', 10, 'bold')
        )
        self.active_status_indicator.pack(side='left')
        
        # RIGHT COLUMN - Background Session
        right_frame = tk.Frame(content_frame, bg="#f8f9fa")
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        # Background session card
        self.background_session_card = tk.LabelFrame(
            right_frame,
            text="ACHTERGROND SESSIE",
            bg="#ffffff",
            fg="#8e44ad",
            font=('Segoe UI', 11, 'bold'),
            padx=15,
            pady=10,
            relief=tk.SOLID,
            borderwidth=2
        )
        self.background_session_card.pack(fill='both', expand=True)
        
        # Background session info
        self.background_session_id = tk.Label(
            self.background_session_card,
            text="Geen achtergrond sessie",
            bg="#ffffff",
            fg="#bdc3c7",
            font=('Segoe UI', 10)
        )
        self.background_session_id.pack(anchor='w', pady=2)
        
        self.background_session_start = tk.Label(
            self.background_session_card,
            text="Start tijd: --:--",
            bg="#ffffff",
            fg="#bdc3c7",
            font=('Segoe UI', 10)
        )
        self.background_session_start.pack(anchor='w', pady=2)
        
        self.background_session_duration = tk.Label(
            self.background_session_card,
            text="Duur: 0h 0m",
            bg="#ffffff",
            fg="#7f8c8d",
            font=('Segoe UI', 11, 'bold')
        )
        self.background_session_duration.pack(anchor='w', pady=5)
        
        # Background session status
        self.background_status_frame = tk.Frame(self.background_session_card, bg="#ffffff")
        self.background_status_frame.pack(fill='x', pady=5)
        
        self.background_status_indicator = tk.Label(
            self.background_status_frame,
            text="● INACTIEF",
            bg="#ffffff",
            fg="#bdc3c7",
            font=('Segoe UI', 10, 'bold')
        )
        self.background_status_indicator.pack(side='left')
        
        # CONTROL BUTTONS - Larger and clearer
        controls_frame = tk.Frame(self.session_container, bg="#f8f9fa")
        controls_frame.pack(fill='x', pady=(15, 0))
        
        # Button container with equal spacing
        button_container = tk.Frame(controls_frame, bg="#f8f9fa")
        button_container.pack()
        
        # START/STOP button
        self.start_button_frame = tk.Frame(button_container, bg="#f8f9fa")
        self.start_button_frame.pack(side='left', padx=10)
        
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
            bd=2
        )
        self.start_button.pack()
        
        self.start_label = tk.Label(
            self.start_button_frame,
            text="Start Sessie",
            bg="#f8f9fa",
            font=('Segoe UI', 10)
        )
        self.start_label.pack()
        
        # PAUSE button
        self.pause_button_frame = tk.Frame(button_container, bg="#f8f9fa")
        self.pause_button_frame.pack(side='left', padx=10)
        
        self.pause_button = tk.Button(
            self.pause_button_frame,
            text="⏸",
            font=('Arial', 28, 'bold'),
            bg="#95a5a6",
            fg="white",
            width=4,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            activebackground="#7f8c8d",
            bd=2,
            state='disabled'
        )
        self.pause_button.pack()
        
        self.pause_label = tk.Label(
            self.pause_button_frame,
            text="Pauzeer",
            bg="#f8f9fa",
            font=('Segoe UI', 10)
        )
        self.pause_label.pack()
        
        # NEW BATCH button
        self.batch_button_frame = tk.Frame(button_container, bg="#f8f9fa")
        self.batch_button_frame.pack(side='left', padx=10)
        
        self.batch_button = tk.Button(
            self.batch_button_frame,
            text="⟳",
            font=('Arial', 28, 'bold'),
            bg="#3498db",
            fg="white",
            width=4,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            activebackground="#2980b9",
            bd=2,
            state='disabled'
        )
        self.batch_button.pack()
        
        self.batch_label = tk.Label(
            self.batch_button_frame,
            text="Nieuwe Batch",
            bg="#f8f9fa",
            font=('Segoe UI', 10)
        )
        self.batch_label.pack()
        
    def update_active_session(self, session_id, start_time, is_paused=False):
        """Update active session display"""
        if session_id:
            self.active_session_id.config(
                text=f"Sessie ID: {session_id[-8:]}",
                fg="#2c3e50"
            )
            self.active_session_start.config(
                text=f"Start tijd: {start_time.strftime('%H:%M')}",
                fg="#2c3e50"
            )
            
            # Calculate duration
            duration = datetime.now() - start_time
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            self.active_session_duration.config(
                text=f"Duur: {hours}h {minutes}m",
                fg="#2c3e50"
            )
            
            if is_paused:
                self.active_status_indicator.config(
                    text="● GEPAUZEERD",
                    fg="#f39c12"
                )
            else:
                self.active_status_indicator.config(
                    text="● ACTIEF",
                    fg="#27ae60"
                )
        else:
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
    
    def update_background_session(self, session_id, start_time):
        """Update background session display"""
        if session_id:
            self.background_session_id.config(
                text=f"Sessie ID: {session_id[-8:]}",
                fg="#2c3e50"
            )
            self.background_session_start.config(
                text=f"Start tijd: {start_time.strftime('%H:%M')}",
                fg="#2c3e50"
            )
            
            # Calculate duration
            duration = datetime.now() - start_time
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            self.background_session_duration.config(
                text=f"Duur: {hours}h {minutes}m",
                fg="#2c3e50"
            )
            
            self.background_status_indicator.config(
                text="● ACHTERGROND",
                fg="#8e44ad"
            )
        else:
            self.background_session_id.config(
                text="Geen achtergrond sessie",
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