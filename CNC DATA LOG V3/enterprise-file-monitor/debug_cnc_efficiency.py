#!/usr/bin/env python3
"""
Debug script to check why CNC Efficiency Analysis isn't showing on dashboard
"""
import sqlite3
import os
from datetime import datetime, timezone

def debug_cnc_efficiency():
    """Debug CNC efficiency display issues"""
    
    db_path = 'file_monitor.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database file {db_path} not found")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Debugging CNC Efficiency Analysis Display...")
        print("=" * 50)
        
        # 1. Check if cnc_analysis table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cnc_analysis'")
        if not cursor.fetchone():
            print("❌ cnc_analysis table does not exist!")
            return
        else:
            print("✅ cnc_analysis table exists")
        
        # 2. Check total CNC analysis records
        cursor.execute("SELECT COUNT(*) FROM cnc_analysis")
        total_cnc_records = cursor.fetchone()[0]
        print(f"📊 Total CNC analysis records: {total_cnc_records}")
        
        # 3. Check today's events with CNC analysis
        cursor.execute("""
            SELECT DATE(e.timestamp) as date, COUNT(*) as count
            FROM event e
            JOIN cnc_analysis c ON e.id = c.event_id
            WHERE c.cycle_time_seconds IS NOT NULL
            GROUP BY DATE(e.timestamp)
            ORDER BY date DESC
            LIMIT 5
        """)
        
        recent_dates = cursor.fetchall()
        print(f"\n📅 Recent dates with CNC analysis:")
        for date, count in recent_dates:
            print(f"  {date}: {count} events")
        
        # 4. Check today specifically
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) as today_count,
                   SUM(c.cycle_time_seconds) as total_seconds,
                   AVG(c.cycle_time_seconds) as avg_seconds
            FROM event e
            JOIN cnc_analysis c ON e.id = c.event_id
            WHERE DATE(e.timestamp) = ?
              AND c.cycle_time_seconds IS NOT NULL
              AND c.cycle_time_seconds > 0
        """, (today,))
        
        today_data = cursor.fetchone()
        today_count, total_seconds, avg_seconds = today_data
        
        print(f"\n🎯 Today's CNC Analysis ({today}):")
        print(f"  Events with valid CNC analysis: {today_count}")
        print(f"  Total cycle time: {total_seconds or 0} seconds")
        print(f"  Average cycle time: {avg_seconds or 0} seconds")
        
        # 5. Check for invalid records
        cursor.execute("""
            SELECT COUNT(*) as invalid_count
            FROM cnc_analysis c
            JOIN event e ON c.event_id = e.id
            WHERE DATE(e.timestamp) = ?
              AND (c.cycle_time_seconds IS NULL OR c.cycle_time_seconds <= 0)
        """, (today,))
        
        invalid_count = cursor.fetchone()[0]
        print(f"  Invalid records (cycle_time <= 0): {invalid_count}")
        
        # 6. Sample recent CNC analysis data
        cursor.execute("""
            SELECT e.file_path, c.cycle_time_seconds, c.machine_time_minutes, c.tool_changes,
                   e.timestamp
            FROM event e
            JOIN cnc_analysis c ON e.id = c.event_id
            WHERE c.cycle_time_seconds IS NOT NULL
              AND c.cycle_time_seconds > 0
            ORDER BY e.timestamp DESC
            LIMIT 3
        """)
        
        sample_data = cursor.fetchall()
        print(f"\n📋 Sample CNC analysis records:")
        for file_path, cycle_time, machine_time, tool_changes, timestamp in sample_data:
            print(f"  {timestamp}: {os.path.basename(file_path)}")
            print(f"    Cycle time: {cycle_time}s ({cycle_time/60:.1f}min)")
            print(f"    Machine time: {machine_time}min")
            print(f"    Tool changes: {tool_changes}")
        
        # 7. Dashboard condition check
        print(f"\n🎯 Dashboard Display Condition:")
        print(f"  cnc_efficiency exists: {'✅' if today_count > 0 else '❌'}")
        print(f"  cnc_efficiency.total_programs > 0: {'✅' if today_count > 0 else '❌'}")
        print(f"  Section will display: {'✅ YES' if today_count > 0 else '❌ NO - No valid CNC events today'}")
        
        # 8. Recommendations
        print(f"\n💡 Recommendations:")
        if today_count == 0:
            if total_cnc_records == 0:
                print("  - No CNC analysis data in database")
                print("  - Check if C# tray app is running and processing CNC files")
                print("  - Verify CNC file monitoring is enabled")
            else:
                print("  - No CNC events recorded for today")
                print("  - Process some CNC files (.nc, .gcode, etc.) to see the analysis")
                print("  - Check if file monitoring is active for CNC file extensions")
        else:
            print("  - CNC Efficiency Analysis should be visible on dashboard")
            print("  - If not visible, check browser cache or restart Flask app")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error debugging: {e}")

if __name__ == "__main__":
    debug_cnc_efficiency()