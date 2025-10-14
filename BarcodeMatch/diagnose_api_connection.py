#!/usr/bin/env python3
"""
BarcodeMatch API Connection Diagnostic Tool
Helps identify and fix API connection issues to BarcodeMaster
"""

import json
import requests
import os
import sys

def load_config():
    """Load BarcodeMatch config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        return None

    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

def test_url(url, description):
    """Test a URL and report results"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"URL: {url}")
    print(f"{'='*60}")

    try:
        response = requests.get(url, timeout=3)
        print(f"✅ Status Code: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ Response is valid JSON")
                if isinstance(data, list):
                    print(f"✅ Response is a list with {len(data)} items")
                elif isinstance(data, dict):
                    print(f"✅ Response is a dict with keys: {list(data.keys())[:5]}")
            except:
                print(f"⚠️  Response is not JSON: {response.text[:100]}")
        elif response.status_code == 404:
            print(f"❌ 404 Not Found - Endpoint does not exist")
            print(f"   Response: {response.text[:200]}")
        else:
            print(f"⚠️  Unexpected status code")
            print(f"   Response: {response.text[:200]}")

        return True

    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: Cannot connect to server")
        print(f"   Details: {str(e)[:200]}")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Timeout: Server took too long to respond")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)[:200]}")
        return False

def diagnose():
    """Run full diagnostic"""
    print("\n" + "="*60)
    print("BARCODEMATCH API CONNECTION DIAGNOSTIC")
    print("="*60)

    # Load config
    config = load_config()
    if not config:
        return

    api_url = config.get('api_url', '')
    user = config.get('user', 'UNKNOWN')
    database_enabled = config.get('database_enabled', False)

    print(f"\n📋 Configuration:")
    print(f"   API URL: {api_url}")
    print(f"   User: {user}")
    print(f"   Database Enabled: {database_enabled}")

    if not database_enabled:
        print(f"\n⚠️  WARNING: Database is DISABLED in config!")
        print(f"   Enable it in the BarcodeMatch Database panel")

    if not api_url:
        print(f"\n❌ PROBLEM: API URL is not configured!")
        return

    # Check for localhost issue
    if 'localhost' in api_url or '127.0.0.1' in api_url:
        print(f"\n⚠️  WARNING: Using localhost!")
        print(f"   This only works if BarcodeMaster runs on the SAME computer")
        print(f"   If BarcodeMaster is on another computer, you need the LAN IP")
        print(f"   Example: http://192.168.1.100:5001/log")

    # Check URL format
    if not api_url.endswith('/log'):
        print(f"\n⚠️  WARNING: URL doesn't end with '/log'")
        print(f"   BarcodeMatch expects: http://IP:5001/log")
        print(f"   You have: {api_url}")

    if api_url.endswith('/log/'):
        print(f"\n⚠️  WARNING: URL has trailing slash after /log")
        print(f"   Should be: http://IP:5001/log (no trailing slash)")
        print(f"   You have: {api_url}")

    # Test base URL
    if api_url.endswith('/log'):
        base_url = api_url[:-4]  # Remove '/log'
    else:
        base_url = api_url.rstrip('/')

    print(f"\n🔍 Testing connections...")
    print(f"   Base URL: {base_url}")

    # Test 1: Base URL
    test_url(base_url, "Base API URL")

    # Test 2: /log endpoint (POST endpoint, will fail with GET but shows it exists)
    test_url(api_url, "/log endpoint (will show 405 Method Not Allowed if exists)")

    # Test 3: /logs endpoint (the one BarcodeMatch uses)
    logs_url = api_url.replace('/log', '/logs')
    print(f"\n📊 This is the endpoint BarcodeMatch uses for fetching logs:")
    print(f"   Constructed URL: {logs_url}")
    test_url(logs_url, "/logs endpoint (GET all logs)")

    # Test 4: Test with user filter
    logs_with_user_url = f"{logs_url}?user={user}"
    test_url(logs_with_user_url, f"/logs endpoint with user filter ({user})")

    # Test 5: Test connection endpoint
    test_connection_data = {
        "event": "test_connect",
        "details": "Diagnostic test",
        "project": "DIAGNOSTIC_TEST",
        "user": user
    }

    print(f"\n🔍 Testing POST to /log endpoint...")
    print(f"URL: {api_url}")
    try:
        response = requests.post(api_url, json=test_connection_data, timeout=3)
        print(f"✅ Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Connection test SUCCESSFUL!")
            else:
                print(f"⚠️  Connection test failed: {data}")
        else:
            print(f"❌ Connection test failed with status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {str(e)[:200]}")

    # Summary
    print(f"\n{'='*60}")
    print(f"DIAGNOSTIC SUMMARY")
    print(f"{'='*60}")

    issues = []

    if 'localhost' in api_url or '127.0.0.1' in api_url:
        issues.append("Using localhost - change to LAN IP if BarcodeMaster is on different computer")

    if not api_url.endswith('/log'):
        issues.append("URL doesn't end with '/log' - add it!")

    if api_url.endswith('/log/'):
        issues.append("URL has trailing slash - remove it!")

    if not database_enabled:
        issues.append("Database is disabled in config - enable it!")

    if issues:
        print(f"\n❌ ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")

        print(f"\n💡 RECOMMENDED FIX:")
        print(f"   1. Open BarcodeMatch")
        print(f"   2. Go to Database panel")
        print(f"   3. Set API URL to: http://[IP_OF_BARCODEMASTER_COMPUTER]:5001/log")
        print(f"      Example: http://192.168.1.100:5001/log")
        print(f"   4. Click 'Test verbinding' to verify")
        print(f"   5. Click 'Opslaan' to save")
    else:
        print(f"\n✅ No configuration issues found!")
        print(f"   If you still have problems, check:")
        print(f"   - BarcodeMaster API is running")
        print(f"   - Firewall allows port 5001")
        print(f"   - Network connection is working")

if __name__ == "__main__":
    diagnose()
    input("\nPress Enter to exit...")
