@echo off
echo Building FileMonitorTrayApp...

REM Try with dotnet first
where dotnet >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using dotnet build...
    dotnet build FileMonitorTray.csproj
    if %ERRORLEVEL% EQU 0 (
        echo Build successful with dotnet!
        goto :run
    )
)

REM Try with msbuild
where msbuild >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using msbuild...
    msbuild FileMonitorTray.csproj /p:Configuration=Release
    if %ERRORLEVEL% EQU 0 (
        echo Build successful with msbuild!
        goto :run
    )
)

REM Try with csc directly
where csc >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using csc compiler...
    csc /target:winexe /out:FileMonitorTrayApp.exe FileMonitorTrayApp.cs
    if %ERRORLEVEL% EQU 0 (
        echo Build successful with csc!
        goto :run
    )
)

echo ERROR: No build tools found. Please install .NET SDK or Visual Studio.
pause
exit /b 1

:run
echo.
echo Build completed. Run the application? (Y/N)
set /p answer=
if /i "%answer%"=="Y" (
    echo Starting FileMonitorTrayApp...
    start FileMonitorTrayApp.exe
)
pause