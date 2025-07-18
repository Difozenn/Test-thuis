import tkinter as tk
from tkinter import PhotoImage
from PIL import Image, ImageTk
import os

# Panel imports for BarcodeMatch
from gui.panels.import_panel import ImportPanel
from gui.panels.scanner_panel import ScannerPanel
from gui.panels.email_panel import EmailPanel
from gui.panels.database_panel import DatabasePanel
from gui.panels.help_panel import HelpPanel
from gui.panels.settings_panel import SettingsPanel
from gui.asset_utils import get_asset_path, asset_exists

MENU_OPTIONS = [
    {"name": "Import", "panel": ImportPanel, "icon": "importeren.png"},
    {"name": "Scanner", "panel": ScannerPanel, "icon": "scanner.png"},
    {"name": "Email", "panel": EmailPanel, "icon": "email.png"},
    {"name": "Database", "panel": DatabasePanel, "icon": "database.png"},
    {"name": "Help", "panel": HelpPanel, "icon": "help.png"},
    {"name": "Settings", "panel": SettingsPanel, "icon": "settings.png"},
]

def create_menu(root, main_app):
    menu_frame = tk.Frame(root, bg="#f0f0f0", height=75)
    menu_frame.pack(side=tk.TOP, fill=tk.X, padx=(5, 0))
    menu_frame.pack_propagate(False)

    # Load icons for each menu option
    icon_imgs = []
    for opt in MENU_OPTIONS:
        icon_path = get_asset_path(opt["icon"])
        if os.path.exists(icon_path):
            try:
                pil_img = Image.open(icon_path).resize((75, 75), Image.LANCZOS)
                icon_img = ImageTk.PhotoImage(pil_img)
            except Exception as e:
                print(f"[ERROR] Failed to load icon {opt['icon']}: {e}")
                icon_img = None
        else:
            print(f"[WARNING] Icon file not found: {icon_path}")
            icon_img = None
        icon_imgs.append(icon_img)
    root.icon_imgs = icon_imgs  # Prevent garbage-collection

    # Track active tab and buttons
    root.active_tab = tk.IntVar(value=0)
    root._tab_buttons = []
    root._active_panel = None

    def update_tabs():
        MENU_BG = "#f0f0f0"
        for idx, (btn, frame) in enumerate(zip(root._tab_buttons, root._tab_frames)):
            if idx == root.active_tab.get():
                # Frame should not be highlighted, button color indicates active state
                frame.config(bg=MENU_BG, highlightbackground=MENU_BG, highlightcolor=MENU_BG, highlightthickness=0)
                btn.config(bg="#d0e0ff", relief=tk.FLAT)
            else:
                frame.config(bg=MENU_BG, highlightbackground=MENU_BG, highlightcolor=MENU_BG, highlightthickness=0)
                btn.config(bg=MENU_BG, relief=tk.FLAT)

    def open_panel_idx(idx):
        # Hide any existing panel
        if root._active_panel is not None:
            try:
                if hasattr(root._active_panel, 'winfo_exists') and root._active_panel.winfo_exists():
                    root._active_panel.pack_forget()
            except tk.TclError:
                pass  # Widget already destroyed
        
        # Show the persistent panel instance
        panel_name = MENU_OPTIONS[idx]["name"]
        panel = main_app.get_panel_by_name(panel_name)
        if panel:
            root._active_panel = panel  # Assign before pack!
            panel.pack(fill=tk.BOTH, expand=True)
            # If this is the DatabasePanel, start auto-refresh after packing
            from gui.panels.database_panel import DatabasePanel
            if isinstance(panel, DatabasePanel):
                panel.start_auto_refresh()
            root.active_tab.set(idx)
            update_tabs()

    MENU_BG = "#f0f0f0"
    root._tab_buttons = []
    root._tab_frames = []
    for idx, opt in enumerate(MENU_OPTIONS):
        frame = tk.Frame(menu_frame, width=75, height=75, bg=MENU_BG, highlightthickness=0)
        frame.pack_propagate(False)
        frame.pack(side=tk.LEFT, padx=0, pady=0)
        
        # Create button with or without icon
        btn_kwargs = {
            'command': lambda i=idx: open_panel_idx(i),
            'width': 75, 
            'height': 75,
            'bg': MENU_BG,
            'activebackground': "#d0e0ff",
            'activeforeground': "black",
            'relief': tk.FLAT,
            'bd': 0,
            'highlightthickness': 0,
            'takefocus': 0
        }
        
        if icon_imgs[idx]:
            btn_kwargs['image'] = icon_imgs[idx]
        else:
            btn_kwargs['text'] = opt["name"]
            
        btn = tk.Button(frame, **btn_kwargs)
        btn.pack(expand=True, fill=tk.BOTH, padx=0, pady=0)
        root._tab_buttons.append(btn)
        root._tab_frames.append(frame)

    # Open the first panel by default
    open_panel_idx(0)
    # Ensure frame backgrounds are set correctly at startup
    update_tabs()