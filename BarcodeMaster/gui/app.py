import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import os
import psutil
import requests
from services.background_import_service import BackgroundImportService
from gui.panels.scanner_panel import ScannerPanel
from gui.panels.database_panel import DatabasePanel
from gui.panels.help_panel import HelpPanel
from gui.panels.admin_panel import AdminPanel
from gui.panels.settings_panel import SettingsPanel
from path_utils import get_resource_path

MENU_BG = "#f0f0f0"
PANEL_BG = "#f0f0f0"

class ServiceStatus:
    def __init__(self):
        self.db_api_status = "Not Started"
        self.com_splitter_status = "Not Started"

def create_placeholder_image(size=(75, 75), text="?", bg_color='lightgray'):
    """Create a placeholder image when the actual image is not found."""
    img = Image.new('RGB', size, color=bg_color)
    draw = ImageDraw.Draw(img)
    # Simple text positioning
    text_x = size[0] // 3
    text_y = size[1] // 3
    draw.text((text_x, text_y), text, fill='black')
    return img

def load_image_safe(path, size=(75, 75), fallback_text="?"):
    """Safely load an image, creating a placeholder if it doesn't exist."""
    try:
        if os.path.exists(path):
            pil_img = Image.open(path).resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(pil_img)
        else:
            print(f"Image not found: {path}")
    except Exception as e:
        print(f"Failed to load image {path}: {e}")
    
    # Create placeholder image
    placeholder = create_placeholder_image(size, fallback_text)
    return ImageTk.PhotoImage(placeholder)

class MainApp(tk.Frame):
    def __init__(self, parent, service_status):
        super().__init__(parent)
        self.parent = parent
        self.service_status = service_status
        
        # Initialize instance variables first
        self.panel_instances = []
        self.active_panel_idx = None
        self.active_panel = None
        self._admin_unlocked = False 
        self.admin_config_locked_var = tk.BooleanVar(value=True)
        
        # Set up window close handler
        self.parent.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.parent.title("BarcodeMaster")
        self.parent.geometry("800x600")

        # Try to set icon
        icon_path = get_resource_path("assets/ico.ico")
        if os.path.exists(icon_path):
            try:
                self.parent.iconbitmap(icon_path)
            except Exception as e:
                print(f"Error setting icon: {e}")

        # Load all icons using safe loading
        print("Loading icons...")
        icon_scanner = load_image_safe(get_resource_path('assets/scanner.png'), fallback_text="SCAN")
        icon_db = load_image_safe(get_resource_path('assets/database.png'), fallback_text="DB")
        icon_help = load_image_safe(get_resource_path("assets/help.png"), fallback_text="HELP")
        icon_admin = load_image_safe(get_resource_path('assets/admin.png'), fallback_text="ADMIN")
        icon_settings = load_image_safe(get_resource_path('assets/settings.png'), fallback_text="SET")
        
        self.tab_icons = [icon_scanner, icon_db, icon_help, icon_admin, icon_settings]
        self.panels = [
            ScannerPanel,
            DatabasePanel,
            HelpPanel,
            AdminPanel,
            SettingsPanel
        ]
        self.panel_names = ["Scanner", "Database", "Help", "Admin", "Settings"]
        
        # Create menu frame
        self.menu_frame = tk.Frame(self, bg=MENU_BG, height=75)
        self.menu_frame.pack(side=tk.TOP, fill=tk.X, padx=(5, 0))
        self.menu_frame.pack_propagate(False)
        
        self.tab_buttons = []
        self.button_frames = []
        for i, icon in enumerate(self.tab_icons):
            frame = tk.Frame(self.menu_frame, width=75, height=75, bg=MENU_BG, highlightthickness=0)
            frame.pack_propagate(False)
            frame.pack(side=tk.LEFT, padx=0, pady=0)
            btn = tk.Button(frame, image=icon, width=75, height=75, bg=MENU_BG, relief=tk.FLAT, bd=0, 
                          highlightthickness=0, activebackground="#d0e0ff", 
                          command=lambda idx=i: self.switch_panel(idx))
            btn.image = icon  # Keep a reference
            btn.pack(expand=True, fill=tk.BOTH, padx=0, pady=0)
            self.tab_buttons.append(btn)
            self.button_frames.append(frame)

        # Create content frame
        self.content_frame = tk.Frame(self, bg=PANEL_BG)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Initialize background service
        self.background_import_service = BackgroundImportService(
            log_callback=self.log_to_status_bar if hasattr(self, 'log_to_status_bar') else None
        )

        # Window focus tracking
        self.window_has_focus = tk.BooleanVar(value=True)
        self.parent.bind("<FocusIn>", self._on_focus_in)
        self.parent.bind("<FocusOut>", self._on_focus_out)

        # Create panel instances
        try:
            for panel_cls in self.panels:
                if panel_cls == ScannerPanel:
                    panel = panel_cls(self.content_frame, app=self, 
                                    app_has_focus_var=self.window_has_focus, 
                                    background_service_instance=self.background_import_service)
                elif panel_cls == SettingsPanel:
                    panel = panel_cls(self.content_frame, app=self, 
                                    background_service_instance=self.background_import_service)
                else:
                    panel = panel_cls(self.content_frame, app=self)
                self.panel_instances.append(panel)
        except Exception as e:
            print(f"Error creating panels: {e}")
            import traceback
            traceback.print_exc()

        # Switch to first panel
        if self.panel_instances:
            self.switch_panel(0)

    def switch_panel(self, idx):
        if idx >= len(self.panel_instances):
            return
            
        if self.panels[idx] == AdminPanel and not self._admin_unlocked:
            if not self.prompt_admin_password():
                return
            self._admin_unlocked = True
            self.admin_config_locked_var.set(False)
            self.set_all_lock_buttons_visibility(True)
            self.set_all_config_lock_buttons_visibility(True)

        if self.active_panel is not None:
            self.active_panel.pack_forget()

        panel = self.panel_instances[idx]
        panel.pack(fill=tk.BOTH, expand=True)

        self.active_panel = panel
        self.active_panel_idx = idx
        self._highlight_tab(idx)

    def prompt_admin_password(self):
        import tkinter.simpledialog
        import tkinter.messagebox
        pw = tkinter.simpledialog.askstring("Admin Panel", "Enter admin password:", show='*', parent=self)
        if pw == 'sunrise':
            return True
        tkinter.messagebox.showerror("Access Denied", "Incorrect password.")
        return False

    def set_all_lock_buttons_visibility(self, visible):
        for panel in self.panel_instances:
            if hasattr(panel, 'set_lock_button_visibility'):
                try:
                    panel.set_lock_button_visibility(visible)
                except Exception as e:
                    print(f"Error setting lock button visibility: {e}")

    def set_all_config_lock_buttons_visibility(self, visible):
        for panel in self.panel_instances:
            if hasattr(panel, 'set_config_lock_visibility'):
                try:
                    panel.set_config_lock_visibility(visible)
                except Exception as e:
                    print(f"Error setting config lock visibility: {e}")

    def _on_focus_in(self, event=None):
        if event and event.widget == self.parent:
            self.window_has_focus.set(True)

    def _on_focus_out(self, event=None):
        if event and event.widget == self.parent:
            self.window_has_focus.set(False)

    def _highlight_tab(self, idx):
        for i, (btn, frame) in enumerate(zip(self.tab_buttons, self.button_frames)):
            if i == idx:
                btn.config(bg="#d0e0ff")
            else:
                btn.config(bg=MENU_BG)

    def lock_admin_panel(self):
        self._admin_unlocked = False
        self.admin_config_locked_var.set(True)
        self.set_all_lock_buttons_visibility(False)
        self.set_all_config_lock_buttons_visibility(False)
        self.switch_panel(0)

    def _on_closing(self):
        print("[MainApp] Closing application...")
        
        # Check if panel_instances exists and is not empty
        if hasattr(self, 'panel_instances') and self.panel_instances:
            # Shutdown all panels
            for panel in self.panel_instances:
                if hasattr(panel, 'shutdown'):
                    try:
                        panel.shutdown()
                    except Exception as e:
                        print(f"[MainApp] Error shutting down {panel.__class__.__name__}: {e}")

        # Terminate child processes
        try:
            parent = psutil.Process(os.getpid())
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            psutil.wait_procs(children, timeout=3)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        except Exception as e:
            print(f"[MainApp] Error during child process termination: {e}")

        self.parent.destroy()

def run(root, splash, service_status):
    if splash:
        splash.destroy()
    app = MainApp(root, service_status=service_status)
    app.pack(side="top", fill="both", expand=True)