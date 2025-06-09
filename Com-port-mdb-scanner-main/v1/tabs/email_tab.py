import tkinter as tk
from tkinter import ttk
import os
import json
from config_utils import update_config, get_config_path

class EmailTab:
    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        self.build_tab()

    def build_tab(self):
        email_group = ttk.LabelFrame(self.parent, text="Email Configuratie", padding="10")
        email_group.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
        copyright_label = tk.Label(self.parent, text="© 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)

        # Load config
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
        self.mail_sender = config.get('email_sender', '')
        self.mail_receiver = config.get('email_receiver', '')
        self.smtp_server = config.get('smtp_server', '')
        self.smtp_port = int(config.get('smtp_port', 587))
        self.smtp_user = config.get('smtp_user', '')
        self.smtp_password = config.get('smtp_password', '')
        self.email_enabled_var = tk.BooleanVar(value=config.get('email_enabled', False))
        self.email_send_mode_var = tk.StringVar(value=config.get('email_send_mode', 'per_scan'))

        # Email enabled checkbox
        email_checkbox = ttk.Checkbutton(
            email_group,
            text="E-mail inschakelen",
            variable=self.email_enabled_var,
            command=self.on_email_enabled_change
        )
        email_checkbox.grid(row=0, column=0, sticky=tk.W, pady=(0, 6), columnspan=2)

        ttk.Label(email_group, text="Afzender:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.sender_var = tk.StringVar(value=self.mail_sender)
        sender_entry = ttk.Entry(email_group, textvariable=self.sender_var, width=35)
        sender_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.sender_var.trace_add('write', lambda *args: self.save_email_settings_to_config())
        ttk.Label(email_group, text="Ontvanger:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.receiver_var = tk.StringVar(value=self.mail_receiver)
        receiver_entry = ttk.Entry(email_group, textvariable=self.receiver_var, width=35)
        receiver_entry.grid(row=2, column=1, sticky=tk.W, pady=2)
        self.receiver_var.trace_add('write', lambda *args: self.save_email_settings_to_config())
        ttk.Label(email_group, text="SMTP server:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.smtp_var = tk.StringVar(value=self.smtp_server)
        smtp_entry = ttk.Entry(email_group, textvariable=self.smtp_var, width=35)
        smtp_entry.grid(row=3, column=1, sticky=tk.W, pady=2)
        self.smtp_var.trace_add('write', lambda *args: self.save_email_settings_to_config())
        ttk.Label(email_group, text="SMTP poort:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.port_var = tk.StringVar(value=str(self.smtp_port))
        port_entry = ttk.Entry(email_group, textvariable=self.port_var, width=10)
        port_entry.grid(row=4, column=1, sticky=tk.W, pady=2)
        self.port_var.trace_add('write', lambda *args: self.save_email_settings_to_config())
        ttk.Label(email_group, text="SMTP gebruiker:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.user_var = tk.StringVar(value=self.smtp_user)
        user_entry = ttk.Entry(email_group, textvariable=self.user_var, width=35)
        user_entry.grid(row=5, column=1, sticky=tk.W, pady=2)
        self.user_var.trace_add('write', lambda *args: self.save_email_settings_to_config())
        ttk.Label(email_group, text="SMTP wachtwoord:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.password_var = tk.StringVar(value=self.smtp_password)
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
        self.email_send_mode_combobox.bind("<<ComboboxSelected>>", lambda e: self.on_email_mode_select(mode_value_map, mode_display_map))
        self.email_send_mode_var.trace_add('write', lambda *args: self.sync_combobox_to_var(mode_display_map, mode_display_names))

        # Store widgets for enabling/disabling
        self._email_widgets = [sender_entry, receiver_entry, smtp_entry, port_entry, user_entry, password_entry, test_btn]
        self.update_email_widget_state()

    def on_email_enabled_change(self):
        enabled = self.email_enabled_var.get()
        self.update_email_widget_state()
        self.save_email_settings_to_config()

    def update_email_widget_state(self):
        state = "normal" if self.email_enabled_var.get() else "disabled"
        for widget in getattr(self, '_email_widgets', []):
            widget.config(state=state)

    def on_email_mode_select(self, mode_value_map, mode_display_map):
        display = self.email_send_mode_combobox.get()
        value = mode_value_map.get(display, "per_scan")
        self.email_send_mode_var.set(value)
        self.save_email_settings_to_config()

    def sync_combobox_to_var(self, mode_display_map, mode_display_names):
        v = self.email_send_mode_var.get()
        self.email_send_mode_combobox.set(mode_display_map.get(v, mode_display_names[0]))

    def save_email_settings_to_config(self):
        updates = {
            'email_sender': self.sender_var.get(),
            'email_receiver': self.receiver_var.get(),
            'smtp_server': self.smtp_var.get(),
            'smtp_port': self.port_var.get(),
            'smtp_user': self.user_var.get(),
            'smtp_password': self.password_var.get(),
            'email_enabled': self.email_enabled_var.get(),
            'email_send_mode': self.email_send_mode_var.get(),
        }
        update_config(updates)

    def send_test_email(self):
        # Placeholder for sending a test email. Integrate with main_app if needed.
        if hasattr(self.main_app, 'send_log_via_email'):
            self.main_app.send_log_via_email(test=True)
        else:
            messagebox.showinfo("Testmail", "Testmail verzenden is niet geconfigureerd.")
