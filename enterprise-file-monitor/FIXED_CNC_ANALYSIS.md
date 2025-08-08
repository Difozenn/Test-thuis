# Fixed CNC Analysis for All 3 Formats

## Bugs Fixed:

### 1. **Missing Tool Change Count for D-codes**
- **Problem**: D-code tool changes (D601 → D181) weren't incrementing ToolChanges
- **Fix**: Added `analysis.ToolChanges++` when D-code changes to different tool

### 2. **Tool State Not Reset Between Files**
- **Problem**: `_currentActiveTool` wasn't reset, causing issues when analyzing multiple files
- **Fix**: Added reset of `_currentActiveTool = 0` and `_toolSessions.Clear()`

### 3. **Incorrect Time Unit Conversion**
- **Problem**: Movement times were incorrectly multiplied by 60
- **Fix**: Removed the * 60 multiplication as times are already in correct units

## Expected Results After Fix:

### **opus.nc**
- Tool Changes: **2**
  - Line 82: CH_TOOLCHANGE → Tool 601
  - Line 191: D181 → Tool 181 (change from 601)
- Tools Used: 601, 181

### **nesting.NC**
- Tool Changes: **2**
  - Line 78: CP_TC → Tool 601
  - Line 148: CP_TC → Tool 181
- Tools Used: 601, 181

### **Field1.spf**
- Tool Changes: **2**
  - Line 79: C_WECHSEL → Tool 17
  - Line 154: C_WECHSEL → Tool 10
- Tools Used: 17, 10

## How It Works Now:

1. **OPUS Format (opus.nc)**:
   - Primary: `CH_TOOLCHANGE.NC @P4=XXX`
   - Secondary: `DXXX` (when different from current tool)
   - Both increment tool change count

2. **HH7 Format (nesting.NC)**:
   - Primary: `CP_TC.NC @P4=XXX`
   - Increments tool change count

3. **Vision/Siemens Format (Field1.spf)**:
   - Primary: `C_WECHSEL(XX`
   - Increments tool change count

## Timing Calculation:
- Tool change time: 13.05 seconds per change (default)
- All 3 files: 2 × 13.05s = 26.1 seconds overhead
- Plus cutting time based on actual feedrates and distances
- Total time: ~30-40 seconds as expected