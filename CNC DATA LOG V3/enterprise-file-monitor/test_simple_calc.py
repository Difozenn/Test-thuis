#!/usr/bin/env python3
# Simple test to verify time calculations

# Example movement: 100mm at 8000 mm/min
distance = 100  # mm
feedrate = 8000  # mm/min

time_minutes = distance / feedrate
time_seconds = time_minutes * 60

print(f"Distance: {distance} mm")
print(f"Feedrate: {feedrate} mm/min")
print(f"Time: {time_minutes:.4f} minutes = {time_seconds:.2f} seconds")

# Test with values from the issue
# If TotalTime is 116446.69 minutes, and we have about 600 moves
# That's about 194 minutes per move average
print("\nIssue analysis:")
print(f"Total time reported: 116446.69 minutes")
print(f"If 600 moves: {116446.69/600:.2f} minutes per move average")
print(f"At 8000 mm/min, that would be: {194.08 * 8000:.0f} mm per move")
print("That's 1552 meters per move - clearly wrong!")

# Likely issue: feedrate = 0 or very small value
print("\nIf feedrate was 1 instead of 8000:")
time_wrong = 100 / 1  # 100 minutes for 100mm!
print(f"Time would be: {time_wrong} minutes")