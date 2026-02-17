#!/usr/bin/env python3
import requests
import json

# Test the fixed API endpoint for batch sessions
api_url = "http://localhost:5001"

projects = [
    "MO06787_Dressing_A_deel2_(5-16)",
    "MO06797_Bureaukast_(15-16)"
]

print("=== Testing Batch Session Idle Time Fix ===\n")

for project in projects:
    print(f"\nProject: {project}")
    print("-" * 50)
    
    try:
        # Call the API endpoint
        response = requests.get(f"{api_url}/api/project/{project}/linked_sessions")
        
        if response.ok:
            data = response.json()
            
            # Display metrics
            metrics = data.get('metrics', {})
            print(f"Total Work Minutes: {metrics.get('total_work_minutes', 0):.1f}")
            print(f"Total Pause Minutes: {metrics.get('total_pause_minutes', 0):.1f}")
            print(f"Total Handoff Minutes: {metrics.get('total_handoff_minutes', 0):.1f}")
            
            # Display sessions
            sessions = data.get('sessions', [])
            print(f"\nSessions ({len(sessions)}):")
            for s in sessions:
                if s.get('session_type') == 'SCANNER':
                    print(f"  - {s['user']} (SCANNER batch):")
                    print(f"    Total session time: {s.get('work_duration_minutes', 0):.1f} min")
                    if 'allocated_work_minutes' in s:
                        print(f"    Allocated to this project: {s['allocated_work_minutes']:.1f} min")
                    if s.get('batch_items'):
                        print(f"    Items: {s['batch_items']} / {s['batch_total_items']} total")
                else:
                    print(f"  - {s['user']} ({s['session_type']}):")
                    print(f"    Work time: {s.get('work_duration_minutes', 0):.1f} min")
            
            # Calculate idle time
            # This would need project_sessions data to get total project time
            # For now just show the work time breakdown
            
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error calling API: {e}")

print("\n✓ Test complete!")