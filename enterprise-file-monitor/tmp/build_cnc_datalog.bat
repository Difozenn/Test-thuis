@echo off
REM Build script for CNC Datalog - Multiple versions
REM Requires Visual Studio 2019+ or .NET Framework SDK installed

echo ========================================
echo Building CNC Datalog Executables
echo ========================================
echo.

REM Set paths - adjust these based on your Visual Studio installation
set VS2022_PATH=C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin
set VS2019_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin
set DOTNET_PATH=C:\Windows\Microsoft.NET\Framework64\v4.0.30319

REM Try to find MSBuild
set MSBUILD_PATH=
if exist "%VS2022_PATH%\MSBuild.exe" (
    set MSBUILD_PATH=%VS2022_PATH%
    echo Found MSBuild in VS2022
) else if exist "%VS2019_PATH%\MSBuild.exe" (
    set MSBUILD_PATH=%VS2019_PATH%
    echo Found MSBuild in VS2019
) else if exist "%DOTNET_PATH%\csc.exe" (
    echo Using .NET Framework compiler
    goto USE_CSC
) else (
    echo ERROR: Could not find MSBuild or CSC compiler!
    echo Please install Visual Studio 2019+ or .NET Framework SDK
    pause
    exit /b 1
)

:BUILD_WITH_MSBUILD
echo.
echo Creating project file...

REM Create a temporary project file for building
echo ^<Project Sdk="Microsoft.NET.Sdk"^> > CNCDatalog.csproj
echo   ^<PropertyGroup^> >> CNCDatalog.csproj
echo     ^<OutputType^>WinExe^</OutputType^> >> CNCDatalog.csproj
echo     ^<TargetFramework^>net472^</TargetFramework^> >> CNCDatalog.csproj
echo     ^<AssemblyName^>CNC Datalog^</AssemblyName^> >> CNCDatalog.csproj
echo     ^<ApplicationIcon^>static\cncmenu.ico^</ApplicationIcon^> >> CNCDatalog.csproj
echo     ^<UseWindowsForms^>true^</UseWindowsForms^> >> CNCDatalog.csproj
echo   ^</PropertyGroup^> >> CNCDatalog.csproj
echo ^</Project^> >> CNCDatalog.csproj

REM Build 64-bit version
echo.
echo Building 64-bit version...
"%MSBUILD_PATH%\MSBuild.exe" CNCDatalog.csproj /p:Configuration=Release /p:Platform=x64 /p:OutputPath=.\build\x64\ /p:AssemblyName="CNC Datalog x64"
if errorlevel 1 goto BUILD_ERROR

REM Build 32-bit version
echo.
echo Building 32-bit version...
"%MSBUILD_PATH%\MSBuild.exe" CNCDatalog.csproj /p:Configuration=Release /p:Platform=x86 /p:OutputPath=.\build\x86\ /p:AssemblyName="CNC Datalog x86"
if errorlevel 1 goto BUILD_ERROR

REM Build Windows 7 compatible 64-bit version (using .NET 4.0)
echo.
echo Building Windows 7 64-bit version...
echo ^<Project Sdk="Microsoft.NET.Sdk"^> > CNCDatalog_Win7.csproj
echo   ^<PropertyGroup^> >> CNCDatalog_Win7.csproj
echo     ^<OutputType^>WinExe^</OutputType^> >> CNCDatalog_Win7.csproj
echo     ^<TargetFramework^>net40^</TargetFramework^> >> CNCDatalog_Win7.csproj
echo     ^<AssemblyName^>CNC Datalog Win7^</AssemblyName^> >> CNCDatalog_Win7.csproj
echo     ^<ApplicationIcon^>static\cncmenu.ico^</ApplicationIcon^> >> CNCDatalog_Win7.csproj
echo     ^<UseWindowsForms^>true^</UseWindowsForms^> >> CNCDatalog_Win7.csproj
echo   ^</PropertyGroup^> >> CNCDatalog_Win7.csproj
echo ^</Project^> >> CNCDatalog_Win7.csproj

"%MSBUILD_PATH%\MSBuild.exe" CNCDatalog_Win7.csproj /p:Configuration=Release /p:Platform=x64 /p:OutputPath=.\build\win7_x64\ /p:AssemblyName="CNC Datalog Win7 x64"
if errorlevel 1 goto BUILD_ERROR

goto BUILD_SUCCESS

:USE_CSC
REM Use CSC compiler directly if MSBuild not available
echo.
echo Using CSC compiler directly...

REM Create resource file for icon
echo ^<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0"^> > app.manifest
echo   ^<assemblyIdentity version="1.0.0.0" name="CNCDatalog.app"/^> >> app.manifest
echo   ^<trustInfo xmlns="urn:schemas-microsoft-com:asm.v2"^> >> app.manifest
echo     ^<security^> >> app.manifest
echo       ^<requestedPrivileges xmlns="urn:schemas-microsoft-com:asm.v3"^> >> app.manifest
echo         ^<requestedExecutionLevel level="asInvoker" uiAccess="false"/^> >> app.manifest
echo       ^</requestedPrivileges^> >> app.manifest
echo     ^</security^> >> app.manifest
echo   ^</trustInfo^> >> app.manifest
echo ^</assembly^> >> app.manifest

REM Build 64-bit version
echo.
echo Building 64-bit version with CSC...
"%DOTNET_PATH%\csc.exe" /target:winexe /platform:x64 /optimize /win32icon:static\cncmenu.ico /out:"build\CNC Datalog x64.exe" filemonitortrayapp.cs FileSelectorForm.cs LocalizationManager.cs LoginForm.cs UserManagementForm.cs /r:System.dll /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.Core.dll /r:System.Data.dll /r:System.Xml.dll /r:System.Xml.Linq.dll
if errorlevel 1 goto BUILD_ERROR

REM Build 32-bit version
echo.
echo Building 32-bit version with CSC...
"%DOTNET_PATH%\..\Framework\v4.0.30319\csc.exe" /target:winexe /platform:x86 /optimize /win32icon:static\cncmenu.ico /out:"build\CNC Datalog x86.exe" filemonitortrayapp.cs FileSelectorForm.cs LocalizationManager.cs LoginForm.cs UserManagementForm.cs /r:System.dll /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.Core.dll /r:System.Data.dll /r:System.Xml.dll /r:System.Xml.Linq.dll
if errorlevel 1 goto BUILD_ERROR

REM Build Windows 7 compatible version (targeting .NET 4.0)
echo.
echo Building Windows 7 64-bit version with CSC...
"%DOTNET_PATH%\csc.exe" /target:winexe /platform:x64 /optimize /win32icon:static\cncmenu.ico /out:"build\CNC Datalog Win7 x64.exe" /nostdlib+ /r:"%DOTNET_PATH%\..\Framework\v4.0.30319\mscorlib.dll" /r:"%DOTNET_PATH%\..\Framework\v4.0.30319\System.dll" /r:"%DOTNET_PATH%\..\Framework\v4.0.30319\System.Windows.Forms.dll" /r:"%DOTNET_PATH%\..\Framework\v4.0.30319\System.Drawing.dll" /r:"%DOTNET_PATH%\..\Framework\v4.0.30319\System.Core.dll" /r:"%DOTNET_PATH%\..\Framework\v4.0.30319\System.Data.dll" /r:"%DOTNET_PATH%\..\Framework\v4.0.30319\System.Xml.dll" /r:"%DOTNET_PATH%\..\Framework\v4.0.30319\System.Xml.Linq.dll" filemonitortrayapp.cs FileSelectorForm.cs LocalizationManager.cs LoginForm.cs UserManagementForm.cs
if errorlevel 1 goto BUILD_ERROR

:BUILD_SUCCESS
echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executables created in build\ folder:
echo   - CNC Datalog x64.exe (64-bit for Windows 10/11)
echo   - CNC Datalog x86.exe (32-bit for Windows 10/11)
echo   - CNC Datalog Win7 x64.exe (64-bit for Windows 7)
echo.
dir /B build\*.exe
pause
exit /b 0

:BUILD_ERROR
echo.
echo ========================================
echo Build FAILED!
echo ========================================
echo Please check error messages above.
pause
exit /b 1