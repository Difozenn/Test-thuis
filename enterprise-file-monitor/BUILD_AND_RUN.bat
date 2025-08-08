@echo off
echo ========================================
echo CNC DATALOG Build and Run Script
echo ========================================
echo.
echo Building the project...
echo.
dotnet build
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
echo Starting CNC DATALOG...
echo.
dotnet run
pause