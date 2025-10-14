# BarcodeMatch API Connection Troubleshooting Guide

## Problem Description

BarcodeMatch cannot connect to the BarcodeMaster database API on a new computer installation, showing **404 errors** in the logs, even though:
- The web interface (`http://IP:5001`) works fine
- Manually accessing `/log` endpoint in browser works
- The same setup works perfectly on other computers

## Root Cause Analysis

### The Issue

The problem is in the **API URL configuration**. BarcodeMatch requires a very specific URL format:

```
http://[IP_ADDRESS]:5001/log
```

Common mistakes that cause 404 errors:

1. **Using `localhost` when BarcodeMaster runs on a different computer**
   - ❌ `http://localhost:5001/log`
   - ✅ `http://192.168.1.100:5001/log`

2. **Missing `/log` at the end**
   - ❌ `http://192.168.1.100:5001`
   - ✅ `http://192.168.1.100:5001/log`

3. **Trailing slash after `/log`**
   - ❌ `http://192.168.1.100:5001/log/`
   - ✅ `http://192.168.1.100:5001/log`

4. **Using base URL instead of `/log` endpoint**
   - ❌ `http://192.168.1.100:5001/`
   - ✅ `http://192.168.1.100:5001/log`

### Why This Happens

BarcodeMatch constructs other API endpoints by replacing `/log` with the specific endpoint:

```python
# Code from database_panel.py line 933
logs_url = url.replace('/log', '/logs')
```

If the URL is configured incorrectly:
- `http://192.168.1.100:5001` → becomes `http://192.168.1.100:5001` (no change!)
- `http://192.168.1.100:5001/` → becomes `http://192.168.1.100:5001//logs` (double slash!)
- `http://192.168.1.100:5001/log/` → becomes `http://192.168.1.100:5001/logs/` (trailing slash!)

## How to Fix

### Step 1: Run the Diagnostic Tool

On the computer with the problem, run:

```bash
cd C:\Users\Rob\Desktop\Test-thuis\BarcodeMatch
python diagnose_api_connection.py
```

This will:
- Check your current configuration
- Test all API endpoints
- Show exactly what's wrong
- Provide specific recommendations

### Step 2: Fix the Configuration

1. **Find the BarcodeMaster computer's IP address**
   - On the computer running BarcodeMaster:
     - Open Command Prompt
     - Run: `ipconfig`
     - Look for "IPv4 Address" (e.g., `192.168.1.100`)

2. **Update BarcodeMatch configuration**
   - Open BarcodeMatch
   - Go to the **Database** panel
   - Set **API URL** to: `http://[BARCODEMASTER_IP]:5001/log`
     - Example: `http://192.168.1.100:5001/log`
   - **Important**: Must end with `/log` (no trailing slash!)

3. **Test the connection**
   - Click **"Test verbinding"** button
   - Should show: ✅ "Verbonden (TEST)"
   - If still shows error, double-check the IP address

4. **Save the configuration**
   - Click **"Opslaan"** button
   - Configuration is saved to `config.json`

### Step 3: Verify

1. Click **"Log test event"** in BarcodeMatch
2. Check the log section - should show test events
3. Try scanning a project - should work normally

## Technical Details

### API Endpoints Used by BarcodeMatch

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/log` | POST | Send events (OPEN, AFGEMELD, etc.) |
| `/logs` | GET | Fetch all logs for display |
| `/session/add_project` | POST | Link project to session |
| `/session/close` | POST | Close work session |
| `/session/manual_start` | POST | Start manual session |
| `/session/manual_finish` | POST | Finish manual session |

All these endpoints are constructed from the base `/log` URL using string replacement.

### URL Construction Pattern

```python
# From database_panel.py
api_url = "http://192.168.1.100:5001/log"

# Fetching logs
logs_url = api_url.replace('/log', '/logs')
# Result: http://192.168.1.100:5001/logs ✅

# Session endpoints
base_url = api_url.replace('/log', '')
session_url = f"{base_url}/session/add_project"
# Result: http://192.168.1.100:5001/session/add_project ✅
```

If `api_url` doesn't end with `/log`, this pattern fails!

## Common Scenarios

### Scenario 1: Both on Same Computer
- BarcodeMaster running on Computer A
- BarcodeMatch running on Computer A
- ✅ Use: `http://localhost:5001/log`

### Scenario 2: Different Computers (Most Common)
- BarcodeMaster running on Computer A (IP: 192.168.1.100)
- BarcodeMatch running on Computer B
- ✅ Use: `http://192.168.1.100:5001/log`

### Scenario 3: Network Access
- BarcodeMaster on Server (IP: 10.0.0.50)
- Multiple BarcodeMatch clients
- ✅ Use: `http://10.0.0.50:5001/log`

## Verification Checklist

After fixing, verify:

- [ ] Can open web interface at `http://IP:5001` in browser
- [ ] "Test verbinding" shows green "Verbonden (TEST)"
- [ ] Logs section loads and shows entries
- [ ] Can double-click log entry to open project
- [ ] Manual AFGEMELD event works
- [ ] No 404 errors in logs

## Firewall Configuration

If still getting connection errors (not 404):

### On BarcodeMaster Computer:
1. Allow inbound connections on port 5001
2. Windows Firewall:
   - Control Panel → Windows Defender Firewall
   - Advanced Settings → Inbound Rules
   - New Rule → Port → TCP → 5001
   - Allow the connection

### Network Firewall:
- Ensure port 5001 is allowed between computers
- Check if antivirus blocks connections

## Additional Notes

### Why Does Browser Work But Python Doesn't?

When you manually type `http://IP:5001/log` in a browser:
- Browser shows the endpoint response
- Python program expects specific JSON structure
- Different endpoints require different HTTP methods (GET vs POST)

### Config.json Location

The configuration file is at:
```
C:\Users\Rob\Desktop\Test-thuis\BarcodeMatch\config.json
```

You can manually edit it, but using the Database panel GUI is recommended.

### Correct config.json Format

```json
{
  "database_enabled": true,
  "api_url": "http://192.168.1.100:5001/log",
  "user": "ACCURA"
}
```

## Contact & Support

If issues persist after following this guide:
1. Run the diagnostic tool and save the output
2. Check BarcodeMaster logs in `database/db_log_api.log`
3. Verify BarcodeMaster API is running (check Admin Panel → Database tab)
4. Test connectivity with: `ping [BARCODEMASTER_IP]`

---

Last Updated: 2025-10-13
