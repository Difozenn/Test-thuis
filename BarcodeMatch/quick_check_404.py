#!/usr/bin/env python3
"""
Quick 404 Check - Identifies the most likely cause in 30 seconds
Run this FIRST before the detailed diagnostics
"""

import json
import requests
import os

def quick_check():
    print("\n" + "="*60)
    print("  QUICK 404 CHECK - Finding the issue fast")
    print("="*60)

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.exists(config_path):
        print(f"\n❌ Config not found: {config_path}")
        return

    with open(config_path, 'r') as f:
        config = json.load(f)

    api_url = config.get('api_url', '')
    print(f"\nAPI URL from config: {api_url}")

    if not api_url:
        print("❌ API URL not configured!")
        return

    # Test 1: Base URL
    print(f"\n{'─'*60}")
    print("TEST 1: Base URL (should work)")
    print(f"{'─'*60}")

    base_url = api_url.replace('/log', '')
    print(f"Testing: {base_url}")

    try:
        r = requests.get(base_url, timeout=5)
        print(f"✅ Status: {r.status_code} - Base URL is accessible")
    except Exception as e:
        print(f"❌ Failed: {e}")
        print(f"\n🔍 PROBLEM: Can't reach BarcodeMaster at all")
        print(f"   • Check if BarcodeMaster is running")
        print(f"   • Check IP address is correct")
        print(f"   • Check firewall allows connection")
        return

    # Test 2: /log endpoint
    print(f"\n{'─'*60}")
    print("TEST 2: /log endpoint (might be 405, that's OK)")
    print(f"{'─'*60}")

    print(f"Testing: {api_url}")

    try:
        r = requests.get(api_url, timeout=5)
        if r.status_code == 404:
            print(f"❌ Status: 404 - /log endpoint doesn't exist!")
            print(f"\n🔍 PROBLEM: BarcodeMaster API not running properly")
            print(f"   • Check BarcodeMaster Admin Panel → Database tab")
            print(f"   • Make sure API is started")
            return
        else:
            print(f"✅ Status: {r.status_code} - /log endpoint exists")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return

    # Test 3: /logs endpoint - THIS IS THE CRITICAL ONE
    print(f"\n{'─'*60}")
    print("TEST 3: /logs endpoint (THE IMPORTANT ONE)")
    print(f"{'─'*60}")

    logs_url = api_url.replace('/log', '/logs')
    print(f"Testing: {logs_url}")
    print(f"(This is what database_panel.py uses)")

    try:
        r = requests.get(logs_url, timeout=5)

        if r.status_code == 404:
            print(f"\n❌❌❌ FOUND THE PROBLEM! ❌❌❌")
            print(f"\nStatus: 404 - /logs endpoint DOES NOT EXIST")
            print(f"\n{'='*60}")
            print(f"ROOT CAUSE: BarcodeMaster API is missing the /logs endpoint")
            print(f"{'='*60}")
            print(f"\nThis means:")
            print(f"  • BarcodeMaster's db_log_api.py doesn't have @app.route('/logs')")
            print(f"  • Or the API server isn't properly initialized")
            print(f"  • Or you're connecting to wrong server/port")
            print(f"\nTo fix:")
            print(f"  1. On BarcodeMaster computer, check:")
            print(f"     C:\\...\\BarcodeMaster\\database\\db_log_api.py")
            print(f"     Look for: @app.route('/logs', methods=['GET'])")
            print(f"\n  2. Verify BarcodeMaster API is running:")
            print(f"     - Open BarcodeMaster")
            print(f"     - Go to Admin Panel → Database tab")
            print(f"     - Check 'API Status' shows 'Actief'")
            print(f"\n  3. Test /logs in browser:")
            print(f"     Open: {logs_url}")
            print(f"     Should show JSON list of logs")
            print(f"\n  4. If browser ALSO shows 404:")
            print(f"     The endpoint truly doesn't exist")
            print(f"     Update BarcodeMaster to latest version")
            print(f"\n  5. If browser WORKS but Python doesn't:")
            print(f"     Run deep_diagnostic.py for detailed analysis")

            return

        elif r.status_code == 200:
            try:
                data = r.json()
                if isinstance(data, list):
                    print(f"✅ Status: 200 - /logs endpoint works!")
                    print(f"✅ Got {len(data)} log entries")

                    print(f"\n{'='*60}")
                    print(f"INTERESTING: /logs endpoint EXISTS and WORKS")
                    print(f"{'='*60}")
                    print(f"\nBut you said BarcodeMatch gets 404...")
                    print(f"\nPossible causes:")
                    print(f"  1. URL in BarcodeMatch config is different")
                    print(f"     Check config.json api_url matches: {api_url}")
                    print(f"\n  2. BarcodeMatch is using different network path")
                    print(f"     (WiFi vs Ethernet, VPN, proxy)")
                    print(f"\n  3. Intermittent network issue")
                    print(f"     Try refreshing logs in BarcodeMatch now")
                    print(f"\n  4. Firewall blocking BarcodeMatch but not this script")
                    print(f"     Check Windows Firewall rules")
                    print(f"\n  5. Different Python/requests version issue")
                    print(f"     Run: pip show requests")
                    print(f"\nNext step:")
                    print(f"  • Open BarcodeMatch")
                    print(f"  • Go to Database panel")
                    print(f"  • Click 'Test verbinding'")
                    print(f"  • Does it work now?")
                    print(f"  • If still 404, run deep_diagnostic.py")

                else:
                    print(f"⚠️  Got 200 but response isn't a list")
                    print(f"   Response type: {type(data)}")
            except:
                print(f"⚠️  Got 200 but response isn't JSON")
                print(f"   Response: {r.text[:100]}")

        else:
            print(f"⚠️  Status: {r.status_code}")
            print(f"   Response: {r.text[:200]}")

    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT after 5 seconds")
        print(f"\n🔍 PROBLEM: Server taking too long to respond")
        print(f"   • Network latency issue")
        print(f"   • Try increasing timeout in database_panel.py")
    except Exception as e:
        print(f"❌ Failed: {e}")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"\nIf you saw '❌❌❌ FOUND THE PROBLEM! ❌❌❌' above:")
    print(f"  → Follow the fix steps shown")
    print(f"\nIf all tests passed (✅):")
    print(f"  → The API works from this script")
    print(f"  → But BarcodeMatch might still fail")
    print(f"  → Run monitor_requests.py to see what BarcodeMatch actually sends")
    print(f"\nIf you see connection errors:")
    print(f"  → Basic network connectivity issue")
    print(f"  → Check IP address, firewall, BarcodeMaster running")

if __name__ == "__main__":
    quick_check()
    print("\n")
    input("Press Enter to exit...")
