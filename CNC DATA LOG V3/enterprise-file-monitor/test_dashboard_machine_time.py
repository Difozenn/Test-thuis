#!/usr/bin/env python3
"""
Test dashboard machine time vs work hours calculation
"""
import sqlite3
import os

def test_dashboard_calculation():
    """Test dashboard machine time calculation"""
    
    db_path = 'instance/file_monitor.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database file {db_path} not found")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Testing Dashboard Machine Time vs Work Hours calculation...")
        
        # Simulate the dashboard query
        cursor.execute("""
            SELECT DATE(e.timestamp) as date,
                   SUM(c.cycle_time_seconds) as total_cycle_time_seconds,
                   COUNT(e.id) as event_count
            FROM event e
            JOIN cnc_analysis c ON e.id = c.event_id
            WHERE c.cycle_time_seconds IS NOT NULL
            GROUP BY DATE(e.timestamp)
            ORDER BY date DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if not result:
            print("❌ No CNC events found")
            return False
        
        date, total_cycle_seconds, event_count = result
        total_machine_hours = total_cycle_seconds / 3600
        
        print(f"\n📊 Dashboard Calculation for {date}:")
        print(f"  Events with CNC analysis: {event_count}")
        print(f"  Total cycle time: {total_cycle_seconds} seconds")
        print(f"  Total machine hours: {total_machine_hours:.3f} hours")
        
        # Get work hours for comparison
        cursor.execute("""
            SELECT work_hours, start_time, end_time 
            FROM work_calendar 
            WHERE date = ?
        """, (date,))
        
        work_result = cursor.fetchone()
        if work_result:
            work_hours, start_time, end_time = work_result
            print(f"  Work hours: {work_hours} hours ({start_time}-{end_time})")
            
            # Calculate utilization
            if work_hours and work_hours > 0:
                utilization = (total_machine_hours / work_hours) * 100
                print(f"  Machine utilization: {utilization:.1f}%")
            
        print(f"\n✅ Dashboard should show:")
        print(f"  Machine Time: {total_machine_hours:.3f} hours (not 2.2 hours)")
        print(f"  This is the TOTAL machine time, not just overhead time")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing dashboard: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    test_dashboard_calculation()