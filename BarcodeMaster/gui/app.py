import tkinter as tk
from PIL import Image, ImageTk
import os
import requests
from gui.panels.scanner_panel import ScannerPanel
from gui.panels.database_panel import DatabasePanel
from gui.panels.help_panel import HelpPanel
from gui.panels.admin_panel import AdminPanel
# from .panels.settings_panel5 import SettingsPanel5  # Temporarily hidden

MENU_BG = "#f0f0f0"
PANEL_BG = "#f0f0f0"

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BarcodeMaster")
        self.geometry("800x600")
        # Set window icon if available
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "database.png")
        if os.path.exists(icon_path):
            try:
                self.iconphoto(True, ImageTk.PhotoImage(file=icon_path))
            except Exception:
                pass
        # Load icons
        pil_img_db = Image.open(icon_path).resize((75, 75), Image.LANCZOS)
        icon_db = ImageTk.PhotoImage(pil_img_db)
        help_icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "help.png")
        pil_img_help = Image.open(help_icon_path).resize((75, 75), Image.LANCZOS)
        icon_help = ImageTk.PhotoImage(pil_img_help)
        admin_icon_path = os.path.join(os.path.dirname(__file__), '../assets/admin.png')
        pil_img_admin = Image.open(admin_icon_path).resize((75, 75), Image.LANCZOS)
        icon_admin = ImageTk.PhotoImage(pil_img_admin)
        scanner_icon_path = os.path.join(os.path.dirname(__file__), '../assets/scanner.png')
        if os.path.exists(scanner_icon_path):
            pil_img_scanner = Image.open(scanner_icon_path).resize((75, 75), Image.LANCZOS)
            icon_scanner = ImageTk.PhotoImage(pil_img_scanner)
        else:
            icon_scanner = icon_db
        self.tab_icons = [icon_scanner, icon_db, icon_help, icon_admin]  # Panel 5 hidden, match count
        self.panels = [
            ScannerPanel,
            DatabasePanel,
            HelpPanel,
            AdminPanel
            # SettingsPanel5  # Temporarily hidden
        ]
        self.panel_names = ["Panel 1", "Database", "Help", "Panel 4"]  # Panel 5 hidden
        # --- Custom Menu Bar ---
        self.menu_frame = tk.Frame(self, bg=MENU_BG, height=75)
        self.menu_frame.pack(side=tk.TOP, fill=tk.X)
        self.menu_frame.pack_propagate(False)
        self.tab_buttons = []
        self.button_frames = []
        for i, icon in enumerate(self.tab_icons):
            frame = tk.Frame(self.menu_frame, width=75, height=75, bg=MENU_BG, highlightthickness=0)
            frame.pack_propagate(False)
            frame.pack(side=tk.LEFT, padx=0, pady=0)
            btn = tk.Button(frame, image=icon, width=67, height=67, bg=MENU_BG, relief=tk.RAISED, bd=0, highlightthickness=0, activebackground="#d0e0ff", command=lambda idx=i: self.switch_panel(idx))
            btn.pack(expand=True, fill=tk.BOTH, padx=0, pady=0)
            self.tab_buttons.append(btn)
            self.button_frames.append(frame)
        # --- Content Area ---
        self.content_frame = tk.Frame(self, bg=PANEL_BG)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.active_panel_idx = None
        self.active_panel = None
        self._admin_unlocked = False
        self.switch_panel(0)
        # --- Initial database connection test on program startup ---
        import config_utils
        config = config_utils.get_config()
        if config.get('database_enabled', True):
            import threading
            print("[MainApp] Starting initial database connection test in background thread...")
            self._dbpanel_for_startup = DatabasePanel(self)
            self._dbpanel_for_startup.pack_forget()
            def run_and_update_visible():
                print("[MainApp] Running test_connect on hidden DatabasePanel...")
                result = [False, None]  # [connected, error_reason]
                try:
                    url = self._dbpanel_for_startup.api_url_var.get()
                    resp = requests.post(url, json={"event": "test_connect", "details": "Test verbinding", "user": self._dbpanel_for_startup.user_var.get()}, timeout=3)
                    print(f"[MainApp] test_connect response: {resp.status_code} {resp.text}")
                    if resp.status_code == 200 and resp.json().get('success'):
                        result[0] = True
                    else:
                        result[0] = False
                        result[1] = f"{resp.status_code}"
                except Exception as e:
                    print(f"[MainApp] Exception during test_connect: {e}")
                    result[0] = False
                    result[1] = str(e)
                # Cache the result
                self._last_db_connection_status = tuple(result)
                # Find visible DatabasePanel and update status
                def update_visible():
                    print(f"[MainApp] Updating visible DatabasePanel connection status: {result}")
                    for child in self.content_frame.winfo_children():
                        if child.__class__.__name__ == 'DatabasePanel':
                            child.set_connection_status(result[0], result[1])
                self.after(0, update_visible)
            threading.Thread(target=run_and_update_visible, daemon=True).start()
        # (Removed erroneous idx block; admin password logic is handled in switch_panel)
    def switch_panel(self, idx):
        # Password protection for Admin panel (last index)
        if idx == self.panels.index(AdminPanel):
            if not hasattr(self, '_admin_unlocked') or not self._admin_unlocked:
                if not self.prompt_admin_password():
                    return  # Do not switch if not authenticated
                self._admin_unlocked = True
        # Do not reset self._admin_unlocked when switching away from admin panel
        if self.active_panel is not None:
            self.active_panel.destroy()
        panel_cls = self.panels[idx]
        panel = panel_cls(self.content_frame)
        panel.pack(fill=tk.BOTH, expand=True)
        self.active_panel = panel
        self._highlight_tab(idx)
        self.active_panel_idx = idx
        # If this is the DatabasePanel, sync the last known connection status
        if panel_cls.__name__ == 'DatabasePanel' and hasattr(self, '_last_db_connection_status'):
            conn, err = self._last_db_connection_status
            panel.set_connection_status(conn, err)
        # Hide/show lock buttons based on admin status
        self.set_lock_buttons_visibility(self._admin_unlocked)

    def prompt_admin_password(self):
        import tkinter.simpledialog
        import tkinter.messagebox
        pw = tkinter.simpledialog.askstring("Admin Panel", "Enter admin password:", show='*', parent=self)
        if pw == 'sunrise':
            return True
        tkinter.messagebox.showerror("Access Denied", "Incorrect password.")
        return False

    def set_lock_buttons_visibility(self, visible):
        # Call on the active panel instance if it supports it
        if hasattr(self.active_panel, 'set_lock_button_visibility'):
            self.active_panel.set_lock_button_visibility(visible)
    def _highlight_tab(self, idx):
        for i, (btn, frame) in enumerate(zip(self.tab_buttons, self.button_frames)):
            if i == idx:
                frame.config(bg="white", highlightbackground="white", highlightthickness=2)
                btn.config(bg="#d0e0ff", relief=tk.SUNKEN)
            else:
                frame.config(bg=MENU_BG, highlightbackground=MENU_BG, highlightthickness=0)
                btn.config(bg=MENU_BG, relief=tk.RAISED)
    def lock_admin_panel(self):
        self._admin_unlocked = False
        # Switch to default panel (index 0)
        self.switch_panel(0)

def run():
    app = MainApp()
    app.mainloop()
