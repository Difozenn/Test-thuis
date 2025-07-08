#!/usr/bin/env python3
"""
Test script to verify work hours persistence functionality.
This script tests the complete flow: save -> restart -> load
"""

import requests
import json
import time
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from path_utils import get_writable_path

def test_work_hours_persistence():
    """Test complete work hours persistence flow"""
    
    print("=== Work Hours Persistence Test ===")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test configuration - change Friday to 21:00 (9 PM)
    test_config = {
        'monday_start': '07:30',
        'monday_end': '16:00',
        'tuesday_start': '07:30',
        'tuesday_end': '16:00',
        'wednesday_start': '07:30',
        'wednesday_end': '16:00',
        'thursday_start': '07:30',
        'thursday_end': '16:00',
        'friday_start': '07:30',
        'friday_end': '21:00',  # Change to 21:00 for testing
        'saturday_start': '00:00',
        'saturday_end': '00:00',
        'sunday_start': '00:00',
        'sunday_end': '00:00',
        'break_start': '12:00',
        'break_end': '12:30',
        'work_days': [0, 1, 2, 3, 4]
    }
    
    api_base = 'http://localhost:5001'
    
    # Step 1: Check if API is running
    print("\\n1. Checking API availability...")
    try:
        response = requests.get(f"{api_base}/api/settings/work-hours", timeout=5)
        if response.status_code == 200:
            print("✓ API is running and responsive")
        else:
            print(f"✗ API returned error: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ API not available: {e}")
        print("Please start the BarcodeMaster API first (python database/db_log_api.py)")
        return False
    
    # Step 2: Get current work hours
    print("\\n2. Getting current work hours...")
    try:
        response = requests.get(f"{api_base}/api/settings/work-hours")
        if response.status_code == 200:
            current_settings = response.json()
            friday_end = current_settings['settings']['friday']['end']
            print(f"✓ Current Friday end time: {friday_end} ({friday_end:.1f} hours)")
        else:
            print(f"✗ Failed to get current settings: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error getting current settings: {e}")
        return False
    
    # Step 3: Update work hours
    print("\\n3. Updating work hours (Friday to 21:00)...")
    try:
        response = requests.post(
            f"{api_base}/api/settings/work-hours",
            json=test_config,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            result = response.json()
            new_friday_end = result['settings']['friday']['end']
            print(f"✓ Settings updated successfully")
            print(f"✓ New Friday end time: {new_friday_end} ({new_friday_end:.1f} hours)")
        else:
            print(f"✗ Failed to update settings: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error updating settings: {e}")
        return False
    
    # Step 4: Verify config.json was updated
    print("\\n4. Verifying config.json was updated...")
    try:
        config_path = get_writable_path('config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if 'work_hours' in config:
            saved_friday_end = config['work_hours']['friday']['end']
            print(f"✓ config.json updated successfully")
            print(f"✓ Saved Friday end time: {saved_friday_end} ({saved_friday_end:.1f} hours)")
        else:
            print("✗ work_hours not found in config.json")
            return False
    except Exception as e:
        print(f"✗ Error checking config.json: {e}")
        return False
    
    # Step 5: Instructions for restart test
    print("\\n5. Manual restart test instructions:")
    print("   - Stop the BarcodeMaster API (Ctrl+C)")
    print("   - Restart the API: python database/db_log_api.py")
    print("   - Run: python test_work_hours_persistence.py verify")
    print("   - The Friday end time should still be 21:00 after restart")
    
    print("\\n=== Test Phase 1 Complete ===")
    print("Settings have been updated and saved to config.json")
    print("Now restart the API and run 'python test_work_hours_persistence.py verify'")
    
    return True

def verify_persistence():
    """Verify that work hours persist after restart"""
    
    print("=== Work Hours Persistence Verification ===")
    print(f"Verification started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    api_base = 'http://localhost:5001'
    
    # Step 1: Check API availability
    print("\\n1. Checking API availability...")
    try:
        response = requests.get(f"{api_base}/api/settings/work-hours", timeout=5)
        if response.status_code == 200:
            print("✓ API is running and responsive")
        else:
            print(f"✗ API returned error: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ API not available: {e}")
        return False
    
    # Step 2: Get current work hours after restart
    print("\\n2. Getting work hours after restart...")
    try:
        response = requests.get(f"{api_base}/api/settings/work-hours")
        if response.status_code == 200:
            current_settings = response.json()
            friday_end = current_settings['settings']['friday']['end']
            print(f"✓ Current Friday end time: {friday_end} ({friday_end:.1f} hours)")
            
            # Check if persistence worked
            if friday_end == 21.0:
                print("✅ SUCCESS: Work hours persisted after restart!")
                print("✅ Friday end time is correctly set to 21:00")
                return True
            else:
                print(f"❌ FAILURE: Work hours did not persist")
                print(f"❌ Expected Friday end time: 21.0, Got: {friday_end}")
                return False
        else:
            print(f"✗ Failed to get current settings: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error getting current settings: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        verify_persistence()
    else:
        test_work_hours_persistence()