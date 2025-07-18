# BarcodeMatch - Technical Documentation

## 1. Overview

BarcodeMatch is a desktop application built with Python and Tkinter designed to streamline barcode scanning and data matching processes, primarily for manufacturing and inventory management environments (like OPUS and GANNOMAT systems).

The application features a tab-based interface, allowing users to switch between different functional panels:

- **Scanner**: The primary panel for barcode scanning and matching against a loaded project file (Excel).
- **Import**: Allows importing data from various sources (directory scans or Access databases) and exporting it to Excel format for use in the scanner.
- **Database**: Configures and interacts with a remote API for logging events and retrieving log data.
- **Email**: Configures email settings for sending notifications.
- **Settings**: Provides application-level settings.
- **Help**: Displays help information and application version.

### Core Technologies

- **GUI Framework**: `tkinter` / `ttk`
- **Data Handling**: `pandas` for Excel operations, `pyodbc` for Access database interaction.
- **API Communication**: `requests` for REST API calls.
- **Email**: `smtplib` for sending emails.
- **Configuration**: A custom `config_utils.py` module manages settings stored in a `config.json` file.

---

## 3. Panel Documentation

### 3.5. Settings Panel (`settings_panel.py`)

**Purpose:**
The Settings Panel provides a user interface for configuring various application-level settings.

**UI Components:**
- **Settings Checkboxes**: A list of checkboxes, each corresponding to a specific setting. Tooltips are available to explain what each setting does.
- **Current Settings**: As of the last review, it includes an option to "Archiveer Excel bestand als alle items OK zijn" (Archive Excel file if all items are OK).

**Core Logic:**
- **Loading Settings**: When the panel is created, it reads the current settings from `config.json` and sets the state of the checkboxes accordingly.
- **Saving Settings**: Whenever a checkbox's state is changed by the user, the new value is immediately saved back to `config.json`.

---

### 3.6. Help Panel (`help_panel.py`)

**Purpose:**
The Help Panel provides users with access to help resources and displays information about the application.

**UI Components:**
- **Open Manual Button**: A button that, when clicked, opens the application's user manual (a PDF file located in the `assets` directory).
- **Build Information Label**: A label that displays the application's build number and copyright information.

**Core Logic:**
- The panel uses `os.startfile` to open the PDF manual with the system's default PDF viewer.
- The build number is read from `build_info.py`.

---

### 3.4. Email Panel (`email_panel.py`)

**Purpose:**
The Email Panel is used to configure settings for sending email notifications, such as project completion reports.

**UI Components:**
- **Enable/Disable Checkbox**: A master switch to turn email functionality on or off.
- **Sender/Receiver Fields**: Entry fields for the sender's and receiver's email addresses.
- **SMTP Server Configuration**: Entry fields for the SMTP server address and port.
- **SMTP Credentials**: Entry fields for the username and password required for SMTP authentication.
- **Send Test Email Button**: A button to send a test email using the provided configuration to verify that the settings are correct.
- **Email Mode Selection**: Radio buttons to select when emails should be sent (e.g., per scan, daily report).

**Core Logic:**
1.  **Configuration**: All email settings (server, port, credentials, addresses, and enabled status) are saved to `config.json` in real-time as the user modifies them.
2.  **Email Sending**: The panel uses Python's `smtplib` and `email` modules to construct and send emails.
3.  **Test Email**: The "Send Test Email" function creates a simple, predefined email and sends it to the configured receiver. This provides immediate feedback on the validity of the settings.
4.  **Project Completion Email**: The application can be configured to automatically send an email when a project is completed (e.g., all items in the scanner list are marked 'OK'). This email can include the final Excel file as an attachment.

**Configuration:**
All settings on this panel are saved to `config.json` immediately upon being changed.

---

### 3.3. Database Panel (`database_panel.py`)

**Purpose:**
The Database Panel provides an interface to configure and interact with a remote REST API for event logging and viewing historical log data.

**UI Components:**
- **Enable/Disable Checkbox**: A master switch to turn database logging on or off.
- **API URL Entry**: A field to enter the base URL of the logging API.
- **API User Entry**: A field to specify the user or client name for API requests.
- **Test Connection Button**: A button to verify that the application can successfully connect to the configured API endpoint.
- **Log Display**: A `ttk.Treeview` widget that displays log entries fetched from the API, with columns for `Timestamp`, `User`, `Event Type`, and `Message`.
- **Manual Log Entry**: A section with an entry field and a "Log" button to allow users to submit custom log messages manually.
- **Context Menu**: A right-click menu on the log display to refresh the logs.

**Core Logic:**
1.  **Configuration**: The API URL, user, and the enabled/disabled state are stored in `config.json` and loaded on startup.
2.  **API Interaction**: The panel uses the `requests` library to make HTTP `GET` (to fetch logs) and `POST` (to create new logs) requests to the API.
3.  **Connection Test**: The "Test Connection" button sends a request to a specific health-check endpoint (e.g., `/api/v1/health`) to validate the API URL and connectivity.
4.  **Automatic Log Refresh**: The panel starts a background thread that automatically fetches the latest logs from the API every 10 seconds, keeping the log view up-to-date without blocking the UI.
5.  **Log Display and Sorting**: Fetched logs are displayed in the treeview. Users can click on column headers to sort the logs by that column (e.g., by timestamp).
6.  **Double-Click Action**: Double-clicking a log entry attempts to find and open the associated Excel project file. It uses the log message to infer the filename and searches in common locations.

**Configuration:**
All database-related settings (URL, user, enabled status) are saved to `config.json` whenever they are changed in the UI.

---

### 3.2. Import Panel (`import_panel.py`)

**Purpose:**
The Import Panel is used to gather data from external sources and compile it into a structured Excel file, which can then be loaded into the Scanner Panel for barcode matching.

**UI Components:**
- **Scan Mode Selection**: Radio buttons to choose between `OPUS` and `GANNOMAT` scan modes.
- **Directory/File Selection**: A button and entry field to select the source directory (for OPUS mode) or the Access MDB/ACCDB file (for GANNOMAT mode).
- **Scan Button**: Initiates the scanning process based on the selected mode and source.
- **Output Log**: A text widget that displays the progress of the scan, lists the files or program numbers found, and provides feedback on the export process.
- **Save Directory Selection**: A button and entry field to specify where the generated Excel file should be saved.

**Core Logic:**
1.  **Scan Modes**:
    - **OPUS Mode**: Scans a selected directory and its subdirectories for files with `.hop` or `.hops` extensions. It extracts relevant information from these files to build the item list.
    - **GANNOMAT Mode**: Connects to a selected Microsoft Access database (`.mdb` or `.accdb`) using `pyodbc`. It queries the database for `ProgramNumber` entries and associated data.
2.  **Scanning Process**: The scanning operation runs in a separate thread to prevent the UI from freezing. The output log is updated in real-time with the progress.
3.  **Data Export**: Once the scan is complete, the collected data is compiled into a `pandas` DataFrame with the standard columns (`Programma`, `Omschrijving`, `Aantal`, `Barcode`, `Status`).
4.  **Excel File Generation**: The DataFrame is then exported to an Excel file. The filename is automatically generated based on a timestamp and the project name (e.g., `OPUS_20231027_103000.xlsx`). The `Status` for all items is initialized to `NIET OK`.

**Configuration:**
The last used scan mode, source path, and save directory are saved to `config.json` for persistence across sessions.

**Note on `import_panel_debug_patch.py`:**
A debug version of this panel exists, which includes extensive `print` statements and more verbose logging to the output widget. This version is likely used for troubleshooting and development.

---

### 3.1. Scanner Panel (`scanner_panel.py`)

**Purpose:**
The Scanner Panel is the core functional unit of the application, designed for real-time barcode scanning and matching against a pre-loaded list of items from an Excel file.

**UI Components:**
- **Scanner Selection**: A dropdown menu to select the scanner type (`USB Keyboard` or `COM Port`).
- **COM Port Selection**: If `COM Port` is selected, another dropdown appears to choose the specific port.
- **Excel File Selection**: A button and entry field to browse for and select the project's Excel file.
- **Item Display**: A `ttk.Treeview` widget displays the items from the Excel file with the following columns:
    - `Programma`: Program name/identifier.
    - `Omschrijving`: Description.
    - `Aantal`: Quantity.
    - `Barcode`: The barcode value.
    - `Status`: The current status of the item, color-coded for clarity:
        - `OK` (Green): The item has been successfully scanned.
        - `DUPLICAAT` (Orange): The item was scanned more than once.
        - `NIET OK` (Red): The item is not yet scanned or has an issue.
- **Status Bar**: Displays real-time feedback about the last scan (e.g., 'MATCH', 'NO MATCH', 'DUPLICATE').

**Core Logic:**
1.  **Loading Data**: The user selects an Excel file. The panel reads this file using `pandas` and populates the treeview. It expects specific column names (`Programma`, `Omschrijving`, `Aantal`, `Barcode`, `Status`).
2.  **Scanner Input**: 
    - **USB Keyboard**: It listens for keyboard input globally. A sequence of characters followed by an 'Enter' key press is treated as a barcode scan.
    - **COM Port**: It opens a serial connection to the selected COM port and listens for data in a separate thread.
3.  **Barcode Matching**: When a barcode is scanned, the application performs a lookup in the loaded item list. The matching logic is flexible:
    - It first attempts an **exact match**.
    - If no exact match is found, it performs a **normalized match**, where it strips whitespace and common path separators (`/`, `\`) from both the scanned barcode and the barcodes in the list before comparing.
4.  **Status Updates**: 
    - On a successful first match, the item's status is updated to `OK`.
    - If a barcode for an `OK` item is scanned again, the status changes to `DUPLICAAT`.
    - The UI is updated instantly with the new status and color.
5.  **Event Logging**: Scan events (match, no match, duplicate) are logged to the database if the database connection is enabled.

**Configuration:**
The selected scanner type and COM port are saved to `config.json` and automatically loaded the next time the application starts.

---

## 2. Application Structure

### `main.py`

The entry point of the application. It initializes the main window, creates a `ttk.Notebook` widget to hold the different panels, and adds each panel as a tab. It also manages the display of a splash screen on startup.

### `gui/`

This directory contains all the GUI-related code.

- `gui/panels/`: Contains the source code for each of the functional panels (tabs) in the application.
- `gui/splash_screen.py`: Implements the splash screen window shown at startup.
- `gui/tooltip.py`: A helper class for showing tooltips on widgets.

### `config_utils.py`

A utility module to handle reading from and writing to the `config.json` file, which stores all persistent application settings.

### `startup_utils.py`

Contains utility functions used during application startup, such as resource path management for PyInstaller builds.

---
