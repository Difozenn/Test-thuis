import threading
import sys
import traceback
import time
import os
import signal
from PIL import Image, ImageDraw, ImageTk
import pystray
import tkinter as tk
from tkinter import simpledialog, messagebox
from datetime import datetime
from hops_file_logger import main as hfl_main, load_seen, save_seen, update_reports, clear_seen_entries_but_keep_last_on_exit, CATEGORIES, CONFIG # Aliased main
SCAN_INTERVAL = CONFIG.get('scan_interval_seconds', 30) # Get SCAN_INTERVAL
from settings_gui import SettingsWindow

def create_image():
    # Use ico.png for the tray icon
    try:
        image = Image.open("ico.png")
    except FileNotFoundError:
        # Fallback to a simple black circle icon if ico.png is not found
        image = Image.new('RGB', (64, 64), color1 := (0, 0, 0))
        d = ImageDraw.Draw(image)
        d.ellipse((8, 8, 56, 56), fill=(0, 128, 255))
        print("[WARNING] ico.png not found. Using default tray icon.")
    return image

# Global logger thread reference and shutdown event
logger_thread = None
shutdown_event = threading.Event()

# New signal handler for the main thread (tray_logger.py)
def tray_signal_handler(signum, frame):
    """Handles SIGINT and SIGTERM in the main tray_logger thread."""
    # Use signal.Signals(signum).name to get the signal's name (e.g., 'SIGINT')
    print(f'\n[{datetime.now()}] [TRAY_SIGNAL] Signal {signal.Signals(signum).name} received, initiating shutdown...')
    shutdown_event.set() # Signal the logger_thread and potentially other parts to shut down

def run_logger_thread(event_to_signal):
    print(f"[{datetime.now()}] [LOGGER_THREAD] Logger thread process starting...")
    try:
        print(f"[{datetime.now()}] [LOGGER_THREAD_DEBUG] About to call hfl_main.")
        hfl_main(shutdown_event=event_to_signal) # Pass event to hops_file_logger's main
        print(f"[{datetime.now()}] [LOGGER_THREAD_DEBUG] hfl_main returned normally.")
    except Exception as e:
        print(f"[{datetime.now()}] [LOGGER_THREAD_ERROR] Exception in logger thread (run_logger_thread): {e}")
        print("--- TRACEBACK START ---")
        traceback.print_exc()
        print("--- TRACEBACK END ---")
    finally:
        print(f"[{datetime.now()}] [LOGGER_THREAD_FINALIZE] Logger thread's finally block reached.")
        try:
            print(f"[{datetime.now()}] [LOGGER_THREAD_FINALIZE] Calling clear_seen_entries_but_keep_last_on_exit to save final runtime state...")
            clear_seen_entries_but_keep_last_on_exit()
            print(f"[{datetime.now()}] [LOGGER_THREAD_FINALIZE] clear_seen_entries_but_keep_last_on_exit completed.")
        except Exception as e_save_final:
            print(f"[{datetime.now()}] [LOGGER_THREAD_ERROR] Exception during clear_seen_entries_but_keep_last_on_exit: {e_save_final}")
            traceback.print_exc()
        print(f"[{datetime.now()}] [LOGGER_THREAD] Logger thread (run_logger_thread) has finished.")

# --- Begin ManualAddApp integration ---
import json
from tkinter import ttk

CATEGORIES_FILE = 'categories.json'
SEEN_ENTRIES_FILE = '.seen_entries.json'

# Load categories
with open(CATEGORIES_FILE, 'r') as f:
    CATEGORIES = json.load(f)
category_list = sorted(set(CATEGORIES.values()))
if 'Allerlei' not in category_list:
    category_list.append('Allerlei')

class ManualAddApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Handmatig toevoegen')
        self.geometry('340x180')
        self.resizable(False, False)
        try:
            self.iconphoto(True, tk.PhotoImage(file='ico.png'))
        except tk.TclError:
            print("[WARNING] Could not load ico.png for ManualAddApp window icon.")
        self.create_widgets()

    def create_widgets(self):
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        tk.Label(self, text='Datum:').grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.date_entry = tk.Entry(self)
        self.date_entry.insert(0, now_str)
        self.date_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self, text='Aantal:').grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.amount_entry = tk.Entry(self)
        self.amount_entry.insert(0, '1')
        self.amount_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(self, text='Categorie:').grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.cat_var = tk.StringVar(value=category_list[0])
        self.cat_combo = ttk.Combobox(self, textvariable=self.cat_var, values=category_list, state='readonly')
        self.cat_combo.grid(row=2, column=1, padx=5, pady=5)

        self.submit_btn = tk.Button(self, text='Toevoegen', command=self.submit)
        self.submit_btn.grid(row=3, column=0, columnspan=2, pady=10)

    def submit(self):
        date_str = self.date_entry.get()
        try:
            dt = datetime.fromisoformat(date_str)
        except Exception:
            messagebox.showerror('Fout', 'Ongeldig datumformaat! Gebruik YYYY-MM-DD HH:MM')
            return
        try:
            amount = int(self.amount_entry.get())
        except Exception:
            messagebox.showerror('Fout', 'Ongeldig aantal!')
            return
        if amount < 1:
            return
        cat = self.cat_var.get()
        if not cat or cat not in category_list:
            messagebox.showerror('Fout', 'Onbekende categorie!')
            return
        # Add events to .seen_entries.json
        if os.path.exists(SEEN_ENTRIES_FILE):
            try:
                with open(SEEN_ENTRIES_FILE, 'r') as f:
                    seen = json.load(f)
                print(f"[{datetime.now()}] [MANUAL_ADD_DEBUG] Loaded .seen_entries.json: {seen}")
            except json.JSONDecodeError:
                print(f"[{datetime.now()}] [MANUAL_ADD_ERROR] Error decoding .seen_entries.json. Initializing fresh.")
                seen = {'entries': {}, 'save_events': []} # Ensure save_events key exists
        else:
            print(f"[{datetime.now()}] [MANUAL_ADD_DEBUG] .seen_entries.json not found. Initializing fresh.")
            seen = {'entries': {}, 'save_events': []} # Ensure save_events key exists

        # Ensure 'save_events' key exists if file was loaded but key was missing
        if 'save_events' not in seen:
            print(f"[{datetime.now()}] [MANUAL_ADD_DEBUG] 'save_events' key missing from loaded data. Adding it.")
            seen['save_events'] = []
        events = seen.get('save_events', [])
        for i in range(amount):
            entry_name = f"manual_add_{dt.isoformat()}_{i}"
            events.append({'timestamp': dt.isoformat(), 'type': 'new', 'entry': entry_name, 'category': cat})
        print(f"[{datetime.now()}] [MANUAL_ADD_DEBUG] Events list after adding new items: {events}")
        seen['save_events'] = events
        print(f"[{datetime.now()}] [MANUAL_ADD_DEBUG] 'seen' data before writing to .seen_entries.json: {seen}")
        try:
            with open(SEEN_ENTRIES_FILE, 'w') as f:
                json.dump(seen, f, indent=4) # Added indent for readability
            print(f"[{datetime.now()}] [MANUAL_ADD_SUCCESS] Successfully wrote to .seen_entries.json")
        except Exception as e_write:
            print(f"[{datetime.now()}] [MANUAL_ADD_ERROR] Failed to write .seen_entries.json: {e_write}")
    
        messagebox.showinfo('Succes', f'{amount} item(s) toegevoegd op {date_str} voor categorie {cat}.')

        # The background logger thread will pick up the manual entry automatically within the next scan interval (e.g., 5 seconds).
        # No explicit trigger is needed here. Removing it prevents state corruption.

        self.destroy()
# --- End ManualAddApp integration ---

def on_manual_add(icon, item):
    import subprocess
    import sys
    # Launch the same script/exe with --manual-add argument
    subprocess.Popen([sys.executable, sys.argv[0], '--manual-add'])

settings_window_thread = None
settings_window_instance = None

def open_settings(icon, item):
    global settings_window_instance, settings_window_thread
    if settings_window_instance and settings_window_instance.winfo_exists():
        print("[TRAY] Settings window already open. Requesting focus or re-creation logic could go here.")
        # Optionally, bring to front if possible, or just return
        settings_window_instance.focus_force()
        return

    def run_gui():
        global settings_window_instance
        root = tk.Tk()
        root.withdraw() # Hide the main Tk window
        app = SettingsWindow(master=root) # SettingsWindow's protocol WM_DELETE_WINDOW calls its own close_window
        settings_window_instance = app
        print("[TRAY] Settings GUI root.mainloop() starting.")
        try:
            root.mainloop()
        except Exception as e:
            print(f"[TRAY] Exception in Settings GUI root.mainloop(): {e}")
        finally:
            print("[TRAY] Settings GUI root.mainloop() finished.")
            # Ensure instance is cleared if window was closed, allowing re-opening
            if settings_window_instance == app: # Check if it's still the same instance
                settings_window_instance = None

    print("[TRAY] Starting settings_window_thread.")
    settings_window_thread = threading.Thread(target=run_gui, daemon=True)
    settings_window_thread.start()

def on_exit(icon, item):
    global logger_thread, shutdown_event, settings_window_instance, settings_window_thread
    print(f"[{datetime.now()}] [TRAY_EXIT] Exit requested via tray menu.")

    # 1. Request Settings Window to close and wait for its thread
    if settings_window_instance and settings_window_instance.winfo_exists():
        print(f"[{datetime.now()}] [TRAY_EXIT] Requesting settings window to close...")
        try:
            settings_window_instance.request_close_from_external() # This should trigger its WM_DELETE_WINDOW
        except Exception as e_sw_close_req:
            print(f"[{datetime.now()}] [TRAY_EXIT_WARN] Exception requesting settings_window close: {e_sw_close_req}")
        
        if settings_window_thread and settings_window_thread.is_alive():
            print(f"[{datetime.now()}] [TRAY_EXIT] Waiting for settings window thread to join (timeout 5s)...")
            settings_window_thread.join(timeout=5.0)
            if settings_window_thread.is_alive():
                print(f"[{datetime.now()}] [TRAY_EXIT_WARN] Settings window thread did not join in time.")
            else:
                print(f"[{datetime.now()}] [TRAY_EXIT] Settings window thread joined.")
        settings_window_instance = None # Clear reference

    # 2. Signal the logger thread to stop and wait for it
    print(f"[{datetime.now()}] [TRAY_EXIT] Signaling logger thread to stop...")
    shutdown_event.set()
    if logger_thread and logger_thread.is_alive():
        # SCAN_INTERVAL might not be defined here, use a fixed reasonable timeout
        logger_join_timeout = getattr(sys.modules.get('hops_file_logger', {}), 'SCAN_INTERVAL', 5) + 5
        print(f"[{datetime.now()}] [TRAY_EXIT] Waiting for logger thread to join (timeout {logger_join_timeout}s)...")
        logger_thread.join(timeout=float(logger_join_timeout))
        if logger_thread.is_alive():
            print(f"[{datetime.now()}] [TRAY_EXIT_WARN] Logger thread did not join in time.")
        else:
            print(f"[{datetime.now()}] [TRAY_EXIT] Logger thread joined.")

    # 3. Stop the pystray icon
    # This should cause icon.run() in setup_tray to return
    print(f"[{datetime.now()}] [TRAY_EXIT] Stopping pystray icon...")
    if icon:
        icon.stop()
        print(f"[{datetime.now()}] [TRAY_EXIT] pystray icon.stop() called.")
        # Attempt to clear PIL image reference if it was loaded
        if hasattr(icon, 'icon') and icon.icon:
             print(f"[{datetime.now()}] [TRAY_EXIT] Clearing icon.icon (PIL Image) reference.")
             icon.icon = None
    else:
        print(f"[{datetime.now()}] [TRAY_EXIT_WARN] 'icon' object was None in on_exit.")

    # The main thread (in setup_tray) is expected to call sys.exit() after icon.run() returns.
    # If it still hangs, os._exit() will be called there.
    print(f"[{datetime.now()}] [TRAY_EXIT] on_exit sequence finished. Main thread should proceed to exit.")
    # sys.exit(0) removed to allow natural exit

def on_clear_all_events_history(icon, item):
    print(f"[{datetime.now()}] [TRAY_ACTION] 'Verwijder ALLE Events...' selected.")
    try:
        from hops_file_logger import prompt_and_clear_all_events_history # This function will be in hops_file_logger.py
        threading.Thread(target=prompt_and_clear_all_events_history, daemon=True).start()
    except ImportError:
        print(f"[{datetime.now()}] [TRAY_ERROR] Could not import prompt_and_clear_all_events_history from hops_file_logger.")
        messagebox.showerror("Fout", "Functie nog niet geïmplementeerd of verkeerd genoemd in hoofdlogger.")
    except Exception as e:
        print(f"[{datetime.now()}] [TRAY_ERROR] Fout bij poging tot verwijderen alle events: {e}")
        messagebox.showerror("Fout", f"Fout bij starten opschoonactie: {e}")

def setup_tray():
    icon = pystray.Icon("HopsFileLogger")
    icon.icon = create_image()
    menu_items = (
        pystray.MenuItem('Instellingen', open_settings),
        pystray.MenuItem('Handmatig Toevoegen', on_manual_add),
        pystray.MenuItem('Beheer Event Geschiedenis', pystray.Menu(
            pystray.MenuItem('Verwijder ALLE Events...', on_clear_all_events_history),
            # Future: pystray.MenuItem('Archiveer Oude Events...', on_archive_old_events) # Placeholder for potential future archive option
        )),
        pystray.MenuItem('Exit', on_exit)
    )
    icon.menu = pystray.Menu(*menu_items)
    global logger_thread, shutdown_event # Ensure we're assigning to the global
    # Run logger in background thread
    print("Setting up logger thread...")
    logger_thread = threading.Thread(target=run_logger_thread, args=(shutdown_event,), daemon=True)
    logger_thread.start()
    try:
        icon.run()
    finally:
        print(f"[{datetime.now()}] [TRAY_MAIN_EXIT] pystray icon.run() has finished or an error occurred.")
        # Attempt a clean exit first
        print(f"[{datetime.now()}] [TRAY_MAIN_EXIT] Attempting sys.exit(0)...")
        try:
            sys.exit(0)
        except SystemExit:
            print(f"[{datetime.now()}] [TRAY_MAIN_EXIT] sys.exit(0) called, process should be terminating.")
            # If sys.exit() doesn't work quickly, it might be because of stubborn non-daemon threads
            # or problematic atexit handlers. Give it a moment, then force exit.
            time.sleep(2) # Give atexit handlers a brief moment
            print(f"[{datetime.now()}] [TRAY_MAIN_EXIT_FORCE] Process still alive. Forcing exit with os._exit(0).")
            os._exit(0) # Force exit if sys.exit is blocked
        except Exception as e_sys_exit:
            print(f"[{datetime.now()}] [TRAY_MAIN_EXIT_ERROR] Exception during sys.exit: {e_sys_exit}. Forcing os._exit(0).")
            os._exit(0) # Force exit on error

# --- Splash Screen Function ---
def show_splash_screen():
    splash_root = tk.Tk()
    splash_root.overrideredirect(True) # Remove window decorations
    try:
        pil_img = Image.open("logo.png")
        pil_img = pil_img.resize((350, 350), Image.Resampling.LANCZOS)
        splash_img = ImageTk.PhotoImage(pil_img)
        splash_label = tk.Label(splash_root, image=splash_img, bd=0)
        splash_label.image = splash_img # Keep a reference!
        splash_label.pack()

        # Set desired splash screen size
        window_width = 350
        window_height = 350
        splash_root.geometry(f"{window_width}x{window_height}")

        # Center the splash screen
        screen_width = splash_root.winfo_screenwidth()
        screen_height = splash_root.winfo_screenheight()
        position_top = int(screen_height / 2 - window_height / 2)
        position_right = int(screen_width / 2 - window_width / 2)
        # Geometry for size is already set, now just set position
        splash_root.geometry(f"+{position_right}+{position_top}")

        splash_root.after(3000, splash_root.destroy) # Auto-close after 3 seconds
        splash_root.mainloop()
    except tk.TclError:
        print("[WARNING] logo.png not found or could not be loaded. Skipping splash screen.")
        splash_root.destroy()
    except FileNotFoundError:
        print("[WARNING] logo.png not found. Skipping splash screen.")
        splash_root.destroy()

if __name__ == '__main__':
    if '--manual-add' not in sys.argv and '--no-splash' not in sys.argv:
        show_splash_screen()

    if '--manual-add' in sys.argv:
        app = ManualAddApp()
        app.mainloop()
    else:
        # Register signal handlers for graceful shutdown in the main thread
        try:
            signal.signal(signal.SIGINT, tray_signal_handler)
            signal.signal(signal.SIGTERM, tray_signal_handler)
            print("[TRAY_SETUP] Signal handlers registered for SIGINT and SIGTERM.")
        except ValueError as e:
            print(f"[TRAY_SETUP_ERROR] Could not set signal handler: {e}. This might happen if not in main thread or on certain OS configurations.")
        except Exception as e: # Catch any other unexpected errors during signal setup
            print(f"[TRAY_SETUP_ERROR] An unexpected error occurred while setting signal handlers: {e}")
        setup_tray()
