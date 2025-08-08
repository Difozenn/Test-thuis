#!/usr/bin/env python3
"""
Run database migration script to update WorkCalendar table structure
"""
import sqlite3
import os

def migrate_database():
    """Apply Migration 6: Transform WorkCalendar table"""
    # Try different possible database locations
    possible_paths = [
        'file_monitor.db',
        'instance/file_monitor.db',
        os.path.join('instance', 'file_monitor.db')
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print(f"❌ Database file not found in any of these locations: {possible_paths}")
        return False
    
    print(f"📍 Using database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Starting Migration 6: Work Calendar transformation...")
        
        # Check current table structure
        cursor.execute("PRAGMA table_info(work_calendar)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Current columns: {columns}")
        
        # Check if transformation is needed
        needs_transformation = 'work_hours' in columns
        
        if not needs_transformation:
            print("📝 Migration 6: Work calendar already transformed")
            return True
            
        print("📝 Migration 6: Transforming work calendar and creating work schedule config...")
        
        # Create new work_schedule_config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_schedule_config (
                id INTEGER PRIMARY KEY,
                monday_start REAL DEFAULT 8.0,
                monday_end REAL DEFAULT 17.0,
                tuesday_start REAL DEFAULT 8.0,
                tuesday_end REAL DEFAULT 17.0,
                wednesday_start REAL DEFAULT 8.0,
                wednesday_end REAL DEFAULT 17.0,
                thursday_start REAL DEFAULT 8.0,
                thursday_end REAL DEFAULT 17.0,
                friday_start REAL DEFAULT 8.0,
                friday_end REAL DEFAULT 17.0,
                saturday_start REAL DEFAULT 0.0,
                saturday_end REAL DEFAULT 0.0,
                sunday_start REAL DEFAULT 0.0,
                sunday_end REAL DEFAULT 0.0,
                break_start REAL DEFAULT 12.0,
                break_duration REAL DEFAULT 1.0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default work schedule config
        cursor.execute("""
            INSERT INTO work_schedule_config 
            (monday_start, monday_end, tuesday_start, tuesday_end, 
             wednesday_start, wednesday_end, thursday_start, thursday_end,
             friday_start, friday_end, saturday_start, saturday_end,
             sunday_start, sunday_end, break_start, break_duration, is_active)
            VALUES (8.0, 17.0, 8.0, 17.0, 8.0, 17.0, 8.0, 17.0, 8.0, 17.0, 0.0, 0.0, 0.0, 0.0, 12.0, 1.0, 1)
        """)
        print("✅ Created work_schedule_config table with default values")
        
        # Backup existing work_calendar data
        cursor.execute("CREATE TABLE work_calendar_backup AS SELECT * FROM work_calendar")
        print("✅ Created backup of existing work_calendar data")
        
        # Extract holidays from existing data (keep only entries with day_type='holiday' or work_hours=0)
        cursor.execute("""
            SELECT date, notes, day_type 
            FROM work_calendar 
            WHERE day_type = 'holiday' OR work_hours = 0
        """)
        holiday_entries = cursor.fetchall()
        
        # Drop the old work_calendar table
        cursor.execute("DROP TABLE work_calendar")
        print("✅ Dropped old work_calendar table")
        
        # Create new work_calendar table with holiday-only structure
        cursor.execute("""
            CREATE TABLE work_calendar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL UNIQUE,
                is_holiday BOOLEAN DEFAULT 1,
                holiday_type VARCHAR(20) DEFAULT 'company',
                name VARCHAR(100),
                notes VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Created new work_calendar table structure")
        
        # Insert holiday entries into new table
        for date_val, notes, day_type in holiday_entries:
            holiday_type = 'country' if 'country' in str(notes).lower() else 'company'
            cursor.execute("""
                INSERT INTO work_calendar (date, is_holiday, holiday_type, name, notes)
                VALUES (?, 1, ?, ?, ?)
            """, (date_val, holiday_type, notes or day_type, notes))
        
        print(f"✅ Inserted {len(holiday_entries)} holiday entries")
        
        # Create index
        cursor.execute("CREATE INDEX idx_work_calendar_date ON work_calendar (date)")
        
        conn.commit()
        print("✅ Migration 6: Work calendar transformation completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n🎉 Migration completed successfully!")
        print("You can now restart the application.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")