# Field1.spf Timing Issue Analysis

## The Problem
- Field1.spf shows 23.6 seconds instead of 39.5 seconds
- Missing exactly 16 seconds (close to the 26.1s tool change time)

## What's Happening

### C# Side (FileMonitorTrayApp.cs)
1. **Tool Detection**: Tools T602 and T181 ARE detected ✓
2. **Tool Changes Count**: `analysis.ToolChanges` should be 2
3. **Tool Change Time**: Should be 2 × 13.05 = 26.1 seconds
4. **Total Time Calculation**:
   ```csharp
   double toolChangeTime = analysis.ToolChanges * _config.TC_51_51;
   double totalCycleTimeSeconds = cutTimeSeconds + overheadTimeSeconds;
   // overheadTimeSeconds includes toolChangeTime
   analysis.TotalTime = totalCycleTimeSeconds / 60.0;
   ```

### Python Side (app.py)
1. **Receives from C#**:
   - `TotalTime`: 0.393 minutes (23.6 seconds)
   - `ToolChanges`: Should be 2 (but might be 0?)
2. **Stores in database**:
   - `cycle_time_seconds = TotalTime * 60`
   - `tool_changes = ToolChanges`

## The Root Cause

The issue is likely that `analysis.ToolChanges` is **0** instead of **2**.

This means:
- Tool change time = 0 × 13.05 = 0 seconds
- Total time = cutting + rapids + 0 = 23.6 seconds

## Why ToolChanges Might Be 0

1. **C_WECHSEL not detected**: Lines 79 and 154 in Field1.spf
2. **Platz mapping failed**: Platz 17→602, Platz 10→181
3. **Tool changes not counted**: The `analysis.ToolChanges++` not executed

## Solution

We need to ensure:
1. C_WECHSEL lines are detected
2. Platz to Box mapping works
3. `analysis.ToolChanges` is incremented

## Verification Needed

Run with debug output to see:
- "Found C_WECHSEL" messages
- "Tool change added, total changes now: X"
- Final ToolChanges count in payload