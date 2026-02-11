# Windows Shutdown & Crash Recovery Testing Guide

## Overview
The enhanced shutdown handling system provides multiple layers of protection to ensure active sessions are properly paused when Windows shuts down or the application crashes.

## Three Layers of Protection

### 1. **Session File Persistence** (`session_manager.py`)
- Saves session state to `%APPDATA%\BarcodeMatch\active_session.json`
- Updates whenever session starts, pauses, or changes
- Automatically recovered on next startup if crash detected

### 2. **Windows Shutdown Detection** (`windows_shutdown.py`)
- Listens for Windows `WM_QUERYENDSESSION` and `WM_ENDSESSION` messages
- Triggers immediate session pause when Windows initiates shutdown
- Works even when normal signal handlers fail

### 3. **Standard Signal Handlers** (existing)
- `SIGTERM` - Normal termination signal
- `SIGINT` - Ctrl+C
- `SIGBREAK` - Windows Ctrl+Break
- `atexit` - Normal Python exit

## Files Added/Modified

### New Files:
- `session_manager.py` - Handles session file persistence
- `windows_shutdown.py` - Windows-specific shutdown detection
- `SHUTDOWN_TESTING.md` - This testing guide

### Modified Files:
- `gui/app.py` - Added Windows shutdown handler initialization
- `gui/panels/scanner_panel.py` - Added session persistence and recovery

## Testing Scenarios

### Test 1: Normal Application Close
1. Start BarcodeMatch
2. Load an Excel file in Scanner panel
3. Start scanning (creates active session)
4. Close application using X button
5. Check console: Should see `[SHUTDOWN] Pausing active session`
6. Restart application
7. Session should be properly paused in database

### Test 2: Windows Shutdown While Active
1. Start BarcodeMatch
2. Load Excel file and start scanning
3. Note the session ID in console
4. **Shut down Windows** (Start → Power → Shut down)
5. After restart, check database logs
6. Session should show as PAUSED, not still BEZIG

### Test 3: Force Kill Recovery
1. Start BarcodeMatch
2. Load Excel file and start scanning
3. Open Task Manager (Ctrl+Shift+Esc)
4. Find BarcodeMatch.exe
5. Click "End Task" (forceful termination)
6. Restart BarcodeMatch
7. Check console for: `[SESSION_MANAGER] Crash detected - recovering session`
8. Database should show CRASH_RECOVERY event and session should be paused

### Test 4: Power Loss Simulation
1. Start BarcodeMatch with active session
2. Note session details
3. Hold power button for 5 seconds (forced shutdown)
4. Restart computer
5. Start BarcodeMatch
6. Should detect crash and recover session

### Test 5: Multiple Sessions
1. Start session for project A
2. Switch to Database panel (pauses session A)
3. Force kill application
4. Restart - session A should be recovered
5. Verify only the active session was affected

## What to Look For

### Console Output:

**On Startup (after crash):**
```
[SESSION_MANAGER] Lock file found - previous instance may have crashed
[SESSION_MANAGER] Previous process 12345 not running - crash detected
[SESSION_MANAGER] Recovering session: OPUS_MO12345_20251109_143022
[SESSION_MANAGER] Successfully sent crash recovery pause event
```

**On Windows Shutdown:**
```
[SHUTDOWN] WM_QUERYENDSESSION received - Windows shutdown initiated
[SHUTDOWN] Pausing active session: OPUS_MO12345_20251109_143022
[PAUSE_API] Session pause successful
```

**Session File Location:**
- Windows: `%APPDATA%\BarcodeMatch\active_session.json`
- Example: `C:\Users\[Username]\AppData\Roaming\BarcodeMatch\active_session.json`

### Database Logs Should Show:

1. **After normal shutdown:** SESSION_PAUSE event
2. **After crash recovery:** CRASH_RECOVERY event followed by SESSION_PAUSE
3. **Status:** Changed from BEZIG to PAUZE

## Session File Format

The session file (`active_session.json`) contains:
```json
{
  "session_id": "OPUS_MO12345_20251109_143022",
  "user": "OPUS",
  "project": "MO12345_TestProject",
  "file_path": "C:\\Projects\\MO12345.xlsx",
  "start_time": "2025-11-09T14:30:22",
  "paused": false,
  "item_count": 25,
  "last_saved": "2025-11-09T14:35:15"
}
```

## Troubleshooting

### Session Not Pausing on Shutdown:
1. Check if `%APPDATA%\BarcodeMatch\` directory exists
2. Verify write permissions to AppData
3. Look for `[SESSION_MANAGER]` messages in console
4. Check if Windows Fast Startup is enabled (can skip shutdown signals)

### Recovery Not Working:
1. Check for `session.lock` file in `%APPDATA%\BarcodeMatch\`
2. Verify `active_session.json` exists and is valid JSON
3. Session older than 24 hours won't be recovered

### Windows Handler Not Starting:
1. Check for: `[APP] Setting up Windows shutdown handler`
2. Verify Python has permission to create windows
3. Anti-virus might block window message hooks

## Configuration

No configuration needed - the system works automatically. However:

- Session files expire after 24 hours
- Lock files are cleaned up on successful start
- Failed API calls during recovery are non-fatal

## Important Notes

1. **Windows Fast Startup**: If enabled, Windows may not send proper shutdown signals. Consider disabling for testing.

2. **API Availability**: If the API is down during recovery, the session file is still cleared to prevent duplicate recovery attempts.

3. **Multiple Instances**: The lock file prevents multiple instances from interfering with each other.

4. **Crash vs Shutdown**: The system differentiates between crashes (no cleanup) and shutdowns (partial cleanup).

## Expected Behavior Summary

| Scenario | Session File | Database Event | Session Status |
|----------|-------------|----------------|----------------|
| Normal close | Deleted | SESSION_PAUSE | PAUZE |
| Windows shutdown | Deleted after pause | SESSION_PAUSE | PAUZE |
| Application crash | Recovered on startup | CRASH_RECOVERY + SESSION_PAUSE | PAUZE |
| Power loss | Recovered on startup | CRASH_RECOVERY + SESSION_PAUSE | PAUZE |
| API unavailable | Still deleted | No event (local only) | Unknown |

## Debug Mode

Enable debug output to see detailed shutdown handling:
```batch
set BARCODEMATCH_DEBUG=true
BarcodeMatch.exe
```

Look for these prefixes in console:
- `[SESSION_MANAGER]` - Session file operations
- `[SHUTDOWN]` - Windows shutdown detection
- `[PAUSE_API]` - Session pause operations
- `[CRASH_RECOVERY]` - Recovery operations