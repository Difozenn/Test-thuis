import pyodbc
import pandas as pd
import os

# Path to your .mdb file
mdb_file = r"c:\Users\Rob_v\Desktop\Test-main\Hops-File-logger-main\0520_MO07987_TV-wand (1-1).Mdb"

# Output Excel file
excel_file = os.path.splitext(mdb_file)[0] + '.xlsx'

# Connection string for Access .mdb files
conn_str = (
    r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
    rf'DBQ={mdb_file};'
)

# Connect to the database
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Get all table names
tables = [row.table_name for row in cursor.tables(tableType='TABLE')]

# Export each table to a separate sheet in Excel
with pd.ExcelWriter(excel_file) as writer:
    for table in tables:
        df = pd.read_sql(f'SELECT * FROM [{table}]', conn)
        df.to_excel(writer, sheet_name=table[:31], index=False)  # Excel sheet names max 31 chars
        print(f"Exported table '{table}' to Excel sheet '{table[:31]}'")

cursor.close()
conn.close()

print(f"All tables exported to {excel_file}")
