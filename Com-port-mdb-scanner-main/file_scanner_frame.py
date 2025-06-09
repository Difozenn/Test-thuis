import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
from config_utils import update_config, get_config_path
import threading

class FileScannerFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.root = parent  # For compatibility with original code
        self.scanning = False
        self.total_files = 0
        self.processed_files = 0
        self.files = []
        self.base_dir = ""
        self.directory_var = tk.StringVar()
        self.base_dir_var = tk.StringVar()
        self.base_dir_var.trace_add('write', lambda *args: self.save_config())
        # Config file path
        self.CONFIG_FILE = get_config_path()
        self.scan_mode_var = tk.StringVar(value="OPUS")  # Ensure it's initialized before load_config
        self.load_config()
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.columnconfigure(0, weight=1)

        self.directory_frame = ttk.LabelFrame(self.main_frame, text="Selecteer map", padding="5")
        self.directory_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        dir_entry = ttk.Entry(self.directory_frame, textvariable=self.directory_var, width=50)
        dir_entry.grid(row=0, column=0, padx=5)
        dir_btn = ttk.Button(self.directory_frame, text="Bladeren", command=self.browse_directory)
        dir_btn.grid(row=0, column=1, padx=5)
        # Tooltip is not included here, add if needed
        self.scan_mode_var = tk.StringVar(value="OPUS")
        scan_mode_combo = ttk.Combobox(self.directory_frame, textvariable=self.scan_mode_var, values=["OPUS", "GANNOMAT"], state="readonly", width=16)
        scan_mode_combo.grid(row=0, column=2, padx=5)
        scan_mode_combo.bind("<<ComboboxSelected>>", self.on_scan_mode_change)
        self.dir_entry = dir_entry
        self.dir_btn = dir_btn
        self.base_dir_frame = ttk.LabelFrame(self.main_frame, text="Basis map", padding="5")
        self.base_dir_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        base_entry = ttk.Entry(self.base_dir_frame, textvariable=self.base_dir_var, width=50)
        base_entry.grid(row=0, column=0, padx=5)
        base_btn = ttk.Button(self.base_dir_frame, text="Bladeren", command=self.browse_base_directory)
        base_btn.grid(row=0, column=1, padx=5)

        if isinstance(self.root, tk.Tk):
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.progress_frame = ttk.Frame(self.main_frame, padding="5")
        self.progress_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        self.progress_frame.columnconfigure(0, weight=1)
        self.progress_frame.columnconfigure(1, weight=0)
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100)
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.scan_button = ttk.Button(self.progress_frame, text="Map scannen", command=self.start_scan)
        self.scan_button.grid(row=0, column=1, padx=(10, 0))
        self.status_label = ttk.Label(self.progress_frame, text="")
        self.status_label.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.results_frame = ttk.LabelFrame(self.main_frame, text="Resultaten", padding="5")
        self.results_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.S))
        self.results_text = tk.Text(self.results_frame, height=15, width=80)
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.S))
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)
        self.main_frame.rowconfigure(3, weight=1)

    def load_config(self):
        try:
            config_file = get_config_path()
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.base_dir_var.set(config.get('default_base_dir', ''))
                    if hasattr(self, 'scan_mode_var'):
                        self.scan_mode_var.set(config.get('default_scan_mode', 'OPUS'))
                    if hasattr(self, 'scanner_type_var'):
                        self.scanner_type_var.set(config.get('default_scanner_type', 'COM'))
            else:
                self.base_dir_var.set('')
                if hasattr(self, 'scan_mode_var'):
                    self.scan_mode_var.set('OPUS')
                if hasattr(self, 'scanner_type_var'):
                    self.scanner_type_var.set('COM')
        except Exception as e:
            print(f"Error loading config: {str(e)}")

    def save_config(self):
        base_dir = self.base_dir_var.get()
        if base_dir:
            try:
                updates = {'default_base_dir': base_dir}
                if hasattr(self, 'scan_mode_var'):
                    updates['default_scan_mode'] = self.scan_mode_var.get()
                if hasattr(self, 'scanner_type_var'):
                    updates['default_scanner_type'] = self.scanner_type_var.get()
                update_config(updates)
            except Exception as e:
                print(f"Error saving config: {str(e)}")

    def on_closing(self):
        self.save_config()
        self.root.destroy()

    def browse_directory(self):
        scan_mode = self.scan_mode_var.get() if hasattr(self, 'scan_mode_var') else "OPUS"
        if scan_mode == "GANNOMAT":
            mdb_file = filedialog.askopenfilename(
                filetypes=[("Access Database", "*.mdb;*.accdb")],
                title="Selecteer GANNOMAT .mdb bestand"
            )
            if mdb_file:
                self.directory_var.set(mdb_file)
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(tk.END, f"Selected file: {mdb_file}\n")
                self.results_text.see(tk.END)
        else:
            directory = filedialog.askdirectory()
            if directory:
                self.directory_var.set(directory)
                if not self.base_dir_var.get():
                    self.base_dir_var.set(directory)
                    self.base_dir = os.path.abspath(directory)
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(tk.END, f"Selected directory: {directory}\n")
                self.results_text.see(tk.END)

    def browse_base_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.base_dir_var.set(directory)
            self.base_dir = os.path.abspath(directory)

    def start_scan(self):
        scan_mode = self.scan_mode_var.get() if hasattr(self, 'scan_mode_var') else "OPUS"
        path = self.directory_var.get()
        if scan_mode == "GANNOMAT":
            if not path or not (path.lower().endswith('.mdb') or path.lower().endswith('.accdb')):
                messagebox.showwarning("Missing File", "Please select a .mdb file to scan.")
                return
            self.scan_button.config(state=tk.DISABLED)
            self.scanning = True
            threading.Thread(target=self._scan_thread, args=(path, scan_mode), daemon=True).start()
        else:
            if not path:
                messagebox.showwarning("Missing Directory", "Please select a directory to scan.")
                return
            self.scan_button.config(state=tk.DISABLED)
            self.scanning = True
            threading.Thread(target=self._scan_thread, args=(path, scan_mode), daemon=True).start()

    def on_scan_mode_change(self, event=None):
        self.save_scan_mode_to_config()

    def save_scan_mode_to_config(self):
        try:
            updates = {'default_scan_mode': self.scan_mode_var.get()}
            if hasattr(self, 'scanner_type_var'):
                updates['default_scanner_type'] = self.scanner_type_var.get()
            update_config(updates)
        except Exception as e:
            print(f"Error saving scan mode to config: {e}")

    def save_scanner_type_to_config(self):
        try:
            updates = {'default_scanner_type': self.scanner_type_var.get()}
            update_config(updates)
        except Exception as e:
            print(f"Error saving scanner type to config: {e}")

    def _scan_thread(self, path, scan_mode):
        try:
            self.files = []
            self.processed_files = 0
            self.progress_var.set(0)
            self.status_label.config(text="Scannen gestart...")
            if scan_mode == "GANNOMAT" and (path.lower().endswith('.mdb') or path.lower().endswith('.accdb')):
                try:
                    import pyodbc
                except ImportError:
                    self.root.after(0, lambda: self.results_text.insert('end', 'pyodbc is niet geïnstalleerd. Kan MDB-bestanden niet scannen.\n'))
                    self.root.after(0, lambda: self.scan_button.config(state=tk.NORMAL))
                    self.root.after(0, lambda: messagebox.showerror("Scanfout", "pyodbc is niet geïnstalleerd. Kan MDB-bestanden niet scannen."))
                    return
                results = []
                try:
                    conn_str = (
                        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
                        f'DBQ={path};'
                    )
                    conn = pyodbc.connect(conn_str, autocommit=True)
                    cursor = conn.cursor()
                    tables = [tbl_info.table_name for tbl_info in cursor.tables(tableType='TABLE')]
                    program_table = None
                    fallback_table = None
                    for table in tables:
                        columns = [column.column_name for column in cursor.columns(table=table)]
                        if table.lower() == 'program' and 'ProgramNumber' in columns:
                            program_table = table
                            break
                        elif not fallback_table and 'ProgramNumber' in columns:
                            fallback_table = table
                    if program_table:
                        cursor.execute(f'SELECT ProgramNumber FROM [{program_table}]')
                        for row in cursor.fetchall():
                            results.append({'MDB File': os.path.basename(path), 'ProgramNumber': row.ProgramNumber})
                    elif fallback_table:
                        cursor.execute(f'SELECT ProgramNumber FROM [{fallback_table}]')
                        for row in cursor.fetchall():
                            results.append({'MDB File': os.path.basename(path), 'ProgramNumber': row.ProgramNumber})
                    else:
                        self.root.after(0, lambda: self.results_text.insert('end', f"Geen tabel met 'ProgramNumber' kolom gevonden in {os.path.basename(path)}\n"))
                    conn.close()
                    self.files = results
                    self.processed_files = 1
                    self.total_files = 1
                    self.root.after(0, lambda: self._show_results(results, scan_mode, path))
                    self.root.after(0, lambda: self._update_progress(1, 1))
                    self.root.after(0, lambda: messagebox.showinfo("Scan voltooid", f"Scan voltooid. {len(results)} resultaten gevonden."))
                except Exception as e:
                    self.root.after(0, lambda: self.results_text.insert('end', f"Fout bij verwerken van {os.path.basename(path)}: {str(e)}\n"))
                    self.root.after(0, lambda: messagebox.showerror("Scanfout", f"Fout bij het scannen van het MDB-bestand: {str(e)}"))
            else:
                # Directory scan for .hop/.hops
                def count_files():
                    total_files = 0
                    for root, _, filenames in os.walk(path):
                        for filename in filenames:
                            if filename.lower().endswith(('.hop', '.hops')):
                                total_files += 1
                    return total_files
                self.total_files = count_files()
                files = []
                processed = 0
                for rootdir, _, filenames in os.walk(path):
                    for filename in filenames:
                        if filename.lower().endswith(('.hop', '.hops')):
                            try:
                                file_path = os.path.join(rootdir, filename)
                                relative_path = os.path.relpath(file_path, path)
                                files.append({'Relative Path': relative_path})
                                processed += 1
                                self.root.after(0, lambda count=processed, total=self.total_files: self._update_progress(count, total))
                            except Exception as e:
                                self.root.after(0, lambda: self.results_text.insert('end', f"Fout bij verwerken van {filename}: {str(e)}\n"))
                self.files = files
                self.processed_files = processed
                self.root.after(0, lambda: self._show_results(files, scan_mode, path))
                self.root.after(0, lambda: messagebox.showinfo("Scan voltooid", f"Scan voltooid. {len(files)} bestanden gevonden."))
            # Save to Excel after scan
            self.root.after(0, lambda: self._create_excel(path, scan_mode))
        except Exception as e:
            self.root.after(0, lambda: self.results_text.insert('end', f"Scan error: {str(e)}\n"))
            self.root.after(0, lambda: messagebox.showerror("Scanfout", f"Fout tijdens het scannen: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.scan_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.status_label.config(text="Scan voltooid."))

    def _update_progress(self, current, total):
        if total > 0:
            self.progress_var.set((current / total) * 100)
            self.status_label.config(text=f"Scanning... {current}/{total} files processed")
            self.root.update()

    def _show_results(self, results, scan_mode, path):
        self.results_text.delete(1.0, tk.END)
        if not results:
            self.results_text.insert(tk.END, "Geen resultaten gevonden.\n")
            return
        if scan_mode == "GANNOMAT":
            self.results_text.insert(tk.END, f"Resultaten voor {os.path.basename(path)}:\n")
            for entry in results:
                self.results_text.insert(tk.END, f"ProgramNumber: {entry.get('ProgramNumber', '')}\n")
        else:
            self.results_text.insert(tk.END, f"Gevonden bestanden in {path}:\n")
            for entry in results:
                self.results_text.insert(tk.END, f"{entry.get('Relative Path', '')}\n")
        self.results_text.see(tk.END)

    def _create_excel(self, directory, scan_mode="OPUS"):
        import pandas as pd
        if not self.files:
            self.results_text.insert(tk.END, "No files to save to Excel.\n")
            return
        df = pd.DataFrame(self.files)
        # For GANNOMAT, if 'directory' is a file, use its containing folder
        export_dir = directory
        if scan_mode == "GANNOMAT" and os.path.isfile(directory):
            export_dir = os.path.dirname(directory)
            folder_name = os.path.splitext(os.path.basename(directory))[0]  # Just the MDB name, no extension
        else:
            folder_name = os.path.basename(os.path.normpath(directory))
        if scan_mode == "GANNOMAT":
            # Only export ProgramNumber column if it exists
            if 'ProgramNumber' in df.columns:
                df = df[['ProgramNumber']]
                # Always add an empty 'Status' column for scanner compatibility
                df['Status'] = ''
            excel_path = os.path.join(export_dir, f"{folder_name}_GANNOMAT.xlsx")
        else:
            # For OPUS and other modes, always add an empty 'Status' column if missing
            if 'Status' not in df.columns:
                df['Status'] = ''
            excel_path = os.path.join(export_dir, f"{folder_name}_scan.xlsx")
        try:
            df.to_excel(excel_path, index=False)
            self.results_text.insert(tk.END, f"\nExcel file saved: {excel_path}\n")
        except Exception as e:
            self.results_text.insert(tk.END, f"Error saving Excel: {str(e)}\n")
        self.results_text.see(tk.END)
