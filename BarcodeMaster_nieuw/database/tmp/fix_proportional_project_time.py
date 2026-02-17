#!/usr/bin/env python3
"""
Fix project_sessions to use proportional time for batch projects
"""
import sqlite3
from datetime import datetime

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== Fixing Project Sessions to Use Proportional Time ===\n")

# Find batch sessions and their linked projects
c.execute("""
    SELECT 
        s.session_id,
        s.start_time,
        s.end_time,
        s.work_duration_minutes,
        s.pause_duration_minutes,
        (s.work_duration_minutes + COALESCE(s.pause_duration_minutes, 0)) as total_time,
        GROUP_CONCAT(sp.project || ':' || sp.item_count) as projects,
        SUM(sp.item_count) as total_items
    FROM sessions s
    JOIN session_projects sp ON s.session_id = sp.session_id
    WHERE s.session_type = 'SCANNER'
    GROUP BY s.session_id
    HAVING COUNT(sp.project) > 1
""")

batch_sessions = c.fetchall()

for session in batch_sessions:
    session_id = session[0]
    total_time = session[5]
    total_items = session[7]
    
    print(f"Batch Session: {session_id}")
    print(f"  Total time: {total_time:.1f} min")
    print(f"  Total items: {total_items}")
    
    # Get individual projects
    c.execute("""
        SELECT project, item_count
        FROM session_projects
        WHERE session_id = ?
    """, (session_id,))
    
    for project in c.fetchall():
        project_name = project[0]
        item_count = project[1]
        proportion = item_count / total_items if total_items > 0 else 0
        proportional_duration = total_time * proportion
        
        print(f"\n  Project: {project_name}")
        print(f"    Items: {item_count} ({proportion:.1%})")
        print(f"    Proportional duration: {proportional_duration:.1f} min")
        
        # Update project_sessions with proportional time
        c.execute("""
            UPDATE project_sessions
            SET total_duration_minutes = ?
            WHERE project = ?
        """, (proportional_duration, project_name))
        
        print(f"    ✓ Updated project_sessions")

conn.commit()

print("\n\n=== Verifying Updated Times ===\n")

# Check the updated values
projects = ['MO06787_Dressing_A_deel2_(5-16)', 'MO06797_Bureaukast_(15-16)']

for project in projects:
    c.execute("""
        SELECT 
            ps.total_duration_minutes as project_time,
            (
                SELECT SUM(
                    CASE 
                        WHEN s.session_type = 'SCANNER' AND sp.item_count IS NOT NULL THEN
                            s.work_duration_minutes * sp.item_count / 
                            (SELECT SUM(sp2.item_count) FROM session_projects sp2 WHERE sp2.session_id = s.session_id)
                        ELSE
                            s.work_duration_minutes
                    END
                )
                FROM sessions s
                LEFT JOIN session_projects sp ON s.session_id = sp.session_id AND sp.project = ps.project
                WHERE s.project = ps.project OR sp.project = ps.project
            ) as work_time
        FROM project_sessions ps
        WHERE ps.project = ?
    """, (project,))
    
    row = c.fetchone()
    if row:
        project_time = row[0]
        work_time = row[1] or 0
        idle_time = project_time - work_time
        idle_percent = (idle_time / project_time * 100) if project_time > 0 else 0
        
        print(f"{project}:")
        print(f"  Project Time: {project_time:.1f} min")
        print(f"  Work Time: {work_time:.1f} min")
        print(f"  Idle Time: {idle_time:.1f} min ({idle_percent:.1f}%)")
        print()

conn.close()
print("✓ Done!")