@echo off
REM Simple build script for CNC Datalog using CSC directly
REM Requires .NET Framework 4.0+ (included in Windows 7+)

echo ========================================
echo Building CNC Datalog with CSC
echo ========================================
echo.

REM Create build directory
if not exist build mkdir build

REM Set compiler paths for different .NET versions
set CSC_NET48=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe
set CSC_NET48_32=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe

REM Check if 64-bit compiler exists
if not exist "%CSC_NET48%" (
    echo ERROR: .NET Framework compiler not found!
    echo Path checked: %CSC_NET48%
    echo Please install .NET Framework 4.0 or higher
    pause
    exit /b 1
)

echo Found .NET Framework compiler
echo.

REM ===== BUILD 64-BIT VERSION =====
echo Building CNC Datalog x64.exe (64-bit)...
"%CSC_NET48%" ^
    /nologo ^
    /target:winexe ^
    /platform:x64 ^
    /optimize+ ^
    /win32icon:static\cncmenu.ico ^
    /out:"build\CNC Datalog x64.exe" ^
    /reference:System.dll ^
    /reference:System.Windows.Forms.dll ^
    /reference:System.Drawing.dll ^
    /reference:System.Core.dll ^
    /reference:System.Data.dll ^
    /reference:System.Xml.dll ^
    /reference:System.Xml.Linq.dll ^
    /reference:System.Management.dll ^
    filemonitortrayapp.cs FileSelectorForm.cs LocalizationManager.cs LoginForm.cs UserManagementForm.cs

if %errorlevel% equ 0 (
    echo SUCCESS: CNC Datalog x64.exe created
) else (
    echo FAILED: Could not build 64-bit version
    echo Trying with just main file...
    "%CSC_NET48%" /nologo /target:winexe /platform:x64 /optimize+ /win32icon:static\cncmenu.ico /out:"build\CNC Datalog x64.exe" filemonitortrayapp.cs
)

echo.

REM ===== BUILD 32-BIT VERSION =====
if exist "%CSC_NET48_32%" (
    echo Building CNC Datalog x86.exe (32-bit)...
    "%CSC_NET48_32%" ^
        /nologo ^
        /target:winexe ^
        /platform:x86 ^
        /optimize+ ^
        /win32icon:static\cncmenu.ico ^
        /out:"build\CNC Datalog x86.exe" ^
        /reference:System.dll ^
        /reference:System.Windows.Forms.dll ^
        /reference:System.Drawing.dll ^
        /reference:System.Core.dll ^
        /reference:System.Data.dll ^
        /reference:System.Xml.dll ^
        /reference:System.Xml.Linq.dll ^
        /reference:System.Management.dll ^
        filemonitortrayapp.cs FileSelectorForm.cs LocalizationManager.cs LoginForm.cs UserManagementForm.cs
    
    if %errorlevel% equ 0 (
        echo SUCCESS: CNC Datalog x86.exe created
    ) else (
        echo FAILED: Could not build 32-bit version
        echo Trying with just main file...
        "%CSC_NET48_32%" /nologo /target:winexe /platform:x86 /optimize+ /win32icon:static\cncmenu.ico /out:"build\CNC Datalog x86.exe" filemonitortrayapp.cs
    )
) else (
    echo SKIPPED: 32-bit compiler not found
)

echo.

REM ===== BUILD WINDOWS 7 COMPATIBLE VERSION =====
echo Building CNC Datalog Win7.exe (Windows 7 compatible)...
REM For Windows 7, we target .NET 4.0 specifically
"%CSC_NET48%" ^
    /nologo ^
    /target:winexe ^
    /platform:x64 ^
    /optimize+ ^
    /win32icon:static\cncmenu.ico ^
    /out:"build\CNC Datalog Win7.exe" ^
    /reference:System.dll ^
    /reference:System.Windows.Forms.dll ^
    /reference:System.Drawing.dll ^
    /reference:System.Core.dll ^
    /reference:System.Data.dll ^
    /reference:System.Xml.dll ^
    filemonitortrayapp.cs FileSelectorForm.cs LocalizationManager.cs LoginForm.cs UserManagementForm.cs

if %errorlevel% equ 0 (
    echo SUCCESS: CNC Datalog Win7.exe created
) else (
    echo FAILED: Could not build Windows 7 version
    echo Trying with just main file...
    "%CSC_NET48%" /nologo /target:winexe /platform:x64 /optimize+ /win32icon:static\cncmenu.ico /out:"build\CNC Datalog Win7.exe" filemonitortrayapp.cs
)

echo.
echo ========================================
echo Build process completed!
echo ========================================
echo.

REM List created files
echo Created files in build folder:
dir /B build\*.exe 2>nul

echo.
pause