Project Datalog - Installation & Usage Guide

=== INSTALLATION ===

1. Extract all files to a folder of your choice
2. Run ProjectDatalog.exe
3. The application will automatically create necessary folders:
   - database/ (SQLite databases and web interface)
   - logs/ (application logs)
   - backups/ (database backups)

=== FEATURES ===

🖥️  Desktop Application:
- Advanced barcode scanning with multiple scanner support
- Real-time project management and coordination
- Multi-user workflow management
- Background processing services

🌐 Web Interface:
- Modern responsive dashboard at http://localhost:5001
- Project statistics and performance analytics
- User management and reporting
- Real-time activity monitoring

📊 Data Processing:
- Excel file processing (.xlsx/.xls) for NESTING, ACCURA, BOERE workflows
- Automatic color and metadata extraction
- PDF processing and analysis
- MDB database integration

👥 Multi-User Support:
- User-specific configurations and paths
- Efficiency targets and performance tracking
- Team utilization analytics
- Work hours and scheduling management

🔧 Administration:
- Comprehensive settings management
- Database backup and maintenance
- System monitoring and diagnostics
- Configuration import/export

=== SYSTEM REQUIREMENTS ===

- Windows 7 or later (64-bit recommended)
- 4GB RAM minimum, 8GB recommended
- 500MB free disk space
- Microsoft Visual C++ Redistributable (usually pre-installed)

For MDB file processing:
- Microsoft Access Database Engine 2016 Redistributable

=== CONFIGURATION ===

Default Settings:
- Database API: http://localhost:5001
- Web Interface: http://localhost:5001/dashboard
- Default Users: NESTING, ACCURA, OPUS, KL GANNOMAT, BOERE

Scanner Configuration:
- Supports USB and Serial (COM port) scanners
- Configurable baud rates and connection types
- Automatic scanner detection and reconnection

Processing Paths:
- NESTING: C:/Rapporten
- OPUS: C:/OPUS/KORPUS  
- KL GANNOMAT: C:/GANNOMAT
- ACCURA: C:/Rapporten
- BOERE: C:/Rapporten

=== USAGE ===

1. Launch ProjectDatalog.exe
2. Configure your scanner and processing paths in Settings
3. Select your user profile (NESTING, ACCURA, etc.)
4. Start scanning barcodes or processing files
5. Monitor progress in the web interface at http://localhost:5001

=== TROUBLESHOOTING ===

Application Won't Start:
- Check Windows Event Viewer for error details
- Ensure all required directories have write permissions
- Verify antivirus software isn't blocking the executable

Scanner Issues:
- Check COM port settings in Device Manager
- Verify scanner driver installation
- Test with different USB ports

Web Interface Issues:
- Check if port 5001 is available
- Disable Windows Firewall temporarily for testing
- Check logs/ folder for detailed error messages

Performance Issues:
- Ensure adequate free disk space
- Monitor CPU and memory usage in Task Manager
- Check database backup settings (default: daily)

=== SUPPORT ===

For technical support:
- Check the logs/ folder for detailed error information
- Review the web interface diagnostics at /database
- Consult the built-in Help panel in the application

Admin Panel Access:
- Password: sunrise
- Provides advanced configuration and system diagnostics

=== VERSION INFORMATION ===

Project Datalog v1.2.0
Built with Python 3.x and modern web technologies
Optimized for Windows enterprise environments

Copyright (C) 2025. All rights reserved.

=== SECURITY NOTES ===

- This executable may trigger antivirus false positives (common with PyInstaller)
- Add an exception in your antivirus software if needed
- The application only accesses configured directories and network ports
- No data is transmitted outside your local network
