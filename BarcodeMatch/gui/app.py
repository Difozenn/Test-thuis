import time
print(f'[DIAG] app.py starting import {time.time()}')
import tkinter as tk
from tkinter import ttk
from gui.panels.import_panel import ImportPanel
from gui.panels.scanner_panel import ScannerPanel
from gui.panels.email_panel import EmailPanel
from gui.panels.database_panel import DatabasePanel
from gui.panels.help_panel import HelpPanel
from gui.panels.settings_panel import SettingsPanel
import os

from gui.menu import create_menu

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

    def _preload_critical_panels(self):
        """Pre-load critical panels in background thread"""
        def preload():
            try:
                # Pre-load Scanner panel as it's most commonly used
                print('[DIAG] Pre-loading Scanner panel...')
                self.get_panel_by_name("Scanner")
                print('[DIAG] Scanner panel pre-loaded')
                
                # Pre-load Database panel for connection status
                print('[DIAG] Pre-loading Database panel...')
                self.get_panel_by_name("Database")
                print('[DIAG] Database panel pre-loaded')
            except Exception as e:
                print(f'[DIAG ERROR] Panel pre-loading failed: {e}')
        
        threading.Thread(target=preload, daemon=True).start()

    def get_panel_by_name(self, name):
        """Get panel by name, creating it lazily if needed"""
        if name not in self.panels:
            if name in self._panel_classes:
                print(f'[DIAG] Creating panel: {name}')
                try:
                    panel_class = self._panel_classes[name]
                    self.panels[name] = panel_class(self.root, self)
                    print(f'[DIAG] Panel created successfully: {name}')
                except Exception as e:
                    print(f'[DIAG ERROR] Failed to create panel {name}: {e}')
                    return None
            else:
                print(f'[DIAG ERROR] Unknown panel name: {name}')
                return None
        return self.panels.get(name)

    def subscribe_db_status(self, callback):
        self._db_status_callbacks.append(callback)

    def _notify_db_status(self):
        for cb in self._db_status_callbacks:
            try:
                cb(self.db_connection_status, self.db_connection_status_color)
            except Exception:
                pass

    def _start_db_connection_check(self):
        def check():
            config = load_config()
            if not config.get('database_enabled', True):
                print('[DB CHECK] Database disabled in config.')
                self._set_db_status("Niet verbonden", "red")
                return
            url = config.get('api_url', 'http://localhost:5001/log')
            # Robustly replace only the trailing '/log' with '/logs'
            if url.endswith('/log'):
                url = url[:-4] + '/logs'
            elif not url.endswith('/logs'):
                url = url.rstrip('/') + '/logs'
            print(f'[DB CHECK] Checking database connection at: {url}')
            try:
                import requests
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    try:
                        # Optionally check if response is valid JSON (list of logs)
                        data = resp.json()
                        if isinstance(data, list):
                            print('[DB CHECK] Connection successful, valid logs received.')
                            self._set_db_status("Verbonden", "green")
                        else:
                            print(f'[DB CHECK] Connection OK but unexpected response: {data}')
                            self._set_db_status("Verbonden", "green")
                    except Exception as e:
                        print(f'[DB CHECK] Connection OK but JSON decode failed: {e}')
                        self._set_db_status("Verbonden", "green")
                else:
                    print(f'[DB CHECK] Connection failed, status: {resp.status_code}, body: {resp.text}')
                    self._set_db_status("Niet verbonden", "red")
            except Exception as e:
                print(f'[DB CHECK] Exception during GET: {e}')
                self._set_db_status("Niet verbonden", "red")
        threading.Thread(target=check, daemon=True).start()

    def recheck_db_connection(self):
        """Public method for panels to trigger a database connection recheck."""
        self._start_db_connection_check()


    def subscribe_db_status(self, callback):
        self._db_status_callbacks.append(callback)

    def _notify_db_status(self):
        for cb in self._db_status_callbacks:
            try:
                cb(self.db_connection_status, self.db_connection_status_color)
            except Exception:
                pass

    def _start_db_connection_check(self):
        def check():
            config = load_config()
            if not config.get('database_enabled', True):
                print('[DB CHECK] Database disabled in config.')
                self._set_db_status("Niet verbonden", "red")
                return
            url = config.get('api_url', 'http://localhost:5001/log')
            # Robustly replace only the trailing '/log' with '/logs'
            if url.endswith('/log'):
                url = url[:-4] + '/logs'
            elif not url.endswith('/logs'):
                url = url.rstrip('/') + '/logs'
            print(f'[DB CHECK] Checking database connection at: {url}')
            try:
                import requests
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    try:
                        # Optionally check if response is valid JSON (list of logs)
                        data = resp.json()
                        if isinstance(data, list):
                            print('[DB CHECK] Connection successful, valid logs received.')
                            self._set_db_status("Verbonden", "green")
                        else:
                            print(f'[DB CHECK] Connection OK but unexpected response: {data}')
                            self._set_db_status("Verbonden", "green")
                    except Exception as e:
                        print(f'[DB CHECK] Connection OK but JSON decode failed: {e}')
                        self._set_db_status("Verbonden", "green")
                else:
                    print(f'[DB CHECK] Connection failed, status: {resp.status_code}, body: {resp.text}')
                    self._set_db_status("Niet verbonden", "red")
            except Exception as e:
                print(f'[DB CHECK] Exception during GET: {e}')
                self._set_db_status("Niet verbonden", "red")
        threading.Thread(target=check, daemon=True).start()


    def recheck_db_connection(self):
        """Public method for panels to trigger a database connection recheck."""
        self._start_db_connection_check()


    def _set_db_status(self, status, color):
        def update():
            self.db_connection_status = status
            self.db_connection_status_color = color
            self._notify_db_status()
        self.root.after(0, update)

    def _load_tab_images(self):
        # Load images for tabs from assets
        from PIL import Image, ImageTk
        asset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
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
            path = os.path.join(asset_dir, filename)
            if os.path.exists(path):
                try:
                    img = Image.open(path)
                    img = img.resize((20, 20), Image.ANTIALIAS)
                    self.tab_images[name] = ImageTk.PhotoImage(img)
                except Exception:
                    self.tab_images[name] = None
            else:
                self.tab_images[name] = None

    def _set_icon(self):
        ico_ico_path = os.path.join('assets', 'ico.ico')
        ico_png_path = os.path.join('assets', 'ico.png')
        print(f'[ICON DIAG] ico.ico path: {os.path.abspath(ico_ico_path)} exists: {os.path.exists(ico_ico_path)}')
        print(f'[ICON DIAG] ico.png path: {os.path.abspath(ico_png_path)} exists: {os.path.exists(ico_png_path)}')
        icon_set = False
        if os.path.exists(ico_ico_path):
            try:
                self.root.iconbitmap(ico_ico_path)
                icon_set = True
                print('[ICON DIAG] iconbitmap succeeded')
            except Exception as e:
                print(f'[ICON DIAG] iconbitmap failed: {e}')
        if not icon_set and os.path.exists(ico_png_path):
            try:
                self.root.iconphoto(True, tk.PhotoImage(file=ico_png_path))
                icon_set = True
                print('[ICON DIAG] iconphoto succeeded')
            except Exception as e:
                print(f'[ICON DIAG] iconphoto failed: {e}')
        if not icon_set:
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
                print(f'[DIAG] Creating panel for tab: {name} using {PanelClass}')
                panel = PanelClass(frame, self)
                print(f'[DIAG] Panel created for tab: {name}')
                panel.pack(fill=tk.BOTH, expand=True)
                self.tab_instances[name] = panel
            except Exception as e:
                print(f'[DIAG ERROR] Failed to create panel for tab {name}: {e}')


def run_app():
    print('[DIAG] run_app() called')
    root = tk.Tk()
    root.withdraw()  # Hide main window for splash
    
    from gui.splashscreen import SplashScreen
    import os
    logo_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'Logo.png')
    splash = SplashScreen(root, logo_path, duration=2000)

    # Force the splash screen to draw immediately
    splash.update_idletasks()
    splash.update()

    # This function will run in the background to initialize the app
    def background_init():
        """Initialize the application in a background thread."""
        try:
            print('[DIAG] Background initialization started')
            # Create the app instance. Its own __init__ will start background tasks.
            BarcodeMatchApp(root)
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
    print('[DIAG] mainloop exited')


if __name__ == "__main__":
    print('[DIAG] __main__ entry, calling run_app()')
    run_app()
