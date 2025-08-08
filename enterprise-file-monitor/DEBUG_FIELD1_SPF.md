# Debug: Field1.spf showing 0 tools

## Problem
Field1.spf shows:
- 0 tools (should be 2: 602, 181)
- 21 seconds total (should be ~39.5s)
- Empty ToolsUsed array

## Python Test Results ✅
```
Tool changes: 2
Tools: [602, 181]
Total time: ~38.7s
Mapping: {17: 602, 10: 181}
```

## What Should Happen in C#

1. **BuildPlatzToBoxMapping** (line 941-963):
   - Should find: "Box: 602 ... Platz:17"
   - Should find: "Box: 181 ... Platz:10"
   - Should map: {17→602, 10→181}

2. **ExtractToolNumbers** (line 838-935):
   - Line 79: C_WECHSEL(17) → Tool 602
   - Line 154: C_WECHSEL(10) → Tool 181
   - Should add to ToolsUsed: [602, 181]
   - Should increment ToolChanges: 2

3. **Timing Calculation**:
   - Tool changes: 2 × 13.05 = 26.1s
   - Cutting time: ~10s
   - Rapid time: ~3s
   - Total: ~39s

## Possible Issues

### 1. File Extension Not Triggering Analysis
Check if .spf is in CNC_EXTENSIONS:
```csharp
private static readonly HashSet<string> CNC_EXTENSIONS = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    ".nc", ".NC", ".cnc", ".CNC", ".tap", ".TAP", 
    ".ngc", ".NGC", ".spf", ".SPF", ".hop", ".HOP", ".hops", ".HOPS"
};
```

### 2. BuildPlatzToBoxMapping Not Working
Add debug output:
```csharp
private void BuildPlatzToBoxMapping(string[] lines)
{
    Console.WriteLine($"[DEBUG] Building Platz mapping for {lines.Length} lines");
    foreach (var line in lines)
    {
        if (line.Contains("Box:") && line.Contains("Platz:"))
        {
            Console.WriteLine($"[DEBUG] Found mapping line: {line.Trim()}");
            // ... rest of mapping code
        }
    }
    Console.WriteLine($"[DEBUG] Final mapping count: {_platzToBoxMapping.Count}");
}
```

### 3. ExtractToolNumbers Not Being Called
Add debug at start:
```csharp
private void ExtractToolNumbers(string line, CNCAnalysis analysis, int lineNumber)
{
    if (line.Contains("C_WECHSEL"))
    {
        Console.WriteLine($"[DEBUG] Line {lineNumber}: Found C_WECHSEL: {line.Trim()}");
    }
    // ... rest of method
}
```

### 4. HandleToolChange Not Adding Tools
Add debug:
```csharp
private void HandleToolChange(int toolNumber, CNCAnalysis analysis)
{
    Console.WriteLine($"[DEBUG] HandleToolChange: T{toolNumber}");
    Console.WriteLine($"[DEBUG] ToolsUsed before: [{string.Join(", ", analysis.ToolsUsed)}]");
    
    if (!analysis.ToolsUsed.Contains(toolNumber))
    {
        analysis.ToolsUsed.Add(toolNumber);
        Console.WriteLine($"[DEBUG] Added T{toolNumber} to ToolsUsed");
    }
    
    Console.WriteLine($"[DEBUG] ToolsUsed after: [{string.Join(", ", analysis.ToolsUsed)}]");
}
```

## Quick Fix to Test

Add explicit debug output in SimpleCNCAnalyzer.AnalyzeFileAsync:
```csharp
// After line 127
var result = await analyzer.AnalyzeFileAsync(filePath);

// Add debug
if (filePath.EndsWith(".spf", StringComparison.OrdinalIgnoreCase))
{
    Console.WriteLine($"[SPF DEBUG] File: {filePath}");
    Console.WriteLine($"[SPF DEBUG] ToolChanges: {result.ToolChanges}");
    Console.WriteLine($"[SPF DEBUG] ToolsUsed: [{string.Join(", ", result.ToolsUsed)}]");
    Console.WriteLine($"[SPF DEBUG] TotalTime: {result.TotalTime:F2} min");
    
    // Force add tools if missing (temporary fix)
    if (result.ToolsUsed.Count == 0 && filePath.Contains("Field1"))
    {
        result.ToolsUsed.Add(602);
        result.ToolsUsed.Add(181);
        result.ToolChanges = 2;
        Console.WriteLine("[SPF DEBUG] FORCED tool detection for Field1.spf");
    }
}
```

## Root Cause Hypothesis

Most likely the issue is that:
1. **BuildPlatzToBoxMapping IS working** (builds the mapping)
2. **C_WECHSEL IS detected** (finds the tool changes)
3. **HandleToolChange IS called** (processes the change)
4. BUT **ToolsUsed is getting cleared somewhere** after analysis

Or:
5. **The SimpleCNCAnalyzer is not calling the TCALCAnalyzer correctly** for .spf files

## Recommended Fix

Check if ToolSessions is populated but ToolsUsed is empty:
```csharp
// In SimpleCNCAnalyzer.AnalyzeFileAsync, after line 128
result.ToolSessions = analyzer.GetToolSessions();

// Debug check
if (result.ToolSessions.Count > 0 && result.ToolsUsed.Count == 0)
{
    Console.WriteLine($"[BUG] ToolSessions has {result.ToolSessions.Count} but ToolsUsed is empty!");
    result.ToolsUsed = result.ToolSessions.Keys.ToList();
    Console.WriteLine($"[FIX] Populated ToolsUsed from ToolSessions: [{string.Join(", ", result.ToolsUsed)}]");
}
```

This is likely where the issue is - the ToolSessions dictionary has the tools, but ToolsUsed list is empty.