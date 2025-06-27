"""
Startup Manager for BarcodeMaster Application

This module handles the complete startup sequence in a clean, organized way
that's compatible with both development and EXE environments.
"""

import sys
import os
import time
import threading
import importlib
from pathlib import Path
from urllib.parse import urlparse
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk


class StartupManager:
    """Manages the complete application startup sequence."""
    
    def __init__(self):
        self.startup_start_time = time.time()
        self.splash_window = None
        self.root_window = None
        self.initialization_complete = False
        self.initialization_error = None
        
        # Required modules for dependency checking
        self.required_modules = {
            "PIL": "Pillow",
            "psutil": "psutil", 
            "requests": "requests",
            "serial.tools.list_ports": "pyserial",
            "pandas": "pandas",
            "openpyxl": "openpyxl",
            "pyodbc": "pyodbc"
        }
    
    def setup_python_path(self):
        """Setup Python path for both development and EXE environments."""
        if getattr(sys, 'frozen', False):
            # Running as EXE
            application_path = os.path.dirname(sys.executable)
        else:
            # Running as script
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        project_root = os.path.abspath(os.path.join(application_path, '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        return application_path, project_root
    
    def check_dependencies(self):
        """Check for required dependencies and exit gracefully if missing."""
        missing_modules = []
        
        for import_name, pip_name in self.required_modules.items():
            try:
                importlib.import_module(import_name)
            except ImportError:
                missing_modules.append(pip_name)
        
        if missing_modules:
            error_msg = (
                "Missing Required Dependencies\n\n"
                f"The following packages are required but not installed:\n"
                f"• {chr(10).join(missing_modules)}\n\n"
                f"Please install them using:\n"
                f"pip install {' '.join(missing_modules)}"
            )
            
            # Try to show GUI error if possible, otherwise console
            try:
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("BarcodeMaster - Missing Dependencies", error_msg)
                root.destroy()
            except:
                print("=" * 60)
                print("BARCODE MASTER - FATAL ERROR")
                print("=" * 60)
                print(error_msg)
                print("=" * 60)
            
            sys.exit(1)
    
    def create_splash_screen(self):
        """Create and display the splash screen."""
        self.root_window = tk.Tk()
        self.root_window.withdraw()  # Hide main window initially
        
        # Create splash window
        self.splash_window = tk.Toplevel(self.root_window)
        self.splash_window.overrideredirect(True)
        
        # Configure splash window
        width, height = 400, 400
        screen_width = self.splash_window.winfo_screenwidth()
        screen_height = self.splash_window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.splash_window.geometry(f"{width}x{height}+{x}+{y}")
        self.splash_window.configure(bg='white')
        
        # Add logo or text
        try:
            from BarcodeMaster.path_utils import get_resource_path
            logo_path = get_resource_path("assets/logo.png")
            
            if os.path.exists(logo_path):
                pil_image = Image.open(logo_path)
                pil_image = pil_image.resize((width, height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(pil_image)
                
                label = tk.Label(self.splash_window, image=photo, bg='white')
                label.image = photo  # Keep a reference
                label.pack(expand=True)
            else:
                raise FileNotFoundError("Logo not found")
                
        except Exception:
            # Fallback to text splash
            label = tk.Label(
                self.splash_window, 
                text="BarcodeMaster",
                font=("Arial", 24, "bold"),
                bg='white',
                fg='#333333'
            )
            label.pack(expand=True)
        
        # Add loading indicator
        self.status_label = tk.Label(
            self.splash_window,
            text="Starting application...",
            font=("Arial", 10),
            bg='white',
            fg='#666666'
        )
        self.status_label.pack(side='bottom', pady=20)
        
        self.splash_window.update()
        return self.splash_window
    
    def update_splash_status(self, message):
        """Update the status message on splash screen."""
        if self.splash_window and self.status_label:
            try:
                self.status_label.config(text=message)
                self.splash_window.update()
            except:
                pass  # Ignore if splash is destroyed
    
    def initialize_application(self):
        """Initialize application components in background."""
        try:
            self.update_splash_status("Loading configuration...")
            
            # Import application modules
            from BarcodeMaster.gui.app import run as run_main_app, ServiceStatus
            from BarcodeMaster.config_utils import get_config
            from BarcodeMaster.database.db_log_api import run_api_server
            
            self.update_splash_status("Starting database API...")
            
            # Start database API if enabled
            config = get_config()
            db_api_thread = None
            
            if config.get('database_enabled', True):
                api_url = config.get('api_url', 'http://localhost:5001/log')
                port = 5001  # Default port
                
                try:
                    parsed_url = urlparse(api_url)
                    if parsed_url.port:
                        port = parsed_url.port
                except Exception as e:
                    print(f"Could not parse port from api_url: {e}. Using default port {port}.")
                
                db_api_thread = threading.Thread(
                    target=run_api_server, 
                    kwargs={'port': port}, 
                    daemon=True
                )
                db_api_thread.start()
                print(f"Database API started on port {port}")
            
            self.update_splash_status("Preparing user interface...")
            
            # Prepare service status
            service_status = ServiceStatus()
            if db_api_thread:
                service_status.db_api_status = "Starting..."
            else:
                service_status.db_api_status = "Disabled"
            service_status.com_splitter_status = "Managed in-app"
            
            # Store references for main app launch
            self.run_main_app = run_main_app
            self.service_status = service_status
            
            self.initialization_complete = True
            self.update_splash_status("Ready to launch...")
            
        except Exception as e:
            self.initialization_error = str(e)
            print(f"Initialization error: {e}")
            import traceback
            traceback.print_exc()
    
    def launch_main_application(self):
        """Launch the main application after initialization."""
        if self.initialization_error:
            messagebox.showerror(
                "Startup Error", 
                f"Failed to initialize application:\n{self.initialization_error}"
            )
            sys.exit(1)
        
        if not self.initialization_complete:
            # Still initializing, check again later
            self.root_window.after(100, self.launch_main_application)
            return
        
        # Ensure minimum splash time
        elapsed_time = time.time() - self.startup_start_time
        min_splash_time = 2.0  # Minimum 2 seconds
        
        if elapsed_time < min_splash_time:
            remaining_time = int((min_splash_time - elapsed_time) * 1000)
            self.root_window.after(remaining_time, self._do_launch)
        else:
            self._do_launch()
    
    def _do_launch(self):
        """Actually launch the main application."""
        try:
            # Launch main application
            self.run_main_app(self.root_window, self.splash_window, self.service_status)
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch main application:\n{e}")
            sys.exit(1)
    
    def start(self):
        """Start the complete application startup sequence."""
        try:
            # 1. Setup environment
            self.setup_python_path()
            
            # 2. Check dependencies
            self.check_dependencies()
            
            # 3. Create splash screen
            self.create_splash_screen()
            
            # 4. Start initialization in background
            init_thread = threading.Thread(target=self.initialize_application, daemon=True)
            init_thread.start()
            
            # 5. Schedule main app launch check
            self.root_window.after(500, self.launch_main_application)
            
            # 6. Start main event loop
            self.root_window.mainloop()
            
        except KeyboardInterrupt:
            print("\nApplication startup cancelled by user.")
            sys.exit(0)
        except Exception as e:
            error_msg = f"Fatal startup error: {e}"
            print(error_msg)
            try:
                messagebox.showerror("BarcodeMaster - Fatal Error", error_msg)
            except:
                pass
            sys.exit(1)


def main():
    """Main entry point for the application."""
    startup_manager = StartupManager()
    startup_manager.start()


if __name__ == "__main__":
    main()
