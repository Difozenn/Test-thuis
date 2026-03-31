"""
Session Manager - Handles persistent session storage for crash/shutdown recovery
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path

class SessionManager:
    """Manages session persistence to handle unexpected shutdowns"""

    def __init__(self):
        # Store session file in user's app data directory
        self.session_dir = Path(os.environ.get('APPDATA', '.')) / 'BarcodeMatch'
        self.session_dir.mkdir(exist_ok=True)
        self.session_file = self.session_dir / 'active_session.json'
        self.lock_file = self.session_dir / 'session.lock'

    def save_session(self, session_data):
        """Save session data to file for recovery after crash/shutdown"""
        try:
            # Add timestamp
            session_data['last_saved'] = datetime.now().isoformat()

            # Write to temp file first, then rename (atomic operation)
            temp_file = self.session_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(session_data, f, indent=2)

            # Atomic rename
            temp_file.replace(self.session_file)

            print(f"[SESSION_MANAGER] Saved session to {self.session_file}")
            return True

        except Exception as e:
            print(f"[SESSION_MANAGER ERROR] Failed to save session: {e}")
            return False

    def load_session(self):
        """Load saved session data if it exists"""
        try:
            if not self.session_file.exists():
                return None

            with open(self.session_file, 'r') as f:
                data = json.load(f)

            # Check if session is recent (within last 24 hours)
            if 'last_saved' in data:
                last_saved = datetime.fromisoformat(data['last_saved'])
                age_hours = (datetime.now() - last_saved).total_seconds() / 3600

                if age_hours > 24:
                    print(f"[SESSION_MANAGER] Session too old ({age_hours:.1f} hours), ignoring")
                    self.clear_session()
                    return None

            print(f"[SESSION_MANAGER] Loaded session from {self.session_file}")
            return data

        except Exception as e:
            print(f"[SESSION_MANAGER ERROR] Failed to load session: {e}")
            return None

    def clear_session(self):
        """Clear saved session data"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                print(f"[SESSION_MANAGER] Cleared session file")

            if self.lock_file.exists():
                self.lock_file.unlink()

        except Exception as e:
            print(f"[SESSION_MANAGER ERROR] Failed to clear session: {e}")

    def create_lock(self):
        """Create a lock file to detect crashes"""
        try:
            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))
            return True
        except:
            return False

    def check_crash_recovery(self):
        """Check if we need to recover from a crash"""
        try:
            # If lock file exists, previous instance didn't shut down cleanly
            if self.lock_file.exists():
                print("[SESSION_MANAGER] Lock file found - previous instance may have crashed")

                # Check if PID in lock file is still running
                try:
                    with open(self.lock_file, 'r') as f:
                        old_pid = int(f.read().strip())

                    # Check if process is still running
                    try:
                        import psutil
                        if not any(p.pid == old_pid for p in psutil.process_iter()):
                            print(f"[SESSION_MANAGER] Previous process {old_pid} not running - crash detected")
                            return True
                    except ImportError:
                        # If psutil not available, check using os methods
                        try:
                            # Windows: try to open the process
                            import ctypes
                            kernel32 = ctypes.windll.kernel32
                            handle = kernel32.OpenProcess(0x1000, False, old_pid)  # PROCESS_QUERY_LIMITED_INFORMATION
                            if handle:
                                kernel32.CloseHandle(handle)
                                return False  # Process exists
                            else:
                                print(f"[SESSION_MANAGER] Previous process {old_pid} not running - crash detected")
                                return True
                        except:
                            # Fallback: assume crash if we can't check
                            print(f"[SESSION_MANAGER] Cannot verify process {old_pid} - assuming crash")
                            return True
                except:
                    # If we can't check, assume crash
                    return True

            return False

        except Exception as e:
            print(f"[SESSION_MANAGER ERROR] Failed to check crash recovery: {e}")
            return False

    def recover_session(self, scanner_panel):
        """Recover a session after crash/shutdown"""
        try:
            session_data = self.load_session()
            if not session_data:
                return False

            print(f"[SESSION_MANAGER] Recovering session: {session_data.get('session_id')}")

            # Send pause event to API if session was active
            if session_data.get('session_id') and not session_data.get('paused', False):
                print("[SESSION_MANAGER] Session was active at shutdown - sending pause event")

                # Import here to avoid circular dependency
                import requests
                from config_utils import get_config_path

                # Create session that bypasses system/WAMP proxy
                http_session = requests.Session()
                http_session.trust_env = False
                http_session.proxies = {"http": "", "https": ""}

                config_path = get_config_path()
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)

                    api_url = config.get('api_url', '')
                    if api_url and api_url.startswith('http'):
                        try:
                            # Send pause event with timestamp from when it was saved
                            pause_data = {
                                'session_id': session_data['session_id'],
                                'timestamp': session_data['last_saved'],
                                'user': session_data.get('user', 'UNKNOWN'),
                                'project': session_data.get('project', 'Unknown'),
                                'crash_recovery': True  # Flag to indicate this is a recovery
                            }

                            pause_url = api_url.replace('/log', '/session/pause')
                            response = http_session.post(pause_url, json=pause_data, timeout=3)

                            if response.ok:
                                print("[SESSION_MANAGER] Successfully sent crash recovery pause event")

                                # Also log a CRASH_RECOVERY event for visibility
                                log_data = {
                                    'event': 'CRASH_RECOVERY',
                                    'user': session_data.get('user', 'UNKNOWN'),
                                    'project': session_data.get('project', 'Unknown'),
                                    'session_id': session_data['session_id'],
                                    'details': f'Session recovered after unexpected shutdown',
                                    'status': 'PAUZE',
                                    'timestamp': datetime.now().isoformat()
                                }
                                http_session.post(api_url, json=log_data, timeout=3)

                        except Exception as e:
                            print(f"[SESSION_MANAGER ERROR] Failed to send recovery pause: {e}")

            # Clear the saved session
            self.clear_session()
            return True

        except Exception as e:
            print(f"[SESSION_MANAGER ERROR] Failed to recover session: {e}")
            return False