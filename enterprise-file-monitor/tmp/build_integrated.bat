@echo off
echo Building CNC File Monitor with Flask Integration...
echo.

REM Check if .NET SDK is installed
dotnet --version >nul 2>&1
if %errorlevel% neq 0 (
    echo .NET SDK is not installed!
    echo Trying with .NET Framework compiler...
    goto try_framework
)

REM Create a temporary project file for the integrated version
echo Creating temporary project file...
(
echo ^<Project Sdk="Microsoft.NET.Sdk"^>
echo   ^<PropertyGroup^>
echo     ^<OutputType^>WinExe^</OutputType^>
echo     ^<TargetFramework^>net6.0-windows^</TargetFramework^>
echo     ^<UseWindowsForms^>true^</UseWindowsForms^>
echo     ^<ImplicitUsings^>disable^</ImplicitUsings^>
echo     ^<Nullable^>disable^</Nullable^>
echo     ^<AssemblyName^>CNCMonitorIntegrated^</AssemblyName^>
echo   ^</PropertyGroup^>
echo   ^<ItemGroup^>
echo     ^<PackageReference Include="Newtonsoft.Json" Version="13.0.3" /^>
echo   ^</ItemGroup^>
echo ^</Project^>
) > CNCMonitorIntegrated.csproj

REM Build with .NET SDK
echo Building with .NET SDK...
dotnet restore CNCMonitorIntegrated.csproj
dotnet build CNCMonitorIntegrated.csproj -c Release

if %errorlevel% equ 0 (
    echo.
    echo Build successful!
    echo.
    echo Starting CNC Monitor (Flask Integrated)...
    start "" "bin\Release\net6.0-windows\CNCMonitorIntegrated.exe"
    echo.
    echo Application started. Check the system tray for the CNC Monitor icon.
    echo Make sure your Flask app is running at http://localhost:5000
    pause
    exit /b 0
)

:try_framework
echo.
echo Attempting to compile with .NET Framework...

REM Try to find .NET Framework compiler
if exist "%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" (
    set CSC="%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
) else (
    echo .NET Framework compiler not found!
    echo Please install .NET SDK from: https://dotnet.microsoft.com/download
    pause
    exit /b 1
)

echo Compiling with .NET Framework...
%CSC% /target:winexe /out:CNCMonitorIntegrated.exe filemonitortrayapp_integrated.cs /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.Net.Http.dll

if %errorlevel% neq 0 (
    echo.
    echo Compilation failed!
    echo You need to install Newtonsoft.Json package.
    echo Please install .NET SDK and use the first method.
    pause
    exit /b 1
)

echo.
echo Compilation successful!
echo Starting CNCMonitorIntegrated.exe...
start CNCMonitorIntegrated.exe
echo.
echo Application started. Check the system tray for the CNC Monitor icon.
echo Make sure your Flask app is running at http://localhost:5000
pause