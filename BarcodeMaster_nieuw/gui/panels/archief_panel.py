import tkinter as tk
from tkinter import ttk, messagebox
import os
import shutil
import glob
from config_utils import get_config, save_config


class ArchiefPanel(tk.Frame):
    """
    Archief Panel - Standalone feature for archiving Excel files.

    Takes scanner input, matches it with files in a source folder,
    and moves matched files to an archive folder.

    Input isolation: Only processes scanner input when this panel is active.
    COM port is managed by scanner panel and routes data here when this panel is active.
    """

    def __init__(self, parent, app=None, **kwargs):
        super().__init__(parent, bg="#f0f0f0")
        self.app = app
        self.parent = parent

        # Load config
        self.config = get_config()

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Set up the user interface."""
        # Title
        title_label = tk.Label(self, text="Excel Archief", font=("Arial", 16, "bold"), bg="#f0f0f0")
        title_label.pack(pady=(20, 10))

        description = tk.Label(self,
            text="Scan een barcode om het bijbehorende Excel bestand te archiveren.\nCOM poort wordt gedeeld met Scanner panel.",
            font=("Arial", 10), bg="#f0f0f0", fg="gray")
        description.pack(pady=(0, 20))

        # --- USB Scanner Input ---
        scanner_frame = tk.LabelFrame(self, text="Scanner Input", bg="#f0f0f0", padx=10, pady=10)
        scanner_frame.pack(fill='x', padx=20, pady=(0, 10))

        input_frame = tk.Frame(scanner_frame, bg="#f0f0f0")
        input_frame.pack(fill='x', pady=5)

        tk.Label(input_frame, text="Scan Input:", bg="#f0f0f0").pack(side='left')
        self.usb_code_var = tk.StringVar()
        self.usb_entry = tk.Entry(input_frame, textvariable=self.usb_code_var, width=50, font=("Arial", 12))
        self.usb_entry.pack(side='left', padx=(10, 0), fill='x', expand=True)
        self.usb_entry.bind('<Return>', self._on_usb_scan)

        hint_label = tk.Label(scanner_frame,
            text="USB scanner: typ/scan hier | COM scanner: verbind via Scanner panel",
            font=("Arial", 9, "italic"), fg="gray", bg="#f0f0f0")
        hint_label.pack(anchor='w', pady=(5, 0))

        # --- Activity Log ---
        log_frame = tk.LabelFrame(self, text="Activiteitenlog", bg="#f0f0f0", padx=10, pady=5)
        log_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Log text widget with scrollbar
        log_scroll = tk.Scrollbar(log_frame)
        log_scroll.pack(side='right', fill='y')

        self.log_text = tk.Text(log_frame, height=15, bg="white", fg="black",
                                state='disabled', wrap=tk.WORD, yscrollcommand=log_scroll.set)
        self.log_text.pack(fill='both', expand=True)
        log_scroll.config(command=self.log_text.yview)

        # Configure log tags for coloring
        self.log_text.tag_configure('success', foreground='green')
        self.log_text.tag_configure('error', foreground='red')
        self.log_text.tag_configure('warning', foreground='orange')
        self.log_text.tag_configure('info', foreground='blue')

        # Clear log button
        clear_btn = tk.Button(log_frame, text="Log Wissen", command=self._clear_log)
        clear_btn.pack(anchor='e', pady=(5, 0))

    def _load_settings(self):
        """Load settings from config."""
        self.config = get_config()

        # Source folder: nesting_archive_directory (same folder configured in settings panel)
        archive_base = self.config.get('nesting_archive_directory', '')
        self.source_folder = archive_base

        # Archive folder: nesting_archive_directory + /ARCHIEF subfolder
        self.archive_folder = os.path.join(archive_base, "ARCHIEF") if archive_base else ''

        # Archive mode: copy or move
        self.archive_mode = self.config.get('nesting_archive_mode', 'move')

    def receive_com_data(self, data):
        """Receive COM port data routed from scanner panel."""
        # Strip prefix before and including ';' (e.g. "4554656561;projectname" -> "projectname")
        if ';' in data:
            data = data.split(';', 1)[1]
        print(f"[ArchiefPanel] Received COM data: {data}")
        self._process_scan(data)

    def _on_usb_scan(self, event):
        """Handle USB scanner input."""
        code = self.usb_code_var.get().strip()
        # Strip prefix before and including ';' (e.g. "4554656561;projectname" -> "projectname")
        if ';' in code:
            code = code.split(';', 1)[1]
        if code:
            self.usb_code_var.set('')  # Clear input
            print(f"[ArchiefPanel] Processing USB scan: {code}")
            self._process_scan(code)

    def _process_scan(self, scanned_input):
        """Process scanned input - match and archive file."""
        import datetime

        self._log(f"Scan ontvangen: {scanned_input}", "info")

        # Reload settings to get latest config
        self._load_settings()

        # Parse the scanned input
        # Format might be: "54454546153;0116_S05559_Ecclesia_T255_Spoed_Stootbord"
        # We want the part after the semicolon for matching
        if ';' in scanned_input:
            parts = scanned_input.split(';', 1)
            match_code = parts[1].strip() if len(parts) > 1 else scanned_input
            self._log(f"Match code: {match_code}", "info")
        else:
            match_code = scanned_input

        # Get source and archive folders
        source_folder = self.source_folder
        archive_folder = self.archive_folder

        if not source_folder:
            self._log("Bron map niet geconfigureerd! (NESTING pad in instellingen)", "error")
            return

        if not archive_folder:
            self._log("Archief map niet geconfigureerd! (Settings > Excel Archive Options)", "error")
            return

        if not os.path.isdir(source_folder):
            self._log(f"Bron map niet toegankelijk: {source_folder}", "error")
            return

        # Create archive folder if it doesn't exist
        if not os.path.exists(archive_folder):
            try:
                os.makedirs(archive_folder)
                self._log(f"Archief map aangemaakt: {archive_folder}", "info")
            except Exception as e:
                self._log(f"Kan archief map niet aanmaken: {e}", "error")
                return

        # Search for matching files (.xls and .xlsx only)
        matched_files = []

        try:
            for ext in ['*.xls', '*.xlsx']:
                pattern = os.path.join(source_folder, ext)
                for filepath in glob.glob(pattern):
                    filename = os.path.basename(filepath)
                    # Partial match - filename contains the match code
                    if match_code.lower() in filename.lower():
                        matched_files.append(filepath)
        except Exception as e:
            self._log(f"Fout bij zoeken naar bestanden: {e}", "error")
            return

        if not matched_files:
            self._log(f"Geen bestanden gevonden voor: {match_code}", "warning")
            return

        # Archive matched files (copy or move based on settings)
        archived_count = 0
        for filepath in matched_files:
            original_filename = os.path.basename(filepath)

            # Generate archive filename with timestamp (same format as background_import_service)
            date_stamp = datetime.datetime.now().strftime("%Y%m%d")
            time_stamp = datetime.datetime.now().strftime("%H%M%S")
            base_name, ext = os.path.splitext(original_filename)
            archive_filename = f"{base_name}_{date_stamp}_{time_stamp}{ext}"
            dest_path = os.path.join(archive_folder, archive_filename)

            try:
                if self.archive_mode == 'move':
                    shutil.move(filepath, dest_path)
                    self._log(f"Verplaatst: {original_filename}", "success")
                else:
                    shutil.copy2(filepath, dest_path)
                    self._log(f"Gekopieerd: {original_filename}", "success")

                archived_count += 1

            except Exception as e:
                self._log(f"Fout bij archiveren {original_filename}: {e}", "error")

        if archived_count > 0:
            mode_text = "verplaatst" if self.archive_mode == 'move' else "gekopieerd"
            self._log(f"Totaal {archived_count} bestand(en) {mode_text} naar archief", "success")

    def _log(self, message, level="info"):
        """Add a message to the log."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        self.log_text.config(state='normal')

        tag = level if level in ['success', 'error', 'warning', 'info'] else 'info'
        self.log_text.insert('end', f"[{timestamp}] {message}\n", tag)

        self.log_text.see('end')
        self.log_text.config(state='disabled')

        # Also print to console for debugging
        print(f"[ArchiefPanel] [{level.upper()}] {message}")

    def _clear_log(self):
        """Clear the activity log."""
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.config(state='disabled')

    def shutdown(self):
        """Clean up resources on panel/app shutdown."""
        print("[ArchiefPanel] Shutdown called")

    def on_panel_activated(self):
        """Called when this panel becomes the active panel."""
        print("[ArchiefPanel] Panel activated")
        # Focus the USB entry for keyboard input
        self.usb_entry.focus_set()

    def on_panel_deactivated(self):
        """Called when this panel is no longer the active panel."""
        print("[ArchiefPanel] Panel deactivated")
