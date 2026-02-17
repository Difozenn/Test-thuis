import tkinter as tk
from PIL import Image, ImageTk
import os

class SplashScreen(tk.Toplevel):
    def __init__(self, parent, logo_path, duration=2000):
        super().__init__(parent)
        self.overrideredirect(True)

        # Center splash
        w, h = 400, 400
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Load and resize logo
        try:
            if os.path.exists(logo_path):
                pil_img = Image.open(logo_path).resize((400, 400), Image.LANCZOS)
                self.img = ImageTk.PhotoImage(pil_img)
                label = tk.Label(self, image=self.img, borderwidth=0, highlightthickness=0)
                label.image = self.img # Keep a reference
                label.pack(expand=True)
            else:
                print(f"[WARNING] Splash screen image not found: {logo_path}")
                self._show_fallback()
        except Exception as e:
            print(f"[ERROR] Loading splash screen image: {e}")
            self._show_fallback()

        # This is a fallback, the main app should destroy it.
        self.after(duration, self.destroy)
    
    def _show_fallback(self):
        """Show fallback UI when image fails to load"""
        self.configure(bg='white')
        tk.Label(self, text="BarcodeMatch", bg='white', font=("Arial", 24)).pack(expand=True, pady=(150, 20))
        tk.Label(self, text="Loading...", bg='white', font=("Arial", 16)).pack(expand=True)