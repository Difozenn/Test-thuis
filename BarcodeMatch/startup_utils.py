"""
Startup utilities for BarcodeMatch application.
Provides global functions for improved startup management and background initialization.
"""

import threading
import time
import tkinter as tk
from typing import Callable, Optional


class StartupManager:
    """Manages application startup with background threading and progress tracking"""
    
    def __init__(self):
        self.progress_callbacks = []
        self.startup_tasks = []
        self.completed_tasks = []
        self.failed_tasks = []
        
    def add_progress_callback(self, callback: Callable[[str], None]):
        """Add a callback for progress updates"""
        self.progress_callbacks.append(callback)
        
    def update_progress(self, message: str):
        """Update progress for all registered callbacks"""
        print(f'[STARTUP] {message}')
        for callback in self.progress_callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f'[STARTUP ERROR] Progress callback failed: {e}')
    
    def add_startup_task(self, name: str, task_func: Callable, *args, **kwargs):
        """Add a startup task to be executed in background"""
        self.startup_tasks.append({
            'name': name,
            'func': task_func,
            'args': args,
            'kwargs': kwargs
        })
    
    def execute_startup_tasks(self, on_complete: Optional[Callable] = None):
        """Execute all startup tasks in background thread"""
        def run_tasks():
            try:
                total_tasks = len(self.startup_tasks)
                for i, task in enumerate(self.startup_tasks):
                    try:
                        self.update_progress(f"{task['name']} ({i+1}/{total_tasks})")
                        result = task['func'](*task['args'], **task['kwargs'])
                        self.completed_tasks.append({
                            'name': task['name'],
                            'result': result
                        })
                    except Exception as e:
                        print(f"[STARTUP ERROR] Task '{task['name']}' failed: {e}")
                        self.failed_tasks.append({
                            'name': task['name'],
                            'error': str(e)
                        })
                
                self.update_progress("Opstarten voltooid!")
                
                if on_complete:
                    on_complete(self.completed_tasks, self.failed_tasks)
                    
            except Exception as e:
                print(f'[STARTUP ERROR] Critical startup failure: {e}')
                self.update_progress("Kritieke fout bij opstarten!")
                
        threading.Thread(target=run_tasks, daemon=True).start()


def create_startup_manager() -> StartupManager:
    """Create a new startup manager instance"""
    return StartupManager()


def safe_ui_update(root: tk.Tk, update_func: Callable, *args, **kwargs):
    """Safely schedule UI updates from background threads"""
    def safe_update():
        try:
            update_func(*args, **kwargs)
        except tk.TclError as e:
            print(f'[STARTUP] UI update failed (widget destroyed?): {e}')
        except Exception as e:
            print(f'[STARTUP ERROR] UI update failed: {e}')
    
    try:
        root.after(0, safe_update)
    except tk.TclError:
        print('[STARTUP] Cannot schedule UI update - root window destroyed')


def wait_for_condition(condition_func: Callable[[], bool], 
                      timeout: float = 10.0, 
                      check_interval: float = 0.1) -> bool:
    """Wait for a condition to become true with timeout"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(check_interval)
    return False


def background_task(func: Callable):
    """Decorator to run a function in background thread"""
    def wrapper(*args, **kwargs):
        def run():
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f'[BACKGROUND TASK ERROR] {func.__name__} failed: {e}')
                raise
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread
    
    return wrapper
