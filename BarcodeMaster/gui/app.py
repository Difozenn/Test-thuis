import tkinter as tk
from PIL import Image, ImageTk
import os
import psutil
import requests
from services.background_import_service import BackgroundImportService
from BarcodeMaster.gui.panels.scanner_panel import ScannerPanel
from BarcodeMaster.gui.panels.database_panel import DatabasePanel
from BarcodeMaster.gui.panels.help_panel import HelpPanel
from BarcodeMaster.gui.panels.admin_panel import AdminPanel
from BarcodeMaster.gui.panels.settings_panel import SettingsPanel
# from .panels.settings_panel5 import SettingsPanel5  # Temporarily hidden

MENU_BG = "#f0f0f0"
PANEL_BG = "#f0f0f0"

class ServiceStatus:
    """A simple wrapper to hold the shared services dictionary."""
    def __init__(self):
        self.services = {}

class MainApp(tk.Frame):
    def __init__(self, parent, service_status=None):
        super().__init__(parent)
        self.parent = parent
        # If no status object is passed, create a new one.
        # This ensures self.service_status is never None.
        self.service_status = service_status or ServiceStatus()
        self.parent.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.parent.title("BarcodeMaster")
        self.parent.geometry("800x600")
        # Set window icon if available
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "ico.png")
        if os.path.exists(icon_path):
            try:
                self.parent.iconphoto(True, ImageTk.PhotoImage(file=icon_path))
            except Exception:
                pass
        # Load icons
        db_icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'database.png')
        pil_img_db = Image.open(db_icon_path).resize((75, 75), Image.LANCZOS)
        icon_db = ImageTk.PhotoImage(pil_img_db)
        help_icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "help.png")
        pil_img_help = Image.open(help_icon_path).resize((75, 75), Image.LANCZOS)
        icon_help = ImageTk.PhotoImage(pil_img_help)
        admin_icon_path = os.path.join(os.path.dirname(__file__), '../assets/admin.png')
        pil_img_admin = Image.open(admin_icon_path).resize((75, 75), Image.LANCZOS)
        icon_admin = ImageTk.PhotoImage(pil_img_admin)
        
        settings_icon_path = os.path.join(os.path.dirname(__file__), '../assets/settings.png')
        pil_img_settings = Image.open(settings_icon_path).resize((75, 75), Image.LANCZOS)
        icon_settings = ImageTk.PhotoImage(pil_img_settings)
        
        scanner_icon_path = os.path.join(os.path.dirname(__file__), '../assets/scanner.png')
        if os.path.exists(scanner_icon_path):
            pil_img_scanner = Image.open(scanner_icon_path).resize((75, 75), Image.LANCZOS)
            icon_scanner = ImageTk.PhotoImage(pil_img_scanner)
        else:
            icon_scanner = icon_db
        self.tab_icons = [icon_scanner, icon_db, icon_help, icon_admin, icon_settings]  # Added settings icon
        self.panels = [
            ScannerPanel,
            DatabasePanel,
            HelpPanel,
            AdminPanel,
            SettingsPanel
            # SettingsPanel5  # Temporarily hidden
        ]
        self.panel_names = ["Panel 1", "Database", "Help", "Panel 4", "Instellingen"]  # Added settings name
        # --- Custom Menu Bar ---
        self.menu_frame = tk.Frame(self, bg=MENU_BG, height=75)
        self.menu_frame.pack(side=tk.TOP, fill=tk.X, padx=(5, 0))
        self.menu_frame.pack_propagate(False)
        self.tab_buttons = []
        self.button_frames = []
        for i, icon in enumerate(self.tab_icons):
            frame = tk.Frame(self.menu_frame, width=75, height=75, bg=MENU_BG, highlightthickness=0)
            frame.pack_propagate(False)
            frame.pack(side=tk.LEFT, padx=0, pady=0)
            btn = tk.Button(frame, image=icon, width=75, height=75, bg=MENU_BG, relief=tk.FLAT, bd=0, highlightthickness=0, activebackground="#d0e0ff", command=lambda idx=i: self.switch_panel(idx))
            btn.pack(expand=True, fill=tk.BOTH, padx=0, pady=0)
            self.tab_buttons.append(btn)
            self.button_frames.append(frame)
        # --- Content Area ---
        self.content_frame = tk.Frame(self, bg=PANEL_BG)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.active_panel_idx = None
        self.active_panel = None
        self._admin_unlocked = False 
        self.admin_config_locked_var = tk.BooleanVar(value=True) 
        self.panel_instances = []

        # Instantiate shared BackgroundImportService
        # Assuming self.log_to_status_bar exists and is a suitable callback for the service.
        # If not, this can be None or a more generic logger from the app.
        self.background_import_service = BackgroundImportService(log_callback=self.log_to_status_bar if hasattr(self, 'log_to_status_bar') else None)

        # Window focus tracking
        self.window_has_focus = tk.BooleanVar(value=True) # Assume focus on startup
        self.parent.bind("<FocusIn>", self._on_focus_in)
        self.parent.bind("<FocusOut>", self._on_focus_out)

        # Create all panel instances once to preserve state
        for panel_cls in self.panels:
            if panel_cls == ScannerPanel:
                panel = panel_cls(self.content_frame, app=self, app_has_focus_var=self.window_has_focus, background_service_instance=self.background_import_service)
            elif panel_cls == SettingsPanel:
                panel = panel_cls(self.content_frame, app=self, background_service_instance=self.background_import_service)
            else:
                panel = panel_cls(self.content_frame, app=self)
            self.panel_instances.append(panel)

        self.switch_panel(0) # Show the first panel

        # --- Initial database connection test on program startup ---
        from BarcodeMaster.config_utils import get_config
        config = get_config()
        if config.get('database_enabled', True):
            import threading
            print("[MainApp] Starting initial database connection test in background thread...")
            
            db_panel_instance = next((p for p in self.panel_instances if isinstance(p, DatabasePanel)), None)

            if db_panel_instance:
                def run_and_update_visible():
                    print("[MainApp] Running test_connect on stored DatabasePanel instance...")
                    result = [False, None]
                    try:
                        url = db_panel_instance.api_url_var.get()
                        user = db_panel_instance.user_var.get()
                        resp = requests.post(url, json={"event": "test_connect", "details": "Test verbinding", "user": user}, timeout=3)
                        if resp.status_code == 200 and resp.json().get('success'):
                            result[0] = True
                        else:
                            result[1] = f"HTTP {resp.status_code}"
                    except Exception as e:
                        result[1] = str(e)
                    
                    self._last_db_connection_status = tuple(result)
                    self.after(0, lambda: db_panel_instance.set_connection_status(result[0], result[1]))
                
                threading.Thread(target=run_and_update_visible, daemon=True).start()
    def switch_panel(self, idx):
        """Switches the visible panel in the content frame without destroying them."""
        # Password protection for Admin panel
        if self.panels[idx] == AdminPanel and not self._admin_unlocked:
            if not self.prompt_admin_password():
                return  # Do not switch if authentication fails
            self._admin_unlocked = True
            self.admin_config_locked_var.set(False) # UNLOCKED
            self.set_all_lock_buttons_visibility(True)
            self.set_all_config_lock_buttons_visibility(True)

        # Hide the current active panel
        if self.active_panel is not None:
            self.active_panel.pack_forget()

        # Show the new panel from the stored instances
        panel = self.panel_instances[idx]
        panel.pack(fill=tk.BOTH, expand=True)

        self.active_panel = panel
        self.active_panel_idx = idx
        self._highlight_tab(idx)

        # If switching to the DatabasePanel, sync the last known connection status
        if isinstance(panel, DatabasePanel) and hasattr(self, '_last_db_connection_status'):
            conn, err = self._last_db_connection_status
            panel.set_connection_status(conn, err)

        # Ensure the lock button visibility is correct for the newly active panel
        if hasattr(self.active_panel, 'set_lock_button_visibility'):
            self.active_panel.set_lock_button_visibility(self._admin_unlocked)

    def prompt_admin_password(self):
        import tkinter.simpledialog
        import tkinter.messagebox
        pw = tkinter.simpledialog.askstring("Admin Panel", "Enter admin password:", show='*', parent=self)
        if pw == 'sunrise':
            return True
        tkinter.messagebox.showerror("Access Denied", "Incorrect password.")
        return False

    def set_all_lock_buttons_visibility(self, visible):
        """Iterates through all panel instances and sets lock button visibility."""
        for panel in self.panel_instances:
            if hasattr(panel, 'set_lock_button_visibility'):
                panel.set_lock_button_visibility(visible)

    def set_all_config_lock_buttons_visibility(self, visible):
        """Iterates through all panel instances and sets config lock button visibility."""
        for panel in self.panel_instances:
            if hasattr(panel, 'set_config_lock_visibility'):
                panel.set_config_lock_visibility(visible)
    def _on_focus_in(self, event=None):
        if event and event.widget == self.parent: # Ensure the event is for the main window
            self.window_has_focus.set(True)
            print("[MainApp] Window focused")

    def _on_focus_out(self, event=None):
        if event and event.widget == self.parent: # Ensure the event is for the main window
            self.window_has_focus.set(False)
            print("[MainApp] Window lost focus")

    def _highlight_tab(self, idx):
        for i, (btn, frame) in enumerate(zip(self.tab_buttons, self.button_frames)):
            if i == idx:
                frame.config(bg=MENU_BG, highlightbackground=MENU_BG, highlightthickness=0)
                btn.config(bg="#d0e0ff", relief=tk.FLAT)
            else:
                frame.config(bg=MENU_BG, highlightbackground=MENU_BG, highlightthickness=0)
                btn.config(bg=MENU_BG, relief=tk.FLAT)
    def lock_admin_panel(self):
        self._admin_unlocked = False
        self.admin_config_locked_var.set(True) # LOCKED
        self.set_all_lock_buttons_visibility(False)
        self.set_all_config_lock_buttons_visibility(False)
        # Switch to default panel (index 0)
        self.switch_panel(0)

    def _on_closing(self):
        """Handle graceful shutdown of background services and the app."""
        print("[MainApp] Closing application...")

        # 1. Shutdown all panels that have a shutdown routine
        print("[MainApp] Shutting down all panels...")
        for panel in self.panel_instances:
            if hasattr(panel, 'shutdown'):
                try:
                    print(f"[MainApp] Shutting down {panel.__class__.__name__}...")
                    panel.shutdown()
                except Exception as e:
                    print(f"[MainApp] Error shutting down {panel.__class__.__name__}: {e}")

        # 2. Shutdown services that were started at boot
        if self.service_status.services:
            splitter = self.service_status.services.get('splitter')
            if splitter:
                print("[MainApp] Stopping COM splitter started at boot...")
                splitter.stop()

        # 3. Terminate all child processes started by the application
        print("[MainApp] Terminating all child processes...")
        try:
            parent = psutil.Process(os.getpid())
            children = parent.children(recursive=True)
            for child in children:
                print(f"[MainApp] Terminating child process {child.pid} ({child.name()})...")
                try:
                    child.terminate() # or child.kill()
                except psutil.NoSuchProcess:
                    pass # Process may have already terminated
            # Optional: wait for termination
            psutil.wait_procs(children, timeout=3)
        except psutil.NoSuchProcess:
            print("[MainApp] Could not find parent process to terminate children.")
        except Exception as e:
            print(f"[MainApp] Error during child process termination: {e}")

        # 4. Finally, destroy the main window to exit Tkinter mainloop
        print("[MainApp] Destroying main window...")
        self.parent.destroy()

def run(service_status, root):
    """Configures the root window and starts the application."""
    # root is the pre-created main window from main.py.
    # MainApp is now a Frame, so we create it with root as its parent.
    app = MainApp(root, service_status=service_status)
    app.pack(side="top", fill="both", expand=True)
    # The mainloop is called on the root window.
    root.mainloop()
