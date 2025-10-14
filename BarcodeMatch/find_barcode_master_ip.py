#!/usr/bin/env python3
"""
Quick script to find the correct IP address to use in config.json
Run this to determine if localhost vs IP is the issue
"""

import socket
import requests
import json
import os

def find_correct_ip():
    print("\n" + "="*70)
    print("FINDING CORRECT IP FOR BARCODEMATCH CONFIG")
    print("="*70)

    # Test localhost
    print("\n[TEST 1] Testing with 'localhost':")
    print(f"  URL: http://localhost:5001/logs")
    try:
        r = requests.get("http://localhost:5001/logs", timeout=5)
        print(f"  ✅ Status: {r.status_code}")
        if r.status_code == 200:
            print(f"  ✅ localhost WORKS! No need to change config.")
            return "localhost"
    except Exception as e:
        print(f"  ❌ Failed: {e}")

    # Test 127.0.0.1
    print("\n[TEST 2] Testing with '127.0.0.1':")
    print(f"  URL: http://127.0.0.1:5001/logs")
    try:
        r = requests.get("http://127.0.0.1:5001/logs", timeout=5)
        print(f"  ✅ Status: {r.status_code}")
        if r.status_code == 200:
            print(f"  ✅ 127.0.0.1 WORKS!")
            return "127.0.0.1"
    except Exception as e:
        print(f"  ❌ Failed: {e}")

    # Get local network IPs
    print("\n[TEST 3] Getting local network IP addresses:")
    hostname = socket.gethostname()
    print(f"  Hostname: {hostname}")

    try:
        local_ips = socket.gethostbyname_ex(hostname)[2]
        print(f"  Found IPs: {local_ips}")

        # Test each IP
        for ip in local_ips:
            if ip.startswith('127.'):
                continue  # Skip loopback

            print(f"\n  Testing {ip}:")
            print(f"    URL: http://{ip}:5001/logs")
            try:
                r = requests.get(f"http://{ip}:5001/logs", timeout=5)
                print(f"    ✅ Status: {r.status_code}")
                if r.status_code == 200:
                    print(f"    ✅ {ip} WORKS!")
                    return ip
            except Exception as e:
                print(f"    ❌ Failed: {e}")
    except Exception as e:
        print(f"  ❌ Failed to get IPs: {e}")

    print("\n[TEST 4] Manual IP entry:")
    print("  None of the automatic tests worked.")
    print("  Please enter the IP you used in your browser that worked:")
    manual_ip = input("  IP address: ").strip()

    if manual_ip:
        print(f"\n  Testing {manual_ip}:")
        try:
            r = requests.get(f"http://{manual_ip}:5001/logs", timeout=5)
            print(f"  ✅ Status: {r.status_code}")
            if r.status_code == 200:
                return manual_ip
        except Exception as e:
            print(f"  ❌ Failed: {e}")

    return None

def update_config(ip):
    """Update config.json with the correct IP"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        old_url = config.get('api_url', '')
        new_url = f"http://{ip}:5001/log"

        print("\n" + "="*70)
        print("UPDATING CONFIG.JSON")
        print("="*70)
        print(f"\n  Old: {old_url}")
        print(f"  New: {new_url}")

        config['api_url'] = new_url

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)

        print(f"\n  ✅ Config updated successfully!")
        print(f"\n  Restart BarcodeMatch to use the new settings.")

    except Exception as e:
        print(f"\n  ❌ Failed to update config: {e}")

def main():
    print("\n" + "="*70)
    print("  BARCODEMATCH IP DIAGNOSTIC")
    print("  This will find the correct IP to use in config.json")
    print("="*70)

    correct_ip = find_correct_ip()

    if correct_ip:
        print("\n" + "="*70)
        print("RESULT")
        print("="*70)
        print(f"\n  ✅ Found working IP: {correct_ip}")
        print(f"\n  The config.json should use:")
        print(f"    \"api_url\": \"http://{correct_ip}:5001/log\"")

        response = input("\n  Update config.json automatically? (y/n): ")
        if response.lower() == 'y':
            update_config(correct_ip)
        else:
            print("\n  Please update config.json manually:")
            print(f"    Change line 4 to: \"api_url\": \"http://{correct_ip}:5001/log\",")
    else:
        print("\n" + "="*70)
        print("FAILED")
        print("="*70)
        print("\n  ❌ Could not find working IP address")
        print("\n  Things to check:")
        print("    1. Is BarcodeMaster running?")
        print("    2. Is the Database API started in BarcodeMaster?")
        print("    3. Are you on the same network as BarcodeMaster?")
        print("    4. What IP did you use in browser that worked?")

if __name__ == "__main__":
    main()
    print("\n")
    input("Press Enter to exit...")
