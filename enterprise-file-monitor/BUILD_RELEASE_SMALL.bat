@echo off
echo ========================================
echo Building CNC DATALOG (Small Size)
echo ========================================
echo.

REM Clean previous builds
echo Cleaning previous builds...
if exist "bin\Release" rmdir /s /q "bin\Release"
if exist "publish-small" rmdir /s /q "publish-small"

echo.
echo Building framework-dependent single file...
echo.

REM Build framework-dependent single file (requires .NET 6 runtime on target machine)
dotnet publish -c Release -r win-x64 --self-contained false -p:PublishSingleFile=true -o publish-small

if %errorlevel% neq 0 (
    echo.
    echo BUILD FAILED! Please check the errors above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo Your single executable is located at:
echo.
echo     publish-small\CNC DATALOG.exe
echo.
echo NOTE: This smaller version requires .NET 6 Desktop Runtime
echo to be installed on the target computer.
echo.
echo File size comparison:
dir "publish\CNC DATALOG.exe" 2>nul | find "CNC DATALOG.exe"
dir "publish-small\CNC DATALOG.exe" 2>nul | find "CNC DATALOG.exe"
echo.
pause