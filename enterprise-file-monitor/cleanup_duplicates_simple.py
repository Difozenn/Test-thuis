#!/usr/bin/env python3
"""
Simple cleanup script using sqlite3 to remove duplicate tool usage entries.
"""

import sqlite3
import os

def cleanup_duplicates():
    conn = sqlite3.connect('enterprise_monitor.db')
    cursor = conn.cursor()
    
    # First, let's see what we have
    cursor.execute("""
        SELECT cnc_analysis_id, tool_number, COUNT(*) as count, 
               GROUP_CONCAT(id) as ids,
               GROUP_CONCAT(total_time) as times
        FROM tool_usage 
        GROUP BY cnc_analysis_id, tool_number 
        HAVING COUNT(*) > 1
    """)
    
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print("No duplicate tool entries found")
        return
    
    print(f"Found {len(duplicates)} groups of duplicate tool entries")
    
    total_removed = 0
    
    for cnc_id, tool_num, count, ids_str, times_str in duplicates:
        ids = [int(x) for x in ids_str.split(',')]
        times = [float(x) for x in times_str.split(',')]
        
        print(f"\nCNC Analysis {cnc_id}, Tool T{tool_num}: {count} entries")
        
        # Find the entry with the most reasonable time (< 100s)
        best_idx = -1
        for i, time_val in enumerate(times):
            print(f"  Entry ID {ids[i]}: {time_val:.1f}s")
            if 0 < time_val < 100 and best_idx == -1:
                best_idx = i
        
        # If no reasonable time found, keep the last (newest) entry
        if best_idx == -1:
            best_idx = len(ids) - 1
        
        # Delete all except the best entry
        ids_to_delete = [ids[i] for i in range(len(ids)) if i != best_idx]
        
        if ids_to_delete:
            print(f"  Keeping ID {ids[best_idx]} ({times[best_idx]:.1f}s), removing {len(ids_to_delete)} duplicates")
            placeholders = ','.join('?' * len(ids_to_delete))
            cursor.execute(f"DELETE FROM tool_usage WHERE id IN ({placeholders})", ids_to_delete)
            total_removed += len(ids_to_delete)
    
    conn.commit()
    print(f"\nTotal removed: {total_removed} duplicate entries")
    
    # Show current data for the most recent analysis
    cursor.execute("""
        SELECT e.id, e.timestamp, c.id, c.file_path
        FROM event e
        JOIN cnc_analysis c ON c.event_id = e.id
        WHERE e.event_type = 'cnc_analysis'
        ORDER BY e.timestamp DESC
        LIMIT 1
    """)
    
    recent = cursor.fetchone()
    if recent:
        event_id, timestamp, cnc_id, file_path = recent
        print(f"\nMost recent CNC analysis (Event {event_id}):")
        print(f"  File: {os.path.basename(file_path)}")
        print(f"  Timestamp: {timestamp}")
        
        cursor.execute("""
            SELECT tool_number, total_time, cutting_time, total_distance
            FROM tool_usage
            WHERE cnc_analysis_id = ?
            ORDER BY tool_number
        """, (cnc_id,))
        
        tools = cursor.fetchall()
        print(f"  Tool usage ({len(tools)} tools):")
        for tool_num, total_time, cutting_time, distance in tools:
            print(f"    T{tool_num}: total={total_time:.1f}s, cutting={cutting_time:.1f}s, distance={distance:.1f}mm")
    
    conn.close()

if __name__ == "__main__":
    print("Tool Usage Duplicate Cleanup")
    print("=" * 50)
    cleanup_duplicates()