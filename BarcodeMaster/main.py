import sys
import os
import tkinter as tk
import importlib
import threading
import time
from urllib.parse import urlparse
from PIL import Image, ImageTk

# Add the project root to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import path utilities first
from path_utils import ensure_writable_dirs, get_resource_path, get_writable_path

# --- Dependency Check ---
REQUIRED_MODULES = {
    "PIL": "Pillow",
    "psutil": "psutil",
    "requests": "requests",
    "serial.tools.list_ports": "pyserial",
    "pandas": "pandas",
    "openpyxl": "openpyxl",
    "pyodbc": "pyodbc"
}

def check_dependencies():
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
        print("="*60)
        print("FATAL: MISSING DEPENDENCIES")
        print(error_message)
        print("="*60)
        
        # Try to show GUI error if possible
        try:
            root = tk.Tk()
            root.withdraw()
            tk.messagebox.showerror("Missing Dependencies", error_message)
        except:
            pass
        
        sys.exit(1)

# Check dependencies early
check_dependencies()

# --- App Imports (after dependency check) ---
from gui.app import MainApp, ServiceStatus
from config_utils import get_config
from database.db_log_api import run_api_server, stop_api_server

# Global variable to track the API thread
db_api_thread = None

def show_splash(main_tk_root):
    splash = tk.Toplevel(main_tk_root)
    splash.overrideredirect(True)
    w, h = 400, 400
    ws = splash.winfo_screenwidth()
    hs = splash.winfo_screenheight()
    x = (ws // 2) - (w // 2)
    y = (hs // 2) - (h // 2)
    splash.geometry(f"{w}x{h}+{x}+{y}")
    try:
        logo_path = get_resource_path("assets/Logo.png")
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
    global db_api_thread
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

    db_api_thread = threading.Thread(target=run_api_server, kwargs={'port': port}, daemon=True)
    db_api_thread.start()
    print(f"Database API thread started on port {port}.")
    print(f"Dashboard available at: http://localhost:{port}/dashboard")
    return db_api_thread

def cleanup_on_exit():
    """Cleanup function called on application exit"""
    global db_api_thread
    print("Cleaning up on exit...")
    
    # Stop the DB API server
    try:
        stop_api_server()
        if db_api_thread and db_api_thread.is_alive():
            db_api_thread.join(timeout=2.0)
    except Exception as e:
        print(f"Error stopping DB API: {e}")

def main():
    # Ensure writable directories exist
    ensure_writable_dirs()
    
    # Create root window but keep it hidden initially
    root = tk.Tk()
    root.withdraw()
    
    # Register cleanup on exit
    import atexit
    atexit.register(cleanup_on_exit)
    
    splash = show_splash(root)
    
    # Start DB API in background
    db_api_thread = start_db_api_thread()

    # Prepare service status
    service_status = ServiceStatus()
    if db_api_thread:
        service_status.db_api_status = "Starting..."
    else:
        service_status.db_api_status = "Disabled"
    service_status.com_splitter_status = "Managed in-app"

    root.update()
    
    # Launch main app after splash screen
    def launch_main_app():
        if splash:
            splash.destroy()
        
        # Configure the root window
        root.title("BarcodeMaster")
        root.geometry("800x600")
        
        # Set icon if available
        try:
            icon_path = get_resource_path("assets/ico.ico")
            if os.path.exists(icon_path):
                root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Could not set icon: {e}")
        
        root.deiconify()  # Show the main window
        
        # Create the main app
        app = MainApp(root, service_status=service_status)
        app.pack(side="top", fill="both", expand=True)
    
    root.after(3000, launch_main_app)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        cleanup_on_exit()

if __name__ == "__main__":
    main()