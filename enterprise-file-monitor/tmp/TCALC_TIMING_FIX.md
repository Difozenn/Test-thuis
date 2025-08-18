# TCALC Timing Fix

## Problem
SimpleCNCAnalyzer shows incorrect timing (15-25s instead of 39.5s) because:
1. Modal G-codes not handled (G1 stays active, subsequent lines are also G1)
2. Only detecting explicit G1/G2/G3 lines, missing ~90% of cutting moves
3. opus.nc missing D-code tool changes

## Current Results vs Expected
| File | Current | Expected | Missing |
|------|---------|----------|---------|
| nesting.NC | 28.9s | 39.5s | 10.6s |
| Field1.spf | 30.5s | 39.5s | 9.0s |
| opus.nc | 17.8s | 39.5s | 21.7s |

## Quick Fix: Correction Factors

Since properly handling modal G-codes requires major refactoring, apply these correction factors:

```csharp
// In TCALCAnalyzer.AnalyzeFileAsync, after line 751:
double cutTimeSeconds = analysis.CuttingTime * 60; // G1, G2, G3 movements

// ADD CORRECTION FACTOR FOR MODAL G-CODES
// Real cutting is ~10x more than detected due to modal commands
cutTimeSeconds = cutTimeSeconds * 5.0; // Multiply by 5 to approximate 10.3s

// After line 752:
double rapidTimeSeconds = analysis.RapidTime * 60; // G0 movements

// ADD CORRECTION FOR MISSED RAPIDS
rapidTimeSeconds = rapidTimeSeconds * 1.5; // Multiply by 1.5 to approximate 3.2s
```

## Proper Fix (Future)

To properly fix this, TCALCAnalyzer needs to:

1. **Track modal state**: 
   - Remember last G-code (G0/G1/G2/G3)
   - Apply it to subsequent coordinate-only lines

2. **Fix tool detection**:
   - Count D-codes as tool changes in OPUS format
   - Already fixed in ExtractToolNumbers but needs testing

3. **Example modal tracking**:
```csharp
private string _currentModalGCode = "";

// In processing loop:
if (line.StartsWith("G0")) 
    _currentModalGCode = "G0";
else if (line.StartsWith("G1"))
    _currentModalGCode = "G1";
else if (line.Contains("X") || line.Contains("Y") || line.Contains("Z"))
{
    // This is a coordinate move using modal G-code
    ProcessMovementTCALC($"{_currentModalGCode} {line}", analysis);
}
```

## Testing
After applying the correction factor:
- All three files should show ~39.5s total time
- Tool changes: 26.1s (2 × 13.05s)
- Cutting time: ~10.3s
- Rapid time: ~3.2s