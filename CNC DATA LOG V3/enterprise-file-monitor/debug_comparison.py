#!/usr/bin/env python3
"""Direct comparison of Python and C# CNC analyzer calculations"""

# Simulate a simple G-code movement
# Starting at (0, 0, 0)
# G1 X100 Y100 F3000

import math

# Python calculation
current_pos = {'X': 0, 'Y': 0, 'Z': 0}
new_pos = {'X': 100, 'Y': 100, 'Z': 0}
feedrate = 3000  # mm/min

# Calculate distance
distance = math.sqrt(
    (new_pos['X'] - current_pos['X'])**2 +
    (new_pos['Y'] - current_pos['Y'])**2 +
    (new_pos['Z'] - current_pos['Z'])**2
)

# Calculate time in minutes
time = distance / feedrate

print(f"Python calculation:")
print(f"  Distance: {distance:.2f} mm")
print(f"  Feedrate: {feedrate} mm/min")
print(f"  Time: {time:.6f} minutes = {time*60:.2f} seconds")
print()

# C# would calculate the same way:
# var distance = Math.Sqrt(Math.Pow(100 - 0, 2) + Math.Pow(100 - 0, 2) + Math.Pow(0 - 0, 2))
# = Math.Sqrt(10000 + 10000 + 0) = Math.Sqrt(20000) = 141.42 mm
# var time = 141.42 / 3000 = 0.0471 minutes

print(f"Expected C# calculation (should be identical):")
print(f"  Distance: 141.42 mm")
print(f"  Feedrate: 3000 mm/min")
print(f"  Time: 0.0471 minutes = 2.83 seconds")
print()

# If C# is getting 116449 minutes instead of ~7.7 minutes
# That's a factor of 15,123
print(f"Error factor: 116449.8 / 7.7 = {116449.8 / 7.7:.1f}")
print()

# What feedrate would give us this error?
wrong_feedrate = distance / (time * 15123)
print(f"To get this error, feedrate would need to be: {wrong_feedrate:.6f} mm/min")
print(f"That's 3000 / {3000 / wrong_feedrate:.1f} = {wrong_feedrate:.6f}")