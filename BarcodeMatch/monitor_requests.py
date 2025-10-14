#!/usr/bin/env python3
"""
Real-time Request Monitor for BarcodeMatch
Monkey-patches the requests library to show exactly what's being sent/received
Run this BEFORE starting BarcodeMatch to see all HTTP traffic
"""

import requests
import json
import sys
from datetime import datetime

# Store original methods
_original_get = requests.get
_original_post = requests.post
_original_request = requests.request

def log_request(method, url, **kwargs):
    """Log HTTP request details"""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print("\n" + "="*80)
    print(f"[{timestamp}] {method} REQUEST")
    print("="*80)
    print(f"URL: {url}")

    if 'headers' in kwargs:
        print(f"\nHeaders:")
        for key, value in kwargs['headers'].items():
            print(f"  {key}: {value}")

    if 'json' in kwargs:
        print(f"\nJSON Payload:")
        print(json.dumps(kwargs['json'], indent=2))

    if 'params' in kwargs:
        print(f"\nURL Parameters:")
        print(json.dumps(kwargs['params'], indent=2))

    if 'timeout' in kwargs:
        print(f"\nTimeout: {kwargs['timeout']}s")

def log_response(response, duration_ms):
    """Log HTTP response details"""
    print(f"\n{'─'*80}")
    print(f"RESPONSE (took {duration_ms:.1f}ms)")
    print(f"{'─'*80}")
    print(f"Status Code: {response.status_code} {response.reason}")
    print(f"Final URL: {response.url}")

    if response.history:
        print(f"\nRedirects:")
        for i, redirect in enumerate(response.history, 1):
            print(f"  {i}. {redirect.status_code} -> {redirect.url}")

    print(f"\nResponse Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")

    # Try to format response body
    content_type = response.headers.get('content-type', '')

    if 'application/json' in content_type:
        try:
            print(f"\nResponse Body (JSON):")
            data = response.json()
            if isinstance(data, list) and len(data) > 3:
                print(f"  [List with {len(data)} items, showing first 3]")
                print(json.dumps(data[:3], indent=2))
            else:
                print(json.dumps(data, indent=2))
        except:
            print(f"\nResponse Body (Raw):")
            print(response.text[:500])
    else:
        print(f"\nResponse Body (first 500 chars):")
        print(response.text[:500])

    # Special highlighting for errors
    if response.status_code >= 400:
        print(f"\n{'!'*80}")
        print(f"❌ ERROR RESPONSE! Status {response.status_code}")
        if response.status_code == 404:
            print(f"❌ 404 NOT FOUND - This endpoint doesn't exist on the server!")
            print(f"❌ The server is saying: I don't have '{response.url}'")
        print(f"{'!'*80}")

    print("="*80 + "\n")

def monitored_get(url, **kwargs):
    """Monitored GET request"""
    import time
    start = time.time()

    log_request("GET", url, **kwargs)

    try:
        response = _original_get(url, **kwargs)
        duration_ms = (time.time() - start) * 1000
        log_response(response, duration_ms)
        return response
    except requests.exceptions.Timeout as e:
        duration_ms = (time.time() - start) * 1000
        print(f"\n❌ REQUEST TIMEOUT after {duration_ms:.1f}ms")
        print(f"   {str(e)}")
        print("="*80 + "\n")
        raise
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        print(f"\n❌ REQUEST FAILED after {duration_ms:.1f}ms")
        print(f"   {str(e)}")
        print("="*80 + "\n")
        raise

def monitored_post(url, **kwargs):
    """Monitored POST request"""
    import time
    start = time.time()

    log_request("POST", url, **kwargs)

    try:
        response = _original_post(url, **kwargs)
        duration_ms = (time.time() - start) * 1000
        log_response(response, duration_ms)
        return response
    except requests.exceptions.Timeout as e:
        duration_ms = (time.time() - start) * 1000
        print(f"\n❌ REQUEST TIMEOUT after {duration_ms:.1f}ms")
        print(f"   {str(e)}")
        print("="*80 + "\n")
        raise
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        print(f"\n❌ REQUEST FAILED after {duration_ms:.1f}ms")
        print(f"   {str(e)}")
        print("="*80 + "\n")
        raise

# Monkey patch requests module
requests.get = monitored_get
requests.post = monitored_post

print("\n" + "="*80)
print(" "*25 + "REQUEST MONITOR ACTIVE")
print("="*80)
print("\nAll HTTP requests from this Python process will be logged")
print("Including requests from BarcodeMatch database_panel.py")
print("\nYou will see:")
print("  • Exact URLs being requested")
print("  • Request headers and payloads")
print("  • Response status codes")
print("  • Response bodies")
print("  • Timing information")
print("  • Special highlighting for 404 errors")
print("\n" + "="*80)
print("\nNow run BarcodeMatch from this same terminal:")
print("  python main.py")
print("\nOr import this module in your code:")
print("  import monitor_requests  # Must be first import!")
print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    print("\nWaiting for BarcodeMatch to start...")
    print("(Or run: python -c 'import monitor_requests; import main')")
    input("\nPress Enter to exit monitor...")
