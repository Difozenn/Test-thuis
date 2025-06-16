import sys
import os

# Add the project root to the Python path to allow for absolute imports
# This makes the script runnable from anywhere.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import importlib # For dependency check

# --- Dependency Check (MUST RUN BEFORE APP IMPORTS) ---
REQUIRED_MODULES = {
    "PIL": "Pillow",
    "psutil": "psutil",
    "requests": "requests",
    "serial.tools.list_ports": "pyserial"  # More specific check for pyserial
}

def check_dependencies():
    missing_for_pip = []
    missing_module_details = []

    for import_name, pip_name in REQUIRED_MODULES.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing_for_pip.append(pip_name)
            # Adjust message for the specific pyserial check
            if import_name == "serial.tools.list_ports":
                missing_module_details.append(f"- {pip_name} (could not import '{import_name}', part of pyserial)")
            else:
                missing_module_details.append(f"- {pip_name} (could not import '{import_name}')")

    if missing_for_pip:
        error_message_console = (
            "Error: Missing required Python packages.\n"
            "Please install them by running:\n"
            f"  pip install {' '.join(missing_for_pip)}\n"
            "Details of missing modules:\n" +
            "\n".join(missing_module_details)
        )
        print(error_message_console, file=sys.stderr)

        try:
            # Attempt to show a Tkinter messagebox if Tkinter itself is available
            # We need to import tkinter here locally for the check, as a top-level import
            # might fail if tkinter itself is the issue (though less common for this app's deps)
            import tkinter as tk_dep_check
            from tkinter import messagebox as messagebox_dep_check
            root_dep_check = tk_dep_check.Tk()
            root_dep_check.withdraw() # Hide the main Tk window for the error dialog
            messagebox_dep_check.showerror(
                "Dependency Error",
                "The following required packages are missing or not installed correctly:\n\n" +
                "\n".join(missing_module_details) +
                "\n\nPlease install them to run BarcodeMaster.\n"
                "You can typically install them using pip:\n\n" +
                f"pip install {' '.join(missing_for_pip)}"
            )
            root_dep_check.destroy()
        except ImportError:
            # If tkinter import fails (e.g., minimal environment or tkinter not installed),
            # the console message is the fallback.
            pass 
        sys.exit(1)

check_dependencies() # Execute the check immediately
# --- End Dependency Check ---

# Now proceed with other imports
import tkinter as tk
from PIL import Image, ImageTk
import time
import psutil # psutil needed for functions below
import subprocess
import threading
# 'sys', 'os', and 'importlib' were already imported for the dependency check

from BarcodeMaster.gui.app import run as run_main_app, ServiceStatus
from BarcodeMaster import config_manager
from BarcodeMaster.config_utils import get_config
from BarcodeMaster.com_splitter import ComSplitter

# --- Define key paths at module level for robustness ---
DB_API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'database', 'db_log_api.py'))

def show_splash(main_tk_root):  # Modified to accept main_tk_root
    splash = tk.Toplevel(main_tk_root)
    splash.overrideredirect(True)
    splash.configure(bg='white')
    # Center splash
    w, h = 400, 400
    ws = splash.winfo_screenwidth()
    hs = splash.winfo_screenheight()
    x = (ws // 2) - (w // 2)
    y = (hs // 2) - (h // 2)
    splash.geometry(f"{w}x{h}+{x}+{y}")
    # Load logo
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
    pil_img = Image.open(logo_path).resize((350, 350), Image.LANCZOS)
    img = ImageTk.PhotoImage(pil_img)
    label = tk.Label(splash, image=img, bg='white')
    label.image = img
    label.pack(expand=True)

    splash.update_idletasks()  # Process geometry and other idle tasks
    splash.update()          # Force redraw of the splash screen

    splash.after(2000, splash.destroy) # Schedule splash destruction
    main_tk_root.after(2010, main_tk_root.deiconify) # Schedule main window to appear after splash

def is_db_log_api_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'db_log_api.py' in ' '.join(cmdline):
                return True
        except Exception:
            continue
    return False

def start_db_log_api():
    python_exe = sys.executable
    # Use the globally defined DB_API_PATH
    subprocess.Popen([python_exe, DB_API_PATH], cwd=os.path.dirname(DB_API_PATH), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def manage_services(service_status):
    """Checks config, starts background services, and updates their status."""
    print("Starting service management thread...")
    # Get configs
    from BarcodeMaster.config_utils import get_config
    config = get_config()
    start_db, start_splitter = config_manager.get_startup_settings()

    # --- Manage DB API ---
    if start_db:
        if not is_db_log_api_running():
            print("Service Manager: Starting Database API...")
            service_status.services['db_api'] = 'STARTING'
            start_db_log_api()
            time.sleep(2) # Give it time to initialize
            if is_db_log_api_running():
                print("Service Manager: Database API is RUNNING.")
                service_status.services['db_api'] = 'RUNNING'
            else:
                print("Service Manager: Database API FAILED to start.")
                service_status.services['db_api'] = 'FAILED'
        else:
            print("Service Manager: Database API was already running.")
            service_status.services['db_api'] = 'RUNNING'
    else:
        print("Service Manager: Database API is DISABLED.")
        service_status.services['db_api'] = 'DISABLED'


    # --- Manage COM Splitter ---
    if start_splitter:
        print("Service Manager: Starting COM Splitter...")
        cfg = get_config()
        splitter_config = {
            'physical_port': cfg.get('splitter_physical_port'),
            'virtual_port_1': cfg.get('splitter_virtual_port_1'),
            'virtual_port_2': cfg.get('splitter_virtual_port_2'),
            'baud_rate': int(cfg.get('splitter_baud_rate', 9600))
        }
        # Ensure essential port configs are present
        if splitter_config['physical_port'] and splitter_config['virtual_port_1'] and splitter_config['virtual_port_2']:
            splitter = ComSplitter(splitter_config, lambda msg: print(f"[ComSplitter Startup] {msg}"))
            splitter.start()
            service_status.services['splitter'] = splitter
            service_status.services['splitter_status'] = 'RUNNING'
        else:
            print("COM Splitter startup skipped: configuration is incomplete.")
            service_status.services['splitter_status'] = 'CONFIG_INCOMPLETE'
    else:
        service_status.services['splitter_status'] = 'DISABLED'


def main():
    # 1. Initialize service status and get config
    service_status = ServiceStatus()
    config = get_config()
    start_db, start_splitter = config_manager.get_startup_settings()

    # 2. Create and hide the main Tkinter window
    root = tk.Tk()
    root.withdraw()

    # 3. Show the splash screen. It's non-blocking.
    show_splash(root)

    # 4. Start background services in a separate thread if enabled
    if start_db or start_splitter:
        service_thread = threading.Thread(target=manage_services, args=(service_status,), daemon=True)
        service_thread.start()
        print("Main thread: Service management thread started.")
    else:
        print("Main thread: Background services disabled.")

    # 5. Run the main application, which contains the mainloop.
    #    The main window will be shown by the splash screen logic.
    run_main_app(service_status, root)

import atexit

def terminate_db_on_exit():
    from BarcodeMaster.config_utils import get_config
    import psutil
    import sys
    import time
    config = get_config()
    print("[main.py] terminate_db_on_exit called")
    if config.get('admin_terminate_db_on_exit', False):
        found = False
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if p.info['cmdline'] and any('db_log_api.py' in str(arg) for arg in p.info['cmdline']):
                    print(f"  Found db_log_api.py process: PID={p.pid} CMD={p.info['cmdline']}")
                    found = True
                    p.terminate()
                    try:
                        p.wait(timeout=3)
                        print(f"  Process {p.pid} terminated with terminate().")
                    except psutil.TimeoutExpired:
                        print(f"  Process {p.pid} did not terminate, killing...")
                        p.kill()
                        print(f"  Process {p.pid} killed.")
            except Exception as e:
                print(f"  Exception while terminating process: {e}")
        if not found:
            print("  No db_log_api.py process found.")
    else:
        print("  admin_terminate_db_on_exit is False; not terminating database.")
    # Clear the database log file
    import os, sys
    try:
        base_dir = os.path.dirname(__file__)
    except NameError:
        base_dir = os.path.dirname(sys.argv[0]) if sys.argv[0] else os.getcwd()
    log_path = os.path.join(base_dir, 'database', 'db_log_api.log')
    if os.path.exists(log_path):
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.truncate(0)
            print(f"[main.py] Cleared database log file: {log_path}")
        except Exception as e:
            print(f"[main.py] Failed to clear database log file: {e}")
    print("[main.py] Exit cleanup complete.")

atexit.register(terminate_db_on_exit)

if __name__ == "__main__":
    main()
