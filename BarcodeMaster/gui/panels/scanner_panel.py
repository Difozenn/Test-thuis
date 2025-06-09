import tkinter as tk
from config_utils import get_config, save_config

class ScannerPanel(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="#f0f0f0")
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
        self.com_frame = tk.LabelFrame(self, text="COM Poort", bg="#f0f0f0", padx=10, pady=5)
        self.com_port_var = tk.StringVar(value=config.get('scanner_panel_com_port', ''))
        self.com_port_var.trace_add('write', self.save_com_port)
        tk.Label(self.com_frame, text="Selecteer COM Poort:", bg="#f0f0f0").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.com_port_combo = tk.ttk.Combobox(self.com_frame, textvariable=self.com_port_var, width=15)
        self.com_port_combo.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        tk.Button(self.com_frame, text="Vernieuw", command=self.refresh_ports).grid(row=0, column=2, padx=5, pady=5)
        self.baud_rate_var = tk.StringVar(value=config.get('scanner_panel_baud_rate', '9600'))
        self.baud_rate_var.trace_add('write', self.save_baud_rate)
        tk.Label(self.com_frame, text="Baud Rate:", bg="#f0f0f0").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        tk.Entry(self.com_frame, textvariable=self.baud_rate_var, width=10).grid(row=1, column=1, padx=5, pady=5, sticky='w')
        self.connect_btn = tk.Button(self.com_frame, text="Verbinden", command=self.connect_com)
        self.connect_btn.grid(row=2, column=0, padx=5, pady=10, sticky='w')
        self.disconnect_btn = tk.Button(self.com_frame, text="Verbreek", command=self.disconnect_com)
        self.disconnect_btn.grid(row=2, column=1, padx=5, pady=10, sticky='w')
        self.com_status_label = tk.Label(self.com_frame, text="Niet verbonden", fg="red", bg="#f0f0f0")
        self.com_status_label.grid(row=2, column=2, padx=5, pady=10, sticky='w')
        # --- Event Type Selection ---
        event_type = config.get('scanner_panel_event_type', 'OPEN')
        self.event_type_var = tk.StringVar(value=event_type)
        event_frame = tk.LabelFrame(self, text="Event Type", bg="#f0f0f0", padx=10, pady=5)
        event_frame.pack(pady=(0, 10), fill='x', padx=20)
        self.event_type_locked = config.get('scanner_panel_event_type_locked', False)
        self.open_radio = tk.Radiobutton(event_frame, text="OPEN", variable=self.event_type_var, value="OPEN", bg="#f0f0f0", command=self.save_event_type)
        self.closed_radio = tk.Radiobutton(event_frame, text="CLOSED", variable=self.event_type_var, value="CLOSED", bg="#f0f0f0", command=self.save_event_type)
        self.open_radio.pack(side='left', padx=10)
        self.closed_radio.pack(side='left', padx=10)
        self.lock_btn = tk.Button(event_frame, text="Lock", command=self.toggle_event_type_lock)
        self._lock_btn_packed = False
        # Do not pack yet; controlled by set_lock_button_visibility
        # self.lock_btn.pack(side='left', padx=10)
        # Apply lock state on startup
        self.apply_event_type_lock_ui()
        # Ensure correct secondary frame is visible on panel open
        self.update_frame_visibility()

    def set_lock_button_visibility(self, visible):
        if visible and not self._lock_btn_packed:
            self.lock_btn.pack(side='left', padx=10)
            self._lock_btn_packed = True
        elif not visible and self._lock_btn_packed:
            self.lock_btn.pack_forget()
            self._lock_btn_packed = False

    def update_frame_visibility(self):
        if self.scanner_type_var.get() == 'COM':
            self.com_frame.pack(fill='x', padx=20, pady=5)
            self.usb_frame.forget()
        else:
            self.usb_frame.pack(fill='x', padx=20, pady=5)
            self.com_frame.forget()

    def on_scanner_type_change(self):
        self.save_scanner_type()
        self.update_frame_visibility()

    def save_scanner_type(self):
        save_config({'scanner_panel_type': self.scanner_type_var.get()})

    def save_com_port(self, *args):
        save_config({'scanner_panel_com_port': self.com_port_var.get()})

    def save_baud_rate(self, *args):
        save_config({'scanner_panel_baud_rate': self.baud_rate_var.get()})

    
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

    def log_scan_event(self, code):
        import requests
        from config_utils import get_config
        import traceback
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')
        print("[ScannerPanel] log_scan_event called")
        print(f"  Code: {code}")
        print(f"  Event type: {self.event_type_var.get()}")
        print(f"  User: {config.get('user', 'unknown')}")
        print(f"  API URL: {api_url}")
        if not api_url:
            print("  [ERROR] No API URL configured!")
            return

        event_type = self.event_type_var.get()
        # For OPEN event, log for each user in config['scanner_panel_open_event_users'] (default: GANNOMAT, OPUS)
        if event_type == 'OPEN':
            open_users = config.get('scanner_panel_open_event_users', ['GANNOMAT', 'OPUS'])
            current_user = config.get('user', 'unknown')
            all_ok = True

            # Log CLOSED event for current user
            data_closed = {
                'event': 'CLOSED',
                'details': code,
                'project': code,
                'user': current_user
            }
            print(f"  [OPEN LOGIC] Payload for current user (CLOSED): {data_closed}")
            try:
                resp = requests.post(api_url, json=data_closed, timeout=3)
                print(f"    Response status: {resp.status_code}")
                print(f"    Response text: {resp.text}")
                if not resp.ok:
                    all_ok = False
            except Exception as e:
                print(f"    [EXCEPTION] Exception for current user!")
                print(traceback.format_exc())
                all_ok = False

            # Log OPEN events for all other users
            for user in open_users:
                if user == current_user:
                    continue
                data = {
                    'event': 'OPEN',
                    'details': code,
                    'project': code,
                    'user': user
                }
                print(f"  [OPEN LOGIC] Payload for other user (OPEN): {data}")
                try:
                    resp = requests.post(api_url, json=data, timeout=3)
                    print(f"    Response status: {resp.status_code}")
                    print(f"    Response text: {resp.text}")
                    if not resp.ok:
                        all_ok = False
                except Exception as e:
                    print(f"    [EXCEPTION] Exception for user {user}!")
                    print(traceback.format_exc())
                    all_ok = False
            # UI feedback: green if all succeeded, red otherwise
            if all_ok:
                print("  [SUCCESS] All OPEN/CLOSED events logged, setting entry to green")
                self.after(0, lambda: self.usb_entry.config(bg='#c8f7c5'))
            else:
                print("  [FAILURE] At least one OPEN/CLOSED event failed, setting entry to red")
                self.after(0, lambda: self.usb_entry.config(bg='#f7c5c5'))
        else:
            # Default: log for current user only
            data = {
                'event': event_type,
                'details': code,
                'project': code,
                'user': config.get('user', 'unknown')
            }
            print(f"  Payload: {data}")
            try:
                resp = requests.post(api_url, json=data, timeout=3)
                print(f"  Response status: {resp.status_code}")
                print(f"  Response text: {resp.text}")
                if resp.ok:
                    print("  [SUCCESS] Response OK, setting entry to green")
                    self.after(0, lambda: self.usb_entry.config(bg='#c8f7c5'))  # light green
                    self._set_dbpanel_connection_status(True)
                else:
                    print("  [FAILURE] Response NOT OK, setting entry to red")
                    self.after(0, lambda: self.usb_entry.config(bg='#f7c5c5'))  # light red
                    self._set_dbpanel_connection_status(False)
            except Exception as e:
                print("  [EXCEPTION] Exception occurred during POST request!")
                print(traceback.format_exc())
                self.after(0, lambda: self.usb_entry.config(bg='#f7c5c5'))
                self._set_dbpanel_connection_status(False, str(e))

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
        # Example logic: just update status label for now
        self.com_status_label.config(text="Verbonden", fg="green")
        save_config({'scanner_panel_com_connected': True})

    def disconnect_com(self):
        self.com_status_label.config(text="Niet verbonden", fg="red")
        save_config({'scanner_panel_com_connected': False})

    def on_usb_scan(self, event):
        code = self.usb_code_var.get().strip()
        if code:
            
            # Send to database log API
            import threading
            threading.Thread(target=self.log_scan_event, args=(code,), daemon=True).start()

    def save_field1(self, *args):
        save_config({'scanner_panel_field1': self.field1_var.get()})
    def save_scanner_type(self):
        save_config({'scanner_panel_type': self.scanner_type_var.get()})
