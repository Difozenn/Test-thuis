import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

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
    """Settings panel for BarcodeMaster with Excel archiving options."""

    def __init__(self, parent, app=None, background_service_instance=None):
        super().__init__(parent, bg="#f0f0f0")
        self.app = app
        self.background_service = background_service_instance

        if self.background_service is None:
            # This should ideally not happen if the main app manages service injection properly.
            print("CRITICAL ERROR: SettingsPanel did not receive a BackgroundImportService instance!")
            # Consider raising an exception or displaying an error in the UI if this is critical.

        # Variables for archive settings
        self.archive_enabled_var = tk.BooleanVar()
        self.archive_directory_var = tk.StringVar()
        self.archive_mode_var = tk.StringVar(value="copy")  # "copy" or "move"

        self._setup_ui()
        self.load_config() 
        
    def _setup_ui(self):
        """Setup the user interface for the SettingsPanel."""
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title_label = tk.Label(
            main_frame,
            text="Excel Archiving Settings",
            font=("tahoma", "12", "bold"),
            fg="#333333"
        )
        title_label.pack(anchor="w", pady=(0, 10))

        # Archive settings frame
        archive_frame = ttk.LabelFrame(main_frame, text="Excel Archive Options", padding="10")
        archive_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 10))

        # Archive enabled checkbox
        self.archive_checkbox = ttk.Checkbutton(
            archive_frame,
            text="Enable Excel archiving for NESTING processing",
            variable=self.archive_enabled_var,
            command=self._on_archive_toggle
        )
        self.archive_checkbox.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        Tooltip(self.archive_checkbox, "When enabled, Excel files will be archived after successful processing")

        # Archive directory
        ttk.Label(archive_frame, text="Archive Directory:").grid(row=1, column=0, sticky="w", padx=(0, 10))

        self.archive_dir_entry = ttk.Entry(
            archive_frame,
            textvariable=self.archive_directory_var,
            width=50,
            state="disabled"
        )
        self.archive_dir_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10))

        self.browse_button = ttk.Button(
            archive_frame,
            text="Browse",
            command=self._browse_archive_directory,
            state="disabled"
        )
        self.browse_button.grid(row=1, column=2)

        # Archive mode radio buttons
        ttk.Label(archive_frame, text="Archive Mode:").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=(10, 0))

        mode_frame = ttk.Frame(archive_frame)
        mode_frame.grid(row=2, column=1, sticky="w", pady=(10, 0))

        self.copy_radio = ttk.Radiobutton(
            mode_frame,
            text="Copy (keep original)",
            variable=self.archive_mode_var,
            value="copy",
            state="disabled"
        )
        self.copy_radio.grid(row=0, column=0, padx=(0, 20))

        self.move_radio = ttk.Radiobutton(
            mode_frame,
            text="Move (delete original)",
            variable=self.archive_mode_var,
            value="move",
            state="disabled"
        )
        self.move_radio.grid(row=0, column=1)

        # Configure grid weights
        archive_frame.columnconfigure(1, weight=1)

        # Info section
        info_frame = ttk.LabelFrame(main_frame, text="Information", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))

        info_text = """Archive Functionality:
• When enabled, Excel files will be archived after successful NESTING processing
• Files are organized by date in subdirectories (YYYY-MM-DD)
• Original filename is preserved with project code and timestamp
• Choose between Copy (keep original) or Move (delete original)
• Archive happens after ALL user processing is complete
• Only applies to NESTING_PROCESSING Excel files

Other Settings:
• User-specific import configurations are managed via the Scanner Panel"""

        info_label = tk.Label(
            info_frame,
            text=info_text,
            justify="left",
            fg="#555555",
            font=("tahoma", "9")
        )
        info_label.pack(anchor="w")

        # Save button
        save_button = ttk.Button(
            main_frame,
            text="Save Settings",
            command=self.save_config
        )
        save_button.pack(pady=(15, 0))
        
    def load_config(self):
        """Load configuration for the SettingsPanel."""
        try:
            config = get_config()

            # Load archive settings
            self.archive_enabled_var.set(config.get('nesting_archive_enabled', False))
            self.archive_directory_var.set(config.get('nesting_archive_directory', ''))
            self.archive_mode_var.set(config.get('nesting_archive_mode', 'copy'))

            # Enable/disable controls based on archive enabled state
            self._update_archive_controls_state()

        except Exception as e:
            print(f"Error loading settings configuration: {e}")

    def save_config(self):
        """Save configuration for the SettingsPanel."""
        try:
            config = get_config()

            # Validate archive directory if enabled
            if self.archive_enabled_var.get():
                archive_dir = self.archive_directory_var.get()
                if not archive_dir:
                    messagebox.showerror("Error", "Please select an archive directory")
                    return
                if not os.path.exists(archive_dir):
                    # Try to create it
                    try:
                        os.makedirs(archive_dir)
                    except Exception as e:
                        messagebox.showerror("Error", f"Cannot create archive directory: {e}")
                        return

            # Save archive settings to config.json
            config['nesting_archive_enabled'] = self.archive_enabled_var.get()
            config['nesting_archive_directory'] = self.archive_directory_var.get()
            config['nesting_archive_mode'] = self.archive_mode_var.get()

            save_config(config)

            # Also save to database API so background service can access them
            try:
                import requests
                api_url = config.get('api_url', 'http://localhost:5001/log').rstrip('/')
                base_url = api_url.replace('/log', '') if api_url.endswith('/log') else api_url

                # Update settings via API
                update_data = {
                    'nesting_archive_enabled': self.archive_enabled_var.get(),
                    'nesting_archive_directory': self.archive_directory_var.get(),
                    'nesting_archive_mode': self.archive_mode_var.get()
                }

                response = requests.post(f'{base_url}/api/settings', json=update_data, timeout=5)
                if response.status_code == 200:
                    print(f"[SETTINGS] Archive settings saved to database successfully")
                else:
                    print(f"[SETTINGS] Warning: Failed to save to database API: {response.status_code}")
            except Exception as e:
                print(f"[SETTINGS] Warning: Could not save to database API: {e}")
                # Don't fail the save if database update fails

            messagebox.showinfo("Success", "Settings saved successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def _on_archive_toggle(self):
        """Handle archive checkbox toggle."""
        self._update_archive_controls_state()

    def _update_archive_controls_state(self):
        """Update the state of archive-related controls."""
        if self.archive_enabled_var.get():
            self.archive_dir_entry.config(state="normal")
            self.browse_button.config(state="normal")
            self.copy_radio.config(state="normal")
            self.move_radio.config(state="normal")
        else:
            self.archive_dir_entry.config(state="disabled")
            self.browse_button.config(state="disabled")
            self.copy_radio.config(state="disabled")
            self.move_radio.config(state="disabled")

    def _browse_archive_directory(self):
        """Browse for archive directory."""
        directory = filedialog.askdirectory(
            title="Select Archive Directory",
            initialdir=self.archive_directory_var.get() or os.getcwd()
        )
        if directory:
            self.archive_directory_var.set(directory)

    def shutdown(self):
        """Perform any cleanup for the settings panel. Currently, none needed."""
        # This panel no longer runs 'after' jobs that need cancelling.
        # The BackgroundImportService is managed by the MainApp for shutdown.
        pass
