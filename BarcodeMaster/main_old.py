import sys
import os
import tkinter as tk
import importlib
import threading
import time
from urllib.parse import urlparse

# --- Early Dependency Check ---
# This runs before any other imports to ensure the environment is sane.
# It uses no GUI and exits on failure, which is suitable for fatal errors.
REQUIRED_MODULES = {
    "PIL": "Pillow",
    "psutil": "psutil",
    "requests": "requests",
    "serial.tools.list_ports": "pyserial",
    "pandas": "pandas",
    "openpyxl": "openpyxl",
    "pyodbc": "pyodbc"
}

def check_dependencies_no_gui():
    """Checks for required modules and exits if any are missing."""
    missing_for_pip = []
    for import_name, pip_name in REQUIRED_MODULES.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing_for_pip.append(pip_name)

    if missing_for_pip:
        error_message = (
            "The following required packages are missing:\n\n" +
            "\n".join(missing_for_pip) +
            "\n\nPlease install them using pip:\n\n" +
            f"pip install {' '.join(missing_for_pip)}"
        )
        print("="*60, "\nFATAL: MISSING DEPENDENCIES\n", "="*60, sep="")
        print(error_message)
        print("="*60)
        sys.exit(1)

# Run the check immediately on script load.
check_dependencies_no_gui()


# --- Main Application Imports ---
# It's now safe to import our app modules and other dependencies.
from PIL import Image, ImageTk
# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from BarcodeMaster.gui.app import run as run_main_app, ServiceStatus
from BarcodeMaster.config_utils import get_config
from BarcodeMaster.path_utils import get_resource_path
from BarcodeMaster.database.db_log_api import run_api_server

def show_splash(main_tk_root):
    """Creates and displays the splash screen without a self-destruct timer."""
    splash = tk.Toplevel(main_tk_root)
    splash.overrideredirect(True)
    w, h = 400, 400
    ws = splash.winfo_screenwidth()
    hs = splash.winfo_screenheight()
    x = (ws // 2) - (w // 2)
    y = (hs // 2) - (h // 2)
    splash.geometry(f"{w}x{h}+{x}+{y}")
    try:
        logo_path = get_resource_path("assets/logo.png")
        pil_img = Image.open(logo_path).resize((w, h), Image.LANCZOS)
        img = ImageTk.PhotoImage(pil_img)
        label = tk.Label(splash, image=img, borderwidth=0, highlightthickness=0)
        label.image = img
        label.pack(expand=True)
    except FileNotFoundError:
        label = tk.Label(splash, text="BarcodeMaster", font=("Arial", 24))
        label.pack(expand=True, padx=20, pady=20)
    
    splash.update()
    return splash

def start_db_api_thread():
    """Starts the database API server in a background thread if enabled."""
    config = get_config()
    if not config.get('database_enabled', True):
        print("Database is disabled in config. API server will not start.")
        return None

    api_url = config.get('api_url', 'http://localhost:5001/log')
    port = 5001  # Default port
    try:
        parsed_url = urlparse(api_url)
        if parsed_url.port:
            port = parsed_url.port
    except Exception as e:
        print(f"Could not parse port from api_url: {e}. Falling back to default port {port}.")

    api_thread = threading.Thread(target=run_api_server, kwargs={'port': port}, daemon=True)
    api_thread.start()
    print(f"Database API thread started on port {port}.")
    return api_thread

def run_initialization(root, splash):
    """
    Performs startup tasks in the background while the splash screen is visible.
    Schedules the main application to run after tasks are complete.
    """
    start_time = time.time()

    # 1. Start the DB API thread
    db_api_thread = start_db_api_thread()

    # 2. Prepare service status for the main app
    service_status = ServiceStatus()
    if db_api_thread:
        service_status.db_api_status = "Starting..."
    else:
        service_status.db_api_status = "Disabled"
    service_status.com_splitter_status = "Managed in-app"

    # 3. Ensure splash is shown for a minimum duration
    init_duration = time.time() - start_time
    min_splash_time_sec = 3.0
    delay_ms = max(0, int((min_splash_time_sec - init_duration) * 1000))

    # 4. Schedule the main application to run, which will destroy the splash
    root.after(delay_ms, lambda: run_main_app(root, splash, service_status))

def main():
    """Main entry point for the application."""
    root = tk.Tk()
    root.withdraw()

    splash = show_splash(root)
    
    # Run initialization tasks in a separate thread to not block the GUI
    init_thread = threading.Thread(target=run_initialization, args=(root, splash), daemon=True)
    init_thread.start()

    root.mainloop()

if __name__ == "__main__":
    main()

