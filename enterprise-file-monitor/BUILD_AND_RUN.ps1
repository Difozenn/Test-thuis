Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CNC DATALOG Build and Run Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Building the project..." -ForegroundColor Yellow
Write-Host ""

dotnet build

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "BUILD FAILED! Please check the errors above." -ForegroundColor Red
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "BUILD SUCCESSFUL!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Starting CNC DATALOG..." -ForegroundColor Yellow
Write-Host ""

dotnet run

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")