import tkinter as tk
from config_utils import get_config, save_config

class SettingsPanel5(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="#f0f0f0")
        tk.Label(self, text="Settings Panel 5", font=("Arial", 16), bg="#f0f0f0").pack(pady=20)
        config = get_config()
        self.field1_var = tk.StringVar(value=config.get('settings_panel5_field1', ''))
        entry = tk.Entry(self, textvariable=self.field1_var)
        entry.pack(pady=10)
        self.field1_var.trace_add('write', self.save_field1)
    def save_field1(self, *args):
        save_config({'settings_panel5_field1': self.field1_var.get()})
