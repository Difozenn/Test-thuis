import tkinter as tk
from tkinter import ttk, messagebox
import logging
from PIL import Image, ImageTk
import os
import re
import json
import requests
import threading
from config_utils import get_config, save_config

PANEL_BG = "#f0f0f0"

class DatabasePanel(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=PANEL_BG)
        self.app = app
        self.config = get_config()
        self.build_panel()
        self.start_api_status_check()

    def toggle_database_enabled(self, *args):
        save_config({'database_enabled': self.database_enabled_var.get()})
        self.update_database_ui_state()

    def update_database_ui_state(self):
        enabled = self.database_enabled_var.get()
        state = "normal" if enabled else "disabled"
        def set_state_recursive(widget, state):
            if isinstance(widget, ttk.Checkbutton):
                return
            try:
                widget.config(state=state)
            except Exception:
                pass
            for child in widget.winfo_children():
                set_state_recursive(child, state)
        for child in self.config_frame.winfo_children():
            if isinstance(child, ttk.LabelFrame):
                for w in child.winfo_children():
                    set_state_recursive(w, state)
        if not enabled:
            self.connection_status_label.config(text="Niet verbonden", foreground="red")

    def build_panel(self):
        frame = tk.Frame(self, bg=PANEL_BG)
        frame.pack(fill='both', expand=True)
        # Database enabled toggle
        self.database_enabled_var = tk.BooleanVar(value=self.config.get('database_enabled', True))
        self.database_enabled_var.trace_add('write', self.toggle_database_enabled)
        self.config_frame = ttk.Frame(frame)
        self.config_frame.pack(fill='x', padx=10, pady=10)
        config_frame = ttk.LabelFrame(self.config_frame, text="API Configuratie", padding=10)
        config_frame.pack(fill='x')
        config_frame.grid_columnconfigure(0, weight=0)
        config_frame.grid_columnconfigure(1, weight=1)
        config_frame.grid_columnconfigure(2, weight=0)
        config_frame.grid_columnconfigure(3, weight=0)
        config_frame.grid_columnconfigure(4, weight=0)
        db_enable_chk = ttk.Checkbutton(config_frame, text="Database Inschakelen", variable=self.database_enabled_var)
        db_enable_chk.grid(row=0, column=0, columnspan=2, padx=(0,10), sticky=tk.W)
        self.api_url_var = tk.StringVar(value=self.config.get('api_url', 'http://localhost:5001/log'))
        self.api_url_var.trace_add('write', self.save_api_url)
        self.user_var = tk.StringVar(value=self.config.get('user', os.environ.get('USERNAME', 'user')))
        self.user_var.trace_add('write', self.save_user)
        # Lock state
        self.api_config_locked = self.config.get('database_panel_api_config_locked', False)
        self.api_lock_btn = ttk.Button(config_frame, text="Lock" if not self.api_config_locked else "Unlock", command=self.toggle_api_config_lock)
        ttk.Label(config_frame, text="API URL:").grid(row=1, column=0, sticky=tk.W, pady=(8,0))
        self.api_url_entry = ttk.Entry(config_frame, textvariable=self.api_url_var, width=40)
        self.api_url_entry.grid(row=1, column=1, sticky=tk.W)
        ttk.Label(config_frame, text="Gebruiker:").grid(row=2, column=0, sticky=tk.W)
        self.user_entry = ttk.Entry(config_frame, textvariable=self.user_var, width=18)
        self.user_entry.grid(row=2, column=1, sticky=tk.W)
        self.test_btn = ttk.Button(config_frame, text="Test verbinding", command=self.test_connection)
        self.test_btn.grid(row=3, column=0, sticky=tk.W, pady=(5,0))
        self.save_btn = ttk.Button(config_frame, text="Opslaan", command=self.save_config)
        self.save_btn.grid(row=3, column=1, sticky=tk.W, padx=(5,0), pady=(5,0))
        self.connection_status_label = ttk.Label(config_frame, text="Niet verbonden", foreground="red")
        self.connection_status_label.grid(row=3, column=2, sticky=tk.W, padx=(10,0), pady=(5,0))
        # Restore API config lock UI state on panel creation
        self.apply_api_config_lock_ui()

        self._create_lock_button()

    def _create_lock_button(self):
        self.lock_button_frame = tk.Frame(self, bg=PANEL_BG)
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
        """Shows or hides the API config lock button based on admin lock state."""
        if visible and self.winfo_exists():
            self.api_lock_btn.grid(row=0, column=3, padx=(10,0), sticky=tk.E)
        elif self.winfo_exists():
            self.api_lock_btn.grid_forget()

    def save_api_url(self, *args):
        save_config({'api_url': self.api_url_var.get()})

    def save_user(self, *args):
        save_config({'user': self.user_var.get()})

    def toggle_api_config_lock(self):
        self.api_config_locked = not self.api_config_locked
        save_config({'database_panel_api_config_locked': self.api_config_locked})
        self.apply_api_config_lock_ui()

    def apply_api_config_lock_ui(self):
        state = 'disabled' if self.api_config_locked else 'normal'
        fg = '#888888' if self.api_config_locked else 'black'
        try:
            self.api_url_entry.config(state=state, foreground=fg)
        except Exception:
            self.api_url_entry.config(state=state)
        try:
            self.user_entry.config(state=state, foreground=fg)
        except Exception:
            self.user_entry.config(state=state)
        self.test_btn.config(state=state)
        self.save_btn.config(state=state)
        self.api_lock_btn.config(text='Unlock' if self.api_config_locked else 'Lock')

    def save_config(self, *args):
        save_config({
            'api_url': self.api_url_var.get(),
            'user': self.user_var.get(),
            'database_enabled': self.database_enabled_var.get()
        })
        if self.database_enabled_var.get():
            self.test_connection()

    def test_connection(self):
        health_check_url = self._get_health_check_url()
        try:
            resp = requests.get(health_check_url, timeout=3)
            if resp.status_code == 200:
                self.set_connection_status(True)
                messagebox.showinfo("Succes", "Verbinding met API geslaagd!")
            else:
                self.set_connection_status(False, f"{resp.status_code}")
                messagebox.showerror("Fout", f"Verbinding mislukt: {resp.text}")
        except Exception as e:
            self.set_connection_status(False, str(e))
            messagebox.showerror("Fout", f"Verbinding mislukt: {e}")

    def set_connection_status(self, connected, error_reason=None):
        if connected:
            self.connection_status_label.after(0, lambda: self.connection_status_label.winfo_exists() and self.connection_status_label.config(text="Verbonden", foreground="green"))
        else:
            self.connection_status_label.after(0, lambda: self.connection_status_label.winfo_exists() and self.connection_status_label.config(text="Niet verbonden", foreground="red"))



    def log_event(self, event, details=None):
        if not self.database_enabled_var.get():
            return False
        url = self.api_url_var.get()
        user = self.user_var.get()
        try:
            resp = requests.post(url, json={"event": event, "details": details, "user": user}, timeout=5)
            if resp.status_code == 200 and resp.json().get('success'):
                return True
            else:
                messagebox.showerror("Logfout", f"Kon niet loggen naar centrale API:\n{resp.text}")
                return False
        except Exception as e:
            messagebox.showerror("Logfout", f"Kon niet loggen naar centrale API:\n{e}")
            return False

    def log_project_closed(self, project_name):
        if not self.database_enabled_var.get():
            return False
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        filename = os.path.splitext(os.path.basename(project_name))[0]
        details = f"Project {filename} gesloten op {timestamp}"
        return self.log_event("AFGEMELD", details)

    def log_test_event(self):
        if not self.database_enabled_var.get():
            messagebox.showinfo("Uitgeschakeld", "Database logging is uitgeschakeld.")
            return
        if self.log_event("test_event", "Dit is een test van REST API logging."):
            messagebox.showinfo("Gelukt", "Test event gelogd naar centrale logging API.")

    def _get_health_check_url(self):
        """Constructs the health check URL from the base API URL."""
        base_url = self.api_url_var.get().split('/log')[0]
        return f"{base_url}/logs/count"

    def start_api_status_check(self):
        """Starts the periodic API status check loop using `self.after`."""
        self._check_api_status()  # Start the first check

    def _check_api_status(self):
        """Schedules the network check and the next iteration of itself."""
        if not self.winfo_exists():
            return  # Stop the loop if the widget is destroyed

        if self.database_enabled_var.get():
            # The url parameter for _perform_network_check is now unused, so we can pass None.
            threading.Thread(target=self._perform_network_check, args=(None,), daemon=True).start()

        self.after(5000, self._check_api_status)  # Schedule the next check

    def _perform_network_check(self, url):
        """Performs the blocking network request in a background thread."""
        health_check_url = self._get_health_check_url()
        try:
            resp = requests.get(health_check_url, timeout=3)
            is_active = resp.status_code == 200
            # Schedule the UI update on the main thread
            self.after(0, self.set_connection_status, is_active)
        except Exception:
            # Schedule the UI update on the main thread
            self.after(0, self.set_connection_status, False)

    def shutdown(self):
        """Graceful shutdown method to be called on application close."""
        # The status check loop now stops automatically when the widget is destroyed,
        # so no explicit stop signal is needed.
        logging.info("[DatabasePanel] Shutdown called.")
