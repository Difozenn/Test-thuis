#!/usr/bin/env python3
"""
Quick import script for Accura SystemLog files
Run this to import all historical data from the accura folder
"""

import os
import re
from datetime import datetime
from glob import glob

# Import your app context
from app import app, db, Event, CNCAnalysis, User, MonitoredPath

def import_accura_logs(username='admin', accura_folder='accura'):
    """Import all SystemLog files from the accura folder"""
    
    with app.app_context():
        # Get the user
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"Error: User '{username}' not found")
            return
        
        print(f"Importing for user: {username} (ID: {user.id})")
        
        # Ensure Accura machine type is set
        if user.machine_type != 'accura':
            print(f"Warning: User machine type is '{user.machine_type}', changing to 'accura'")
            user.machine_type = 'accura'
            db.session.commit()
        
        # Get or create monitored path
        accura_path = MonitoredPath.query.filter_by(
            user_id=user.id,
            path=accura_folder
        ).first()
        
        if not accura_path:
            accura_path = MonitoredPath(
                path=accura_folder,
                user_id=user.id,
                is_active=True,
                is_directory=True,
                recursive=False,
                description='Accura SystemLog monitoring'
            )
            db.session.add(accura_path)
            db.session.commit()
            print(f"Created monitored path for '{accura_folder}' directory")
        
        # Find all SystemLog files (including .txt and .bk* backups)
        log_files = []
        log_files.extend(glob(os.path.join(accura_folder, 'SystemLog*.txt')))
        log_files.extend(glob(os.path.join(accura_folder, 'SystemLog.bk*')))
        log_files.sort()  # Process in chronological order
        
        print(f"Found {len(log_files)} SystemLog files")
        
        total_imported = 0
        
        for log_file in log_files:
            print(f"\nProcessing: {log_file}")
            
            current_date = None
            entries_count = 0
            
            # Try to get date from filename
            filename = os.path.basename(log_file)
            if filename == 'SystemLog.txt':
                # Current file, use today's date or date from content
                pass
            else:
                # Try SystemLog_YYYYMMDD.txt format
                date_match = re.search(r'SystemLog_(\d{8})\.txt', filename)
                if date_match:
                    date_str = date_match.group(1)
                    current_date = datetime.strptime(date_str, '%Y%m%d').date()
                    print(f"  Date from filename: {current_date}")
            
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check for date line (DD.MM.YYYY)
                    date_match = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', line)
                    if date_match:
                        day = int(date_match.group(1))
                        month = int(date_match.group(2))
                        year = int(date_match.group(3))
                        current_date = datetime(year, month, day).date()
                        print(f"  Date from content: {current_date}")
                        continue
                    
                    # Skip if no date yet
                    if not current_date:
                        continue
                    
                    # Parse entry lines (HH:mm:ss  Entry text  [data])
                    time_match = re.match(r'^(\d{2}):(\d{2}):(\d{2})\s+(.+)', line)
                    if not time_match:
                        continue
                    
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    second = int(time_match.group(3))
                    entry_text = time_match.group(4)
                    
                    # Create timestamp
                    timestamp = datetime.combine(current_date, datetime.min.time())
                    timestamp = timestamp.replace(hour=hour, minute=minute, second=second)
                    
                    # Check for target patterns
                    entry_name = None
                    machine_time_seconds = 20  # Default 20 seconds
                    
                    if 'M1 von KAM1 Retour1' in entry_text:
                        # Parse BC and B (width) values
                        full_match = re.search(r'M1 von KAM1 Retour1 BC=\s*(\d+).*?B=\s*(\d+)', entry_text)
                        if full_match:
                            bc_num = full_match.group(1)
                            width = int(full_match.group(2))
                            entry_name = f"M1 von KAM1 Retour1 BC={bc_num} (B={width})"
                            
                            # Determine machine time based on width
                            if width >= 2400:
                                machine_time_seconds = 60  # 60 seconds for wide pieces
                            else:
                                machine_time_seconds = 20  # 20 seconds for narrow pieces
                                
                    elif 'Rifo 2 Ende erreicht' in entry_text:
                        entry_name = 'Rifo 2 Ende erreicht'
                        machine_time_seconds = 20  # Default time for Rifo
                    
                    if not entry_name:
                        continue
                    
                    # Check for duplicate
                    existing = db.session.query(Event).filter(
                        Event.user_id == user.id,
                        Event.timestamp == timestamp,
                        Event.file_path == log_file
                    ).first()
                    
                    if existing:
                        continue
                    
                    # Create event
                    event = Event(
                        timestamp=timestamp,
                        file_path=log_file,
                        category_id=None,
                        matched_keyword='Accura Import',
                        computer_name='ACCURA_HISTORICAL',
                        user_id=user.id,
                        event_type='imported',
                        file_size=0
                    )
                    db.session.add(event)
                    db.session.flush()
                    
                    # Create analysis entry with calculated machine time
                    cnc_analysis = CNCAnalysis(
                        event_id=event.id,
                        file_path=entry_name,
                        cycle_time_seconds=machine_time_seconds,  # Width-dependent time
                        machine_time_minutes=machine_time_seconds / 60.0,  # Convert to minutes
                        tool_changes=0,
                        rapid_moves=0,
                        feed_moves=0,
                        spindle_commands=0
                    )
                    db.session.add(cnc_analysis)
                    
                    entries_count += 1
                    total_imported += 1
                    
                    # Commit every 50 entries
                    if entries_count % 50 == 0:
                        db.session.commit()
                        print(f"    Imported {entries_count} entries...")
            
            # Final commit for this file
            db.session.commit()
            print(f"  Total from this file: {entries_count}")
        
        print(f"\n{'='*50}")
        print(f"Import complete!")
        print(f"Total entries imported: {total_imported}")
        print(f"Each entry = 20 seconds (0.33 min) machine time")
        print(f"Total machine hours: {(total_imported * 20 / 3600):.2f} hours")

if __name__ == '__main__':
    import sys
    
    # Check if username was provided
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("Enter username for import (default: admin): ").strip() or 'admin'
    
    # Check if folder was provided
    if len(sys.argv) > 2:
        folder = sys.argv[2]
    else:
        folder = 'accura'
    
    import_accura_logs(username, folder)