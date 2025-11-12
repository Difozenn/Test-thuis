import tkinter as tk
from tkinter import ttk, messagebox
from build_info import get_build_number
from gui.asset_utils import get_asset_path
import os
import sys

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

        # Add test button for SPOED warning (for testing purposes)
        test_spoed_btn = ttk.Button(frame, text="Test SPOED Warning", command=self._test_spoed_warning)
        test_spoed_btn.pack(pady=10)

        build_label = tk.Label(frame, text=f"Build: {get_build_number()}", font=("Arial", 9), fg="#888888")
        build_label.pack(pady=(0, 12))
        spacer = tk.Label(frame)
        spacer.pack(expand=True, fill='both')
        copyright_label = tk.Label(frame, text="© 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)

    def _test_spoed_warning(self):
        """Test function to manually trigger SPOED warning"""
        print("[TEST] Triggering SPOED warning test...")
        if hasattr(self.main_app, 'test_spoed_warning'):
            self.main_app.test_spoed_warning("MO99999_SPOED_TestProject")
            messagebox.showinfo("Test", "SPOED warning should appear in menu bar\n(if not already dismissed)")
        else:
            messagebox.showerror("Error", "SPOED warning system not available")

    def _open_manual(self):
        # Use the asset_utils to get the correct path for both dev and frozen states
        manual_path = get_asset_path('BarcodeMatch_Gebruikershandleiding.pdf')
        
        if not os.path.exists(manual_path):
            messagebox.showerror("Fout", f"Handleiding niet gevonden:\n{manual_path}")
            return
            
        try:
            if sys.platform.startswith('win'):
                os.startfile(manual_path)
            elif sys.platform.startswith('darwin'):  # macOS
                os.system(f'open "{manual_path}"')
            else:  # linux variants
                os.system(f'xdg-open "{manual_path}"')
        except Exception as e:
            messagebox.showerror("Fout", f"Kan handleiding niet openen:\n{manual_path}\n{e}")