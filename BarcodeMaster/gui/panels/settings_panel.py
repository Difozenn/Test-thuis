import tkinter as tk
from tkinter import ttk

from config_utils import get_config, save_config
# from services.background_import_service import BackgroundImportService # For type hinting

class Tooltip:
    """ Simple tooltip class for tkinter widgets. """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

class SettingsPanel(tk.Frame):
    """Simplified settings panel for BarcodeMaster to manage the master background import service toggle."""
    
    def __init__(self, parent, app=None, background_service_instance=None):
        super().__init__(parent, bg="#f0f0f0")
        self.app = app
        self.background_service = background_service_instance
        
        if self.background_service is None:
            # This should ideally not happen if the main app manages service injection properly.
            print("CRITICAL ERROR: SettingsPanel did not receive a BackgroundImportService instance!")
            # Consider raising an exception or displaying an error in the UI if this is critical.

        # self.master_service_active_var = tk.BooleanVar() # Removed
    
        self._setup_ui()
        # self.load_config() # No config to load in this simplified panel anymore 
        
    def _setup_ui(self):
        """Setup the user interface for the SettingsPanel."""
        # Since the master toggle is removed, this panel is currently minimal.
        # We can add a label to inform the user.
        info_label = tk.Label(
            self,
            text="Alle configuraties voor automatische import (per gebruiker)\nworden nu beheerd via het Scanner Paneel.",
            bg="#f0f0f0",
            fg="#333333",
            pady=20,
            font=("tahoma", "10")
        )
        info_label.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
    def load_config(self):
        """Load configuration for the SettingsPanel. Currently no specific settings here."""
        # No configuration specific to this panel anymore after removing master toggle.
        pass

    def save_config(self):
        """Save configuration for the SettingsPanel. Currently no specific settings here."""
        # No configuration specific to this panel anymore.
        pass

    # _on_toggle_master_service removed as the toggle is gone.

    def shutdown(self):
        """Perform any cleanup for the settings panel. Currently, none needed."""
        # This panel no longer runs 'after' jobs that need cancelling.
        # The BackgroundImportService is managed by the MainApp for shutdown.
        pass
