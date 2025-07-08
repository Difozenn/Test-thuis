import sys
import os
import threading
import tkinter as tk

# Optimize path setup
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Critical imports only
from path_utils import ensure_writable_dirs, get_resource_path

# Deferred imports for faster startup
_heavy_imports_loaded = False
_missing_deps = []

def load_heavy_imports():
    """Load heavy imports after UI is shown"""
    global _heavy_imports_loaded, _missing_deps
    if _heavy_imports_loaded:
        return True
    
    # Check dependencies in background
    optional_modules = {
        "PIL": "Pillow",
        "psutil": "psutil",
        "pandas": "pandas",
        "openpyxl": "openpyxl",
        "pyodbc": "pyodbc"
    }
    
    for import_name, pip_name in optional_modules.items():
        try:
            __import__(import_name)
        except ImportError:
            _missing_deps.append(pip_name)
    
    _heavy_imports_loaded = True
    return len(_missing_deps) == 0

def check_critical_dependencies():
    """Check only critical dependencies needed for startup"""
    try:
        import requests
        import serial
        return True
    except ImportError as e:
        error_message = f"Critical dependency missing: {e}"
        print(f"FATAL: {error_message}")
        
        try:
            root = tk.Tk()
            root.withdraw()
            from tkinter import messagebox
            messagebox.showerror("Missing Dependencies", error_message)
        except:
            pass
        
        sys.exit(1)

# Quick critical check only
check_critical_dependencies()

# --- App Imports (after dependency check) ---
from gui.app import MainApp, ServiceStatus
from config_utils import get_config
from database.db_log_api import run_api_server, stop_api_server

# Global variable to track the API thread
db_api_thread = None

def show_splash(main_tk_root):
    """Show splash screen with logo"""
    splash = tk.Toplevel(main_tk_root)
    splash.overrideredirect(True)
    w, h = 400, 400
    ws = splash.winfo_screenwidth()
    hs = splash.winfo_screenheight()
    x = (ws // 2) - (w // 2)
    y = (hs // 2) - (h // 2)
    splash.geometry(f"{w}x{h}+{x}+{y}")
    
    try:
        # Try to load logo image
        from PIL import Image, ImageTk
        logo_path = get_resource_path("assets/Logo.png")
        if os.path.exists(logo_path):
            pil_img = Image.open(logo_path).resize((w, h), Image.Resampling.LANCZOS)
            img = ImageTk.PhotoImage(pil_img)
            label = tk.Label(splash, image=img, borderwidth=0, highlightthickness=0)
            label.image = img  # Keep a reference
            label.pack(expand=True)
        else:
            # Fallback to text if logo not found
            _show_text_splash(splash)
    except Exception:
        # Fallback to text if PIL not available yet
        _show_text_splash(splash)
    
    splash.update()
    return splash

def _show_text_splash(splash):
    """Fallback text splash screen"""
    frame = tk.Frame(splash, bg='#2c3e50')
    frame.pack(fill='both', expand=True)
    tk.Label(frame, text="BarcodeMaster", font=("Arial", 24, "bold"),
             bg='#2c3e50', fg='white').pack(expand=True)

def start_db_api_thread():
    """Start DB API in truly non-blocking way"""
    global db_api_thread
    
    def _start_async():
        try:
            config = get_config()
            if not config.get('database_enabled', True):
                print("Database is disabled in config. API server will not start.")
                return
            
            # Lazy import heavy modules
            from urllib.parse import urlparse
            from database.db_log_api import run_api_server
            
            api_url = config.get('api_url', 'http://localhost:5001/log')
            port = 5001
            try:
                parsed_url = urlparse(api_url)
                if parsed_url.port:
                    port = parsed_url.port
            except:
                pass
            
            # Start server
            print(f"Starting Database API on port {port}...")
            run_api_server(port=port)
            
        except Exception as e:
            print(f"Error starting DB API: {e}")
    
    # Start in background thread
    db_api_thread = threading.Thread(target=_start_async, daemon=True)
    db_api_thread.start()
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
        
        # Check optional dependencies in background after UI is shown
        def check_optional_deps():
            global _missing_deps
            load_heavy_imports()
            if _missing_deps:
                msg = f"Optional dependencies missing: {', '.join(_missing_deps)}\nSome features may be limited."
                root.after(1000, lambda: print(f"Warning: {msg}"))
        
        threading.Thread(target=check_optional_deps, daemon=True).start()
    
    # Show splash for a reasonable time (faster than before but enough to see logo)
    root.after(1500, launch_main_app)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        cleanup_on_exit()

if __name__ == "__main__":
    # Handle exe compilation state
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        import multiprocessing
        multiprocessing.freeze_support()
        
        # Set working directory to exe location
        os.chdir(os.path.dirname(sys.executable))
        
        # Disable console output buffering for exe
        if sys.stdout:
            sys.stdout.reconfigure(line_buffering=True)
    
    main()