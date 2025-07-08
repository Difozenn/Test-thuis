# BarcodeMaster + BarcodeMatch Complete Workflow Test Scenario

## 🎯 Test Overview
This document provides a comprehensive test scenario for the complete workflow between BarcodeMaster and BarcodeMatch, covering all recent fixes and expected behaviors.

---

## 📋 Test Prerequisites

### System Configuration
```json
{
    "user": "NESTING",
    "scanner_panel_open_event_users": ["NESTING", "OPUS", "KL GANNOMAT"],
    "scanner_user_to_processing_type_map": {
        "OPUS": "HOPS_PROCESSING",
        "KL GANNOMAT": "MDB_PROCESSING"
    },
    "dashboard_display_users": ["NESTING", "OPUS", "KL GANNOMAT"]
}
```

### Work Hours Configuration
- Monday-Thursday: 07:30-16:00
- Friday: 07:30-15:00
- Break: 12:00-12:30
- Work days: Monday-Friday

---

## 🔄 Complete Workflow Test Scenario

### **Phase 1: NESTING User Starts Work (BarcodeMaster)**

#### 1.1 Session Start
**Actions:**
1. NESTING user opens BarcodeMaster
2. Clicks "START SESSIE" button at 08:00

**Expected Results:**
```
✓ Work hours validation passes
✓ Session created with ID: NESTING_20250105_080000
✓ Session type: SCANNER
✓ Database: New entry in sessions table (status='active')
✓ UI: Button changes to "STOP SESSIE" (red)
✓ UI: Session timer starts showing "Werktijd: 00:00"
```

**Log Entries:**
```
[08:00:00] ✓ Werk sessie gestart voor NESTING
```

**Database State:**
```sql
-- sessions table
session_id: NESTING_20250105_080000
user: NESTING
start_time: 2025-01-05 08:00:00
status: active
session_type: SCANNER
work_duration_minutes: NULL
item_count: 0
```

#### 1.2 OPEN Event Scan
**Actions:**
1. Scanner panel set to OPEN event type
2. User scans barcode: "0618_MO07840_TestProject"

**Expected Results:**
```
✓ Project code extracted: MO07840
✓ Full project name: MO07840_TestProject
✓ Background service triggered for other users
✓ OPEN events created for OPUS and KL GANNOMAT
✓ Import services triggered based on processing type
```

**Log Entries:**
```
[08:01:00] 🔄 Project MO07840_TestProject wordt verwerkt voor alle gebruikers...
[08:01:01] Event ontvangen: User=OPUS, Project=MO07840_TestProject. Controleren voor import...
[08:01:01] HOPS_PROCESSING voor user 'OPUS' wordt gestart voor gevonden map: /path/to/OPUS/MO07840_TestProject
[08:01:02] Event ontvangen: User=KL GANNOMAT, Project=MO07840_TestProject. Controleren voor import...
[08:01:02] MDB_PROCESSING voor user 'KL GANNOMAT' wordt gestart
```

**Database State:**
```sql
-- logs table
event: OPEN, user: NESTING, project: MO07840_TestProject, status: OPEN
event: OPEN, user: OPUS, project: MO07840_TestProject, status: OPEN
event: OPEN, user: KL GANNOMAT, project: MO07840_TestProject, status: OPEN

-- project_log table
project: MO07840_TestProject, event: OPEN, user: NESTING
project: MO07840_TestProject, event: OPEN, user: OPUS
project: MO07840_TestProject, event: OPEN, user: KL GANNOMAT
```

---

### **Phase 2: Background Import Services**

#### 2.1 HOPS Processing (OPUS)
**Actions:**
1. Background service scans OPUS directory
2. Finds matching folder: MO07840_TestProject
3. Collects all .hop/.hops files
4. Generates Excel report

**Expected Results:**
```
✓ 25 .hop files found in directory
✓ Excel created: /path/to/OPUS/MO07840_TestProject/MO07840_TestProject.xlsx
✓ Item count: 25
✓ OPEN event updated with file path and item count
```

**Log Entries:**
```
[08:01:03] 25 HOPS (.hop/.hops) bestanden gevonden voor Excel rapportage
[08:01:04] HOPS Excel rapport succesvol opgeslagen: /path/to/OPUS/MO07840_TestProject/MO07840_TestProject.xlsx
[08:01:04] HOPS Excel rapport bevat 25 items
[08:01:05] OPEN event updated with Excel path for: OPUS - MO07840_TestProject
[08:01:05] OPEN event updated with item count (25) for: OPUS - MO07840_TestProject
```

#### 2.2 MDB Processing (KL GANNOMAT)
**Actions:**
1. Background service scans KL GANNOMAT directory
2. Finds matching file: MO07840_TestProject.mdb
3. Extracts ProgramNumbers from database
4. Generates Excel report

**Expected Results:**
```
✓ MDB file found and processed
✓ 42 ProgramNumbers extracted
✓ Excel created: /path/to/GANNOMAT/MO07840_TestProject.xlsx
✓ Item count: 42
✓ OPEN event updated with file path and item count
```

**Log Entries:**
```
[08:01:03] Overeenkomend MDB bestand gevonden: MO07840_TestProject.mdb
[08:01:04] Querying 'ProgramNumber' from table 'Program'
[08:01:05] MDB Excel rapport succesvol opgeslagen: /path/to/GANNOMAT/MO07840_TestProject.xlsx
[08:01:05] MDB Excel rapport bevat 42 items
[08:01:06] OPEN event updated with Excel path for: KL GANNOMAT - MO07840_TestProject
[08:01:06] OPEN event updated with item count (42) for: KL GANNOMAT - MO07840_TestProject
```

---

### **Phase 3: BarcodeMatch Session Creation (OPUS User)**

#### 3.1 XLSX Update Triggers Session
**Actions:**
1. BarcodeMatch detects new/updated XLSX file
2. Calls /session/xlsx_updated endpoint

**Expected Results:**
```
✓ New session created for OPUS user
✓ Session type: XLSX_UPDATED
✓ Item count: 0 (NOT the Excel count - this is correct per fix)
✓ Project status changes from OPEN to BEZIG
✓ MO_START event logged
```

**Database State:**
```sql
-- sessions table
session_id: OPUS_MO07840_TestProject_20250105_080106
user: OPUS
project: MO07840_TestProject
start_time: 2025-01-05 08:01:06
status: active
session_type: XLSX_UPDATED
item_count: 0  -- Correct: starts at 0, not 25

-- logs table
event: MO_START, user: OPUS, project: MO07840_TestProject, status: BEZIG
details: "XLSX_UPDATED: 0 items"  -- Shows initial count

-- project_log table (updated)
project: MO07840_TestProject, event: BEZIG, user: OPUS
```

#### 3.2 Work Progress in BarcodeMatch
**Actions:**
1. OPUS user works on items in BarcodeMatch
2. Marks items as completed
3. Right-clicks to finish with count

**Expected Results:**
```
✓ Session remains active
✓ Work duration accumulating (excluding breaks)
✓ Dashboard shows BEZIG status (after 30s refresh)
```

---

### **Phase 4: Session Completion**

#### 4.1 OPUS Completes Work
**Actions:**
1. OPUS user right-clicks → "Finish with count"
2. Enters completed items: 23 (out of 25)
3. Calls /session/manual_finish

**Expected Results:**
```
✓ Session end_time recorded
✓ work_duration_minutes calculated (e.g., 45.5 minutes)
✓ item_count updated to 23 (final count)
✓ Session status: completed
✓ Performance calculated: 30.3 items/hour
```

**Database State:**
```sql
-- sessions table (updated)
session_id: OPUS_MO07840_TestProject_20250105_080106
end_time: 2025-01-05 08:46:36
status: completed
work_duration_minutes: 45.5
item_count: 23  -- Final count, not initial
```

#### 4.2 NESTING Scans AFGEMELD
**Actions:**
1. Scanner panel set to AFGEMELD event type
2. User scans same barcode: "0618_MO07840_TestProject"
3. Item count dialog appears

**Expected Results:**
```
✓ Item count dialog shows (per fix - already implemented)
✓ User enters: 23 items
✓ AFGEMELD event logged with item count
✓ Project session created and completed for NESTING
```

**Log Entries:**
```
[09:30:00] ✓ Project MO07840_TestProject afgesloten
[09:30:01] ✓ Project sessie voor MO07840_TestProject voltooid
```

**Database State:**
```sql
-- New project session for NESTING
session_id: NESTING_MO07840_TestProject_20250105_093000_a1b2c3d4
user: NESTING
project: MO07840_TestProject
start_time: 2025-01-05 08:00:00  -- Uses main session start
end_time: 2025-01-05 09:30:00
status: completed
session_type: SCANNER
work_duration_minutes: 85.0  -- Excludes break (12:00-12:30)
item_count: 23
```

#### 4.3 NESTING Stops Session
**Actions:**
1. Clicks "STOP SESSIE" button

**Expected Results:**
```
✓ Main session ended
✓ Total work duration calculated
✓ UI reset to initial state
```

---

## 📊 Dashboard and Reporting Verification

### Dashboard Display (After Refresh)
**Expected State:**
```
OPEN Projecten: 0
AFGEMELD Vandaag: 1 (MO07840_TestProject)

User Cards:
- NESTING: 
  - Sessietijd: 1h 25m (85 minutes work time)
  - Items voltooid: 23
  - Items/uur: 16.2
  
- OPUS:
  - Sessietijd: 0h 45m (45.5 minutes)
  - Items voltooid: 23
  - Items/uur: 30.3

- KL GANNOMAT:
  - Sessietijd: 0h 0m (no session started)
  - Items voltooid: 0
  - Items/uur: 0.0
```

### Project Logs Page (/logs/MO07840_TestProject)
**Expected Timeline:**
```
08:00:00 - SESSION_START (NESTING)
08:01:00 - OPEN events (all users)
08:01:06 - MO_START (OPUS) - Status: BEZIG
08:46:36 - SESSION_END (OPUS) - 23 items completed
09:30:00 - AFGEMELD (NESTING) - 23 items
09:30:00 - SESSION_END (NESTING)

Performance Analysis:
- NESTING: 23 items in 85 min = 16.2 items/uur ✓
- OPUS: 23 items in 45.5 min = 30.3 items/uur ✓
- Total idle time: 0h 0m (single entry, not spam) ✓
```

---

## ✅ Verification Checklist

### Recent Fixes Verification:
- [ ] **NESTING Performance**: Shows actual work duration and items/hour (not 0.0)
- [ ] **Idle Time Display**: Single entry, no spam of "0h 0m" entries
- [ ] **AFGEMELD Item Count**: Dialog appears and captures count correctly
- [ ] **Session Item Count**: Starts at 0, updated only at completion
- [ ] **Work Duration**: Correctly excludes breaks and non-work hours
- [ ] **Dashboard Updates**: Reflects changes after 30-second refresh

### Performance Metrics:
- [ ] Items per hour calculated correctly for all users
- [ ] Work duration excludes break time (12:00-12:30)
- [ ] Session timers show work time only
- [ ] Project timeline shows correct sequence

### Database Integrity:
- [ ] Sessions have correct session_type values
- [ ] Item counts are final values, not initial
- [ ] Work duration minutes calculated accurately
- [ ] Project status transitions: OPEN → BEZIG → AFGEMELD

---

## 🔍 Troubleshooting Guide

### If NESTING shows 0.0 items/uur:
1. Check sessions table has item_count > 0
2. Verify work_duration_minutes is calculated
3. Ensure session_type = 'SCANNER'

### If idle time shows spam:
1. Clear browser cache
2. Verify logs_project.html has the fix (lines 1604-1612)
3. Check for JavaScript errors in console

### If AFGEMELD dialog missing:
1. Verify scanner_panel.py lines 1210-1219
2. Check event_type_var is set to 'AFGEMELD'
3. Ensure dialog isn't blocked by other windows

### If sessions don't start:
1. Verify work hours configuration
2. Check API connectivity (port 5001)
3. Ensure user has valid session permissions

---

## 📈 Performance Baseline

After successful test completion:
- **NESTING efficiency**: 15-20 items/hour (typical)
- **OPUS efficiency**: 25-35 items/hour (typical)
- **Idle time**: < 5% of total project time
- **Dashboard refresh**: Within 30 seconds
- **Session creation latency**: < 2 seconds

---

*Test Scenario Version: 1.0*
*Last Updated: 2025-01-05*
*Covers: All fixes from FIXES_SUMMARY.md*