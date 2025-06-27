#!/usr/bin/env python3
"""
Check recent events to see how they were categorized
"""

from app import app, db, Event, Category
from datetime import datetime, timedelta, timezone

def check_recent_events():
    with app.app_context():
        # Get events from the last 24 hours
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        
        print("=== Recent Events (Last 24 Hours) ===\n")
        
        events = Event.query.filter(Event.timestamp >= since).order_by(Event.timestamp.desc()).limit(20).all()
        
        if not events:
            print("No events found in the last 24 hours")
            return
        
        # Count by category
        category_counts = {}
        
        for event in events:
            cat_name = event.category.name if event.category else "None"
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
            
            print(f"Timestamp: {event.timestamp}")
            print(f"File: {event.file_path}")
            print(f"Category: {cat_name}")
            print(f"Matched Keyword: {event.matched_keyword}")
            print(f"Event Type: {event.event_type}")
            print("-" * 50)
        
        print("\n=== Category Summary ===")
        for cat, count in category_counts.items():
            print(f"{cat}: {count} events")
        
        # Check specifically for REP files
        print("\n=== REP Files in Allerlei ===")
        allerlei_cat = Category.query.filter_by(name='Allerlei').first()
        if allerlei_cat:
            rep_in_allerlei = Event.query.filter(
                Event.category_id == allerlei_cat.id,
                db.or_(
                    Event.file_path.like('%_REP_%'),
                    Event.file_path.like('%_REP.%'),
                    Event.file_path.like('%_rep_%'),
                    Event.file_path.like('%_rep.%')
                ),
                Event.timestamp >= since
            ).all()
            
            if rep_in_allerlei:
                print(f"Found {len(rep_in_allerlei)} REP files in Allerlei category:")
                for event in rep_in_allerlei[:5]:  # Show first 5
                    print(f"  - {event.file_path} (timestamp: {event.timestamp})")
            else:
                print("No REP files found in Allerlei category")

if __name__ == "__main__":
    check_recent_events()