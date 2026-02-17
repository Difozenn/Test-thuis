#!/usr/bin/env python3
import sqlite3
from datetime import datetime

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Check session_projects table
print("=== SESSION_PROJECTS TABLE ===")
c.execute("""
    SELECT sp.*, s.status, s.session_type, s.user
    FROM session_projects sp
    JOIN sessions s ON sp.session_id = s.session_id
    ORDER BY sp.added_time DESC
    LIMIT 10
""")

for row in c.fetchall():
    print(f"Session: {row['session_id']}")
    print(f"  Project: {row['project']}")
    print(f"  User: {row['user']}")
    print(f"  Type: {row['session_type']}")
    print(f"  Status: {row['status']}")
    print(f"  Items: {row['item_count']}")
    print()

# Check current active sessions
print("=== ACTIVE SESSIONS ===")
c.execute("""
    SELECT s.*, 
           GROUP_CONCAT(sp.project) as linked_projects
    FROM sessions s
    LEFT JOIN session_projects sp ON s.session_id = sp.session_id
    WHERE s.status = 'active'
    GROUP BY s.session_id
    ORDER BY s.start_time DESC
""")

for row in c.fetchall():
    print(f"Session: {row['session_id']}")
    print(f"  User: {row['user']}")
    print(f"  Type: {row['session_type']}")
    print(f"  Project field: {row['project']}")
    print(f"  Linked projects: {row['linked_projects']}")
    print()

# Check for a specific project
project = 'MO07455_IT-Room_(A)_(9-19)'
print(f"=== SESSIONS FOR PROJECT {project} ===")

# Direct project match
c.execute("""
    SELECT * FROM sessions 
    WHERE project = ? OR project LIKE ?
""", (project, f'%{project}%'))
direct = c.fetchall()
print(f"Direct project matches: {len(direct)}")

# Via session_projects
c.execute("""
    SELECT s.*, sp.project as linked_project
    FROM sessions s
    JOIN session_projects sp ON s.session_id = sp.session_id
    WHERE sp.project = ?
""", (project,))
linked = c.fetchall()
print(f"Linked via session_projects: {len(linked)}")

# Via project_id
from db_log_api import normalize_project_id
project_id = normalize_project_id(project)
c.execute("""
    SELECT * FROM sessions
    WHERE project_id = ?
""", (project_id,))
by_id = c.fetchall()
print(f"By project_id: {len(by_id)}")

conn.close()