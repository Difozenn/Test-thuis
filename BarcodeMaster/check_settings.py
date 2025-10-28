import sqlite3
import json

# Connect to database
conn = sqlite3.connect('database/central_logging.sqlite')
cursor = conn.cursor()

# Check app_settings table
cursor.execute("SELECT setting_key, setting_value FROM app_settings WHERE setting_key LIKE '%path%' OR setting_key LIKE '%user%'")
settings = cursor.fetchall()

print("User and path settings in database:")
for key, value in settings:
    print(f"\n{key}:")
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            for k, v in parsed.items():
                print(f"  {k}: {v}")
        elif isinstance(parsed, list):
            for item in parsed:
                print(f"  - {item}")
        else:
            print(f"  {parsed}")
    except:
        print(f"  {value}")

conn.close()
