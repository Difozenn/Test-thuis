import sys
import os
import threading
import queue
import tkinter as tk
from tkinter import messagebox

# Add project root to path for imports
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Early imports for critical paths
from path_utils import ensure_writable_dirs, get_resource_path
from config_utils import get_config

# Global state
_startup_queue = queue.Queue()
_db_api_thread = None

class FastStartup:
    """Optimized startup manager for faster launch times"""
    
    def __init__(self):
        self.root = None
        self.splash = None
        self.app = None
        self.critical_deps = ['tkinter', 'requests', 'serial']
        self.optional_deps = []
        self.startup_tasks = []
        
    def check_critical_dependencies(self):
        """Check only critical dependencies for startup"""
        missing = []
        for dep in self.critical_deps:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)
        
        if missing:
            self._show_dependency_error(missing)
            return False
        return True
    
    def _show_dependency_error(self, missing):
        """Show dependency error and exit"""
        error_msg = f"Critical dependencies missing: {', '.join(missing)}"
        print(f"FATAL: {error_msg}")
        
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Missing Dependencies", error_msg)
        except:
            pass
        sys.exit(1)
    
    def create_minimal_splash(self):
        """Create a minimal splash screen without heavy dependencies"""
        self.splash = tk.Toplevel(self.root)
        self.splash.overrideredirect(True)
        
        # Center splash
        w, h = 300, 100
        ws = self.splash.winfo_screenwidth()
        hs = self.splash.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.splash.geometry(f"{w}x{h}+{x}+{y}")
        
        # Simple text splash
        frame = tk.Frame(self.splash, bg='#2c3e50')
        frame.pack(fill='both', expand=True)
        
        tk.Label(frame, text="BarcodeMaster", font=('Arial', 20, 'bold'),
                bg='#2c3e50', fg='white').pack(pady=20)
        tk.Label(frame, text="Loading...", font=('Arial', 10),
                bg='#2c3e50', fg='#ecf0f1').pack()
        
        self.splash.update()
        return self.splash
    
    def start_background_services(self):
        """Start background services in parallel"""
        def _start_db_api():
            try:
                config = get_config()
                if config.get('database_enabled', True):
                    # Import heavy modules in background
                    from database.db_log_api import run_api_server
                    from urllib.parse import urlparse
                    
                    api_url = config.get('api_url', 'http://localhost:5001/log')
                    port = 5001
                    try:
                        parsed_url = urlparse(api_url)
                        if parsed_url.port:
                            port = parsed_url.port
                    except:
                        pass
                    
                    # Start API server
                    global _db_api_thread
                    _db_api_thread = threading.Thread(
                        target=run_api_server,
                        kwargs={'port': port},
                        daemon=True
                    )
                    _db_api_thread.start()
                    _startup_queue.put(('db_api', 'started', port))
            except Exception as e:
                _startup_queue.put(('db_api', 'error', str(e)))
        
        # Start DB API in background
        threading.Thread(target=_start_db_api, daemon=True).start()
    
    def lazy_load_main_app(self):
        """Load main app components after UI is shown"""
        # Import heavy modules after UI is visible
        from gui.app import MainApp, ServiceStatus
        
        # Create service status
        service_status = ServiceStatus()
        
        # Check background service status
        try:
            while not _startup_queue.empty():
                service, status, data = _startup_queue.get_nowait()
                if service == 'db_api':
                    if status == 'started':
                        service_status.db_api_status = "Running"
                        print(f"Database API started on port {data}")
                    else:
                        service_status.db_api_status = "Error"
                        print(f"Database API error: {data}")
        except:
            pass
        
        service_status.com_splitter_status = "Managed in-app"
        
        # Create main app
        self.app = MainApp(self.root, service_status=service_status)
        self.app.pack(side="top", fill="both", expand=True)
        
        # Load remaining dependencies in background
        self._background_dependency_check()
    
    def _background_dependency_check(self):
        """Check optional dependencies in background"""
        def _check():
            optional_modules = {
                "PIL": "Pillow",
                "psutil": "psutil", 
                "pandas": "pandas",
                "openpyxl": "openpyxl",
                "pyodbc": "pyodbc"
            }
            
            missing = []
            for import_name, pip_name in optional_modules.items():
                try:
                    __import__(import_name)
                except ImportError:
                    missing.append(pip_name)
            
            if missing and hasattr(self.app, 'show_warning'):
                self.root.after(1000, lambda: self.app.show_warning(
                    f"Optional modules missing: {', '.join(missing)}"
                ))
        
        threading.Thread(target=_check, daemon=True).start()
    
    def run(self):
        """Main startup sequence"""
        # 1. Check critical dependencies only
        if not self.check_critical_dependencies():
            return
        
        # 2. Ensure directories (fast operation)
        ensure_writable_dirs()
        
        # 3. Create root window (hidden)
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("BarcodeMaster")
        self.root.geometry("800x600")
        
        # 4. Show minimal splash immediately
        self.create_minimal_splash()
        
        # 5. Start background services
        self.start_background_services()
        
        # 6. Configure main window
        try:
            icon_path = get_resource_path("assets/ico.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
        
        # 7. Show main window quickly (reduced delay)
        self.root.after(500, self._show_main_window)
        
        # 8. Run mainloop
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nApplication interrupted")
            self._cleanup()
    
    def _show_main_window(self):
        """Show main window and load app"""
        if self.splash:
            self.splash.destroy()
        
        self.root.deiconify()
        
        # Load main app after window is visible
        self.root.after(10, self.lazy_load_main_app)
    
    def _cleanup(self):
        """Cleanup on exit"""
        global _db_api_thread
        try:
            from database.db_log_api import stop_api_server
            stop_api_server()
            if _db_api_thread and _db_api_thread.is_alive():
                _db_api_thread.join(timeout=1.0)
        except:
            pass

def main():
    """Optimized entry point"""
    startup = FastStartup()
    startup.run()

if __name__ == "__main__":
    # For exe compilation, handle frozen state
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        os.chdir(os.path.dirname(sys.executable))
    
    main()