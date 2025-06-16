import tkinter as tk
from tkinter import ttk
from config_utils import load_config, update_config

class ToolTip:
    """
    Create a tooltip for a given widget.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        # Calculate position relative to the root window
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + 20

        # Creates a toplevel window
        self.tooltip_window = tk.Toplevel(self.widget)
        
        # Leaves only the label and removes the app window
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(self.tooltip_window, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         wraplength=400) # Wraplength for longer tooltips
        label.pack(ipadx=4, ipady=4)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None


class SettingsPanel(ttk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.main_app = main_app
        self.config = load_config()
        self.vars = {}  # To hold a reference to tk.BooleanVar, etc.

        # Define settings in a structured way for easy future expansion
        self.settings_definitions = [
            {
                'id': 'archive_on_all_ok',
                'type': 'checkbox',
                'label': 'Archiveer Excel-bestand als alle items OK zijn',
                'description': 'Verplaatst het .xlsx-bestand en het _updated.xlsx-bestand naar een "Archief" map wanneer alle barcodes zijn gescand en als OK zijn gemarkeerd.',
                'default': False
            },
            # To add more settings in the future, just add a new dictionary here
        ]

        self._setup_ui()

    def _setup_ui(self):
        # Main container frame with padding
        container = ttk.Frame(self, padding="20 20 20 20")
        container.pack(fill='both', expand=True)

        # Create UI elements for each setting defined above
        for setting in self.settings_definitions:
            self._create_setting_widget(container, setting)

    def _create_setting_widget(self, parent, setting_def):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=10)

        if setting_def['type'] == 'checkbox':
            var = tk.BooleanVar()
            var.set(self.config.get(setting_def['id'], setting_def['default']))
            self.vars[setting_def['id']] = var

            cb = ttk.Checkbutton(
                frame,
                text=setting_def['label'],
                variable=var,
                command=lambda: self._save_setting(setting_def['id'], var.get())
            )
            cb.pack(anchor='w')

            if 'description' in setting_def and setting_def['description']:
                ToolTip(cb, text=setting_def['description'])
        
        # Add 'elif' blocks here for other setting types like 'entry', 'dropdown', etc.

    def _save_setting(self, key, value):
        print(f"[SETTINGS] Saving '{key}' = {value}")
        update_config({key: value})
