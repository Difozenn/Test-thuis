import time
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import threading

# Debug mode check
DEBUG = os.environ.get('BARCODEMATCH_DEBUG', '').lower() == 'true'

try:
    from config_utils import update_config, get_config_path
    if DEBUG:
        print('[DIAG] config_utils import succeeded')
except Exception as e:
    print(f'[DIAG ERROR] config_utils import failed: {e}')

class ImportPanel(ttk.Frame):
    def __init__(self, parent, main_app):
        if DEBUG:
            print(f'[DIAG] ImportPanel __init__ start {time.time()}')
        super().__init__(parent)
        self.main_app = main_app
        self.root = parent
        self.scanning = False
        self.total_files = 0
        self.processed_files = 0
        self.files = []
        self.base_dir = ""
        self.directory_var = tk.StringVar()
        self.base_dir_var = tk.StringVar()
        self.base_dir_var.trace_add('write', lambda *args: self.save_config())
        self.CONFIG_FILE = get_config_path()
        self.scan_mode_var = tk.StringVar(value="OPUS")
        
        # Lazy loading flags
        self._pandas = None
        self._pyodbc = None
        
        self.load_config()
        self._setup_ui()

    def _ensure_pandas(self):
        """Lazy load pandas only when needed"""
        if self._pandas is None:
            try:
                import pandas
                self._pandas = pandas
                if DEBUG:
                    print('[DIAG] pandas loaded lazily')
            except ImportError as e:
                messagebox.showerror("Module Error", "Pandas module niet gevonden. Installeer pandas om door te gaan.")
                raise e
        return self._pandas

    def _ensure_pyodbc(self):
        """Lazy load pyodbc only when needed"""
        if self._pyodbc is None:
            try:
                import pyodbc
                self._pyodbc = pyodbc
                if DEBUG:
                    print('[DIAG] pyodbc loaded lazily')
                return True
            except ImportError:
                if DEBUG:
                    print('[DIAG] pyodbc not available')
                return False
        return True

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

    def _setup_ui(self):
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.columnconfigure(0, weight=1)
        
        # Directory selection
        self.directory_frame = ttk.LabelFrame(self.main_frame, text="Selecteer map", padding="5")
        self.directory_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        dir_entry = ttk.Entry(self.directory_frame, textvariable=self.directory_var, width=50)
        dir_entry.grid(row=0, column=0, padx=5)
        self.dir_btn = ttk.Button(self.directory_frame, text="Bladeren", command=self.browse_directory)
        self.dir_btn.grid(row=0, column=1, padx=5)
        self.scan_mode_combo = ttk.Combobox(self.directory_frame, textvariable=self.scan_mode_var, 
                                           values=["OPUS", "GANNOMAT"], state="readonly", width=16)
        self.scan_mode_combo.grid(row=0, column=2, padx=5)
        self.scan_mode_combo.bind("<<ComboboxSelected>>", self.on_scan_mode_change)
        self.update_browse_button()
        
        # Base directory
        self.base_dir_frame = ttk.LabelFrame(self.main_frame, text="Basis map", padding="5")
        self.base_dir_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        base_entry = ttk.Entry(self.base_dir_frame, textvariable=self.base_dir_var, width=50)
        base_entry.grid(row=0, column=0, padx=5)
        base_btn = ttk.Button(self.base_dir_frame, text="Bladeren", command=self.browse_base_directory)
        base_btn.grid(row=0, column=1, padx=5)
        
        # Progress and scan
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
        
        # Results
        self.results_frame = ttk.LabelFrame(self.main_frame, text="Resultaten", padding="5")
        self.results_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.S))
        self.results_text = tk.Text(self.results_frame, height=15, width=80)
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.S))

        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)
        self.main_frame.rowconfigure(3, weight=1)
        
        # Copyright
        copyright_label = tk.Label(self, text="© 2025 RVL", font=(None, 9), fg="#888888")
        copyright_label.pack(side=tk.BOTTOM, pady=2)

    def start_scan(self):
        scan_mode = self.scan_mode_var.get() if hasattr(self, 'scan_mode_var') else "OPUS"
        path = self.directory_var.get()
        
        if scan_mode == "GANNOMAT":
            if not path or not (path.lower().endswith('.mdb') or path.lower().endswith('.accdb')):
                messagebox.showwarning("Missing File", "Please select a .mdb file to scan.")
                return
        else:
            if not path:
                messagebox.showwarning("Missing Directory", "Please select a directory to scan.")
                return
        
        self.scan_button.config(state=tk.DISABLED)
        self.scanning = True
        threading.Thread(target=self._scan_thread, args=(path, scan_mode), daemon=True).start()

    def _scan_thread(self, path, scan_mode):
        if DEBUG:
            print(f"[DIAG] _scan_thread started. Thread: {threading.current_thread().name}")
        
        try:
            self.files = []
            self.processed_files = 0
            self.progress_var.set(0)
            self.status_label.config(text="Scannen gestart...")
            
            if scan_mode == "GANNOMAT" and (path.lower().endswith('.mdb') or path.lower().endswith('.accdb')):
                if not self._ensure_pyodbc():
                    self.after(0, lambda: self.results_text.insert('end', 'pyodbc is niet geïnstalleerd. Kan MDB-bestanden niet scannen.\n'))
                    self.after(0, lambda: self.scan_button.config(state=tk.NORMAL))
                    self.after(0, lambda: messagebox.showerror("Scanfout", "pyodbc is niet geïnstalleerd. Kan MDB-bestanden niet scannen."))
                    return
                
                pyodbc = self._pyodbc
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
                    mdb_filename_without_extension = os.path.splitext(os.path.basename(path))[0]
                    
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
                            item_name = f"{mdb_filename_without_extension}:{row.ProgramNumber}"
                            results.append({'MDB File': os.path.basename(path), 'Item': item_name})
                    elif fallback_table:
                        cursor.execute(f'SELECT ProgramNumber FROM [{fallback_table}]')
                        for row in cursor.fetchall():
                            item_name = f"{mdb_filename_without_extension}:{row.ProgramNumber}"
                            results.append({'MDB File': os.path.basename(path), 'Item': item_name})
                    else:
                        self.after(0, lambda: self.results_text.insert('end', 
                                  f"Geen tabel met 'ProgramNumber' kolom gevonden in {os.path.basename(path)}\n"))
                    
                    conn.close()
                    self.files = results
                    self.processed_files = 1
                    self.total_files = 1
                    self.after(0, lambda: self._show_results(results, scan_mode, path))
                    self.after(0, lambda: self._update_progress(1, 1))
                    self.after(0, lambda: messagebox.showinfo("Scan voltooid", 
                                                             f"Scan voltooid. {len(results)} resultaten gevonden."))
                except Exception as e:
                    self.after(0, lambda: self.results_text.insert('end', 
                              f"Fout bij verwerken van {os.path.basename(path)}: {str(e)}\n"))
                    self.after(0, lambda: messagebox.showerror("Scanfout", 
                                                               f"Fout bij het scannen van het MDB-bestand: {str(e)}"))
            else:
                # Directory scan for .hop/.hops
                def count_files():
                    total_files = 0
                    for root, _, filenames in os.walk(path):
                        for filename in filenames:
                            if filename.lower().endswith(('.hop', '.hops')):
                                total_files += 1
                    return total_files
                
                user_basis_map_setting = self.base_dir_var.get().strip()
                if DEBUG:
                    print(f"[DEBUG] OPUS scan started for directory: {path}. User 'Basis map' setting: '{user_basis_map_setting}'.")

                self.total_files = count_files()
                if DEBUG:
                    print(f"[DEBUG] Total .hop/.hops files found: {self.total_files}")
                
                if self.total_files == 0:
                    self.after(0, lambda: self.results_text.insert('end', f"Geen .hop/.hops bestanden gevonden in {path}\n"))
                    self.after(0, lambda: self.scan_button.config(state=tk.NORMAL))
                    return
                
                found_files = []
                for root, _, filenames_in_loop in os.walk(path):
                    for filename_item in filenames_in_loop:
                        if filename_item.lower().endswith(('.hop', '.hops')):
                            full_hop_path = os.path.join(root, filename_item)
                            item_to_display = ""

                            if not user_basis_map_setting:
                                item_to_display = full_hop_path
                            else:
                                item_to_display = filename_item
                            
                            found_files.append({'Item': item_to_display})
                            self.processed_files += 1
                            if self.processed_files % 10 == 0 or self.processed_files == self.total_files:
                                self.after(0, lambda: self._update_progress(self.processed_files, self.total_files))
                
                self.files = found_files
                if DEBUG:
                    print(f"[DEBUG] Files to show: {len(found_files)}")
                self.after(0, lambda: self._show_results(found_files, scan_mode, path))
                self.after(0, lambda: self._update_progress(self.total_files, self.total_files))
                self.after(0, lambda: self.scan_button.config(state=tk.NORMAL))
                self.after(0, lambda: messagebox.showinfo("Scan voltooid", 
                                                         f"Scan voltooid. {len(found_files)} bestanden gevonden."))
        except Exception as e:
            if DEBUG:
                print(f"[DIAG ERROR] Exception in _scan_thread: {e}")
            self.after(0, lambda: self.results_text.insert('end', f"[DIAG ERROR] Exception in _scan_thread: {e}\n"))
            self.after(0, lambda: self.scan_button.config(state=tk.NORMAL))
        finally:
            self.scanning = False
            self.after(0, lambda: self._create_excel(path, scan_mode))

    def _create_excel(self, directory, scan_mode="OPUS"):
        if DEBUG:
            print(f'[DIAG] creating excel in import_panel.py {time.time()}')
        
        if not hasattr(self, 'files') or not self.files:
            self.results_text.insert('end', "No files to save to Excel.\n")
            return
        
        try:
            pd = self._ensure_pandas()
            df = pd.DataFrame(self.files)
            
            export_dir = directory
            if scan_mode == "GANNOMAT" and os.path.isfile(directory):
                export_dir = os.path.dirname(directory)
                folder_name = os.path.splitext(os.path.basename(directory))[0]
            else:
                folder_name = os.path.basename(os.path.normpath(directory))
            
            if scan_mode == "GANNOMAT":
                if 'Item' in df.columns:
                    df = df[['Item']]
                    df['Status'] = ''
                excel_path = os.path.join(export_dir, f"{folder_name}.xlsx")
            else:
                if 'Status' not in df.columns:
                    df['Status'] = ''
                excel_path = os.path.join(export_dir, f"{folder_name}.xlsx")
            
            df.to_excel(excel_path, index=False)
            self.results_text.insert('end', f"Excel bestand opgeslagen: {excel_path}\n")
        except Exception as e:
            self.results_text.insert('end', f"Fout bij opslaan van Excel: {e}\n")

    def _update_progress(self, processed, total):
        progress = (processed / total) * 100 if total > 0 else 0
        self.progress_var.set(progress)
        self.status_label.config(text=f"{processed} van {total} bestanden verwerkt...")

    def _show_results(self, results, scan_mode, path):
        self.results_text.delete(1.0, tk.END)
        if scan_mode == "GANNOMAT":
            self.results_text.insert(tk.END, f"Scanned file: {os.path.basename(path)} (mode: {scan_mode})\n")
            for row in results:
                self.results_text.insert(tk.END, f"{row['Item']}\n")
        else:
            self.results_text.insert(tk.END, f"Scanned directory: {path} (mode: {scan_mode})\n")
            for row in results:
                self.results_text.insert(tk.END, f"{row['Item']}\n")

    def browse_directory(self):
        scan_mode = self.scan_mode_var.get() if hasattr(self, 'scan_mode_var') else "OPUS"
        if scan_mode == "GANNOMAT":
            filetypes = [("Access Database", "*.mdb;*.accdb"), ("All Files", "*.*")]
            file_path = filedialog.askopenfilename(title="Selecteer MDB/ACCDB-bestand", filetypes=filetypes)
            if file_path:
                self.directory_var.set(file_path)
        else:
            directory = filedialog.askdirectory()
            if directory:
                self.directory_var.set(directory)

    def browse_base_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.base_dir_var.set(directory)

    def on_scan_mode_change(self, event=None):
        self.update_browse_button()
        self.save_config()

    def update_browse_button(self):
        scan_mode = self.scan_mode_var.get() if hasattr(self, 'scan_mode_var') else "OPUS"
        if scan_mode == "GANNOMAT":
            self.dir_btn.config(text="Bestand kiezen")
            self.directory_frame.config(text="Selecteer MDB/ACCDB-bestand")
        else:
            self.dir_btn.config(text="Bladeren")
            self.directory_frame.config(text="Selecteer map")

    def destroy(self):
        """Clean up when panel is destroyed"""
        self.scanning = False
        super().destroy()