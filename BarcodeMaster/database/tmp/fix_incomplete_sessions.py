#!/usr/bin/env python3
"""
Fix incomplete project_sessions from the last batch session
"""
import sqlite3

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== Fixing Incomplete Project Sessions ===\n")

# Find the completed batch session
c.execute("""
    SELECT 
        s.session_id,
        s.work_duration_minutes,
        s.pause_duration_minutes,
        s.end_time
    FROM sessions s
    WHERE s.session_id = 'NESTING_20250816_181125'
""")

session = c.fetchone()
if session:
    session_id = session[0]
    work_minutes = session[1]
    pause_minutes = session[2] or 0
    end_time = session[3]
    total_time = work_minutes + pause_minutes
    
    print(f"Found completed session: {session_id}")
    print(f"  Total time: {total_time:.1f} min")
    
    # Get projects and their proportions
    c.execute("""
        SELECT 
            project,
            item_count,
            (SELECT SUM(item_count) FROM session_projects WHERE session_id = ?) as total_items
        FROM session_projects
        WHERE session_id = ?
    """, (session_id, session_id))
    
    for project in c.fetchall():
        project_name = project[0]
        item_count = project[1]
        total_items = project[2]
        
        if total_items > 0:
            proportion = item_count / total_items
            proportional_duration = total_time * proportion
            
            print(f"\nFixing {project_name}:")
            print(f"  Items: {item_count}/{total_items} ({proportion:.1%})")
            print(f"  Proportional duration: {proportional_duration:.1f} min")
            
            # Update project_sessions
            c.execute("""
                UPDATE project_sessions
                SET status = 'completed',
                    end_time = ?,
                    total_duration_minutes = ?
                WHERE project = ?
            """, (end_time, proportional_duration, project_name))
            
            # Also create AFGEMELD logs
            c.execute("""
                INSERT INTO logs (timestamp, event, details, project, user, status, item_count)
                VALUES (?, 'AFGEMELD', 'Auto-close on session end', ?, 'NESTING', 'AFGEMELD', 0)
            """, (end_time, project_name))
            
            print(f"  ✓ Updated project_sessions and created AFGEMELD log")

conn.commit()
conn.close()
print("\n✓ Done!")