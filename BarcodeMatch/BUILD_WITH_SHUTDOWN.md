# Building BarcodeMatch with Shutdown Handling

## Important: Required Files for EXE Build

The new shutdown handling system requires these files to be included when building the EXE:

### New Files Added:
1. **`session_manager.py`** - Handles session persistence and crash recovery
2. **`windows_shutdown.py`** - Detects Windows shutdown events (WM_QUERYENDSESSION)

### Files Already Updated:
- `gui/app.py` - Initializes Windows shutdown handler
- `gui/panels/scanner_panel.py` - Integrates session persistence
- `build_exe.py` - Updated with new hidden imports

## Build Configuration Updates

### ✅ Already Updated in build_exe.py:

The `hiddenimports` list now includes:
```python
hiddenimports = [
    # Core modules
    'config_utils',
    'build_info',
    'startup_utils',
    'session_manager',      # NEW - for crash recovery
    'windows_shutdown',     # NEW - for Windows shutdown detection
    # ... rest of imports
]
```

### ✅ Already Updated in BarcodeMatch_32bit.spec:

The spec file includes the new modules in hiddenimports.

## Building the EXE

### For 64-bit Build:
```bash
python build_exe.py
```

### For 32-bit Build:
```bash
# Must use 32-bit Python!
python build_32bit.py
```

## What Gets Compiled Into the EXE

### Session Persistence:
- **Runtime Directory**: `%APPDATA%\BarcodeMatch\`
- **Session File**: `active_session.json`
- **Lock File**: `session.lock`
- These are created at runtime, NOT bundled in EXE

### Windows Shutdown Detection:
- Uses Windows API (ctypes.windll)
- Creates invisible window to receive shutdown messages
- No external dependencies needed

### Signal Handlers:
- Standard Python signal module
- atexit handlers
- All built into Python stdlib

## Dependencies

### Required Python Packages:
All standard - no new packages needed for shutdown handling:
- `ctypes` (built-in) - For Windows API
- `signal` (built-in) - For signal handling
- `atexit` (built-in) - For exit handlers
- `json` (built-in) - For session file
- `pathlib` (built-in) - For file paths

### Optional (fallback only):
- `psutil` - For process detection (not required, has ctypes fallback)

## Testing the Built EXE

### 1. Verify Files Included:
After building, the EXE should have these behaviors:
- Creates `%APPDATA%\BarcodeMatch\` folder on first run
- Shows `[SESSION_MANAGER]` messages in console (debug mode)
- Shows `[SHUTDOWN]` messages when Windows shuts down

### 2. Test Crash Recovery:
1. Run the EXE
2. Start a session in Scanner panel
3. Kill via Task Manager
4. Restart EXE
5. Should see: `[SESSION_MANAGER] Crash detected - recovering session`

### 3. Test Windows Shutdown:
1. Run the EXE with active session
2. Shut down Windows (Start → Shutdown)
3. After restart, check database - session should be PAUSED

## Build Troubleshooting

### If shutdown handling doesn't work in EXE:

1. **Check if modules are included:**
   ```python
   # In your built EXE directory, test:
   import session_manager
   import windows_shutdown
   ```

2. **Verify ctypes works:**
   ```python
   import ctypes
   ctypes.windll.kernel32  # Should not error
   ```

3. **Check AppData permissions:**
   - EXE must be able to write to `%APPDATA%\BarcodeMatch\`
   - Anti-virus might block file creation

### Common Issues:

#### "ModuleNotFoundError: session_manager"
- Solution: Ensure `session_manager.py` is in root directory
- Check `hiddenimports` in spec file

#### "Windows shutdown not detected"
- Windows Fast Startup can skip shutdown signals
- Some anti-virus software blocks window message hooks
- Run as administrator may help

#### "Session file not created"
- Check `%APPDATA%\BarcodeMatch\` exists
- Verify write permissions
- Look for `[SESSION_MANAGER ERROR]` in console

## Build Checklist

Before building:
- [ ] `session_manager.py` exists in root
- [ ] `windows_shutdown.py` exists in root
- [ ] `build_exe.py` has updated hiddenimports
- [ ] Spec files have updated hiddenimports

After building:
- [ ] Test normal close (X button)
- [ ] Test Windows shutdown
- [ ] Test force kill (Task Manager)
- [ ] Check `%APPDATA%\BarcodeMatch\` creation
- [ ] Verify console shows shutdown messages

## Important Notes

1. **Windows-Specific**: The `windows_shutdown.py` only works on Windows. On other platforms it's safely skipped.

2. **No Admin Required**: The shutdown detection doesn't require admin rights.

3. **Portable**: The EXE can be run from any location. Session files always go to `%APPDATA%`.

4. **Clean Uninstall**: To fully remove, delete:
   - The EXE file
   - `%APPDATA%\BarcodeMatch\` folder

5. **Multi-Instance**: Lock files prevent multiple instances from conflicting.

## Summary

The shutdown handling is fully integrated into the build process:
- ✅ All files included in build configurations
- ✅ No external dependencies required
- ✅ Works in compiled EXE form
- ✅ Transparent to end users

Just run your normal build command - shutdown protection is automatically included!