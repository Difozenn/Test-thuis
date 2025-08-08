; Simple test file
G90 ; Absolute positioning
G0 X0 Y0 Z0 ; Start position
G0 X100 Y0 Z0 ; Rapid move 100mm in X
F8000 ; Set feedrate
G1 X200 Y0 Z0 ; Cut 100mm in X at 8000mm/min
G0 X200 Y100 Z0 ; Rapid 100mm in Y
G1 X100 Y100 Z0 F3000 ; Cut 100mm in -X at 3000mm/min
M30 ; End