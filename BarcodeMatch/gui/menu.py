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

MENU_OPTIONS = [
    {"name": "Import", "panel": ImportPanel, "icon": "importeren.png"},
    {"name": "Scanner", "panel": ScannerPanel, "icon": "scanner.png"},
    {"name": "Email", "panel": EmailPanel, "icon": "email.png"},
    {"name": "Database", "panel": DatabasePanel, "icon": "database.png"},
    {"name": "Help", "panel": HelpPanel, "icon": "help.png"},
]

def create_menu(root, main_app):
    menu_frame = tk.Frame(root, bg="#f0f0f0", height=75)
    menu_frame.pack(side=tk.TOP, fill=tk.X)
    menu_frame.pack_propagate(False)

    # Load icons for each menu option
    asset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
    icon_imgs = []
    for opt in MENU_OPTIONS:
        icon_path = os.path.join(asset_dir, opt["icon"])
        if os.path.exists(icon_path):
            pil_img = Image.open(icon_path).resize((75, 75), Image.LANCZOS)
            icon_img = ImageTk.PhotoImage(pil_img)
        else:
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
                frame.config(bg="white", highlightbackground="white", highlightcolor="white", highlightthickness=2)
                btn.config(bg=MENU_BG, activebackground="#d0e0ff", relief=tk.RAISED)
            else:
                frame.config(bg=MENU_BG, highlightbackground=MENU_BG, highlightcolor=MENU_BG, highlightthickness=0)
                btn.config(bg=MENU_BG, activebackground="#d0e0ff", relief=tk.RAISED)

    def open_panel_idx(idx):
        # Hide any existing panel
        if root._active_panel is not None:
            print(f"[DIAG] Hiding panel: {type(root._active_panel).__name__}")
            root._active_panel.pack_forget()
        # Show the persistent panel instance
        panel_name = MENU_OPTIONS[idx]["name"]
        panel = main_app.get_panel_by_name(panel_name)
        root._active_panel = panel  # Assign before pack!
        print(f"[DIAG] Showing panel: {type(panel).__name__}")
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
        btn = tk.Button(
            frame,
            image=icon_imgs[idx],
            command=lambda i=idx: open_panel_idx(i),
            width=67, height=67,
            bg=MENU_BG,
            activebackground="#d0e0ff",
            activeforeground="black",
            relief=tk.RAISED,
            bd=0,
            highlightthickness=0,
            takefocus=0
        )
        btn.pack(expand=True, fill=tk.BOTH, padx=0, pady=0)
        root._tab_buttons.append(btn)
        root._tab_frames.append(frame)

    # Open the first panel by default
    open_panel_idx(0)
    # Ensure frame backgrounds are set correctly at startup
    update_tabs()
