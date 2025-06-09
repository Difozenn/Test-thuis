import tkinter as tk
from tkinter import ttk
from build_info import get_build_number

class HelpPanel(ttk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.main_app = main_app
        self._setup_ui()

    def _setup_ui(self):
        frame = tk.Frame(self)
        frame.pack(fill='both', expand=True)
        help_tab_btn = ttk.Button(frame, text="Open handleiding (PDF)", command=self._open_manual)
        help_tab_btn.pack(pady=20)
        build_label = tk.Label(frame, text=f"Build: {get_build_number()}", font=("Arial", 9), fg="#888888")
        build_label.pack(pady=(0, 12))
        spacer = tk.Label(frame)
        spacer.pack(expand=True, fill='both')
        copyright_label = tk.Label(frame, text="© 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)

    def _open_manual(self):
        # Stub for opening manual
        # In BarcodeMaster, this would open the PDF manual from assets
        # You can implement this to open the file using os.startfile or similar
        import os
        manual_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'BarcodeMatch_Gebruikershandleiding.pdf'))
        try:
            os.startfile(manual_path)
        except Exception as e:
            tk.messagebox.showerror("Fout", f"Kan handleiding niet openen:\n{manual_path}\n{e}")
