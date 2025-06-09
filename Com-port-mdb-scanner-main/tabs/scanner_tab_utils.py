import os
import pandas as pd
import pyodbc
import tkinter as tk
from tkinter import messagebox
from config_utils import update_config, get_config_path

def scan_directory(directory, base_dir, results_text=None):
    total_files = 0
    processed_files = 0
    def count_files():
        total = 0
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if filename.lower().endswith(('.hop', '.hops')):
                    total += 1
        return total
    total_files = count_files()
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.lower().endswith(('.hop', '.hops')):
                try:
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, base_dir)
                    files.append({'Relative Path': relative_path})
                    processed_files += 1
                except Exception as e:
                    if results_text is not None:
                        results_text.insert(tk.END, f"Error processing {filename}: {str(e)}\n")
                        results_text.see(tk.END)
    return files

def scan_mdb_files(mdb_file, results_text=None):
    results = []
    try:
        conn_str = (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            f'DBQ={mdb_file};'
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
                results.append({'MDB File': os.path.basename(mdb_file), 'ProgramNumber': row.ProgramNumber})
        elif fallback_table:
            cursor.execute(f'SELECT ProgramNumber FROM [{fallback_table}]')
            for row in cursor.fetchall():
                results.append({'MDB File': os.path.basename(mdb_file), 'ProgramNumber': row.ProgramNumber})
        else:
            if results_text is not None:
                results_text.insert(tk.END, f"No table with 'ProgramNumber' column found in {os.path.basename(mdb_file)}\n")
                results_text.see(tk.END)
        conn.close()
    except Exception as e:
        if results_text is not None:
            results_text.insert(tk.END, f"Error processing {os.path.basename(mdb_file)}: {str(e)}\n")
            results_text.see(tk.END)
    return results

def create_excel(files, directory, scan_mode="OPUS", results_text=None):
    if not files:
        if results_text is not None:
            results_text.insert(tk.END, "No files to save to Excel.\n")
        return
    df = pd.DataFrame(files)
    folder_name = os.path.basename(os.path.normpath(directory))
    if scan_mode == "GANNOMAT":
        if 'ProgramNumber' in df.columns:
            df = df[['ProgramNumber']]
        if hasattr(directory, 'lower') and directory.lower().endswith('.mdb'):
            mdb_filename = os.path.splitext(os.path.basename(directory))[0]
            excel_path = os.path.join(directory, f"{mdb_filename}_GANNOMAT.xlsx")
        else:
            excel_path = os.path.join(directory, f"{folder_name}_GANNOMAT.xlsx")
    else:
        excel_path = os.path.join(directory, f"{folder_name}_scan.xlsx")
    try:
        df.to_excel(excel_path, index=False)
        if results_text is not None:
            results_text.insert(tk.END, f"\nExcel file saved: {excel_path}\n")
    except Exception as e:
        if results_text is not None:
            results_text.insert(tk.END, f"Error saving Excel: {str(e)}\n")
    if results_text is not None:
        results_text.see(tk.END)
