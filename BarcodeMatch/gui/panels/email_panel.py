import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
from config_utils import update_config, get_config_path

class EmailPanel(ttk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.main_app = main_app
        self._setup_ui()

    def _setup_ui(self):
        email_group = ttk.LabelFrame(self, text="Email Configuratie", padding="10")
        email_group.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
        copyright_label = tk.Label(self, text="© 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)

        config_file = get_config_path()
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                try:
                    config = json.load(f)
                except Exception:
                    config = {}
        else:
            config = {
                'email_sender': '',
                'email_receiver': '',
                'smtp_server': '',
                'smtp_port': 587,
                'smtp_user': '',
                'smtp_password': '',
                'email_enabled': False,
                'email_send_mode': 'per_scan'
            }
        self.sender_var = tk.StringVar(value=config.get('email_sender', ''))
        self.receiver_var = tk.StringVar(value=config.get('email_receiver', ''))
        self.smtp_var = tk.StringVar(value=config.get('smtp_server', ''))
        self.port_var = tk.StringVar(value=str(config.get('smtp_port', 587)))
        self.user_var = tk.StringVar(value=config.get('smtp_user', ''))
        self.password_var = tk.StringVar(value=config.get('smtp_password', ''))
        self.email_enabled_var = tk.BooleanVar(value=config.get('email_enabled', False))
        self.email_send_mode_var = tk.StringVar(value=config.get('email_send_mode', 'per_scan'))

        # Email enabled checkbox
        email_checkbox = ttk.Checkbutton(
            email_group,
            text="E-mail inschakelen",
            variable=self.email_enabled_var,
            command=self.save_email_settings_to_config
        )
        email_checkbox.grid(row=0, column=0, sticky=tk.W, pady=(0, 6), columnspan=2)

        ttk.Label(email_group, text="Afzender:").grid(row=1, column=0, sticky=tk.W, pady=2)
        sender_entry = ttk.Entry(email_group, textvariable=self.sender_var, width=35)
        sender_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.sender_var.trace_add('write', lambda *args: self.save_email_settings_to_config())

        ttk.Label(email_group, text="Ontvanger:").grid(row=2, column=0, sticky=tk.W, pady=2)
        receiver_entry = ttk.Entry(email_group, textvariable=self.receiver_var, width=35)
        receiver_entry.grid(row=2, column=1, sticky=tk.W, pady=2)
        self.receiver_var.trace_add('write', lambda *args: self.save_email_settings_to_config())

        ttk.Label(email_group, text="SMTP server:").grid(row=3, column=0, sticky=tk.W, pady=2)
        smtp_entry = ttk.Entry(email_group, textvariable=self.smtp_var, width=35)
        smtp_entry.grid(row=3, column=1, sticky=tk.W, pady=2)
        self.smtp_var.trace_add('write', lambda *args: self.save_email_settings_to_config())

        ttk.Label(email_group, text="SMTP poort:").grid(row=4, column=0, sticky=tk.W, pady=2)
        port_entry = ttk.Entry(email_group, textvariable=self.port_var, width=10)
        port_entry.grid(row=4, column=1, sticky=tk.W, pady=2)
        self.port_var.trace_add('write', lambda *args: self.save_email_settings_to_config())

        ttk.Label(email_group, text="SMTP gebruiker:").grid(row=5, column=0, sticky=tk.W, pady=2)
        user_entry = ttk.Entry(email_group, textvariable=self.user_var, width=35)
        user_entry.grid(row=5, column=1, sticky=tk.W, pady=2)
        self.user_var.trace_add('write', lambda *args: self.save_email_settings_to_config())

        ttk.Label(email_group, text="SMTP wachtwoord:").grid(row=6, column=0, sticky=tk.W, pady=2)
        password_entry = ttk.Entry(email_group, textvariable=self.password_var, show="*", width=35)
        password_entry.grid(row=6, column=1, sticky=tk.W, pady=2)
        self.password_var.trace_add('write', lambda *args: self.save_email_settings_to_config())

        test_btn = ttk.Button(email_group, text="Verzend testmail", command=self.send_test_email)
        test_btn.grid(row=7, column=0, pady=10, sticky=tk.E)

        # Email send mode dropdown (Combobox)
        send_mode_options = [
            ("Na elk project", "per_scan"),
            ("Dagelijks rapport", "daily")
        ]
        mode_display_names = [opt[0] for opt in send_mode_options]
        mode_value_map = {opt[0]: opt[1] for opt in send_mode_options}
        mode_display_map = {opt[1]: opt[0] for opt in send_mode_options}
        mode_label = ttk.Label(email_group, text="E-mail verzenden:")
        mode_label.grid(row=8, column=0, sticky=tk.W, pady=(15, 5))
        self.email_send_mode_combobox = ttk.Combobox(email_group, state="readonly", values=mode_display_names, width=25)
        current_mode = self.email_send_mode_var.get()
        self.email_send_mode_combobox.set(mode_display_map.get(current_mode, mode_display_names[0]))
        self.email_send_mode_combobox.grid(row=8, column=1, sticky=tk.W, pady=(15, 5))
        self.email_send_mode_combobox.bind("<<ComboboxSelected>>", self.on_email_mode_select)

    def save_email_settings_to_config(self):
        try:
            updates = {
                'email_sender': self.sender_var.get(),
                'email_receiver': self.receiver_var.get(),
                'smtp_server': self.smtp_var.get(),
                'smtp_port': int(self.port_var.get() or 587),
                'smtp_user': self.user_var.get(),
                'smtp_password': self.password_var.get(),
                'email_enabled': self.email_enabled_var.get(),
                'email_send_mode': self.email_send_mode_var.get()
            }
            update_config(updates)
        except Exception as e:
            print(f"Error saving email config: {e}")

    def on_email_mode_select(self, event=None):
        display_to_value = {
            "Na elk project": "per_scan",
            "Dagelijks rapport": "daily"
        }
        selected_display = self.email_send_mode_combobox.get()
        value = display_to_value.get(selected_display, "per_scan")
        self.email_send_mode_var.set(value)
        self.save_email_settings_to_config()

    def send_test_email(self):
        # Stub for sending a test email
        messagebox.showinfo("Testmail", "Testmail verzenden is niet geïmplementeerd in deze migratie.")
