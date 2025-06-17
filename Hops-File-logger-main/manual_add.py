import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import json
import os

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
        messagebox.showinfo('Succes', f'{amount} item(s) toegevoegd op {date_str} voor categorie {cat}.')
        self.destroy()

if __name__ == '__main__':
    app = ManualAddApp()
    app.mainloop()
