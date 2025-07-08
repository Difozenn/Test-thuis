# BarcodeMaster Session Fix - Critical Issue

## The Problem
The main issue is in the `/session/xlsx_updated` endpoint (line 863-865 in db_log_api.py):

```python
# CURRENT CODE (WRONG):
c.execute("""
    INSERT INTO sessions (session_id, user, project, start_time, status, item_count)
    VALUES (?, ?, ?, ?, 'active', ?)
""", (session_id, data['user'], data['project'], data['timestamp'], data.get('item_count', 0)))
```

This sets the `item_count` at session START, but performance metrics expect `item_count` to be set at session END.

## The Fix

### Option 1: Quick Fix (Recommended)
Change line 865 to NOT use the item_count from the request:

```python
# FIXED CODE:
c.execute("""
    INSERT INTO sessions (session_id, user, project, start_time, status, item_count, session_type)
    VALUES (?, ?, ?, ?, 'active', 0, 'XLSX_UPDATED')
""", (session_id, data['user'], data['project'], data['timestamp']))
```

### Option 2: Complete Fix
Also update the project_log table insertion (line 886-888):

```python
# FIXED CODE:
c.execute("""
    INSERT INTO project_log (project, event, user, timestamp, item_count)
    VALUES (?, 'BEZIG', ?, ?, 0)
""", (data['project'], data['user'], data['timestamp']))
```

## Implementation Steps

1. **Locate the file**: `/home/difusion/Projects/BarcodeMaster/database/db_log_api.py`

2. **Find the xlsx_updated function** (around line 842)

3. **Change line 865** from:
   ```python
   """, (session_id, data['user'], data['project'], data['timestamp'], data.get('item_count', 0)))
   ```
   
   To:
   ```python
   """, (session_id, data['user'], data['project'], data['timestamp']))
   ```

4. **Add session_type** to the INSERT statement (line 863):
   ```python
   INSERT INTO sessions (session_id, user, project, start_time, status, item_count, session_type)
   VALUES (?, ?, ?, ?, 'active', 0, 'XLSX_UPDATED')
   ```

5. **Also fix line 888** from:
   ```python
   """, (data['project'], data['user'], data['timestamp'], data.get('item_count', 0)))
   ```
   
   To:
   ```python
   """, (data['project'], data['user'], data['timestamp']))
   ```

## Verification

After applying the fix:

1. Start a new session for OPUS on a project
2. Check the database: `SELECT * FROM sessions WHERE user = 'OPUS' AND status = 'active'`
   - `item_count` should be 0, not the XLSX count
3. Complete the session with manual_finish
4. Check again: `SELECT * FROM sessions WHERE user = 'OPUS' ORDER BY start_time DESC LIMIT 1`
   - `item_count` should now be the final count
   - `status` should be 'completed'
5. Performance metrics should show correct items/hour calculation

## Why This Works

1. **Session Start**: Creates session with item_count = 0
2. **During Work**: Session remains active, item_count stays 0
3. **Session End**: `/session/manual_finish` updates item_count with final value
4. **Performance Calc**: Now has correct end count ÷ work duration = proper items/hour

## Additional Improvements Needed

1. **Real-time updates**: Implement WebSocket or AJAX polling
2. **Dashboard queries**: Add active session display
3. **Status tracking**: Better BEZIG status visibility
4. **Error handling**: Log when sessions don't complete properly