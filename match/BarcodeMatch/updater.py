"""
Auto-updater module for BarcodeMatch.

Checks for updates on a network share and handles download + restart.
"""

import os
import sys
import json
import shutil
import hashlib
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime

# Get local version
try:
    from build_info import BUILD_NUMBER
except ImportError:
    BUILD_NUMBER = "v0"


def _update_log(msg):
    """Log to both console and update_monitor.log file."""
    line = f"[UPDATE MONITOR] {msg}"
    print(line)
    try:
        if getattr(sys, 'frozen', False):
            log_dir = os.path.join(os.path.dirname(sys.executable), 'logs')
        else:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, 'update_monitor.log'), 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}\n")
    except Exception:
        pass


def get_app_dir():
    """Get the directory where the application is running from."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def get_exe_path():
    """Get the path to the current executable."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        return None  # Running as script, no exe to update


def parse_version(version_str):
    """Parse version string to comparable tuple. Handles 'v2', 'v2.1', 'v2.1.3' etc."""
    # Remove 'v' prefix if present
    v = version_str.lower().strip()
    if v.startswith('v'):
        v = v[1:]

    # Split by dots and convert to integers
    parts = []
    for part in v.split('.'):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)

    # Pad to at least 3 parts for consistent comparison
    while len(parts) < 3:
        parts.append(0)

    return tuple(parts)


def is_newer_version(remote_version, local_version):
    """Check if remote version is newer than local version."""
    return parse_version(remote_version) > parse_version(local_version)


def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


class UpdateChecker:
    """Handles checking for updates and managing the update process."""

    def __init__(self, update_server_path, callback=None):
        """
        Initialize the update checker.

        Args:
            update_server_path: Network path to update server (e.g., \\\\SERVER\\Updates\\BarcodeMatch)
            callback: Function to call when update is available. Receives (version, changelog) args.
        """
        self.update_server_path = update_server_path
        self.callback = callback
        self.available_update = None
        self._check_thread = None
        self._download_thread = None
        self._is_downloading = False
        self.download_progress = 0

    def get_version_info(self):
        """
        Read version.json from the update server.

        Expected format:
        {
            "version": "v3",
            "exe_name": "BarcodeMatch_32bit.exe",
            "sha256": "abc123...",
            "changelog": "- Fixed bugs\n- Added features",
            "mandatory": false
        }
        """
        if not self.update_server_path:
            return None

        version_file = os.path.join(self.update_server_path, "version.json")

        try:
            if os.path.exists(version_file):
                with open(version_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            _update_log(f" Error reading version.json: {e}")

        return None

    def check_for_updates(self):
        """
        Check if an update is available.

        Returns:
            dict with update info if available, None otherwise
        """
        version_info = self.get_version_info()

        if not version_info:
            _update_log(" No version info found on server")
            return None

        remote_version = version_info.get('version', 'v0')
        local_version = BUILD_NUMBER

        _update_log(f" Local version: {local_version}, Remote version: {remote_version}")

        if is_newer_version(remote_version, local_version):
            self.available_update = version_info
            _update_log(f" Update available: {remote_version}")
            return version_info
        else:
            _update_log(" No update available")
            return None

    def check_for_updates_async(self):
        """Check for updates in a background thread."""
        def check():
            try:
                update_info = self.check_for_updates()
                if update_info and self.callback:
                    self.callback(update_info.get('version', '?'), update_info.get('changelog', ''))
            except Exception as e:
                _update_log(f" Error checking for updates: {e}")

        self._check_thread = threading.Thread(target=check, daemon=True)
        self._check_thread.start()

    def download_and_install(self, progress_callback=None):
        """
        Download the update and prepare for installation.

        Args:
            progress_callback: Function to call with progress (0-100)

        Returns:
            True if download successful and ready to install, False otherwise
        """
        if not self.available_update:
            _update_log(" No update available to download")
            return False

        if self._is_downloading:
            _update_log(" Download already in progress")
            return False

        self._is_downloading = True
        self.download_progress = 0

        try:
            exe_name = self.available_update.get('exe_name', 'BarcodeMatch_32bit.exe')
            expected_hash = self.available_update.get('sha256', '')

            # Source path on network share
            source_path = os.path.join(self.update_server_path, exe_name)

            if not os.path.exists(source_path):
                _update_log(f" Update file not found: {source_path}")
                return False

            # Destination paths
            app_dir = get_app_dir()
            update_dir = os.path.join(app_dir, '.update')
            archive_dir = os.path.join(app_dir, 'archief')

            # Create directories if needed
            os.makedirs(update_dir, exist_ok=True)
            os.makedirs(archive_dir, exist_ok=True)

            # Download path
            download_path = os.path.join(update_dir, exe_name)

            # Copy file with progress
            source_size = os.path.getsize(source_path)
            copied = 0

            _update_log(f" Downloading {exe_name} ({source_size / 1024 / 1024:.1f} MB)...")

            with open(source_path, 'rb') as src, open(download_path, 'wb') as dst:
                while True:
                    chunk = src.read(65536)  # 64KB chunks
                    if not chunk:
                        break
                    dst.write(chunk)
                    copied += len(chunk)
                    self.download_progress = int((copied / source_size) * 100)
                    if progress_callback:
                        progress_callback(self.download_progress)

            _update_log(f" Download complete: {download_path}")

            # Verify hash if provided
            if expected_hash:
                actual_hash = calculate_sha256(download_path)
                if actual_hash.lower() != expected_hash.lower():
                    _update_log(f" Hash mismatch! Expected: {expected_hash}, Got: {actual_hash}")
                    os.remove(download_path)
                    return False
                _update_log(" Hash verified successfully")

            # Create the update batch script
            self._create_update_script(download_path, archive_dir)

            return True

        except Exception as e:
            _update_log(f" Download error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self._is_downloading = False

    def download_and_install_async(self, progress_callback=None, completion_callback=None):
        """Download and install in a background thread."""
        def download():
            success = self.download_and_install(progress_callback)
            if completion_callback:
                completion_callback(success)

        self._download_thread = threading.Thread(target=download, daemon=True)
        self._download_thread.start()

    def _create_update_script(self, new_exe_path, archive_dir):
        """
        Create a batch script that will:
        1. Wait for the app to close
        2. Move old exe to archive
        3. Copy new exe to app location
        4. Restart the app
        """
        app_dir = get_app_dir()
        current_exe = get_exe_path()

        if not current_exe:
            _update_log(" Not running as exe, cannot create update script")
            return

        exe_name = os.path.basename(current_exe)
        new_exe_name = os.path.basename(new_exe_path)
        version = self.available_update.get('version', 'unknown')

        # Archive filename with version
        archive_name = f"{os.path.splitext(exe_name)[0]}_{BUILD_NUMBER}.exe"
        archive_path = os.path.join(archive_dir, archive_name)

        script_path = os.path.join(app_dir, '.update', 'update.bat')

        # Create batch script
        script_content = f'''@echo off
chcp 65001 >nul
echo BarcodeMatch Update wordt geinstalleerd...
echo.

REM Wait for the application to fully close
timeout /t 3 /nobreak >nul

REM Move old exe to archive
echo Oude versie archiveren...
if exist "{current_exe}" (
    move /Y "{current_exe}" "{archive_path}"
    if errorlevel 1 (
        echo FOUT: Kon oude versie niet archiveren. Probeer opnieuw.
        pause
        exit /b 1
    )
)

REM Copy new exe
echo Nieuwe versie installeren...
copy /Y "{new_exe_path}" "{current_exe}"
if errorlevel 1 (
    echo FOUT: Kon nieuwe versie niet installeren.
    echo Oude versie terugzetten...
    move /Y "{archive_path}" "{current_exe}"
    pause
    exit /b 1
)

REM Cleanup
echo Opruimen...
del /Q "{new_exe_path}" 2>nul

REM Restart app
echo Update voltooid! Applicatie wordt herstart...
timeout /t 2 /nobreak >nul
start "" "{current_exe}"

REM Delete this script
(goto) 2>nul & del "%~f0"
'''

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        _update_log(f" Update script created: {script_path}")

    def execute_update(self):
        """
        Execute the update by running the batch script and closing the app.
        This should be called after download_and_install() returns True.
        """
        app_dir = get_app_dir()
        script_path = os.path.join(app_dir, '.update', 'update.bat')

        if not os.path.exists(script_path):
            _update_log(" Update script not found")
            return False

        try:
            # Start the batch script in a new window
            # Using CREATE_NEW_CONSOLE flag to ensure it survives app close
            if sys.platform == 'win32':
                subprocess.Popen(
                    ['cmd', '/c', script_path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=app_dir
                )
            else:
                subprocess.Popen(['sh', script_path], cwd=app_dir)

            _update_log(" Update script started, application will close...")
            return True

        except Exception as e:
            _update_log(f" Error executing update: {e}")
            return False


# Convenience function for simple usage
def check_for_updates(update_server_path, callback=None):
    """
    Simple function to check for updates.

    Args:
        update_server_path: Network path to update server
        callback: Function called if update available, receives (version, changelog)

    Returns:
        UpdateChecker instance
    """
    checker = UpdateChecker(update_server_path, callback)
    checker.check_for_updates_async()
    return checker
