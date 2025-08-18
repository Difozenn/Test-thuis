# CNC Datalog Build Instructions

## Overview
This document provides instructions for building the CNC Datalog application in multiple configurations:
- **64-bit** (x64) for modern Windows systems
- **32-bit** (x86) for older systems or compatibility
- **Windows 7 64-bit** specifically targeting .NET Framework 4.0

## Prerequisites

### Option 1: Visual Studio (Recommended)
- Visual Studio 2019 or newer (Community Edition is free)
- .NET Framework 4.7.2 SDK (usually included with VS)

### Option 2: .NET Framework SDK
- .NET Framework 4.0 or higher (included in Windows 7+)
- Windows SDK (optional, for advanced features)

## Quick Build Methods

### Method 1: Using Batch File (Simplest)
```cmd
build_cnc_datalog_simple.bat
```
This will create all three versions in the `build\` folder.

### Method 2: Using PowerShell Script
```powershell
powershell -ExecutionPolicy Bypass -File build_cnc_datalog.ps1
```

### Method 3: Using Visual Studio
1. Open `CNCDatalog.csproj` in Visual Studio
2. Select configuration:
   - Release | x64 for 64-bit
   - Release | x86 for 32-bit
3. Build → Build Solution (Ctrl+Shift+B)

### Method 4: Using MSBuild Command Line
```cmd
# 64-bit version
msbuild CNCDatalog.csproj /p:Configuration=Release /p:Platform=x64

# 32-bit version
msbuild CNCDatalog.csproj /p:Configuration=Release /p:Platform=x86

# Windows 7 version
msbuild CNCDatalog_Win7.csproj /p:Configuration=Release /p:Platform=x64
```

### Method 5: Direct CSC Compilation
```cmd
# 64-bit version
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe ^
    /target:winexe /platform:x64 /optimize ^
    /win32icon:static\cncmenu.ico ^
    /out:"CNC Datalog x64.exe" ^
    filemonitortrayapp.cs FileSelectorForm.cs LocalizationManager.cs LoginForm.cs UserManagementForm.cs

# 32-bit version
C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe ^
    /target:winexe /platform:x86 /optimize ^
    /win32icon:static\cncmenu.ico ^
    /out:"CNC Datalog x86.exe" ^
    filemonitortrayapp.cs FileSelectorForm.cs LocalizationManager.cs LoginForm.cs UserManagementForm.cs
```

## Output Files

After successful build, you'll find the executables in the `build\` folder:

| File | Platform | Target Framework | Windows Compatibility |
|------|----------|------------------|----------------------|
| `CNC Datalog x64.exe` | 64-bit | .NET 4.7.2 | Windows 10/11 |
| `CNC Datalog x86.exe` | 32-bit | .NET 4.7.2 | Windows 10/11 (32/64-bit) |
| `CNC Datalog Win7.exe` | 64-bit | .NET 4.0 | Windows 7 SP1+ |

## Troubleshooting

### "CSC not found" Error
- Install .NET Framework 4.7.2 or higher
- Or install Visual Studio Community

### Missing Source Files Warning
The build scripts will try to compile all forms. If some are missing, it will fall back to compiling only `filemonitortrayapp.cs`.

### Icon File Not Found
Ensure `static\cncmenu.ico` exists. The build will continue without an icon if missing.

### Windows 7 Compatibility Issues
The Win7 version targets .NET 4.0 which is included in Windows 7 SP1. If you get errors:
1. Ensure Windows 7 has Service Pack 1 installed
2. Install .NET Framework 4.0 if missing
3. Use the `CNCDatalog_Win7.csproj` project file

## Deployment

### Required Files for Distribution
```
CNC Datalog.exe (choose appropriate version)
config.ini (if needed)
static\ (folder with icons and resources)
```

### .NET Framework Requirements
- **x64/x86 versions**: .NET Framework 4.7.2 or higher
- **Win7 version**: .NET Framework 4.0 or higher

### Creating an Installer (Optional)
Consider using:
- **Inno Setup** - Free, scriptable installer
- **WiX Toolset** - MSI-based installer
- **Visual Studio Installer Projects** - If using VS

## Version Information

The compiled executables will have:
- **Product Name**: CNC Datalog
- **Icon**: static\cncmenu.ico
- **Platform**: As specified (x64, x86, or AnyCPU for Win7)
- **Optimization**: Enabled for release builds

## Support

For issues with building or running the application:
1. Check that all prerequisites are installed
2. Run the build script as Administrator if permission errors occur
3. Verify all source files are present
4. Check the Windows Event Log for detailed error messages