import tkinter as tk
from tkinter import ttk
from file_scanner_frame import FileScannerFrame

class ImportTab:
    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        self.build_tab()

    def build_tab(self):
        self.file_scanner_frame = FileScannerFrame(self.parent)
        self.file_scanner_frame.pack(fill=tk.BOTH, expand=True)
        copyright_label = tk.Label(self.parent, text="© 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)
