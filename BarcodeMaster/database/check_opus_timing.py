import sqlite3
from datetime import datetime

conn = sqlite3.connect("central_logging.sqlite")
c = conn.cursor()

print("OPUS Pause/Resume events for MO08383_TV-wand_(1-1):")
print("-" * 100)
c.execute("""
    SELECT timestamp, event, details
    FROM logs 
    WHERE project = 'MO08383_TV-wand_(1-1)' 
    AND user = 'OPUS'
    AND event IN ('SESSION_PAUSE', 'SESSION_RESUME', 'PROJECT_START', 'AFGEMELD')
    ORDER BY timestamp
""")
rows = c.fetchall()

for i, row in enumerate(rows):
    timestamp = datetime.fromisoformat(row[0])
    event = row[1]
    details = row[2] or ""
    
    print(f"{row[0]} | {event:15} | {details}")
    
    # Check for issues
    if event == "SESSION_RESUME" and i > 0:
        prev_event = rows[i-1]
        if prev_event[1] != "SESSION_PAUSE":
            print(f"  ⚠️  WARNING: Resume without preceding pause!")
        else:
            # Calculate pause duration
            prev_time = datetime.fromisoformat(prev_event[0])
            actual_pause = (timestamp - prev_time).total_seconds() / 60
            # Extract reported pause from details
            if "pause duration:" in details:
                reported = details.split("pause duration:")[1].strip().split()[0]
                print(f"  Actual pause: {actual_pause:.1f} min, Reported: {reported} min")
                try:
                    if abs(actual_pause - float(reported)) > 1:
                        print(f"  ⚠️  MISMATCH: Actual vs reported pause time!")
                except:
                    pass
    
    if event == "SESSION_PAUSE" and i > 0:
        prev_event = rows[i-1]
        if prev_event[1] == "SESSION_PAUSE":
            print(f"  ⚠️  WARNING: Double pause without resume!")

conn.close()