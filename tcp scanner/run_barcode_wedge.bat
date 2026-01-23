@echo off
echo Installing required module...
pip install keyboard

echo.
echo Starting Barcode Wedge...
echo (You may need to allow firewall access)
echo.

python barcode_wedge.py

pause
