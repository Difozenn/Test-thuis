# Entry point for BarcodeMatch (BarcodeMaster structure)
import sys
import os
import traceback
from datetime import datetime

def log_error(error_msg):
    """Log errors to a file for debugging exe issues"""
    try:
        # Get the directory where the exe is running
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            app_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        log_file = os.path.join(app_dir, 'barcodematch_error.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"\n{'='*60}\n")
            f.write(f"[{timestamp}] BarcodeMatch Error\n")
            f.write(f"{'='*60}\n")
            f.write(error_msg)
            f.write(f"\n{'='*60}\n")
    except:
        pass  # If logging fails, don't crash

if __name__ == "__main__":
    try:
        from gui.app import run_app
        run_app()
    except Exception as e:
        error_msg = f"Fatal Error: {str(e)}\n\n"
        error_msg += "Full Traceback:\n"
        error_msg += traceback.format_exc()
        error_msg += "\n\nSystem Information:\n"
        error_msg += f"Python Version: {sys.version}\n"
        error_msg += f"Platform: {sys.platform}\n"
        error_msg += f"Executable: {sys.executable}\n"
        error_msg += f"Frozen: {getattr(sys, 'frozen', False)}\n"
        
        # Log to file
        log_error(error_msg)
        
        # Try to show error dialog if tkinter is available
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "BarcodeMatch Fout",
                f"BarcodeMatch kon niet starten:\n\n{str(e)}\n\n"
                f"Zie barcodematch_error.log voor details."
            )
            root.destroy()
        except:
            pass
        
        sys.exit(1)
