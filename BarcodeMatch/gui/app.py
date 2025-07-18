import os
import sys
import time

# Debug mode check
DEBUG = os.environ.get('BARCODEMATCH_DEBUG', '').lower() == 'true'
if DEBUG:
    print(f'[DIAG] app.py starting import {time.time()}')

import tkinter as tk
from tkinter import ttk
from gui.panels.import_panel import ImportPanel
from gui.panels.scanner_panel import ScannerPanel
from gui.panels.email_panel import EmailPanel
from gui.panels.database_panel import DatabasePanel
from gui.panels.help_panel import HelpPanel
from gui.panels.settings_panel import SettingsPanel
from gui.menu import create_menu
from gui.asset_utils import get_asset_path, asset_exists

import threading
import time
import json
from config_utils import get_config_path, load_config

class BarcodeMatchApp:
    def __init__(self, root, skip_preload=False):
        self.root = root
        self.root.title("BarcodeMatch")
        self._set_icon()
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        self.db_connection_status = "Niet verbonden"
        self.db_connection_status_color = "red"
        self._db_status_callbacks = []

        # Initialize panels lazily - only create when needed
        self.panels = {}
        self._panel_classes = {
            "Import": ImportPanel,
            "Scanner": ScannerPanel,
            "Email": EmailPanel,
            "Database": DatabasePanel,
            "Help": HelpPanel,
            "Settings": SettingsPanel,
        }
        
        self.current_panel_name = None
        
        # Create menu and start background services
        create_menu(self.root, self)
        self._start_db_connection_check()
        
        # Pre-load critical panels in background
        if not skip_preload:
            self._preload_critical_panels()

        self.notebook = None

    def _preload_critical_panels(self):
        """Pre-load critical panels in background thread"""
        def preload():
            try:
                # Pre-load Scanner panel as it's most commonly used
                if DEBUG:
                    print('[DIAG] Pre-loading Scanner panel...')
                self.get_panel_by_name("Scanner")
                if DEBUG:
                    print('[DIAG] Scanner panel pre-loaded')
                
                # Pre-load Database panel for connection status
                if DEBUG:
                    print('[DIAG] Pre-loading Database panel...')
                db_panel = self.get_panel_by_name("Database")
                if db_panel:
                    # Subscribe the database panel to status updates
                    self.subscribe_db_status(db_panel.update_connection_status)
                if DEBUG:
                    print('[DIAG] Database panel pre-loaded')
            except Exception as e:
                print(f'[DIAG ERROR] Panel pre-loading failed: {e}')
        
        threading.Thread(target=preload, daemon=True).start()

    def get_panel_by_name(self, name):
        """Get panel by name, creating it lazily if needed"""
        if name not in self.panels:
            if name in self._panel_classes:
                if DEBUG:
                    print(f'[DIAG] Creating panel: {name}')
                try:
                    panel_class = self._panel_classes[name]
                    panel = panel_class(self.root, self)
                    self.panels[name] = panel
                    
                    # If this is the Database panel, subscribe it to status updates
                    if name == "Database" and hasattr(panel, 'update_connection_status'):
                        self.subscribe_db_status(panel.update_connection_status)
                        # Send current status immediately
                        panel.update_connection_status(self.db_connection_status, self.db_connection_status_color)
                    
                    if DEBUG:
                        print(f'[DIAG] Panel created successfully: {name}')
                except Exception as e:
                    print(f'[DIAG ERROR] Failed to create panel {name}: {e}')
                    return None
            else:
                print(f'[DIAG ERROR] Unknown panel name: {name}')
                return None
        
        return self.panels.get(name)

    def subscribe_db_status(self, callback):
        """Subscribe to database status updates"""
        if callback not in self._db_status_callbacks:
            self._db_status_callbacks.append(callback)
            if DEBUG:
                print(f'[DB STATUS] Subscribed callback: {callback}')

    def _notify_db_status(self):
        """Notify all subscribers of database status changes"""
        if DEBUG:
            print(f'[DB STATUS] Notifying {len(self._db_status_callbacks)} callbacks of status: {self.db_connection_status}')
        for cb in self._db_status_callbacks:
            try:
                cb(self.db_connection_status, self.db_connection_status_color)
            except Exception as e:
                print(f'[DB STATUS ERROR] Callback failed: {e}')

    def _start_db_connection_check(self):
        """Start database connection checking"""
        def check():
            config = load_config()
            if not config.get('database_enabled', True):
                if DEBUG:
                    print('[DB CHECK] Database disabled in config.')
                self._set_db_status("Uitgeschakeld", "orange")
                return
            
            url = config.get('api_url', 'http://localhost:5001/log')
            # Robustly replace only the trailing '/log' with '/logs'
            if url.endswith('/log'):
                url = url[:-4] + '/logs'
            elif not url.endswith('/logs'):
                url = url.rstrip('/') + '/logs'
            
            if DEBUG:
                print(f'[DB CHECK] Checking database connection at: {url}')
            try:
                import requests
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    try:
                        # Optionally check if response is valid JSON (list of logs)
                        data = resp.json()
                        if isinstance(data, list):
                            if DEBUG:
                                print('[DB CHECK] Connection successful, valid logs received.')
                            self._set_db_status("Verbonden", "green")
                        else:
                            if DEBUG:
                                print(f'[DB CHECK] Connection OK but unexpected response: {data}')
                            self._set_db_status("Verbonden", "green")
                    except Exception as e:
                        if DEBUG:
                            print(f'[DB CHECK] Connection OK but JSON decode failed: {e}')
                        self._set_db_status("Verbonden", "green")
                else:
                    if DEBUG:
                        print(f'[DB CHECK] Connection failed, status: {resp.status_code}, body: {resp.text}')
                    self._set_db_status("Niet verbonden", "red")
            except Exception as e:
                if DEBUG:
                    print(f'[DB CHECK] Exception during GET: {e}')
                self._set_db_status("Niet verbonden", "red")
        
        threading.Thread(target=check, daemon=True).start()

    def recheck_db_connection(self):
        """Public method for panels to trigger a database connection recheck."""
        if DEBUG:
            print('[DB CHECK] Manual recheck requested')
        self._start_db_connection_check()

    def _set_db_status(self, status, color):
        """Set database status and notify subscribers"""
        def update():
            old_status = self.db_connection_status
            self.db_connection_status = status
            self.db_connection_status_color = color
            if DEBUG:
                print(f'[DB STATUS] Status changed from "{old_status}" to "{status}" ({color})')
            self._notify_db_status()
        self.root.after(0, update)

    def _load_tab_images(self):
        # Load images for tabs from assets
        from PIL import Image, ImageTk
        asset_dir = get_assets_dir()
        tab_icon_files = {
            "Import": "importeren.png",
            "Scanner": "scanner.png",
            "Email": "email.png",
            "Database": "database.png",
            "Help": "help.png",
            "Settings": "settings.png"
        }
        self.tab_images = {}
        for name, filename in tab_icon_files.items():
            if asset_exists(filename):
                try:
                    img = Image.open(get_asset_path(filename))
                    img = img.resize((20, 20), Image.LANCZOS)
                    self.tab_images[name] = ImageTk.PhotoImage(img)
                except Exception:
                    self.tab_images[name] = None
            else:
                self.tab_images[name] = None

    def load_app_config(self):
        """Loads the application configuration."""
        try:
            # Use the current config system to get the configuration
            return load_config()
        except Exception as e:
            print(f"[ERROR] Could not load app config: {e}")
            return {}

    def switch_to_scanner_and_load(self, excel_file_path):
        """Switches to the Scanner panel and loads the specified Excel file."""
        try:
            if DEBUG:
                print(f"[SWITCH] Attempting to switch to Scanner and load: {excel_file_path}")
            
            scanner_panel = self.get_panel_by_name("Scanner")
            if not scanner_panel:
                from tkinter import messagebox
                messagebox.showerror("Fout", "Scanner paneel kon niet worden geladen.")
                return
            
            # Use the menu-based system to switch to Scanner panel
            from gui.menu import MENU_OPTIONS
            scanner_index = None
            for idx, opt in enumerate(MENU_OPTIONS):
                if opt["name"] == "Scanner":
                    scanner_index = idx
                    break
            
            if scanner_index is not None:
                # Hide current panel if exists
                if hasattr(self.root, '_active_panel') and self.root._active_panel is not None:
                    if DEBUG:
                        print(f"[SWITCH] Hiding current panel: {type(self.root._active_panel).__name__}")
                    self.root._active_panel.pack_forget()
                
                # Show Scanner panel
                self.root._active_panel = scanner_panel
                if DEBUG:
                    print(f"[SWITCH] Showing Scanner panel")
                scanner_panel.pack(fill=tk.BOTH, expand=True)
                
                # Update tab state if the menu system is initialized
                if hasattr(self.root, 'active_tab'):
                    self.root.active_tab.set(scanner_index)
                
                # Update button appearances if they exist
                if hasattr(self.root, '_tab_buttons') and hasattr(self.root, '_tab_frames'):
                    MENU_BG = "#f0f0f0"
                    for idx, (btn, frame) in enumerate(zip(self.root._tab_buttons, self.root._tab_frames)):
                        if idx == scanner_index:
                            frame.config(bg=MENU_BG, highlightbackground=MENU_BG, highlightcolor=MENU_BG, highlightthickness=0)
                            btn.config(bg="#d0e0ff", relief=tk.FLAT)
                        else:
                            frame.config(bg=MENU_BG, highlightbackground=MENU_BG, highlightcolor=MENU_BG, highlightthickness=0)
                            btn.config(bg=MENU_BG, relief=tk.FLAT)
                
                if DEBUG:
                    print(f"[SWITCH] Tab switching completed, now loading Excel file")
            else:
                print("[WARN] Could not find Scanner in menu options.")
            
            # Load the Excel file
            scanner_panel.load_project_excel(excel_file_path)
            if DEBUG:
                print(f"[SWITCH] Successfully switched to Scanner and loaded: {excel_file_path}")
            
        except Exception as e:
            print(f"[SWITCH ERROR] Failed to switch to scanner and load file: {e}")
            from tkinter import messagebox
            messagebox.showerror("Fout", f"Kon niet overschakelen naar scanner paneel: {e}")

    def _set_icon(self):
        ico_ico_path = get_asset_path('ico.ico')
        ico_png_path = get_asset_path('ico.png')
        
        if DEBUG:
            print(f'[ICON DIAG] ico.ico path: {ico_ico_path} exists: {os.path.exists(ico_ico_path)}')
            print(f'[ICON DIAG] ico.png path: {ico_png_path} exists: {os.path.exists(ico_png_path)}')
        
        icon_set = False
        if os.path.exists(ico_ico_path):
            try:
                self.root.iconbitmap(ico_ico_path)
                icon_set = True
                if DEBUG:
                    print('[ICON DIAG] iconbitmap succeeded')
            except Exception as e:
                if DEBUG:
                    print(f'[ICON DIAG] iconbitmap failed: {e}')
        
        if not icon_set and os.path.exists(ico_png_path):
            try:
                self.root.iconphoto(True, tk.PhotoImage(file=ico_png_path))
                icon_set = True
                if DEBUG:
                    print('[ICON DIAG] iconphoto succeeded')
            except Exception as e:
                if DEBUG:
                    print(f'[ICON DIAG] iconphoto failed: {e}')
        
        if not icon_set and DEBUG:
            print("No valid icon found.")

    def _init_tabs(self):
        panels = [
            ("Import", ImportPanel),
            ("Scanner", ScannerPanel),
            ("Email", EmailPanel),
            ("Database", DatabasePanel),
            ("Help", HelpPanel)
        ]
        for idx, (name, PanelClass) in enumerate(panels):
            frame = ttk.Frame(self.notebook)
            # Add tab with image and text if image is available
            if self.tab_images.get(name):
                self.notebook.add(frame, text=name, image=self.tab_images[name], compound="left")
            else:
                self.notebook.add(frame, text=name)
            try:
                if DEBUG:
                    print(f'[DIAG] Creating panel for tab: {name} using {PanelClass}')
                panel = PanelClass(frame, self)
                if DEBUG:
                    print(f'[DIAG] Panel created for tab: {name}')
                panel.pack(fill=tk.BOTH, expand=True)
                self.tab_instances[name] = panel
            except Exception as e:
                print(f'[DIAG ERROR] Failed to create panel for tab {name}: {e}')


def run_app():
    if DEBUG:
        print('[DIAG] run_app() called')
    root = tk.Tk()
    root.withdraw()  # Hide main window for splash
    
    from gui.splashscreen import SplashScreen
    logo_path = get_asset_path('Logo.png')
    splash = SplashScreen(root, logo_path, duration=2000) # Set duration to 2 seconds

    # Force the splash screen to draw immediately
    splash.update_idletasks()
    splash.update()

    # This function will run in the background to initialize the app
    def background_init():
        """Initialize the application in a background thread."""
        try:
            if DEBUG:
                print('[DIAG] Background initialization started')
            # Create the app instance. Its own __init__ will start background tasks.
            BarcodeMatchApp(root)
            if DEBUG:
                print('[DIAG] Background initialization completed')
        except Exception as e:
            print(f'[DIAG ERROR] Background initialization failed: {e}')
            import traceback
            traceback.print_exc()

    # Start the background initialization
    init_thread = threading.Thread(target=background_init, daemon=True)
    init_thread.start()

    # This function will run after the 2-second splash duration
    def show_main_window():
        splash.destroy()
        root.deiconify()

    # Schedule the main window to appear after 2 seconds
    root.after(2000, show_main_window)
    
    root.mainloop()
    if DEBUG:
        print('[DIAG] mainloop exited')


if __name__ == "__main__":
    if DEBUG:
        print('[DIAG] __main__ entry, calling run_app()')
    run_app()