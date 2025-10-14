#!/usr/bin/env python3
"""
Same Computer Diagnostic - Why does browser work but Python doesn't?
This is a VERY specific scenario that eliminates network/firewall issues
"""

import json
import requests
import os
import sys
import urllib.parse

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

def analyze_url_construction(api_url):
    """Check if URL construction has issues"""
    print("\n" + "="*70)
    print("URL CONSTRUCTION ANALYSIS")
    print("="*70)

    print(f"\nOriginal api_url: '{api_url}'")
    print(f"Length: {len(api_url)} characters")
    print(f"Bytes: {api_url.encode('utf-8')}")

    # Check for invisible characters
    has_issues = False
    for i, char in enumerate(api_url):
        if ord(char) < 32 or ord(char) > 126:
            if char not in ['\n', '\r', '\t']:
                print(f"⚠️  WARNING: Non-printable character at position {i}: {repr(char)} (code {ord(char)})")
                has_issues = True

    # Check for whitespace
    if api_url != api_url.strip():
        print(f"⚠️  WARNING: URL has leading/trailing whitespace!")
        print(f"   Before strip: '{api_url}'")
        print(f"   After strip:  '{api_url.strip()}'")
        has_issues = True

    # Check the critical replace operation
    print(f"\nCritical operation: api_url.replace('/log', '/logs')")
    logs_url = api_url.replace('/log', '/logs')
    print(f"Result: '{logs_url}'")

    # Check if replace worked correctly
    if '/log' in api_url:
        print(f"✅ Found '/log' in original URL")
        if '/logs' in logs_url:
            print(f"✅ Replace produced '/logs'")
        else:
            print(f"❌ Replace FAILED to produce '/logs'!")
            has_issues = True
    else:
        print(f"❌ '/log' NOT FOUND in original URL!")
        print(f"   This means replace() does nothing!")
        print(f"   api_url stays as: '{logs_url}'")
        has_issues = True

    # Check for common mistakes
    if api_url.endswith('/log/'):
        print(f"⚠️  WARNING: URL ends with '/log/' (trailing slash)")
        print(f"   This becomes: '{logs_url}' (also with trailing slash)")
        has_issues = True

    if '/log' not in api_url.lower():
        print(f"❌ ERROR: URL doesn't contain '/log' at all!")
        has_issues = True

    if api_url.endswith('/logs'):
        print(f"⚠️  WARNING: URL already ends with '/logs'")
        print(f"   This becomes: '{logs_url}' (double 's'?)")
        has_issues = True

    return logs_url, has_issues

def test_python_vs_browser():
    """Compare Python request to browser behavior"""
    print("\n" + "="*70)
    print("PYTHON VS BROWSER COMPARISON")
    print("="*70)

    config = load_config()
    if not config:
        return

    api_url = config.get('api_url', '')
    logs_url, url_has_issues = analyze_url_construction(api_url)

    if url_has_issues:
        print(f"\n❌ URL CONSTRUCTION ISSUES FOUND!")
        print(f"\nFix in config.json:")
        print(f"  Current: {repr(api_url)}")

        # Suggest fix
        if not api_url.endswith('/log'):
            suggested = api_url.rstrip('/') + '/log'
            print(f"  Suggested: {repr(suggested)}")
        else:
            print(f"  (URL looks correct syntactically)")

    print(f"\n{'─'*70}")
    print("TEST 1: What Python requests library sees")
    print(f"{'─'*70}")

    # Parse the URL like requests library does
    try:
        parsed = urllib.parse.urlparse(logs_url)
        print(f"Parsed URL components:")
        print(f"  Scheme:   '{parsed.scheme}'")
        print(f"  Netloc:   '{parsed.netloc}'")
        print(f"  Hostname: '{parsed.hostname}'")
        print(f"  Port:     {parsed.port}")
        print(f"  Path:     '{parsed.path}'")
        print(f"  Query:    '{parsed.query}'")
        print(f"  Fragment: '{parsed.fragment}'")

        # Check for issues
        if not parsed.scheme:
            print(f"\n❌ ERROR: No scheme (http/https)!")
        if not parsed.netloc:
            print(f"\n❌ ERROR: No network location!")
        if not parsed.path or parsed.path == '/':
            print(f"\n❌ ERROR: No path or just '/'!")

    except Exception as e:
        print(f"❌ URL parsing failed: {e}")
        return

    print(f"\n{'─'*70}")
    print("TEST 2: Actual HTTP request to server")
    print(f"{'─'*70}")

    print(f"\nRequesting: {logs_url}")

    try:
        # Make request exactly as database_panel.py does
        response = requests.get(logs_url, timeout=2)

        print(f"\n✅ Response received!")
        print(f"   Status: {response.status_code} {response.reason}")
        print(f"   Final URL: {response.url}")

        if response.status_code == 404:
            print(f"\n{'!'*70}")
            print(f"❌ 404 NOT FOUND - THIS IS THE PROBLEM!")
            print(f"{'!'*70}")

            print(f"\nServer response:")
            print(f"{response.text[:500]}")

            print(f"\n🔍 This means:")
            print(f"   The server at {parsed.netloc} doesn't have the path '{parsed.path}'")
            print(f"\n   Things to check:")
            print(f"   1. Is this the correct server?")
            print(f"   2. Is BarcodeMaster API actually running?")
            print(f"   3. Does the /logs endpoint exist in db_log_api.py?")

        elif response.status_code == 200:
            print(f"\n✅ SUCCESS! Status 200")
            try:
                data = response.json()
                if isinstance(data, list):
                    print(f"✅ Got valid JSON list with {len(data)} items")
                    print(f"\n🤔 WAIT - This means Python CAN connect!")
                    print(f"\n   If database_panel shows 404, possible causes:")
                    print(f"   1. Different api_url when running from GUI")
                    print(f"   2. Timing issue (server not ready)")
                    print(f"   3. The 404 is from a DIFFERENT request")
                else:
                    print(f"⚠️  Got JSON but not a list: {type(data)}")
            except:
                print(f"⚠️  Response isn't JSON: {response.text[:200]}")

    except requests.exceptions.Timeout:
        print(f"\n❌ TIMEOUT - Server didn't respond in 2 seconds")
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ CONNECTION ERROR: {e}")
        print(f"\n🔍 This means:")
        print(f"   • Server isn't running on {parsed.netloc}")
        print(f"   • Or firewall is blocking")
        print(f"   • Or wrong IP/port")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n{'─'*70}")
    print("TEST 3: Environment variables affecting Python")
    print(f"{'─'*70}")

    env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'ALL_PROXY',
                'http_proxy', 'https_proxy', 'no_proxy']

    found_proxy = False
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"⚠️  {var} = {value}")
            found_proxy = True

    if found_proxy:
        print(f"\n⚠️  PROXY ENVIRONMENT VARIABLES DETECTED!")
        print(f"   Python requests uses these, browsers might not")
        print(f"   This could cause different behavior!")
    else:
        print(f"✅ No proxy environment variables")

    print(f"\n{'─'*70}")
    print("TEST 4: Direct socket connection (bypassing requests library)")
    print(f"{'─'*70}")

    import socket

    try:
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)

        print(f"\nConnecting to {host}:{port}")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((host, port))

        # Send HTTP request
        path = parsed.path or '/'
        request = f"GET {path} HTTP/1.1\r\n"
        request += f"Host: {host}\r\n"
        request += "Connection: close\r\n"
        request += "\r\n"

        sock.sendall(request.encode())

        # Get response
        response = sock.recv(4096).decode('utf-8', errors='replace')
        sock.close()

        # Parse status line
        lines = response.split('\n')
        status_line = lines[0] if lines else ''

        print(f"✅ Connected!")
        print(f"   Status line: {status_line.strip()}")

        if '404' in status_line:
            print(f"\n❌ 404 even with raw socket!")
            print(f"   The endpoint truly doesn't exist on the server")
        elif '200' in status_line:
            print(f"\n✅ 200 OK with raw socket!")
            print(f"   So it's not a requests library issue")

    except Exception as e:
        print(f"❌ Socket connection failed: {e}")

def check_config_file_issues():
    """Check for config file encoding or corruption"""
    print("\n" + "="*70)
    print("CONFIG FILE INTEGRITY CHECK")
    print("="*70)

    config_path = os.path.join(os.path.dirname(__file__), 'config.json')

    # Read raw bytes
    with open(config_path, 'rb') as f:
        raw_bytes = f.read()

    # Check BOM
    if raw_bytes.startswith(b'\xef\xbb\xbf'):
        print(f"⚠️  File has UTF-8 BOM (byte order mark)")
    elif raw_bytes.startswith(b'\xff\xfe'):
        print(f"⚠️  File has UTF-16 LE BOM")
    elif raw_bytes.startswith(b'\xfe\xff'):
        print(f"⚠️  File has UTF-16 BE BOM")
    else:
        print(f"✅ No BOM detected")

    # Check for non-ASCII characters
    try:
        text = raw_bytes.decode('utf-8')
        non_ascii = [c for c in text if ord(c) > 127]
        if non_ascii:
            print(f"⚠️  File contains non-ASCII characters: {set(non_ascii)}")
        else:
            print(f"✅ All ASCII characters")
    except:
        print(f"❌ File is not valid UTF-8")

    # Parse JSON
    try:
        config = json.loads(raw_bytes.decode('utf-8'))
        print(f"✅ Valid JSON")

        api_url = config.get('api_url', '')
        print(f"\napi_url value:")
        print(f"  String: {repr(api_url)}")
        print(f"  Type: {type(api_url)}")
        print(f"  Length: {len(api_url)}")

    except Exception as e:
        print(f"❌ JSON parsing error: {e}")

def main():
    print("\n" + "="*70)
    print("SAME COMPUTER DIAGNOSTIC")
    print("Browser works, Python doesn't - What's different?")
    print("="*70)

    print(f"\nThis script will identify why Python behaves differently than")
    print(f"your browser on the SAME computer.\n")

    check_config_file_issues()
    test_python_vs_browser()

    print("\n" + "="*70)
    print("SUMMARY - Most Likely Causes")
    print("="*70)

    print(f"\nOn the same computer, if browser works but Python doesn't:")
    print(f"\n1. URL Construction Bug (60% likely)")
    print(f"   • api_url in config doesn't end with '/log'")
    print(f"   • Has trailing slash: '/log/'")
    print(f"   • Has invisible characters or whitespace")
    print(f"   → Check URL CONSTRUCTION ANALYSIS above")

    print(f"\n2. /logs Endpoint Missing (30% likely)")
    print(f"   • Browser tests /log (which exists)")
    print(f"   • Python tests /logs (which doesn't exist)")
    print(f"   • They're different endpoints!")
    print(f"   → Check if /logs exists in db_log_api.py")

    print(f"\n3. Timing Issue (5% likely)")
    print(f"   • API not fully initialized when Python connects")
    print(f"   • 2 second timeout too short")
    print(f"   → Try adding delay or increase timeout")

    print(f"\n4. Environment Variables (3% likely)")
    print(f"   • Proxy settings affect Python but not browser")
    print(f"   → Check ENVIRONMENT VARIABLES section above")

    print(f"\n5. Requests Library Bug (2% likely)")
    print(f"   • Old version of requests library")
    print(f"   • Configuration issue")
    print(f"   → Try: pip install --upgrade requests")

    print(f"\n{'='*70}")
    print("NEXT STEPS")
    print(f"{'='*70}")

    print(f"\n1. Read the output above carefully")
    print(f"2. Look for any ❌ or ⚠️  warnings")
    print(f"3. If URL construction has issues, fix config.json")
    print(f"4. If endpoint is missing, check BarcodeMaster")
    print(f"5. If still unclear, run monitor_requests.py")

if __name__ == "__main__":
    main()
    print("\n")
    input("Press Enter to exit...")
