# PowerShell build script for CNC Datalog
# Requires Visual Studio or .NET Framework SDK

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Building CNC Datalog Executables" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Create build directory
$buildDir = ".\build"
if (!(Test-Path $buildDir)) {
    New-Item -ItemType Directory -Path $buildDir | Out-Null
}

# Find CSC compiler
function Find-CSC {
    $locations = @(
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\*\MSBuild\Current\Bin\Roslyn\csc.exe",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2019\*\MSBuild\Current\Bin\Roslyn\csc.exe",
        "${env:WINDIR}\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
        "${env:WINDIR}\Microsoft.NET\Framework\v4.0.30319\csc.exe"
    )
    
    foreach ($location in $locations) {
        $paths = Get-ChildItem -Path $location -ErrorAction SilentlyContinue
        if ($paths) {
            return $paths[0].FullName
        }
    }
    return $null
}

$cscPath = Find-CSC
if (!$cscPath) {
    Write-Host "ERROR: Could not find C# compiler (csc.exe)" -ForegroundColor Red
    Write-Host "Please install Visual Studio or .NET Framework SDK" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Found C# compiler at: $cscPath" -ForegroundColor Green
Write-Host ""

# Common compiler arguments
$commonArgs = @(
    "/target:winexe",
    "/optimize",
    "/win32icon:static\cncmenu.ico",
    "/reference:System.dll",
    "/reference:System.Windows.Forms.dll", 
    "/reference:System.Drawing.dll",
    "/reference:System.Core.dll",
    "/reference:System.Data.dll",
    "/reference:System.Xml.dll",
    "/reference:System.Xml.Linq.dll",
    "/reference:System.Management.dll",
    "/reference:System.Net.Http.dll",
    "/reference:System.Threading.Tasks.dll"
)

# Source files
$sourceFiles = @(
    "filemonitortrayapp.cs",
    "FileSelectorForm.cs",
    "LocalizationManager.cs",
    "LoginForm.cs",
    "UserManagementForm.cs"
)

# Verify all source files exist
$missingFiles = @()
foreach ($file in $sourceFiles) {
    if (!(Test-Path $file)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "WARNING: Some source files are missing:" -ForegroundColor Yellow
    $missingFiles | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    Write-Host "Using only filemonitortrayapp.cs" -ForegroundColor Yellow
    $sourceFiles = @("filemonitortrayapp.cs")
}

# Build 64-bit version
Write-Host "Building 64-bit version..." -ForegroundColor Yellow
$args64 = $commonArgs + @(
    "/platform:x64",
    "/out:build\CNC Datalog x64.exe"
) + $sourceFiles

& $cscPath $args64 2>&1 | Out-String | Write-Host
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 64-bit version built successfully" -ForegroundColor Green
} else {
    Write-Host "✗ 64-bit version build failed" -ForegroundColor Red
}

Write-Host ""

# Build 32-bit version
Write-Host "Building 32-bit version..." -ForegroundColor Yellow
$args32 = $commonArgs + @(
    "/platform:x86",
    "/out:build\CNC Datalog x86.exe"
) + $sourceFiles

& $cscPath $args32 2>&1 | Out-String | Write-Host
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 32-bit version built successfully" -ForegroundColor Green
} else {
    Write-Host "✗ 32-bit version build failed" -ForegroundColor Red
}

Write-Host ""

# Build Windows 7 compatible 64-bit version
Write-Host "Building Windows 7 64-bit version (.NET 4.0)..." -ForegroundColor Yellow

# For Win7, we need to use .NET 4.0 compiler
$win7CscPath = "${env:WINDIR}\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (Test-Path $win7CscPath) {
    $argsWin7 = @(
        "/target:winexe",
        "/platform:x64",
        "/optimize",
        "/win32icon:static\cncmenu.ico",
        "/out:build\CNC Datalog Win7 x64.exe",
        "/reference:System.dll",
        "/reference:System.Windows.Forms.dll",
        "/reference:System.Drawing.dll",
        "/reference:System.Core.dll",
        "/reference:System.Data.dll",
        "/reference:System.Xml.dll"
    ) + $sourceFiles
    
    & $win7CscPath $argsWin7 2>&1 | Out-String | Write-Host
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Windows 7 64-bit version built successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Windows 7 64-bit version build failed" -ForegroundColor Red
    }
} else {
    Write-Host "✗ .NET 4.0 compiler not found - skipping Windows 7 build" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Build process completed!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# List created executables
if (Test-Path $buildDir) {
    $exeFiles = Get-ChildItem -Path $buildDir -Filter "*.exe" -ErrorAction SilentlyContinue
    if ($exeFiles) {
        Write-Host "Created executables:" -ForegroundColor Green
        $exeFiles | ForEach-Object {
            $size = [math]::Round($_.Length / 1MB, 2)
            Write-Host "  - $($_.Name) ($size MB)" -ForegroundColor White
        }
    } else {
        Write-Host "No executables were created successfully." -ForegroundColor Red
    }
}

Write-Host ""
Read-Host "Press Enter to exit"