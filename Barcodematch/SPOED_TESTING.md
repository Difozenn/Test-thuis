# SPOED Warning System - Testing Guide

## Overview
The SPOED warning system monitors for urgent projects (containing "_SPOED", "SPOED", "_SPOED_" in the project name) and displays a persistent warning in the menu bar.

## Features Implemented

### 1. **Persistent Warning Widget**
- Red warning bar appears in the menu (next to Settings tab)
- Shows: `⚠️ SPOED: [Project Name]`
- Includes X button to dismiss
- Only shows one SPOED warning at a time
- Once dismissed, won't show again for that specific project

### 2. **Background Monitoring**
- Checks every 15 seconds for SPOED projects
- Only monitors projects for the current user
- Checks for projects with status: OPEN, EXCEL_GENERATED, or BEZIG
- Works even when user is in Scanner panel working on another project

### 3. **Visual Highlighting in Database Panel**
- SPOED projects appear with bright red background (#ff6666) and white text
- Makes SPOED projects immediately visible and prominent in logs

### 4. **SPOED Pattern Detection**
Detects the following patterns (case-insensitive):
- `_SPOED_` (e.g., "MO12345_SPOED_Urgent")
- `_SPOED` (e.g., "MO12345_SPOED")
- `SPOED_` (e.g., "SPOED_MO12345")
- `SPOED` (e.g., "SPOEDPROJECT")

## Testing Steps

### Test 0: Manual Test Button
1. Go to Help panel
2. Click "Test SPOED Warning" button
3. A red warning should immediately appear in the menu bar showing: `⚠️ SPOED: MO99999_SPOED_TestProject`
4. Click the X button to dismiss it
5. Click the test button again - the warning should NOT appear (already dismissed)

### Test 1: Basic SPOED Detection
1. Start BarcodeMatch
2. Create or import a project with "SPOED" in the name (e.g., "MO99999_SPOED_Test")
3. Within 15 seconds, a red warning should appear in the menu bar
4. The warning should show: `⚠️ SPOED: MO99999_SPOED_Test`

### Test 2: Dismiss Function
1. Click the X button on the SPOED warning
2. The warning should disappear
3. Wait 30 seconds - the same project should NOT trigger again
4. The project remains dismissed until app restart

### Test 3: Multiple SPOED Projects
1. Create two SPOED projects for the same user
2. Only the first one should show initially
3. Dismiss the first warning
4. The second SPOED project should then appear
5. Only one warning shows at a time

### Test 4: Database Panel Highlighting
1. Open Database panel
2. Look for any SPOED projects in the logs
3. They should have a bright red background (#ff6666) with white text
4. The highlighting should persist when sorting or filtering
5. The red rows should be immediately noticeable and stand out from regular entries

### Test 5: Background Monitoring While Working
1. Load a normal (non-SPOED) project in Scanner panel
2. Start working with the barcode scanner
3. Have someone else (or via API) create a new SPOED project for your user
4. Within 15 seconds, the warning should appear even though you're in Scanner panel
5. The warning doesn't interrupt your work - just appears in the menu

### Test 6: User-Specific Warnings
1. Configure BarcodeMatch with user "OPUS"
2. Create a SPOED project for user "BOERE"
3. No warning should appear (different user)
4. Create a SPOED project for user "OPUS"
5. Warning should appear within 15 seconds

### Test 7: Case Insensitivity
Test that all these variations trigger the warning:
- "MO12345_spoed_test"
- "MO12345_SPOED_test"
- "MO12345_Spoed_test"
- "spoedproject"

## Configuration Requirements
- Database must be enabled in settings
- API connection must be working
- User must be configured in settings

## Troubleshooting

### Warning Not Appearing
1. Check database is enabled in Settings panel
2. Verify API connection (green status in Database panel)
3. Check user is configured correctly
4. Verify project has status OPEN, EXCEL_GENERATED, or BEZIG
5. Check project name contains SPOED pattern
6. Wait at least 15 seconds for monitoring cycle

### Warning Keeps Reappearing
- This shouldn't happen - dismissed projects are tracked
- If it does, restart the application

### Database Panel Not Highlighting
1. Refresh the logs (happens automatically every 10 seconds)
2. Check the project name contains SPOED pattern
3. Clear any search filters that might be hiding the project

## Debug Mode
To enable debug output:
```bash
set BARCODEMATCH_DEBUG=true
BarcodeMatch.exe
```

Look for:
- `[SPOED MONITOR]` messages
- `[SPOED WARNING]` messages

## Notes
- Monitoring starts automatically when app launches
- Dismissed warnings reset when app restarts
- Warning appears for ALL panels, not just Scanner/Database
- System works independently of which panel is active