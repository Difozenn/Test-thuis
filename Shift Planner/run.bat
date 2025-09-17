@echo off
echo Shift Planner - Starting...
echo ==========================

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python 3.7+ to run this application.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install requirements
echo Installing dependencies...
pip install -r requirements.txt

:: Ask about sample data
set /p init_data="Initialize with sample data? (y/n): "
if /i "%init_data%"=="y" (
    echo Initializing sample data...
    python init_sample_data.py
)

:: Start the application
echo Starting Shift Planner...
echo ==========================
echo Access the application at: http://localhost:5003
echo Press Ctrl+C to stop the server
echo.

python app.py

pause