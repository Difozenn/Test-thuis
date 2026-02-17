import sqlite3

# Connect to database
conn = sqlite3.connect('database/central_logging.sqlite')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")

# Check for user/path related tables
for table_name in [t[0] for t in tables]:
    if 'user' in table_name.lower() or 'path' in table_name.lower() or 'config' in table_name.lower():
        print(f"\nTable: {table_name}")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print("Columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Show first few rows
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
        rows = cursor.fetchall()
        if rows:
            print("Sample data:")
            for row in rows:
                print(f"  {row}")

conn.close()
