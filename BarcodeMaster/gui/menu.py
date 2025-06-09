import tkinter as tk
from tkinter import PhotoImage
from PIL import Image, ImageTk
import os

# Panel imports (placeholders)
from .panels.settings_panel1 import SettingsPanel1
from .panels.settings_panel2 import SettingsPanel2
from .panels.settings_panel3 import SettingsPanel3
from .panels.settings_panel4 import SettingsPanel4
# from .panels.settings_panel5 import SettingsPanel5  # Temporarily hidden

MENU_OPTIONS = [
    {"name": "Panel 1", "panel": SettingsPanel1},
    {"name": "Panel 2", "panel": SettingsPanel2},
    {"name": "Panel 3", "panel": SettingsPanel3},
    {"name": "Panel 4", "panel": SettingsPanel4},
    # {"name": "Panel 5", "panel": SettingsPanel5},  # Temporarily hidden
]


def create_menu(root):
    menu_frame = tk.Frame(root, bg="#f0f0f0", height=75)
    menu_frame.pack(side=tk.TOP, fill=tk.X)
    menu_frame.pack_propagate(False)

    # Load the icon once and reuse
    icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "database.png")
    pil_img = Image.open(icon_path).resize((75, 75), Image.LANCZOS)
    icon_img = ImageTk.PhotoImage(pil_img)
    root.icon_img = icon_img  # Prevent garbage-collection

    # Track active tab and buttons
    root.active_tab = tk.IntVar(value=0)
    root._tab_buttons = []
    root._active_panel = None

    def update_tabs():
        for idx, btn in enumerate(root._tab_buttons):
            if idx == root.active_tab.get():
                btn.config(bg="#d0e0ff", relief=tk.SUNKEN)
            else:
                btn.config(bg="#f0f0f0", relief=tk.RAISED)

    def open_panel_idx(idx):
        # Destroy any existing panels
        if root._active_panel is not None:
            root._active_panel.destroy()
        # Add new panel
        panel_class = MENU_OPTIONS[idx]["panel"]
        panel = panel_class(root)
        panel.pack(fill=tk.BOTH, expand=True)
        root._active_panel = panel
        root.active_tab.set(idx)
        update_tabs()

    for idx, opt in enumerate(MENU_OPTIONS):
        btn = tk.Button(menu_frame, image=icon_img, command=lambda i=idx: open_panel_idx(i), width=75, height=75, bg="#f0f0f0", relief=tk.RAISED, bd=2)
        btn.pack(side=tk.LEFT, padx=5, pady=0, fill=tk.Y)
        root._tab_buttons.append(btn)

    # Open the first tab by default
    open_panel_idx(0)
