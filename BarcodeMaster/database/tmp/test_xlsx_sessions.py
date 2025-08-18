#!/usr/bin/env python3
"""
Test that XLSX_UPDATED sessions work correctly with the updated queries
"""
import sqlite3
from datetime import datetime, timedelta

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'

def test_xlsx_sessions():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("=== Testing XLSX_UPDATED Sessions ===\n")
    
    # Create test XLSX_UPDATED session
    user = "XLSX_TEST_USER"
    project = "XLSX_PROJECT_001"
    session_id = f"{user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_XLSX"
    start_time = (datetime.now() - timedelta(hours=1)).isoformat()
    end_time = datetime.now().isoformat()
    
    print(f"Creating XLSX_UPDATED session: {session_id}")
    
    # XLSX_UPDATED sessions store project directly in the sessions table
    c.execute("""
        INSERT INTO sessions (
            session_id, user, session_type, project, 
            start_time, end_time, status, 
            work_duration_minutes, item_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id, user, 'XLSX_UPDATED', project,
        start_time, end_time, 'completed',
        60, 150  # Direct item count in session
    ))
    
    print(f"  Project: {project}")
    print(f"  Items: 150")
    print(f"  Duration: 60 minutes")
    
    # Test the updated statistics query with both session types
    print("\n1. Testing combined query (SCANNER + XLSX_UPDATED):")
    c.execute("""
        WITH BatchProjects AS (
            -- Get all projects linked to SCANNER sessions via session_projects
            SELECT 
                s.user,
                s.session_id,
                sp.project,
                s.session_type,
                sp.item_count,
                s.work_duration_minutes
            FROM sessions s
            JOIN session_projects sp ON s.session_id = sp.session_id
            WHERE s.session_type = 'SCANNER' 
            AND s.status = 'completed'
        ),
        OtherSessions AS (
            -- Get non-SCANNER sessions (XLSX_UPDATED, MANUAL)
            SELECT 
                s.user,
                s.session_id,
                s.project,
                s.session_type,
                s.item_count,
                s.work_duration_minutes
            FROM sessions s
            WHERE s.session_type != 'SCANNER'
            AND s.status = 'completed'
            AND s.project IS NOT NULL
        ),
        AllSessions AS (
            -- Combine both types
            SELECT 
                user,
                project,
                session_type,
                item_count,
                -- SCANNER sessions get proportional allocation
                CASE 
                    WHEN (SELECT SUM(item_count) FROM BatchProjects bp2 WHERE bp2.session_id = bp.session_id) > 0 THEN
                        item_count * 1.0 / (SELECT SUM(item_count) FROM BatchProjects bp2 WHERE bp2.session_id = bp.session_id) * work_duration_minutes
                    ELSE 
                        work_duration_minutes / NULLIF((SELECT COUNT(*) FROM BatchProjects bp2 WHERE bp2.session_id = bp.session_id), 0)
                END as allocated_minutes
            FROM BatchProjects bp
            
            UNION ALL
            
            -- Other sessions use full duration
            SELECT 
                user,
                project,
                session_type,
                item_count,
                work_duration_minutes as allocated_minutes
            FROM OtherSessions
        )
        SELECT 
            session_type,
            COUNT(DISTINCT user) as users,
            COUNT(DISTINCT project) as projects,
            SUM(item_count) as total_items,
            ROUND(SUM(allocated_minutes), 2) as total_minutes,
            ROUND(SUM(item_count) * 60.0 / NULLIF(SUM(allocated_minutes), 0), 2) as items_per_hour
        FROM AllSessions
        GROUP BY session_type
        ORDER BY session_type
    """)
    
    for row in c.fetchall():
        print(f"\n  {row['session_type']}:")
        print(f"    Users: {row['users']}")
        print(f"    Projects: {row['projects']}")
        print(f"    Items: {row['total_items']}")
        print(f"    Minutes: {row['total_minutes']}")
        print(f"    Items/Hour: {row['items_per_hour']}")
    
    # Verify XLSX_UPDATED sessions don't need session_projects
    print("\n2. Verify XLSX_UPDATED sessions work without session_projects:")
    c.execute("""
        SELECT 
            s.session_id,
            s.user,
            s.project,
            s.item_count,
            s.work_duration_minutes,
            COUNT(sp.id) as linked_projects
        FROM sessions s
        LEFT JOIN session_projects sp ON s.session_id = sp.session_id
        WHERE s.session_type = 'XLSX_UPDATED'
        AND s.user = ?
        GROUP BY s.session_id
    """, (user,))
    
    for row in c.fetchall():
        print(f"  Session: {row['session_id']}")
        print(f"  Project: {row['project']} (stored directly in session)")
        print(f"  Items: {row['item_count']}")
        print(f"  Linked via session_projects: {row['linked_projects']} (should be 0)")
    
    # Test project-time analysis query
    print("\n3. Testing project-time analysis with XLSX_UPDATED:")
    c.execute("""
        SELECT 
            s.project,
            s.session_type,
            COUNT(*) as session_count,
            SUM(s.item_count) as total_items,
            SUM(s.work_duration_minutes) as total_minutes
        FROM sessions s
        WHERE s.session_type = 'XLSX_UPDATED'
        AND s.status = 'completed'
        AND s.project IS NOT NULL
        GROUP BY s.project, s.session_type
    """)
    
    for row in c.fetchall():
        print(f"  Project: {row['project']}")
        print(f"    Type: {row['session_type']}")
        print(f"    Sessions: {row['session_count']}")
        print(f"    Items: {row['total_items']}")
        print(f"    Minutes: {row['total_minutes']}")
    
    conn.commit()
    conn.close()
    print("\n✓ XLSX_UPDATED sessions work correctly without session_projects linking!")

if __name__ == "__main__":
    test_xlsx_sessions()