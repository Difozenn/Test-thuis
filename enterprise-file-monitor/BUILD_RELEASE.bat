@echo off
echo ========================================
echo Building CNC DATALOG Release Version
echo ========================================
echo.

REM Clean previous builds
echo Cleaning previous builds...
if exist "bin\Release" rmdir /s /q "bin\Release"
if exist "publish" rmdir /s /q "publish"

echo.
echo Building self-contained executable...
echo.

REM Build self-contained single file executable
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o publish

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
echo     publish\CNC DATALOG.exe
echo.
echo This is a completely self-contained executable that includes:
echo - The application
echo - .NET runtime
echo - All dependencies
echo.
echo You can copy this single .exe file anywhere and run it!
echo.
pause