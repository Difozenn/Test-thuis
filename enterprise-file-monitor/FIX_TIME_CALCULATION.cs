// CRITICAL BUG ANALYSIS
// 
// The time calculation formula is:
//   timeMinutes = distance / feedrate
//
// Where:
//   distance is in mm
//   feedrate is in mm/min
//   Result SHOULD be in minutes
//
// Example:
//   distance = 100mm
//   feedrate = 1000 mm/min
//   time = 100/1000 = 0.1 minutes = 6 seconds ✓
//
// BUT the tool times shown are 50-100x too high!
// T181: 505 seconds when it should be ~5 seconds
// T601: 427 seconds when it should be ~4 seconds
//
// HYPOTHESIS 1: Position not being updated (FIXED)
// Before fix: Every movement calculated from 0,0,0
// This would make distances huge, causing huge times
//
// HYPOTHESIS 2: Feedrate units wrong
// Maybe feedrate is being interpreted differently?
// 
// HYPOTHESIS 3: Time accumulation wrong
// Maybe time is being added multiple times?
//
// THE REAL ISSUE:
// Looking at nesting.NC, it's likely a simple file with only a few movements.
// If TCALC says 10.3s processing and 3.2s rapids, the total movement time is ~13.5s
// But we're showing 932s of tool time (15:58)!
//
// This is a 69x multiplication factor!
//
// WAIT - I think I found it!
// The position wasn't being updated in CalculateMoveTime (used by ProcessMovement)
// But ProcessMovementTCALC uses CalculateTCALCMoveTime which DOES update position
// 
// So the position fix might not have helped if TCALC functions are being used!
//
// NEED TO CHECK:
// 1. Which movement function is actually called for .NC files
// 2. If old data is being shown (database was empty!)
// 3. If the file has been re-analyzed with the fixes