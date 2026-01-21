import tkinter as tk
from tkinter import PhotoImage
from PIL import Image, ImageTk
import os

# Panel imports
from .panels.settings_panel import SettingsPanel

MENU_OPTIONS = [
    {"name": "Settings", "panel": SettingsPanel},
]


def create_menu(root):
    menu_frame = tk.Frame(root, height=75, bg="#e0e0e0", highlightthickness=0, bd=0, relief=tk.FLAT)
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
                btn.config(bg="#d0e0ff", relief=tk.FLAT, bd=0, highlightthickness=0)
            else:
                btn.config(bg="#e0e0e0", relief=tk.FLAT, bd=0, highlightthickness=0)

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
        btn = tk.Button(menu_frame, image=icon_img, command=lambda i=idx: open_panel_idx(i), width=75, height=75, relief=tk.FLAT, bd=0, bg="#e0e0e0", highlightthickness=0, overrelief=tk.FLAT)
        btn.pack(side=tk.LEFT, pady=0, fill=tk.Y)
        root._tab_buttons.append(btn)

    # Open the first tab by default
    open_panel_idx(0)
