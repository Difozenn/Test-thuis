import threading
import sys
import time
import os
from PIL import Image, ImageDraw
import pystray
import tkinter as tk
from tkinter import simpledialog, messagebox
from datetime import datetime
from hops_file_logger import main, load_seen, save_seen, update_reports, CATEGORIES

def create_image():
    # Simple black circle icon
    image = Image.new('RGB', (64, 64), color1 := (0, 0, 0))
    d = ImageDraw.Draw(image)
    d.ellipse((8, 8, 56, 56), fill=(0, 128, 255))
    return image

def run_logger():
    try:
        main()
    except Exception as e:
        print(f"Logger stopped: {e}")

# --- Begin ManualAddApp integration ---
import json
from tkinter import ttk

CATEGORIES_FILE = 'categories.json'
SEEN_ENTRIES_FILE = '.seen_entries.json'

# Load categories
with open(CATEGORIES_FILE, 'r') as f:
    CATEGORIES = json.load(f)
category_list = sorted(set(CATEGORIES.values()))
if 'Allerlei' not in category_list:
    category_list.append('Allerlei')

class ManualAddApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Handmatig toevoegen')
        self.geometry('340x180')
        self.resizable(False, False)
        self.create_widgets()

    def create_widgets(self):
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        tk.Label(self, text='Datum:').grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.date_entry = tk.Entry(self)
        self.date_entry.insert(0, now_str)
        self.date_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self, text='Aantal:').grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.amount_entry = tk.Entry(self)
        self.amount_entry.insert(0, '1')
        self.amount_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(self, text='Categorie:').grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.cat_var = tk.StringVar(value=category_list[0])
        self.cat_combo = ttk.Combobox(self, textvariable=self.cat_var, values=category_list, state='readonly')
        self.cat_combo.grid(row=2, column=1, padx=5, pady=5)

        self.submit_btn = tk.Button(self, text='Toevoegen', command=self.submit)
        self.submit_btn.grid(row=3, column=0, columnspan=2, pady=10)

    def submit(self):
        date_str = self.date_entry.get()
        try:
            dt = datetime.fromisoformat(date_str)
        except Exception:
            messagebox.showerror('Fout', 'Ongeldig datumformaat! Gebruik YYYY-MM-DD HH:MM')
            return
        try:
            amount = int(self.amount_entry.get())
        except Exception:
            messagebox.showerror('Fout', 'Ongeldig aantal!')
            return
        if amount < 1:
            return
        cat = self.cat_var.get()
        if not cat or cat not in category_list:
            messagebox.showerror('Fout', 'Onbekende categorie!')
            return
        # Add events to .seen_entries.json
        if os.path.exists(SEEN_ENTRIES_FILE):
            with open(SEEN_ENTRIES_FILE, 'r') as f:
                seen = json.load(f)
        else:
            seen = {'entries': {}, 'last_mod_time': None, 'save_events': []}
        events = seen.get('save_events', [])
        for i in range(amount):
            entry_name = f"manual_add_{dt.isoformat()}_{i}"
            events.append({'timestamp': dt.isoformat(), 'type': 'new', 'entry': entry_name, 'category': cat})
        seen['save_events'] = events
        with open(SEEN_ENTRIES_FILE, 'w') as f:
            json.dump(seen, f)
        # Immediately update reports after manual add
        try:
            from hops_file_logger import update_reports, load_seen
            update_reports(load_seen()['save_events'])
        except Exception as e:
            print(f'[ERROR] Failed to update reports after manual add: {e}')
        messagebox.showinfo('Succes', f'{amount} item(s) toegevoegd op {date_str} voor categorie {cat}.')
        self.destroy()
# --- End ManualAddApp integration ---

def on_manual_add(icon, item):
    import subprocess
    import sys
    # Launch the same script/exe with --manual-add argument
    subprocess.Popen([sys.executable, sys.argv[0], '--manual-add'])

def on_exit(icon, item):
    icon.stop()
    import sys
    sys.exit(0)

def on_clear_seen(icon, item):
    import json
    import tkinter as tk
    from tkinter import messagebox
    try:
        with open(SEEN_ENTRIES_FILE, 'w') as f:
            json.dump({"entries": {}, "save_events": []}, f)
        # Show confirmation using a simple Tkinter dialog (no main window)
        # Use a simple dialog without a persistent root window
        # Show a custom modal Tk window for success, like ManualAddApp
        import tkinter as tk
        class SuccessPopup(tk.Toplevel):
            def __init__(self, master=None):
                super().__init__(master)
                self.title('Succes')
                self.geometry('320x100')
                self.resizable(False, False)
                self.attributes('-topmost', True)
                tk.Label(self, text='.seen_entries.json is geleegd!').pack(pady=20)
                tk.Button(self, text='OK', command=self.close).pack(pady=5)
                self.protocol('WM_DELETE_WINDOW', self.close)
                self.grab_set()
                self.focus_force()
            def close(self):
                self.grab_release()
                self.destroy()
        root = tk.Tk()
        root.withdraw()
        popup = SuccessPopup(root)
        root.mainloop()

    except Exception as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('Fout', f'Kon .seen_entries.json niet legen: {e}')
        root.destroy()

def setup_tray():
    icon = pystray.Icon("HopsFileLogger")
    icon.icon = create_image()
    icon.menu = pystray.Menu(
        pystray.MenuItem('Handmatig toevoegen', on_manual_add),
        pystray.MenuItem('Seen Entries legen', on_clear_seen),
        pystray.MenuItem('Exit', on_exit)
    )
    # Run logger in background thread
    t = threading.Thread(target=run_logger, daemon=True)
    t.start()
    icon.run()


if __name__ == '__main__':
    import sys
    if '--manual-add' in sys.argv:
        app = ManualAddApp()
        app.mainloop()
    else:
        setup_tray()
