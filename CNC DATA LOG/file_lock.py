import os
import time

class FileLock:
    """
    A simple file-based lock for synchronizing access to a shared resource
    across different processes.
    """
    def __init__(self, lock_file, timeout=10, delay=0.05):
        """
        Args:
            lock_file (str): The path to the lock file.
            timeout (int): The maximum time in seconds to wait for the lock.
            delay (float): The time in seconds to wait between lock acquisition attempts.
        """
        self.lock_file = lock_file
        self.timeout = timeout
        self.delay = delay
        self.is_locked = False

    def acquire(self):
        """Acquire the lock."""
        start_time = time.time()
        while True:
            try:
                # Attempt to create the lock file in exclusive mode.
                # This is an atomic operation on most OSes.
                self.fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                self.is_locked = True
                break
            except FileExistsError:
                if time.time() - start_time >= self.timeout:
                    raise TimeoutError(f"Could not acquire lock on {self.lock_file} within {self.timeout} seconds.")
                time.sleep(self.delay)

    def release(self):
        """Release the lock."""
        if self.is_locked:
            os.close(self.fd)
            os.remove(self.lock_file)
            self.is_locked = False

    def __enter__(self):
        """Context manager entry point (for 'with' statements)."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.release()
