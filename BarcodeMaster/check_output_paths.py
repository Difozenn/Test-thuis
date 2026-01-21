import sqlite3
import json

# Connect to database
conn = sqlite3.connect('database/central_logging.sqlite')
cursor = conn.cursor()

# Check for output paths
cursor.execute("SELECT setting_key, setting_value FROM app_settings WHERE setting_key LIKE '%output%' OR setting_key LIKE '%dir%'")
settings = cursor.fetchall()

print("Output paths in database:")
for key, value in settings:
    print(f"  {key}: {value}")

conn.close()
