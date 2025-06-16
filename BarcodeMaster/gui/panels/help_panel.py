import tkinter as tk
from tkinter import ttk

PANEL_BG = "#f0f0f0"

class HelpPanel(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=PANEL_BG)
        self.app = app
        tk.Label(self, text="Help Panel", font=("Arial", 16), bg=PANEL_BG).pack(pady=20)
        tk.Label(self, text="This is a placeholder for help and documentation.", font=("Arial", 12), bg=PANEL_BG).pack(pady=10)

        self._create_lock_button()

    def _create_lock_button(self):
        self.lock_button_frame = tk.Frame(self, bg=PANEL_BG)
        self.lock_button = ttk.Button(
            self.lock_button_frame,
            text="Admin Panel Vergrendelen",
            command=self.app.lock_admin_panel
        )
        self.lock_button.pack(pady=10)

    def set_lock_button_visibility(self, visible):
        """Shows or hides the admin lock button."""
        if visible and self.winfo_exists():
            self.lock_button_frame.pack(side='bottom', fill='x')
        elif self.winfo_exists():
            self.lock_button_frame.pack_forget()
