#!/usr/bin/env python3
"""
Deep Diagnostic Tool for BarcodeMatch API 404 Issues
Identifies differences between browser requests and Python requests
"""

import json
import requests
import os
import sys
import socket
import urllib.parse
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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

def check_proxy_settings():
    """Check if Python is using a proxy"""
    print("\n" + "="*60)
    print("PROXY SETTINGS CHECK")
    print("="*60)

    # Check environment variables
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    no_proxy = os.environ.get('NO_PROXY') or os.environ.get('no_proxy')

    if http_proxy or https_proxy:
        print(f"⚠️  PROXY DETECTED!")
        print(f"   HTTP_PROXY: {http_proxy}")
        print(f"   HTTPS_PROXY: {https_proxy}")
        print(f"   NO_PROXY: {no_proxy}")
        print(f"\n   This could cause requests to go through a proxy that blocks them!")
        return True
    else:
        print(f"✅ No proxy environment variables found")
        return False

def check_dns_resolution(hostname):
    """Check DNS resolution"""
    print("\n" + "="*60)
    print("DNS RESOLUTION CHECK")
    print("="*60)
    print(f"Hostname: {hostname}")

    try:
        ip = socket.gethostbyname(hostname)
        print(f"✅ Resolved to IP: {ip}")
        return ip
    except socket.gaierror as e:
        print(f"❌ DNS Resolution failed: {e}")
        return None

def test_with_verbose_logging(url, description):
    """Test URL with maximum verbosity"""
    print("\n" + "="*60)
    print(f"VERBOSE REQUEST TEST: {description}")
    print("="*60)
    print(f"URL: {url}")

    # Parse URL
    parsed = urllib.parse.urlparse(url)
    print(f"\nURL Components:")
    print(f"   Scheme: {parsed.scheme}")
    print(f"   Hostname: {parsed.hostname}")
    print(f"   Port: {parsed.port}")
    print(f"   Path: {parsed.path}")

    # Create session with verbose settings
    session = requests.Session()

    # Add retry logic
    retry = Retry(total=0, backoff_factor=0)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    try:
        # Test with explicit headers like a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
        }

        print(f"\nRequest Headers:")
        for key, value in headers.items():
            print(f"   {key}: {value}")

        print(f"\n🔄 Sending GET request...")
        response = session.get(url, headers=headers, timeout=5, allow_redirects=True)

        print(f"\n📥 Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Reason: {response.reason}")
        print(f"   Final URL: {response.url}")

        print(f"\n   Response Headers:")
        for key, value in response.headers.items():
            print(f"      {key}: {value}")

        if response.history:
            print(f"\n   Redirects detected:")
            for i, redirect in enumerate(response.history, 1):
                print(f"      {i}. {redirect.status_code} -> {redirect.url}")

        print(f"\n   Response Body (first 500 chars):")
        print(f"   {response.text[:500]}")

        return response

    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_post_request(url, description):
    """Test POST request as BarcodeMatch does it"""
    print("\n" + "="*60)
    print(f"POST REQUEST TEST: {description}")
    print("="*60)
    print(f"URL: {url}")

    payload = {
        "event": "test_connect",
        "details": "Deep diagnostic test",
        "project": "DIAGNOSTIC",
        "user": "DIAGNOSTIC_USER"
    }

    print(f"\nPayload:")
    print(json.dumps(payload, indent=2))

    try:
        print(f"\n🔄 Sending POST request...")
        response = requests.post(url, json=payload, timeout=5)

        print(f"\n📥 Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Reason: {response.reason}")

        print(f"\n   Response Headers:")
        for key, value in response.headers.items():
            print(f"      {key}: {value}")

        print(f"\n   Response Body:")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)

        return response

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def simulate_database_panel_request(api_url):
    """Simulate exactly what database_panel.py does"""
    print("\n" + "="*60)
    print("SIMULATING DATABASE_PANEL.PY REQUEST")
    print("="*60)

    print(f"\n1. Original api_url from config: {api_url}")

    # This is what database_panel.py does at line 933
    logs_url = api_url.replace('/log', '/logs')
    print(f"2. Constructed logs_url: {logs_url}")
    print(f"   (using: api_url.replace('/log', '/logs'))")

    print(f"\n3. Making GET request to {logs_url}")

    try:
        response = requests.get(logs_url, timeout=2)
        print(f"\n✅ Status Code: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ Got valid JSON response")
                if isinstance(data, list):
                    print(f"✅ Response is a list with {len(data)} logs")
                else:
                    print(f"⚠️  Response is not a list: {type(data)}")
            except:
                print(f"❌ Response is not valid JSON")
                print(f"   First 200 chars: {response.text[:200]}")
        elif response.status_code == 404:
            print(f"❌ 404 NOT FOUND!")
            print(f"\n   THIS IS THE ERROR!")
            print(f"   The server says this endpoint doesn't exist")
            print(f"\n   Response body:")
            print(f"   {response.text}")
        else:
            print(f"⚠️  Unexpected status code")
            print(f"   Response: {response.text[:200]}")

        return response

    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT after 2 seconds")
        print(f"   This is the same timeout database_panel.py uses")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_exact_bytes(url):
    """Check the exact bytes being sent"""
    print("\n" + "="*60)
    print("RAW HTTP REQUEST INSPECTION")
    print("="*60)

    import socket
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or 80
    path = parsed.path or '/'

    print(f"Connecting to: {host}:{port}")
    print(f"Path: {path}")

    try:
        # Create raw socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))

        # Build HTTP request
        request = f"GET {path} HTTP/1.1\r\n"
        request += f"Host: {host}:{port}\r\n"
        request += "Connection: close\r\n"
        request += "\r\n"

        print(f"\nRaw HTTP Request:")
        print(request)

        # Send request
        sock.sendall(request.encode())

        # Receive response
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk

        sock.close()

        # Parse response
        response_str = response.decode('utf-8', errors='replace')
        lines = response_str.split('\n')

        print(f"\nRaw HTTP Response (first 20 lines):")
        for i, line in enumerate(lines[:20], 1):
            print(f"   {i:2d}. {line.strip()}")

        # Check status code
        if lines:
            status_line = lines[0]
            if '404' in status_line:
                print(f"\n❌ 404 FOUND IN RAW RESPONSE!")
                print(f"   Status Line: {status_line}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def deep_diagnostic():
    """Run comprehensive diagnostic"""
    print("\n" + "="*80)
    print(" "*20 + "BARCODEMATCH DEEP DIAGNOSTIC")
    print(" "*15 + "Finding the REAL cause of 404 errors")
    print("="*80)

    # Load config
    config = load_config()
    if not config:
        return

    api_url = config.get('api_url', '')
    user = config.get('user', 'UNKNOWN')

    print(f"\n📋 Configuration:")
    print(f"   API URL: {api_url}")
    print(f"   User: {user}")

    # Parse URL
    parsed = urllib.parse.urlparse(api_url)
    hostname = parsed.hostname

    # Check 1: Proxy
    has_proxy = check_proxy_settings()

    # Check 2: DNS
    if hostname and hostname != 'localhost':
        resolved_ip = check_dns_resolution(hostname)

    # Check 3: Simulate exact database_panel.py behavior
    simulate_database_panel_request(api_url)

    # Check 4: Test with verbose logging
    logs_url = api_url.replace('/log', '/logs')
    test_with_verbose_logging(logs_url, "GET /logs (verbose)")

    # Check 5: Test POST to /log
    test_post_request(api_url, "POST /log")

    # Check 6: Raw HTTP inspection
    check_exact_bytes(logs_url)

    # Summary
    print("\n" + "="*80)
    print("DIAGNOSTIC SUMMARY & RECOMMENDATIONS")
    print("="*80)

    print(f"\n📊 What we tested:")
    print(f"   1. Proxy settings")
    print(f"   2. DNS resolution")
    print(f"   3. Exact database_panel.py simulation")
    print(f"   4. Verbose HTTP requests")
    print(f"   5. POST requests to /log")
    print(f"   6. Raw HTTP byte-level inspection")

    print(f"\n💡 What to look for in the results above:")
    print(f"   • If RAW HTTP shows 404: Server truly doesn't have this endpoint")
    print(f"   • If redirects detected: URL might be redirecting somewhere else")
    print(f"   • If proxy detected: Proxy might be blocking/modifying requests")
    print(f"   • If DNS resolution differs: Network routing issue")
    print(f"   • Check 'Final URL' vs 'Original URL' for any changes")

    print(f"\n🔍 Next steps:")
    print(f"   1. Compare the request headers Python uses vs your browser")
    print(f"   2. Check BarcodeMaster API logs at:")
    print(f"      {os.path.dirname(api_url.split(':')[1])}/BarcodeMaster/database/db_log_api.log")
    print(f"   3. Verify BarcodeMaster API is actually listening on {parsed.hostname}:{parsed.port}")
    print(f"   4. On BarcodeMaster computer, check if firewall allows connections FROM this computer")

if __name__ == "__main__":
    deep_diagnostic()
    print("\n")
    input("Press Enter to exit...")
