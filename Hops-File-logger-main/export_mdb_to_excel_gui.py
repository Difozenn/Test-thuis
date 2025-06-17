import tkinter as tk
from tkinter import filedialog, messagebox
import pyodbc
import pandas as pd
import os

class MDBtoExcelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MDB to Excel Exporter")
        self.root.geometry("400x180")
        
        self.mdb_path = tk.StringVar()
        self.status = tk.StringVar()
        
        tk.Label(root, text="Select .mdb file:").pack(pady=5)
        entry = tk.Entry(root, textvariable=self.mdb_path, width=40)
        entry.pack(padx=10)
        tk.Button(root, text="Browse", command=self.browse_mdb).pack(pady=5)
        tk.Button(root, text="Export to Excel", command=self.export).pack(pady=10)
        tk.Label(root, textvariable=self.status, fg="blue").pack(pady=5)

    def browse_mdb(self):
        file_path = filedialog.askopenfilename(
            title="Select MDB file",
            filetypes=[("Access Database", "*.mdb;*.accdb"), ("All Files", "*.*")]
        )
        if file_path:
            self.mdb_path.set(file_path)

    def export(self):
        mdb_file = self.mdb_path.get()
        if not mdb_file or not os.path.exists(mdb_file):
            messagebox.showerror("Error", "Please select a valid .mdb file.")
            return
        excel_file = os.path.splitext(mdb_file)[0] + '.xlsx'
        conn_str = (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            rf'DBQ={mdb_file};'
        )
        try:
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            tables = [row.table_name for row in cursor.tables(tableType='TABLE')]
            if not tables:
                messagebox.showinfo("No Tables", "No tables found in database.")
                return
            with pd.ExcelWriter(excel_file) as writer:
                for table in tables:
                    df = pd.read_sql(f'SELECT * FROM [{table}]', conn)
                    df.to_excel(writer, sheet_name=table[:31], index=False)
            cursor.close()
            conn.close()
            self.status.set(f"Exported to {excel_file}")
            messagebox.showinfo("Success", f"All tables exported to {excel_file}")
        except Exception as e:
            self.status.set(f"Error: {e}")
            messagebox.showerror("Export Error", str(e))

def main():
    root = tk.Tk()
    app = MDBtoExcelApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
