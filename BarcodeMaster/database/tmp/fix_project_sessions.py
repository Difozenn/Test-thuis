#!/usr/bin/env python3
"""
Fix missing project_sessions entries for batch projects
"""
import sqlite3
from datetime import datetime

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== Fixing Project Sessions for Batch Projects ===\n")

# Find projects that have logs but no project_sessions
c.execute("""
    SELECT DISTINCT l.project, 
           MIN(l.timestamp) as first_log,
           MAX(l.timestamp) as last_log,
           MAX(CASE WHEN l.event = 'AFGEMELD' THEN l.timestamp END) as afgemeld_time
    FROM logs l
    LEFT JOIN project_sessions ps ON l.project = ps.project
    WHERE ps.project IS NULL
    AND l.project IS NOT NULL
    AND l.project != ''
    AND DATE(l.timestamp) = DATE('now')
    GROUP BY l.project
""")

projects_to_fix = c.fetchall()

for project in projects_to_fix:
    project_name = project[0]
    first_log = project[1]
    last_log = project[2]
    afgemeld_time = project[3]
    
    # Calculate duration in minutes
    if first_log and last_log:
        start_dt = datetime.fromisoformat(first_log)
        end_dt = datetime.fromisoformat(afgemeld_time) if afgemeld_time else datetime.fromisoformat(last_log)
        duration_minutes = (end_dt - start_dt).total_seconds() / 60
        
        print(f"Creating project_sessions for: {project_name}")
        print(f"  Start: {first_log}")
        print(f"  End: {afgemeld_time or last_log}")
        print(f"  Duration: {duration_minutes:.1f} minutes")
        
        # Create project_sessions entry
        status = 'completed' if afgemeld_time else 'active'
        c.execute("""
            INSERT OR REPLACE INTO project_sessions 
            (project, start_time, end_time, total_duration_minutes, status, total_items)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (project_name, first_log, afgemeld_time or last_log, duration_minutes, status))
        
        print(f"  Created with status: {status}\n")

conn.commit()

# Now verify the idle time calculations
print("\n=== Verifying Idle Time Calculations ===\n")

projects = ['MO06787_Dressing_A_deel2_(5-16)', 'MO06797_Bureaukast_(15-16)']

for project in projects:
    # Get project session
    c.execute("""
        SELECT total_duration_minutes, status
        FROM project_sessions
        WHERE project = ?
    """, (project,))
    
    ps = c.fetchone()
    if ps:
        project_time = ps[0]
        
        # Get allocated work time for this project
        c.execute("""
            SELECT 
                SUM(
                    CASE 
                        WHEN s.session_type = 'SCANNER' AND sp.item_count IS NOT NULL THEN
                            -- Proportional allocation for batch
                            s.work_duration_minutes * sp.item_count / 
                            (SELECT SUM(sp2.item_count) FROM session_projects sp2 WHERE sp2.session_id = s.session_id)
                        ELSE
                            -- Full time for non-batch
                            s.work_duration_minutes
                    END
                ) as allocated_work_time
            FROM sessions s
            LEFT JOIN session_projects sp ON s.session_id = sp.session_id AND sp.project = ?
            WHERE s.project = ? OR sp.project = ?
        """, (project, project, project))
        
        work_time = c.fetchone()[0] or 0
        idle_time = project_time - work_time
        idle_percent = (idle_time / project_time * 100) if project_time > 0 else 0
        
        print(f"{project}:")
        print(f"  Project Time: {project_time:.1f} min")
        print(f"  Work Time: {work_time:.1f} min")
        print(f"  Idle Time: {idle_time:.1f} min ({idle_percent:.1f}%)")
        print()

conn.close()
print("✓ Done!")