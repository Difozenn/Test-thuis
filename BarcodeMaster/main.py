import tkinter as tk
from PIL import Image, ImageTk
import os
import time
import psutil
import subprocess
import sys
from gui.app import run as run_main_app

def show_splash():
    splash = tk.Tk()
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
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "Logo.png")
    pil_img = Image.open(logo_path).resize((350, 350), Image.LANCZOS)
    img = ImageTk.PhotoImage(pil_img)
    label = tk.Label(splash, image=img, bg='white')
    label.image = img
    label.pack(expand=True)
    splash.after(2000, splash.destroy)
    splash.mainloop()

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
    db_api_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'database', 'db_log_api.py'))
    python_exe = sys.executable
    subprocess.Popen([python_exe, db_api_path], cwd=os.path.dirname(db_api_path), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    import os
    from config_utils import get_config
    config = get_config()
    if config.get('admin_db_init_enabled', True):
        if not is_db_log_api_running():
            start_db_log_api()
    # Hide splash screen in development mode
    if os.environ.get('BARCODEMASTER_ENV', '').lower() == 'production':
        show_splash()
    run_main_app()

import atexit

def terminate_db_on_exit():
    from config_utils import get_config
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
