import sys
import os
import subprocess
import psutil
import atexit
import time
import runpy
import tkinter.ttk

# --- Configuration ---
DB_API_SCRIPT = "database/db_log_api.py"
DB_API_LOG_FILE = "db_api.log"
PYTHON_EXECUTABLE = sys.executable

# Store the subprocess object
db_api_process = None

def is_db_log_api_running():
    """Check if the db_log_api.py script is already running."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            # Check if cmdline is valid and contains the script name
            if cmdline and len(cmdline) > 1 and DB_API_SCRIPT in cmdline[1].replace('\\', '/'):
                print(f"Database API process found: PID {proc.pid}")
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def start_db_log_api():
    """Starts the database log API as a silent background process."""
    global db_api_process
    if is_db_log_api_running():
        print("Database API is already running.")
        return

    print("Starting database API...")
    script_path = os.path.abspath(DB_API_SCRIPT)
    log_file_path = os.path.abspath(DB_API_LOG_FILE)

    if not os.path.exists(script_path):
        print(f"Error: Database API script not found at {script_path}")
        # In a real app, you might show a GUI error here
        return

    startupinfo = None
    creationflags = 0
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = subprocess.CREATE_NO_WINDOW

    log_file = open(log_file_path, 'a')

    db_api_process = subprocess.Popen(
        [PYTHON_EXECUTABLE, script_path],
        stdout=log_file,
        stderr=log_file,
        startupinfo=startupinfo,
        creationflags=creationflags,
        cwd=os.path.dirname(script_path)
    )
    print(f"Database API started with PID: {db_api_process.pid}")
    time.sleep(2)  # Give the server a moment to start

def stop_db_log_api():
    """Stops the database log API process if it was started by this script."""
    global db_api_process
    if db_api_process:
        print(f"Terminating database API process (PID: {db_api_process.pid})...")
        db_api_process.terminate()
        try:
            db_api_process.wait(timeout=5)
            print("Database API process terminated successfully.")
        except subprocess.TimeoutExpired:
            print("Process did not terminate in time, killing it.")
            db_api_process.kill()
    else:
        print("No database API process was started by this launcher.")

if __name__ == '__main__':
    # Ensure the cleanup function is called on exit
    atexit.register(stop_db_log_api)

    # Start the background service
    start_db_log_api()

    # Launch the main application
    print("Launching main application from main.py...")
    try:
        runpy.run_path('main.py', run_name='__main__')
    except Exception as e:
        print(f"\n--- AN ERROR OCCURRED IN main.py ---")
        print(f"{e}")
        print("-------------------------------------")
        input("\nPress Enter to exit...")
