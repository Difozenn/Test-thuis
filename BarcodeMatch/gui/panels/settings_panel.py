import tkinter as tk
from tkinter import ttk, filedialog
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
            {
                'id': 'open_image_on_opus_scan',
                'type': 'checkbox',
                'label': 'Afbeelding openen bij scan OPUS',
                'description': 'Opent automatisch de bijbehorende PNG afbeelding wanneer een OPUS item succesvol is gescand. De afbeelding moet dezelfde naam hebben als het gescande .HOP/.HOPS bestand maar met een .png extensie.',
                'default': False
            },
            {
                'id': 'open_stuktekening_on_scan',
                'type': 'checkbox_with_directory',
                'label': 'Stuktekening openen bij scan',
                'description': 'Opent automatisch de bijbehorende PDF stuktekening wanneer een item succesvol is gescand. Zoekt in de PDF naar de pagina met het gescande Objectnaam_Wandnaam.',
                'default': False,
                'directory_id': 'stuktekening_directory',
                'directory_default': ''
            },
            {
                'id': 'scan_highlight_viewer',
                'type': 'checkbox',
                'label': 'Scan Highlight Viewer',
                'description': 'Toont een groot pop-up venster met alle beschikbare informatie van het gescande item (Item, Omschrijving, Lengte, Breedte, Dikte, etc.).',
                'default': False
            },
            {
                'id': 'auto_update_enabled',
                'type': 'checkbox_with_directory',
                'label': 'Automatisch controleren op updates',
                'description': 'Controleert bij opstarten of er een nieuwe versie beschikbaar is op het opgegeven netwerkpad. De map moet een version.json bestand bevatten.',
                'default': False,
                'directory_id': 'update_server_path',
                'directory_default': ''
            },
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

        elif setting_def['type'] == 'directory':
            # Directory selector
            var = tk.StringVar()
            var.set(self.config.get(setting_def['id'], setting_def['default']))
            self.vars[setting_def['id']] = var

            ttk.Label(frame, text=setting_def['label'] + ":").pack(anchor='w')

            dir_frame = ttk.Frame(frame)
            dir_frame.pack(fill='x', pady=(2, 0))

            entry = ttk.Entry(dir_frame, textvariable=var, width=60)
            entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

            def browse_directory(string_var=var, setting_id=setting_def['id']):
                directory = filedialog.askdirectory(
                    title=f"Selecteer {setting_def['label']}",
                    initialdir=string_var.get() or None
                )
                if directory:
                    string_var.set(directory)
                    self._save_setting(setting_id, directory)

            browse_btn = ttk.Button(dir_frame, text="Bladeren...", command=browse_directory)
            browse_btn.pack(side='right')

            # Save on manual entry change (when focus leaves)
            entry.bind('<FocusOut>', lambda e, sid=setting_def['id'], v=var: self._save_setting(sid, v.get()))

            if 'description' in setting_def and setting_def['description']:
                ToolTip(entry, text=setting_def['description'])

        elif setting_def['type'] == 'checkbox_with_directory':
            # Checkbox with directory browser on the same line
            cb_var = tk.BooleanVar()
            cb_var.set(self.config.get(setting_def['id'], setting_def['default']))
            self.vars[setting_def['id']] = cb_var

            dir_var = tk.StringVar()
            dir_var.set(self.config.get(setting_def['directory_id'], setting_def['directory_default']))
            self.vars[setting_def['directory_id']] = dir_var

            # Checkbox on the left
            cb = ttk.Checkbutton(
                frame,
                text=setting_def['label'],
                variable=cb_var,
                command=lambda: self._save_setting(setting_def['id'], cb_var.get())
            )
            cb.pack(side='left')

            # Browse button on the right
            def browse_directory(string_var=dir_var, setting_id=setting_def['directory_id']):
                directory = filedialog.askdirectory(
                    title="Selecteer map",
                    initialdir=string_var.get() or None
                )
                if directory:
                    string_var.set(directory)
                    self._save_setting(setting_id, directory)

            browse_btn = ttk.Button(frame, text="...", command=browse_directory, width=3)
            browse_btn.pack(side='right')

            # Entry field in the middle (smaller width)
            entry = ttk.Entry(frame, textvariable=dir_var, width=35)
            entry.pack(side='right', padx=(10, 5))

            # Save on manual entry change (when focus leaves)
            entry.bind('<FocusOut>', lambda e, sid=setting_def['directory_id'], v=dir_var: self._save_setting(sid, v.get()))

            if 'description' in setting_def and setting_def['description']:
                ToolTip(cb, text=setting_def['description'])

        # Add 'elif' blocks here for other setting types like 'entry', 'dropdown', etc.

    def _save_setting(self, key, value):
        print(f"[SETTINGS] Saving '{key}' = {value}")
        update_config({key: value})
