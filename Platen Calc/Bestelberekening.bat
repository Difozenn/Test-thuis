@echo off
REM Bestelberekening - Enterprise Material Order Planning System
REM Batch file to launch the application

echo.
echo ================================================
echo  Bestelberekening - Material Order Planning
echo ================================================
echo.
echo Starting application...
echo.

REM Run the Python application
python bestelberekening.py

REM Check if there was an error
if errorlevel 1 (
    echo.
    echo ================================================
    echo  ERROR: Application failed to start
    echo ================================================
    echo.
    echo Possible causes:
    echo  - Python is not installed
    echo  - Python is not in PATH
    echo  - Missing dependencies
    echo.
    echo Please check:
    echo  1. Python 3 is installed
    echo  2. Required packages: xlrd
    echo.
    pause
    exit /b 1
)

REM If we get here, the application closed normally
echo.
echo Application closed.
echo.
pause
