@echo off
REM Platen Calculator Launcher
REM Dubbelklik op dit bestand om te starten

echo Platen Calculator starten...
echo.

python platen_calc.py

if errorlevel 1 (
    echo.
    echo Fout: Python of vereiste bibliotheken niet gevonden
    echo.
    echo Installeer Python en voer uit:
    echo   pip install xlrd
    echo.
    pause
)
