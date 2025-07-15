#!/usr/bin/env python3
"""Debug script to check monitoring setup"""

import requests
import json

BASE_URL = "http://localhost:5002"

def check_paths():
    """Check what paths are configured for monitoring"""
    try:
        response = requests.get(f"{BASE_URL}/api/paths")
        if response.status_code == 200:
            paths = response.json()
            print("Configured monitoring paths:")
            for path in paths:
                print(f"  - {path['path']} (directory: {path['is_directory']}, recursive: {path.get('recursive', False)})")
            return len(paths)
        else:
            print(f"Failed to get paths: {response.status_code}")
            return 0
    except Exception as e:
        print(f"Error checking paths: {e}")
        return 0

def check_recent_events():
    """Check recent events to see if any are being detected"""
    try:
        response = requests.get(f"{BASE_URL}/events?limit=10")
        if response.status_code == 200:
            print("Recent events:")
            # This would need to be adjusted based on your events API structure
            print("  Check the web interface for recent events")
        else:
            print(f"Failed to get events: {response.status_code}")
    except Exception as e:
        print(f"Error checking events: {e}")

if __name__ == "__main__":
    print("=== Monitoring Debug Check ===")
    print()
    
    paths_count = check_paths()
    print()
    
    if paths_count == 0:
        print("❌ No monitoring paths configured!")
        print("   Go to Settings page and add some paths to monitor")
    else:
        print(f"✅ {paths_count} path(s) configured for monitoring")
    
    print()
    check_recent_events()
    
    print()
    print("Next steps:")
    print("1. Check if the C# tray app console shows 'Monitoring started successfully'")
    print("2. Check if file changes show 'Queued [change] event for [filename]'")
    print("3. Check if files show 'Processing [change] for [filename]'")
    print("4. Verify the file you're changing matches one of the monitored paths above")