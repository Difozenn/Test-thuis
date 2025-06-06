import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import pandas as pd
from datetime import datetime
import threading
import json

class Tooltip:
    """
    A simple tooltip that appears when hovering over a widget
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind('<Enter>', self.showtip)
        self.widget.bind('<Leave>', self.hidetip)

    def showtip(self, event=None):
        """Display text in tooltip window"""
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tipwindow = tk.Toplevel(self.widget)
        self.tipwindow.wm_overrideredirect(1)
        self.tipwindow.wm_geometry(f"+{x}+{y}")
        try:
            # For Windows
            self.tipwindow.wm_attributes("-toolwindow", 1)
        except tk.TclError:
            pass
        
        label = ttk.Label(self.tipwindow, text=self.text, justify=tk.LEFT,
                          background="white", relief=tk.SOLID, borderwidth=1,
                          font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

import sys

# Get script directory
if getattr(sys, 'frozen', False):
    # If we're running as an executable
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    # If we're running as a script
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")


class FileScannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("File Scanner")
        self.root.geometry("800x600")
        
        # Initialize variables
        self.scanning = False
        self.total_files = 0
        self.processed_files = 0
        self.files = []
        self.base_dir = ""
        
        # Create StringVars first
        self.directory_var = tk.StringVar()
        self.base_dir_var = tk.StringVar()
        
        # Load configuration first
        self.load_config()
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main frame grid
        self.main_frame.columnconfigure(0, weight=1)
        
        # Directory selection
        self.directory_frame = ttk.LabelFrame(self.main_frame, text="Select Directory", padding="5")
        self.directory_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Create widgets with tooltips
        dir_entry = ttk.Entry(self.directory_frame, textvariable=self.directory_var, width=50)
        dir_entry.grid(row=0, column=0, padx=5)
        dir_btn = ttk.Button(self.directory_frame, text="Browse", command=self.browse_directory)
        dir_btn.grid(row=0, column=1, padx=5)
        
        # Add tooltip for browse button
        self.dir_btn_tooltip = Tooltip(dir_btn, "Selecteer de maatkast map")
        
        # Base directory selection
        self.base_dir_frame = ttk.LabelFrame(self.main_frame, text="Base Directory", padding="5")
        self.base_dir_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Create base directory widgets with tooltips
        base_entry = ttk.Entry(self.base_dir_frame, textvariable=self.base_dir_var, width=50)
        base_entry.grid(row=0, column=0, padx=5)
        base_btn = ttk.Button(self.base_dir_frame, text="Browse Base", command=self.browse_base_directory)
        base_btn.grid(row=0, column=1, padx=5)
        
        # Add tooltip for base directory browse button
        self.base_btn_tooltip = Tooltip(base_btn, "Browse for base directory")
        
        # Base directory labels
        self.base_dir_label = ttk.Label(self.base_dir_frame, text="")
        self.base_dir_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5)
        self.default_base_label = ttk.Label(self.base_dir_frame, text="")
        self.default_base_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=5)
        
        # Set up save on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Progress frame
        self.progress_frame = ttk.Frame(self.main_frame, padding="5")
        self.progress_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        # Configure progress frame grid
        self.progress_frame.columnconfigure(0, weight=1)
        self.progress_frame.columnconfigure(1, weight=0)
        
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100)
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Add scan button to progress frame
        self.scan_button = ttk.Button(self.progress_frame, text="Scan Directory", command=self.start_scan)
        self.scan_button.grid(row=0, column=1, padx=(10, 0))
        
        # Set up scan button tooltip after a small delay to ensure proper initialization
        self.root.after(100, lambda: self.setup_scan_tooltip())
        
        self.status_label = ttk.Label(self.progress_frame, text="")
        self.status_label.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Results frame
        self.results_frame = ttk.LabelFrame(self.main_frame, text="Results", padding="5")
        self.results_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.S))
        
        self.results_text = tk.Text(self.results_frame, height=15, width=80)
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.S))
        
        # Configure results frame grid
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)
        
        # Configure main frame grid
        self.main_frame.rowconfigure(3, weight=1)
        
    def setup_scan_tooltip(self):
        """Set up tooltip for the scan button"""
        if hasattr(self, 'scan_button'):
            self.scan_button_tooltip = Tooltip(self.scan_button, "Start scanning the selected directory for .hop and .hops files")
        
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    if 'default_base_dir' in config:
                        base_dir = config['default_base_dir']
                        self.base_dir_var.set(base_dir)
                        self.base_dir = base_dir
                        self.base_dir_label.config(text=f"Base Directory: {base_dir}")
                        self.default_base_label.config(text=f"(Default directory loaded from config)")
                        # Update the entry widget
                        for widget in self.base_dir_frame.winfo_children():
                            if isinstance(widget, ttk.Entry):
                                widget.update_idletasks()
        except Exception as e:
            print(f"Error loading config: {str(e)}")

    def save_config(self):
        """Save current configuration"""
        base_dir = self.base_dir_var.get()
        if base_dir:
            try:
                config = {'default_base_dir': base_dir}
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(config, f, indent=4)
                self.default_base_label.config(text=f"(Default directory saved to config)")
            except Exception as e:
                print(f"Error saving config: {str(e)}")

    def on_closing(self):
        """Handle window close event"""
        self.save_config()
        self.root.destroy()
            

        
    def update_base_dir(self, *args):
        base_dir = self.base_dir_var.get()
        if base_dir:
            self.base_dir = os.path.abspath(base_dir)
            self.base_dir_label.config(text=f"Base Directory: {self.base_dir}")

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.directory_var.set(directory)
            # If no base directory is set, use the selected directory as base
            if not self.base_dir_var.get():
                self.base_dir_var.set(directory)
                self.base_dir = os.path.abspath(directory)
                self.base_dir_label.config(text=f"Base Directory: {self.base_dir}")
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"Selected directory: {directory}\n")
            self.results_text.see(tk.END)

    def update_progress(self, current, total):
        if total > 0:
            self.progress_var.set((current / total) * 100)
            self.status_label.config(text=f"Scanning... {current}/{total} files processed")
            self.root.update()
            
    def scan_directory(self, directory):
        self.total_files = 0
        self.processed_files = 0
        
        def count_files():
            total_files = 0
            for root, _, filenames in os.walk(directory):
                for filename in filenames:
                    if filename.lower().endswith(('.hop', '.hops')):
                        total_files += 1
            return total_files
        
        # Get total files count first
        self.total_files = count_files()
        
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if filename.lower().endswith(('.hop', '.hops')):
                    try:
                        file_path = os.path.join(root, filename)
                        # Store relative path instead of full path
                        relative_path = os.path.relpath(file_path, self.base_dir)
                        
                        files.append({
                            'Relative Path': relative_path
                        })
                        
                        self.processed_files += 1
                        self.update_progress(self.processed_files, self.total_files)
                        
                    except Exception as e:
                        self.results_text.insert(tk.END, f"Error processing {filename}: {str(e)}\n")
                        self.results_text.see(tk.END)
        
        return files

    def browse_base_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.base_dir_var.set(directory)
            self.base_dir = os.path.abspath(directory)
            self.base_dir_label.config(text=f"Base Directory: {self.base_dir}")
        
    def _scan_thread(self, directory):
        try:
            files = self.scan_directory(directory)
            self.files = files
            self._update_gui(directory, len(files))

        except Exception as e:
            self.root.after(0, self._show_error, str(e))
            return

        self.results_text.see(tk.END)
        
        self.scanning = False
        self.scan_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_label.config(text="")
        
        # Automatically create Excel file after scanning
        self._create_excel(directory)
        
    def _update_gui(self, directory, file_count):
        self.results_text.insert(tk.END, f"\nScan complete! Found {file_count} files\n")
        self.results_text.insert(tk.END, "\nFiles found:\n")
        for file_info in self.files:
            self.results_text.insert(tk.END, f"- {file_info['Relative Path']}\n")
        self.results_text.see(tk.END)
        
    def _show_error(self, error_msg):
        messagebox.showerror("Error", error_msg)
        
    def _create_excel(self, directory):
        if not self.files:
            return
            
        try:
            # Create DataFrame with Relative Path column
            df = pd.DataFrame(self.files)[['Relative Path']]
            
            # Generate output filename using scanned directory name and date
            scanned_dir_name = os.path.basename(directory)
            date = datetime.now().strftime("%Y_%m_%d")
            excel_file = os.path.join(self.directory_var.get(), f"{scanned_dir_name}_{date}.xlsx")
            
            # Save to Excel
            df.to_excel(excel_file, index=False)
            
            messagebox.showinfo("Success", f"Excel file created: {excel_file}")
            self.results_text.insert(tk.END, f"\nExcel file created: {excel_file}\n")
            self.results_text.see(tk.END)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create Excel file: {str(e)}")
            
    def start_scan(self):
        if self.scanning:
            return
            
        directory = self.directory_var.get()
        if not directory:
            messagebox.showerror("Error", "Please select a directory first!")
            return
            
        if not os.path.exists(directory):
            messagebox.showerror("Error", f"Directory {directory} does not exist!")
            return
            
        self.scanning = True
        self.scan_button.config(state=tk.DISABLED)
        self.results_text.delete(1.0, tk.END)
        
        # Run scan in a separate thread
        threading.Thread(target=self._scan_thread, args=(directory,), daemon=True).start()
        
    def run(self):
        # Add scan button to progress frame
        self.scan_button = ttk.Button(self.progress_frame, text="Scan Directory", command=self.start_scan)
        self.scan_button.grid(row=0, column=1, padx=(10, 0))
        
        # Start the GUI
        self.root.mainloop()

def main():
    root = tk.Tk()
    app = FileScannerGUI(root)
    app.run()

if __name__ == "__main__":
    main()
