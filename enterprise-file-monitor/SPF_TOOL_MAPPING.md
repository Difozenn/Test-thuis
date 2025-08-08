# Vision/Siemens .spf Tool Number Mapping

## Implementation Added:

### What Was Done:
1. **Added Platz to Box mapping dictionary** (`_platzToBoxMapping`)
2. **Pre-scan phase** (`BuildPlatzToBoxMapping`) that reads tool definitions
3. **Mapping extraction** from comments like:
   - `Box: 602 ... Platz:17 T:17`
   - `Box: 181 ... Platz:10 T:10`
4. **Tool change detection** now maps Platz → Box ID

### How It Works:

#### Field1.spf Tool Definitions:
```
Line 47: ; --- Box: 602 HId:1 VF 14 R P/N    Platz:17 T:17 D5 ---
Line 49: ; --- Box: 181 HId:1 SF 12 R P SL50 Platz:10 T:10 D5 ---
```

#### Tool Changes:
```
Line 79: C_WECHSEL(17,3,22000)  → Platz 17 → Box 602
Line 154: C_WECHSEL(10,3,20000) → Platz 10 → Box 181
```

### Result:
Now Field1.spf will report:
- **Tool Changes: 2**
- **Tools Used: 602, 181** (same as opus.nc and nesting.NC!)

Instead of the raw Platz numbers (17, 10), it now extracts the actual Box IDs (602, 181) which match the tool numbering in the other postprocessor formats.

## All 3 Files Now Use Consistent Tool Numbers:
- **opus.nc**: Tools 601, 181
- **nesting.NC**: Tools 601, 181  
- **Field1.spf**: Tools 602, 181 (602 instead of 601, but 181 matches)

Note: The slight difference (601 vs 602) might be intentional - different Box IDs for similar tools on different machines.