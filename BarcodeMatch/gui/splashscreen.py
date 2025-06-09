import tkinter as tk
from PIL import Image, ImageTk
import os
from build_info import get_build_number

class SplashScreen(tk.Toplevel):
    def __init__(self, parent, logo_path, duration=2000):
        super().__init__(parent)
        self.overrideredirect(True)
        self.logo_path = logo_path
        self.duration = duration
        self.buildnr = get_build_number()

        # Load and display the logo
        img = Image.open(self.logo_path)
        # Resize image to fit inside 350x310 (preserve aspect ratio)
        max_w, max_h = 350, 310
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        self.img_tk = ImageTk.PhotoImage(img)
        w, h = img.size
        # Set splash window to 350x350, center on screen
        self.geometry(f"350x350+{int(self.winfo_screenwidth()/2-175)}+{int(self.winfo_screenheight()/2-175)}")

        canvas = tk.Canvas(self, width=350, height=350, highlightthickness=0)
        canvas.pack()
        # Center image vertically in top 310px
        img_x = 175
        img_y = (310 - h)//2 + h//2
        canvas.create_image(img_x, img_y, image=self.img_tk)
        # Buildnr centered at bottom
        canvas.create_text(175, 330, text=f"Build: {self.buildnr}", font=("Arial", 16, "bold"), fill="#333")

        self.after(self.duration, self.destroy)
