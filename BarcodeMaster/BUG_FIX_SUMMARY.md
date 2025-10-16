# Bug Fix Summary: User Configuration Not Showing in Admin Panel & Scanner Panel

## Problem
1. **Admin Panel**: When adding users in the "Gebruiker Configuratie" tab, the users were not appearing in the UI after being added
2. **Scanner Panel**: The "Handmatige Invoer" button was not showing the configured users in the dialog
3. **Background Import Service**: The automatic file processing service was not picking up newly added users

However, users were actually being saved to the database correctly - they just weren't being displayed or used by the background service.

## Root Cause
There was a **data source mismatch** in multiple functions:

### Admin Panel
1. **When adding a user** (`_add_user_config()`): Saved user data to the **database** via `/api/settings` ✓
2. **When rebuilding the UI** (`_build_user_list_ui()`): Loaded data from `get_config()` which reads from **config.json file** ✗

### Scanner Panel  
1. **Manual entry dialogs** (`open_manual_entry_dialog()` and `open_manual_entry_with_data()`): Loaded users from `get_config()` which reads from **config.json file** ✗
2. **Expected behavior**: Should load from the **database** where users are stored ✓

### Background Import Service
1. **Config loading** (`load_config()` and `_process_all_excel_users_unified()`): Loaded users from `get_config()` which reads from **config.json file** ✗
2. **Expected behavior**: Should load from the **database** where users are stored ✓
3. **Impact**: Newly added users wouldn't be processed automatically until the service was restarted

This caused a disconnect where:
- New users were saved to the database ✓
- But the UI was reading from the old config file ✗
- So users appeared to not be saved, even though they were

## Verification
Running a database query confirmed users WERE being saved:
```
scanner_panel_open_event_users: ["NESTING", "ACCURA", "OPUS", "KL GANNOMAT", "GR GANNOMAT", "HANDWERK", "BOERE"]
scanner_user_to_processing_type_map: {...}
scanner_panel_open_event_user_logic_active: {...}
```

## Solution

### 1. Admin Panel Fix
Modified `_build_user_list_ui()` in `gui/panels/admin_panel.py` (line 910):

**Before:**
```python
config = get_config()  # Reads from config.json file
open_users = config.get('scanner_panel_open_event_users', [])
```

**After:**
```python
# Load from database instead of config file
config = self._load_settings_from_api()  # Reads from database via API
open_users = config.get('scanner_panel_open_event_users', [])

# Update instance variables with database values
self.scanner_panel_open_event_user_paths = config.get('scanner_panel_open_event_user_paths', {})
self.scanner_panel_open_event_user_logic_active = config.get('scanner_panel_open_event_user_logic_active', {})
self.scanner_user_to_processing_type_map = config.get('scanner_user_to_processing_type_map', {})
```

### 2. Scanner Panel Fix

**Added new method** `_load_settings_from_api()` to `ScannerPanel` class (line 2405):
```python
def _load_settings_from_api(self):
    """Load settings from database via API"""
    try:
        config = get_config()
        api_url = config.get('api_url', 'http://localhost:5001')
        base_url = api_url.split('/log')[0]
        response = requests.get(f"{base_url}/api/settings", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('settings', {})
    except Exception as e:
        print(f"Could not load settings from database: {e}")
    
    # Fallback to config file
    return get_config()
```

**Modified** `open_manual_entry_dialog()` (line 3011):
```python
# Before:
config = get_config()

# After:
config = self._load_settings_from_api()
```

**Modified** `open_manual_entry_with_data()` (line 3854):
```python
# Before:
from config_utils import get_config
config = get_config()

# After:
config = self._load_settings_from_api()
```

### 3. Background Import Service Fix

**Added new method** `_load_settings_from_api()` to `BackgroundImportService` class (line 88):
```python
def _load_settings_from_api(self):
    """Load settings from database via API"""
    try:
        config = get_config()
        api_url = config.get('api_url', 'http://localhost:5001')
        base_url = api_url.split('/log')[0]
        response = requests.get(f"{base_url}/api/settings", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('settings', {})
    except Exception as e:
        if self.logger:
            self.logger.warning(f"Could not load settings from database: {e}")
    
    # Fallback to config file
    return get_config()
```

**Modified** `load_config()` (line 106):
```python
# Before:
config = get_config()

# After:
config = self._load_settings_from_api()
```

**Modified** `_process_all_excel_users_unified()` (line 1731):
```python
# Before:
config = get_config()

# After:
config = self._load_settings_from_api()
```

## Result
Now when users are added:
1. They are saved to the database ✓
2. The UI rebuilds and reads from the database ✓
3. Users appear immediately in the panel ✓
4. Background service picks up new users automatically ✓

## Files Modified
1. **`gui/panels/admin_panel.py`**
   - Line 910-917: Modified `_build_user_list_ui()` to load from database

2. **`gui/panels/scanner_panel.py`**
   - Line 2405-2420: Added `_load_settings_from_api()` method
   - Line 3012: Modified `open_manual_entry_dialog()` to use database
   - Line 3854: Modified `open_manual_entry_with_data()` to use database

3. **`services/background_import_service.py`** ⚠️ **CRITICAL FIX**
   - Line 88-104: Added `_load_settings_from_api()` method
   - Line 110: Modified `load_config()` to use database
   - Line 1731: Modified `_process_all_excel_users_unified()` to use database

## Testing

### Admin Panel Test
1. Open the Admin Panel
2. Go to "Gebruiker Configuratie" tab
3. You should see all 7 existing users (NESTING, ACCURA, OPUS, KL GANNOMAT, GR GANNOMAT, HANDWERK, BOERE)
4. Add a new test user with a username and processing type
5. Click "Toevoegen"
6. **Expected**: The user appears immediately in the list above

### Scanner Panel Test
1. Open the Scanner Panel
2. Click the "Handmatige Invoer" button
3. **Expected**: The dialog shows all configured users with input fields
4. Each user should have their correct processing type displayed
5. Users should match what's in the Admin Panel configuration

### Background Service Test ⚠️ **IMPORTANT**
1. Add a new user in Admin Panel (e.g., "TEST_USER" with "ACCURA_PROCESSING")
2. Set an import path for this user
3. Place a test Excel file in that path
4. **Expected**: The background service should automatically detect and process the file
5. **Without this fix**: The service would ignore the new user until restart

## Additional Notes
- The fix includes a fallback mechanism: if the database API is unavailable, it falls back to reading from config.json
- This ensures the application remains functional even if the API is down
- All user configuration changes are now consistently saved to and loaded from the database
