#!/usr/bin/env python3
"""
Test script to verify grid scaling
"""

import tkinter as tk
from tkinter import ttk, scrolledtext

root = tk.Tk()
root.title("Test Scaling")
root.geometry("800x600")

main_frame = ttk.Frame(root, padding="10")
main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

# Configure grid weights
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
main_frame.columnconfigure(0, weight=1)

# Row 0: Header (fixed)
header = ttk.Label(main_frame, text="HEADER (Fixed)", background="lightblue")
header.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)

# Row 1: Table (90%)
table_frame = ttk.LabelFrame(main_frame, text="Table (90%)", padding="5")
table_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
table_frame.columnconfigure(0, weight=1)
table_frame.rowconfigure(0, weight=1)

table_text = tk.Text(table_frame, background="lightgreen")
table_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
table_text.insert("1.0", "This is the TABLE\nShould take 90% of space\n" * 20)

# Row 2: Log (10%)
log_frame = ttk.LabelFrame(main_frame, text="Log (10%)", padding="5")
log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
log_frame.columnconfigure(0, weight=1)
log_frame.rowconfigure(0, weight=1)

log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, background="lightyellow")
log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
log_text.insert("1.0", "This is the LOG\nShould take 10% of space\n" * 10)

# Row 3: Status (fixed)
status = ttk.Label(main_frame, text="STATUS BAR (Fixed)", background="lightcoral")
status.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)

# Configure weights
main_frame.rowconfigure(1, weight=9)  # Table 90%
main_frame.rowconfigure(2, weight=1)  # Log 10%

print("Grid configuration:")
print("Row 0 (header): weight =", main_frame.grid_rowconfigure(0)['weight'])
print("Row 1 (table):  weight =", main_frame.grid_rowconfigure(1)['weight'])
print("Row 2 (log):    weight =", main_frame.grid_rowconfigure(2)['weight'])
print("Row 3 (status): weight =", main_frame.grid_rowconfigure(3)['weight'])
print("\nResize the window to see the effect!")

root.mainloop()
