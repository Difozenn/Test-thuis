import tkinter as tk
from PIL import Image, ImageTk

class SplashScreen(tk.Toplevel):
    def __init__(self, parent, logo_path, duration=2000):
        super().__init__(parent)
        self.overrideredirect(True)
        # self.configure(bg='white') # Remove explicit white background for Toplevel

        # Center splash
        w, h = 400, 400
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Load and resize logo
        try:
            pil_img = Image.open(logo_path).resize((400, 400), Image.LANCZOS) # Resize to fill 400x400 splash window
            self.img = ImageTk.PhotoImage(pil_img)
            label = tk.Label(self, image=self.img, borderwidth=0, highlightthickness=0)
            label.image = self.img # Keep a reference
            label.pack(expand=True)
        except Exception as e:
            print(f"Error loading splash screen image: {e}")
            # Optional: show text if image fails
            tk.Label(self, text="Loading...", bg='white', font=("Arial", 16)).pack(expand=True)

        # This is a fallback, the main app should destroy it.
        self.after(duration, self.destroy)
