#!/usr/bin/env python3
"""
Test to verify NESTING batch session issue with exact data from user
"""

import sqlite3
from datetime import datetime

db_path = '/home/difusion/Projects/BarcodeMaster/database/central_logging.sqlite'

def check_nesting_data():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    project = 'MO07834_Boekenkast_Rep_VL5'
    user = 'NESTING'
    
    print("=== Checking NESTING item count in logs ===")
    c.execute("""
        SELECT event, status, item_count, timestamp, details
        FROM logs
        WHERE user = ? AND LOWER(project) = LOWER(?)
        ORDER BY timestamp
    """, (user, project))
    
    logs = c.fetchall()
    for log in logs:
        print(f"Event: {log['event']}, Status: {log['status']}, Items: {log['item_count']}, Time: {log['timestamp']}")
    
    print("\n=== Checking MAX item count for NESTING ===")
    c.execute("""
        SELECT MAX(COALESCE(item_count, 0)) as project_items
        FROM logs
        WHERE user = ? AND LOWER(project) = LOWER(?)
        AND item_count > 0
    """, (user, project))
    
    result = c.fetchone()
    print(f"MAX item count for NESTING: {result['project_items']}")
    
    print("\n=== Checking NESTING sessions ===")
    c.execute("""
        SELECT session_id, session_type, project, status, start_time, end_time, work_duration_minutes, item_count
        FROM sessions
        WHERE user = ?
        ORDER BY start_time DESC
        LIMIT 5
    """, (user,))
    
    sessions = c.fetchall()
    for session in sessions:
        print(f"Session: {session['session_id']}")
        print(f"  Type: {session['session_type']}, Project: {session['project']}")
        print(f"  Status: {session['status']}, Duration: {session['work_duration_minutes']} min")
        print(f"  Items: {session['item_count']}")
    
    print("\n=== Checking if batch session processed this project ===")
    c.execute("""
        SELECT 
            s.session_id,
            s.start_time,
            s.end_time,
            s.work_duration_minutes,
            s.status
        FROM sessions s
        WHERE s.user = ? 
        AND s.session_type = 'SCANNER' 
        AND s.project IS NULL 
        AND (s.status = 'active' OR s.status = 'completed')
        AND EXISTS (
            SELECT 1 FROM logs l
            WHERE l.user = s.user
            AND LOWER(l.project) = LOWER(?)
            AND l.timestamp >= s.start_time
            AND (s.end_time IS NULL OR l.timestamp <= s.end_time)
        )
        ORDER BY s.start_time DESC
    """, (user, project))
    
    batch_sessions = c.fetchall()
    for batch in batch_sessions:
        print(f"\nBatch session found: {batch['session_id']}")
        print(f"  Status: {batch['status']}")
        print(f"  Duration: {batch['work_duration_minutes']} min")
        
        # Get all projects in this batch
        if batch['end_time']:
            c.execute("""
                SELECT DISTINCT project, SUM(COALESCE(item_count, 0)) as items
                FROM logs
                WHERE user = ?
                AND timestamp BETWEEN ? AND ?
                AND project IS NOT NULL
                GROUP BY project
            """, (user, batch['start_time'], batch['end_time']))
        else:
            c.execute("""
                SELECT DISTINCT project, SUM(COALESCE(item_count, 0)) as items
                FROM logs
                WHERE user = ?
                AND timestamp >= ?
                AND project IS NOT NULL
                GROUP BY project
            """, (user, batch['start_time']))
        
        projects = c.fetchall()
        print(f"  Projects in batch: {len(projects)}")
        for proj in projects:
            print(f"    - {proj['project']}: {proj['items']} items")
    
    conn.close()

if __name__ == "__main__":
    check_nesting_data()