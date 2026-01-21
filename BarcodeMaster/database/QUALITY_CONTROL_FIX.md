# Quality Control API Fix Summary

## Issue
The "Kwaliteitscontrole & Reparaties" section on the statistics page was failing with error: "no such column: l.timestamp"

## Root Cause
There were two quality-related endpoints with date filter issues:

1. `/api/statistics/quality-metrics` (line ~7534)
   - Used `date_filter_with_alias` variable that was never defined
   - Only `date_filter` was being created

2. `/api/statistics/quality-control` (line ~7891)  
   - Had complex parameter handling that wasn't working correctly
   - Used three separate param lists (params1, params2, params3) but implementation was buggy

## Fixes Applied

### 1. Fixed quality-metrics endpoint (line ~7544)
Added the missing `date_filter_with_alias` variable:
```python
# Build date filter
date_filter = ""
date_filter_with_alias = ""  # For queries using 'l' alias
params = []

if period_type == 'custom' and start_date and end_date:
    date_filter = " AND timestamp BETWEEN ? AND ?"
    date_filter_with_alias = " AND l.timestamp BETWEEN ? AND ?"
    params.extend([start_date + ' 00:00:00', end_date + ' 23:59:59'])
elif period_type == 'all':
    pass  # No date filter
else:
    period_int = int(period)
    date_filter = " AND timestamp >= datetime('now', '-{} days')".format(period_int)
    date_filter_with_alias = " AND l.timestamp >= datetime('now', '-{} days')".format(period_int)
```

### 2. Fixed quality-control endpoint (line ~7901)
Properly separated parameters for different queries:
```python
# Build date filter - separate params for each query
date_filter = ""
date_filter_with_alias = ""  # For queries using 'l' alias
params1 = []  # For first query (no alias)
params2 = []  # For second query (with 'l' alias)
params3 = []  # For third query (with 'l' alias)
```

### 3. Added debugging
Added logging to help identify which query fails:
- Log before each query execution with the filter and params being used
- Wrap each query in try/except to identify the specific failing query

## Action Required
**The API server at 192.168.0.120:5001 needs to be restarted to pick up these changes.**

The fixes have been applied to `/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/db_log_api.py` but the Windows API server is still running the old version.

## Testing
After restarting the API, test with:
```bash
curl "http://192.168.0.120:5001/api/statistics/quality-control?period=7&period_type=days"
curl "http://192.168.0.120:5001/api/statistics/quality-metrics?period=7&period_type=days"
```

Both endpoints should return valid JSON without errors.