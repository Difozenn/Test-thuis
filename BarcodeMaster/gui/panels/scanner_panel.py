import tkinter as tk
from tkinter import messagebox, ttk # Added ttk and messagebox
import serial
import serial.tools.list_ports
import threading
import time # Might be useful for small delays or checks
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
        self.baud_rate_entry = tk.Entry(self.com_frame, textvariable=self.baud_rate_var, width=10)
        self.baud_rate_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
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
        self.closed_radio = tk.Radiobutton(event_frame, text="AFGEMELD", variable=self.event_type_var, value="AFGEMELD", bg="#f0f0f0", command=self.save_event_type)
        self.open_radio.pack(side='left', padx=10)
        self.closed_radio.pack(side='left', padx=10)
        self.lock_btn = tk.Button(event_frame, text="Lock", command=self.toggle_event_type_lock)
        self._lock_btn_packed = False
        # Do not pack yet; controlled by set_lock_button_visibility
        # self.lock_btn.pack(side='left', padx=10)
        # Serial port attributes
        self.ser = None
        self.is_reading = False
        self.read_thread = None

        # Apply lock state on startup
        self.apply_event_type_lock_ui()
        # Ensure correct secondary frame is visible on panel open
        self.update_frame_visibility()

        # Auto-connect if COM is selected on startup
        if self.scanner_type_var.get() == 'COM':
            self.after(100, self.connect_com) # Use self.after to ensure UI is built

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
        previous_type_was_com = (hasattr(self, '_previous_scanner_type') and self._previous_scanner_type == 'COM')
        current_type_is_com = (self.scanner_type_var.get() == 'COM')

        self.save_scanner_type()
        self.update_frame_visibility() # This shows/hides frames

        if current_type_is_com:
            self.connect_com()
        elif previous_type_was_com and not current_type_is_com: # Switched away from COM
            self.disconnect_com()
        
        self._previous_scanner_type = self.scanner_type_var.get() # Store current type for next change

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
        import re
        config = get_config()
        api_url = config.get('api_url', '').rstrip('/')

        # Extract project from code using regex
        project_code = code  # Default to full code
        match = re.search(r'_([A-Z]{2}\d+)_', code)
        if match:
            project_code = match.group(1)

        print("[ScannerPanel] log_scan_event called")
        print(f"  Code: {code}")
        print(f"  Extracted Project Code: {project_code}")
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

            # Log AFGEMELD event for current user
            data_closed = {
                'event': 'AFGEMELD',
                'details': code,
                'project': project_code,
                'user': current_user
            }
            print(f"  [OPEN LOGIC] Payload for current user (AFGEMELD): {data_closed}")
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
                    'project': project_code,
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
                print("  [SUCCESS] All OPEN/AFGEMELD events logged, setting entry to green")
                self.after(0, lambda: self.usb_entry.config(bg='#c8f7c5'))
            else:
                print("  [FAILURE] At least one OPEN/AFGEMELD event failed, setting entry to red")
                self.after(0, lambda: self.usb_entry.config(bg='#f7c5c5'))
        else:
            # Default: log for current user only
            data = {
                'event': event_type,
                'details': code,
                'project': project_code,
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
        if self.ser and self.ser.is_open:
            print("[ScannerPanel] COM port already connected.")
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
            print(f"[ScannerPanel] Verbinden met {port} op {baud_rate} baud...")
            self.ser = serial.Serial(port, baud_rate, timeout=1)
            if self.ser.is_open:
                self.com_status_label.config(text=f"Verbonden ({port})", fg="green")
                self.connect_btn.config(state=tk.DISABLED)
                self.disconnect_btn.config(state=tk.NORMAL)
                self.com_port_combo.config(state=tk.DISABLED)
                if hasattr(self, 'baud_rate_entry'):
                    self.baud_rate_entry.config(state=tk.DISABLED)

                self.is_reading = True
                self.read_thread = threading.Thread(target=self._read_com_port_loop, daemon=True)
                self.read_thread.start()
                print(f"[ScannerPanel] Verbonden met {port}. Lees thread gestart.")
                save_config({'scanner_panel_com_connected': True})
            else:
                self.com_status_label.config(text="Verbinden mislukt", fg="red")
                messagebox.showerror("COM Fout", f"Kon niet verbinden met {port}.")
                self.ser = None # Ensure ser is None if connection failed

        except serial.SerialException as e:
            print(f"[ScannerPanel] SerialException: {e}")
            self.com_status_label.config(text="Verbindfout", fg="red")
            messagebox.showerror("COM Fout", f"Fout bij verbinden met {port}:\n{e}")
            self.ser = None
        except Exception as e:
            print(f"[ScannerPanel] Algemene fout bij verbinden: {e}")
            self.com_status_label.config(text="Onbekende fout", fg="red")
            messagebox.showerror("COM Fout", f"Algemene fout: {e}")
            self.ser = None

    def disconnect_com(self):
        print("[ScannerPanel] Poging tot verbreken COM poort...")
        self.is_reading = False # Signal the reading thread to stop

        if self.read_thread and self.read_thread.is_alive():
            print("[ScannerPanel] Wachten op lees thread...")
            self.read_thread.join(timeout=2) # Wait for the thread to finish
            if self.read_thread.is_alive():
                 print("[ScannerPanel] WAARSCHUWING: Lees thread niet gestopt na timeout.")
        self.read_thread = None

        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
                print(f"[ScannerPanel] COM poort {self.ser.portstr} gesloten.")
            except Exception as e:
                print(f"[ScannerPanel] Fout bij sluiten COM poort: {e}")
        else:
            print("[ScannerPanel] COM poort was niet open of self.ser is None.")
        
        self.ser = None
        self.com_status_label.config(text="Niet verbonden", fg="red")
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        self.com_port_combo.config(state='readonly') # Or 'normal' if you allow typing
        if hasattr(self, 'baud_rate_entry'):
            self.baud_rate_entry.config(state=tk.NORMAL)
        save_config({'scanner_panel_com_connected': False})

    def _read_com_port_loop(self):
        print("[ScannerPanel] COM poort leeslus gestart.")
        try:
            while self.is_reading:
                if self.ser and self.ser.is_open and self.ser.in_waiting > 0:
                    try:
                        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            print(f"[ScannerPanel] COM Data Ontvangen: {line}")
                            # Schedule processing on main thread to avoid Tkinter issues from thread
                            self.after(0, self.process_com_data, line)
                    except serial.SerialException as se:
                        print(f"[ScannerPanel] SerialException in leeslus: {se}. Stoppen met lezen.")
                        self.is_reading = False # Stop reading on serial error
                        self.after(0, lambda: self.com_status_label.config(text="Leesfout", fg="orange"))
                        break # Exit loop
                    except Exception as e:
                        print(f"[ScannerPanel] Fout in leeslus: {e}")
                        # Potentially add a small delay to prevent tight loop on continuous errors
                        time.sleep(0.1)
                else:
                    time.sleep(0.05) # Small delay to prevent busy-waiting if no data or port closed
                if not self.is_reading: # Check again in case it was changed by disconnect_com
                    break
        except Exception as e:
            print(f"[ScannerPanel] Externe fout in _read_com_port_loop: {e}")
        finally:
            print("[ScannerPanel] COM poort leeslus beëindigd.")
            # Ensure disconnect UI updates if loop exits unexpectedly
            if self.is_reading: # If loop exited but we were supposed to be reading
                self.is_reading = False # Ensure flag is false
                self.after(0, self.disconnect_com) # Attempt a full disconnect sequence from main thread

    def process_com_data(self, data):
        """Process data received from COM port. Runs in main Tkinter thread."""
        print(f"[ScannerPanel] Verwerken van COM data: {data}")
        # Assuming the data is the barcode itself, log it
        # You might need to clear an entry field or update UI based on this data
        self.log_scan_event(data)
        # Example: if you have an entry for COM data to be displayed:
        # self.com_received_data_var.set(data)

    def on_close(self):
        """Cleanup actions when the panel is being closed or application exits."""
        print("[ScannerPanel] on_close aangeroepen.")
        self.disconnect_com()

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
