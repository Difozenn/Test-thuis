#!/usr/bin/env python3
"""
Test that statistics queries work with session_projects linked data
"""
import sqlite3
from datetime import datetime

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'

def test_statistics_queries():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("=== Testing Statistics Queries with session_projects ===\n")
    
    # Test 1: Batch allocation query (from productivity metrics)
    print("1. Testing batch allocation query:")
    c.execute("""
        WITH BatchProjects AS (
            -- Get all projects linked to SCANNER sessions via session_projects
            SELECT 
                s.user,
                s.session_id,
                sp.project,
                s.session_type,
                sp.item_count,
                s.work_duration_minutes,
                s.start_time,
                s.end_time
            FROM sessions s
            JOIN session_projects sp ON s.session_id = sp.session_id
            WHERE s.session_type = 'SCANNER' 
            AND s.status = 'completed'
            AND s.user = 'TEST_USER'
        ),
        BatchAllocation AS (
            -- For SCANNER sessions, allocate time proportionally based on items
            SELECT 
                bp.user,
                bp.project,
                bp.session_type,
                bp.item_count,
                -- Calculate proportional time allocation
                CASE 
                    WHEN (SELECT SUM(item_count) FROM BatchProjects bp2 WHERE bp2.session_id = bp.session_id) > 0 THEN
                        bp.item_count * 1.0 / (SELECT SUM(item_count) FROM BatchProjects bp2 WHERE bp2.session_id = bp.session_id) * bp.work_duration_minutes
                    ELSE 
                        bp.work_duration_minutes / NULLIF((SELECT COUNT(*) FROM BatchProjects bp2 WHERE bp2.session_id = bp.session_id), 0)
                END as allocated_duration_minutes
            FROM BatchProjects bp
        )
        SELECT 
            user,
            COUNT(DISTINCT project) as projects_worked,
            SUM(item_count) as total_items,
            ROUND(SUM(allocated_duration_minutes), 2) as total_allocated_minutes,
            ROUND(SUM(item_count) * 60.0 / NULLIF(SUM(allocated_duration_minutes), 0), 2) as items_per_hour
        FROM BatchAllocation
        GROUP BY user
    """)
    
    result = c.fetchone()
    if result:
        print(f"  User: {result['user']}")
        print(f"  Projects: {result['projects_worked']}")
        print(f"  Total Items: {result['total_items']}")
        print(f"  Total Minutes: {result['total_allocated_minutes']}")
        print(f"  Items/Hour: {result['items_per_hour']}")
    else:
        print("  No results found")
    
    print("\n2. Testing project-level time allocation:")
    c.execute("""
        WITH BatchProjects AS (
            SELECT 
                s.session_id,
                sp.project,
                sp.item_count,
                s.work_duration_minutes
            FROM sessions s
            JOIN session_projects sp ON s.session_id = sp.session_id
            WHERE s.session_type = 'SCANNER' 
            AND s.status = 'completed'
            AND s.user = 'TEST_USER'
        )
        SELECT 
            project,
            item_count,
            work_duration_minutes as session_minutes,
            ROUND(
                item_count * 1.0 / (SELECT SUM(item_count) FROM BatchProjects bp2 WHERE bp2.session_id = bp.session_id) * work_duration_minutes,
                2
            ) as allocated_minutes
        FROM BatchProjects bp
        ORDER BY project
    """)
    
    for row in c.fetchall():
        print(f"  Project: {row['project']}")
        print(f"    Items: {row['item_count']}")
        print(f"    Session Total: {row['session_minutes']} min")
        print(f"    Allocated: {row['allocated_minutes']} min")
    
    print("\n3. Verify session_projects linking:")
    c.execute("""
        SELECT 
            COUNT(DISTINCT s.session_id) as scanner_sessions,
            COUNT(DISTINCT sp.project) as linked_projects,
            SUM(sp.item_count) as total_items_linked
        FROM sessions s
        JOIN session_projects sp ON s.session_id = sp.session_id
        WHERE s.session_type = 'SCANNER'
    """)
    
    result = c.fetchone()
    print(f"  SCANNER Sessions: {result['scanner_sessions']}")
    print(f"  Linked Projects: {result['linked_projects']}")
    print(f"  Total Items: {result['total_items_linked']}")
    
    conn.close()
    print("\n✓ All queries executed successfully with session_projects linking!")

if __name__ == "__main__":
    test_statistics_queries()