#!/usr/bin/env python3
import sqlite3
from datetime import datetime

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== Testing Statistics Query Patterns ===\n")

# Check current SCANNER sessions structure
print("1. SCANNER sessions with project field:")
c.execute("""
    SELECT session_id, user, session_type, project, item_count, status
    FROM sessions 
    WHERE session_type = 'SCANNER' 
    AND project IS NOT NULL
    AND status = 'completed'
    LIMIT 5
""")
results = c.fetchall()
print(f"Found {len(results)} SCANNER sessions with project field filled")

print("\n2. SCANNER sessions linked via session_projects:")
c.execute("""
    SELECT s.session_id, s.user, s.session_type, sp.project, sp.item_count, s.status
    FROM sessions s
    JOIN session_projects sp ON s.session_id = sp.session_id
    WHERE s.session_type = 'SCANNER' 
    AND s.status = 'completed'
    LIMIT 5
""")
results = c.fetchall()
print(f"Found {len(results)} SCANNER sessions linked via session_projects")
for row in results:
    print(f"  Session: {row['session_id']}, Project: {row['project']}, Items: {row['item_count']}")

print("\n3. Testing batch allocation query (OLD pattern - project field):")
c.execute("""
    WITH BatchAllocation AS (
        SELECT 
            s.user,
            s.project,
            s.session_type,
            s.item_count,
            COUNT(*) as session_count
        FROM sessions s
        WHERE s.session_type = 'SCANNER' 
        AND s.project IS NOT NULL
        AND s.status = 'completed'
        GROUP BY s.user, s.project
    )
    SELECT user, COUNT(DISTINCT project) as project_count, SUM(item_count) as total_items
    FROM BatchAllocation
    GROUP BY user
""")
for row in c.fetchall():
    print(f"  User: {row[0]}, Projects: {row[1]}, Items: {row[2]}")

print("\n4. Testing batch allocation query (NEW pattern - session_projects):")
c.execute("""
    WITH BatchAllocation AS (
        SELECT 
            s.user,
            sp.project,
            s.session_type,
            sp.item_count,
            COUNT(*) as session_count
        FROM sessions s
        JOIN session_projects sp ON s.session_id = sp.session_id
        WHERE s.session_type = 'SCANNER' 
        AND s.status = 'completed'
        GROUP BY s.user, sp.project
    )
    SELECT user, COUNT(DISTINCT project) as project_count, SUM(item_count) as total_items
    FROM BatchAllocation
    GROUP BY user
""")
for row in c.fetchall():
    print(f"  User: {row[0]}, Projects: {row[1]}, Items: {row[2]}")

print("\n5. Main batch sessions (project = NULL):")
c.execute("""
    SELECT session_id, user, start_time, end_time, work_duration_minutes, status
    FROM sessions 
    WHERE session_type = 'SCANNER' 
    AND project IS NULL
    AND status = 'completed'
    ORDER BY start_time DESC
    LIMIT 5
""")
for row in c.fetchall():
    print(f"  Session: {row['session_id']}, User: {row['user']}, Duration: {row['work_duration_minutes']}min")

conn.close()