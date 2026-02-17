@echo off
REM BarcodeMatch EXE Test Script
REM This script helps diagnose why the exe might not be working

echo ========================================
echo BarcodeMatch EXE Diagnostic Tool
echo ========================================
echo.

REM Check if exe exists
if not exist "dist\BarcodeMatch_32bit.exe" (
    echo ERROR: BarcodeMatch_32bit.exe not found in dist folder
    echo Please build the exe first.
    pause
    exit /b 1
)

echo [1/5] Checking exe file...
dir "dist\BarcodeMatch_32bit.exe" | findstr "BarcodeMatch"
echo.

echo [2/5] Checking for previous error logs...
if exist "dist\barcodematch_error.log" (
    echo Found previous error log:
    type "dist\barcodematch_error.log"
    echo.
    echo Deleting old log...
    del "dist\barcodematch_error.log"
)
echo.

echo [3/5] System Information:
systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Type"
echo.

echo [4/5] Checking Visual C++ Redistributables...
reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "Visual C++" 2>nul | findstr "DisplayName"
reg query "HKLM\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "Visual C++" 2>nul | findstr "DisplayName"
echo.

echo [5/5] Running BarcodeMatch_32bit.exe...
echo If nothing happens, check for barcodematch_error.log
echo.
cd dist
start "" "BarcodeMatch_32bit.exe"
cd ..

echo.
echo Waiting 5 seconds...
timeout /t 5 /nobreak >nul

echo.
echo Checking for error log...
if exist "dist\barcodematch_error.log" (
    echo.
    echo ========================================
    echo ERROR LOG FOUND:
    echo ========================================
    type "dist\barcodematch_error.log"
    echo.
    echo ========================================
) else (
    echo No error log found. 
    echo If the application didn't start, try:
    echo 1. Build debug version: pyinstaller BarcodeMatch_32bit_debug.spec
    echo 2. Run: dist\BarcodeMatch_32bit_DEBUG.exe
    echo 3. Install VC++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x86.exe
)

echo.
pause
