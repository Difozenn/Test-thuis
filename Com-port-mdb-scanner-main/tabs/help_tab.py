import tkinter as tk
from tkinter import ttk
try:
    from build_info import get_build_number
except Exception:
    get_build_number = lambda: "?"

class HelpTab:
    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        self.build_tab()

    def build_tab(self):
        # Use a frame for layout
        frame = tk.Frame(self.parent)
        frame.pack(fill='both', expand=True)
        help_tab_btn = ttk.Button(frame, text="Open handleiding (PDF)", command=self.main_app.open_manual)
        help_tab_btn.pack(pady=20)
        build_label = tk.Label(frame, text=f"Build: {get_build_number()}", font=("Arial", 9), fg="#888888")
        build_label.pack(pady=(0, 12))
        # Spacer to push copyright to bottom
        spacer = tk.Label(frame)
        spacer.pack(expand=True, fill='both')
        copyright_label = tk.Label(frame, text="© 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)
