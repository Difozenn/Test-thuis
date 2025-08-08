# Debug Points Added for Field1.spf Analysis

## Key Debug Outputs to Watch For

### 1. **Tool Change Detection** (Lines 945-957)
```
[DEBUG] Line 79: Found C_WECHSEL in line: C_WECHSEL(17,3,22000)
[DEBUG] Line 79: C_WECHSEL detected: Platz 17 → Tool 602
[DEBUG] Tool change added, total changes now: 1
[DEBUG] Line 154: Found C_WECHSEL in line: C_WECHSEL(10,3,20000)
[DEBUG] Line 154: C_WECHSEL detected: Platz 10 → Tool 181
[DEBUG] Tool change added, total changes now: 2
```

### 2. **Tool Change Time Calculation** (Lines 768-774)
```
[TCALC] Tool changes count: 2
[TCALC] Tools used: [602, 181]
[TCALC] TC_51_51 value: 13.05s
[TCALC] Calculated tool change time: 2 × 13.05 = 26.1s
```

### 3. **Field1 Time Breakdown** (Lines 809-817)
```
[DEBUG Field1] Time breakdown:
  - Cutting: 10.3s
  - Rapids: 3.2s
  - Tool changes: 26.1s
  - Spindle starts: 0.0s
  - Cycle overhead: 0.0s
  - Total overhead: 29.3s
  - TOTAL: 39.6s
```

### 4. **Final Timing** (Lines 820-825)
```
[TCALC] ============ FINAL TIMING ============
[TCALC] Gesamtzeit/Total: 39.6s (0.66min)
[TCALC] Bearbeitungszeit/Processing: 10.3s
[TCALC] Werkzeugwechsel/Tool changes: 26.1s (2 changes)
[TCALC] Eilgänge/Rapids: 3.2s
[TCALC] ======================================
```

### 5. **SimpleCNCAnalyzer Debug** (Lines 140-149)
```
[DEBUG] SPF file analysis complete: Field1.spf
[DEBUG] ToolsUsed: [602, 181]
[DEBUG] ToolChanges: 2
[DEBUG] TotalTime: 0.66min (39.6s)
[DEBUG] Expected tool change time: 2 × 13.05s = 26.1s
[DEBUG] If tool changes were included, total would be: 39.6s
```

## Expected vs Actual

**Expected Output:**
- Tool changes: 2
- Tool change time: 26.1s
- Total time: ~39.5s

**Current Problem:**
- Total time showing as 23.6s (missing ~16s)
- Tools ARE detected correctly
- Need to verify if ToolChanges count is reaching the time calculation

## How to Run with Debug

```bash
# Windows Command Prompt
dotnet run > debug.log 2>&1

# Or to see output live
dotnet run

# Look for lines starting with [TCALC], [DEBUG], or [SIMPLE]
```

## Critical Check Points

1. **Is C_WECHSEL being found?** Check for "Found C_WECHSEL" messages
2. **Is ToolChanges being incremented?** Check for "total changes now: X"
3. **What's the TC_51_51 value?** Should be 13.05
4. **What's the calculated tool change time?** Should be 26.1s
5. **What's the final total?** Should be ~39.5s