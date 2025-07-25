# CNC DATALOG - Enterprise File Monitor

A comprehensive file monitoring system with CNC analysis and web interface.

## C# Tray Application (CNC DATALOG)

### Build and Run Instructions

#### ✅ CORRECT Commands:
```bash
# To build the project:
dotnet build

# To run the project:
dotnet run

# Or use the provided batch file:
BUILD_AND_RUN.bat
```

#### ❌ INCORRECT Commands (DO NOT USE):
```bash
# WRONG - This will NOT work:
dotnet run filemonitortrayapp.cs

# WRONG - Don't specify individual files:
dotnet run FileMonitorTrayApp.cs
```

### Quick Start:
1. Open Command Prompt or PowerShell
2. Navigate to: `C:\Users\Rob_v\Desktop\Test-thuis\enterprise-file-monitor`
3. Run: `dotnet build` (to just build)
4. Run: `dotnet run` (to build and run)

### Features:
- System tray integration
- Real-time file monitoring  
- CNC G-code analysis with accurate timing (Simple & TCALC engines)
- Web server integration
- Multi-language support

## Python Web Application

### Setup Instructions

1. Create virtual environment: `python -m venv venv`
2. Activate virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Run the application: `python app.py`
5. Access at http://localhost:5000 (admin/admin123)

## CNC Analysis Modes

The application supports three CNC analyzer modes:
- **Simple**: Basic distance/feedrate calculation (~8.30 min for Field1.nc)
- **Enhanced**: Advanced analysis with tool tracking
- **Auto**: Automatically selects the best analyzer

The Simple mode provides the most accurate real-world timing results.