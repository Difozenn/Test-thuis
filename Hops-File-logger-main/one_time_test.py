import os
import json
from hops_file_logger import update_reports, load_seen, save_seen, categorize, now

# Load config
with open('logger_config.json', 'r') as f:
    CONFIG = json.load(f)

SCAN_FILES = CONFIG['scan_files']

entries = {}
save_events = []
new_entries = []

for f in SCAN_FILES:
    abs_f = os.path.abspath(f)
    if not os.path.exists(abs_f):
        print(f"[ERROR] File {abs_f} does not exist.")
        continue
    mtime = os.path.getmtime(abs_f)
    last_seen = entries.get(abs_f)
    if last_seen is None or last_seen != mtime:
        dt = now().isoformat()
        cat = categorize(abs_f)
        event = {'timestamp': dt, 'type': 'new', 'entry': abs_f, 'category': cat, 'mtime': mtime}
        new_entries.append(event)
        entries[abs_f] = mtime

if not new_entries:
    print("[TEST] No new files found. No report will be generated.")
else:
    save_events.extend(new_entries)
    save_seen({'entries': entries, 'save_events': save_events})
    print(f"[TEST] Calling update_reports with {len(save_events)} events...")
    update_reports(save_events)
    print("[TEST] Report generation complete.")
