// TCALC TIME CALCULATION FIX
// Based on actual TCALC_HH7 output analysis
//
// The TCALC output shows field2.mpf should be:
// - Total time: 3 min 11.41 sec (191.41 seconds)
// - Tool 601: 63.1 seconds total
// - Tool 501: 82.163 seconds (drilling)
// - Tool changes: 37.5 seconds
// - Rapids: 7.10 seconds
//
// Main issues found:
// 1. Movement detection is catching too many non-movement lines
// 2. Feedrate parsing might be wrong (units issue?)
// 3. Drilling operations are being counted multiple times
// 4. Tool change time accumulation is wrong
//
// Key insights from TCALC_HH7 code:
// - GetTimePathAccelerationDeceleration uses complex physics simulation
// - But for most practical cases, simple distance/feedrate works
// - Drilling cycles have specific time multipliers
// - Tool changes are 12.5 seconds each (not 15 or 20)
//
// From PP.ini:
// TC_51_51=10.0001 (but actually uses 12.5 in practice)
// DHFeedrateG00=50000 (rapid feedrate in mm/min)
//
// CRITICAL FIX NEEDED:
// The movement regex is catching lines without coordinates!
// Lines like "N10 G0" or "G1 F1000" are being processed as movements
// when they're just preparatory commands.
//
// PROPER MOVEMENT DETECTION:
// A movement line MUST have at least one coordinate (X, Y, or Z)
// Examples of valid movements:
//   N100 G0 X100 Y200
//   G1 Z-5 F1000
//   X50 Y75 (modal G1 continues)
//
// Examples of NON-movements that were incorrectly processed:
//   N10 G0 (just sets rapid mode)
//   G1 F1000 (just sets feedrate)
//   M3 S12000 (spindle command)
//
// FEEDRATE ISSUE:
// Feedrates in NC files are in mm/min
// Our time calculation is: time = distance / feedrate
// This gives time in MINUTES, not seconds
//
// DRILLING TIME CALCULATION:
// From TCALC_HH7, drilling time includes:
// - Approach time (rapid to safety height)
// - Drilling time (based on depth and feedrate)
// - Retract time (rapid back to safety)
// - For peck drilling: multiply by number of pecks
//
// TOOL CHANGE TIME:
// From actual TCALC output: 37.5 seconds for 3 tool changes = 12.5 seconds each
// This matches the TCALC_HH7 implementation