# Auto-Updater Implementation Analysis for BarcodeMatch

## Executive Summary

**Difficulty Rating: Medium (3-5 days for basic implementation, 1-2 weeks for robust production-ready solution)**

An auto-updater is feasible and recommended for this application. The app already has:
- ✅ Version tracking (`build_info.py` with `BUILD_NUMBER = "v2"`)
- ✅ Network connectivity (API server at localhost:5001)
- ✅ PyInstaller executable build system
- ✅ Config management system
- ✅ Centralized file servers (\\WIN-D62BRA7BHMI\Server\ACCURA, BOERE)

---

## Recommended Approach: **Network Share + Launcher Pattern**

### Architecture Overview

```
Network Share (\\WIN-D62BRA7BHMI\Server\Updates\)
├── version.json              # Version metadata
├── BarcodeMatch_v3.exe      # Latest version
├── BarcodeMatch_v2.exe      # Previous version (rollback)
└── changelog.txt            # What's new

Local Installation
├── BarcodeMatchLauncher.exe # Small updater/launcher (50KB)
├── BarcodeMatch.exe         # Main application
├── .update/                 # Temporary update files
└── config.json
```

### How It Works

1. **Startup Check**: Launcher checks network share for `version.json`
2. **Version Compare**: Compare with local `build_info.py` version
3. **Download If Needed**: If newer version exists, download to `.update/` folder
4. **Verify Integrity**: Check SHA256 hash to ensure file isn't corrupted
5. **Safe Replace**:
   - Backup current .exe to `.bak`
   - Move new version from `.update/` to main location
   - Launch new version
6. **Rollback**: If new version crashes on startup, auto-restore `.bak`

---

## Implementation Complexity Breakdown

### **Option 1: Simple Version Check (Easy - 1 day)**

**What it does:**
- Check version.json on network share at startup
- Show notification if update available
- Provide "Download Update" button that opens network location

**Pros:**
- Minimal code (~100 lines)
- No risk of corrupting installation
- User has full control

**Cons:**
- Manual update process
- Users might ignore updates

**Code Snippet:**
```python
def check_for_updates():
    try:
        update_share = r"\\WIN-D62BRA7BHMI\Server\Updates\version.json"
        with open(update_share, 'r') as f:
            remote_version = json.load(f)

        local_version = build_info.BUILD_NUMBER

        if remote_version['version'] > local_version:
            show_update_notification(remote_version['version'])
    except:
        pass  # Silently fail if network unavailable
```

---

### **Option 2: Automated Download + Manual Install (Medium - 2-3 days)**

**What it does:**
- Automatically download new version to temp folder
- Show progress bar during download
- Prompt user to install (closes app, runs installer)
- Batch script handles the actual file replacement

**Pros:**
- Streamlined user experience
- Progress indication
- Safe file replacement using batch script

**Cons:**
- Requires app restart
- User must confirm installation

**Components:**
1. **Version Checker Module** (`updater.py`)
2. **Download Manager** (with progress callback)
3. **Update Batch Script** (`update.bat`)

**Update Batch Script:**
```batch
@echo off
:: Wait for main app to close
timeout /t 2 /nobreak

:: Backup current version
copy /Y "BarcodeMatch.exe" "BarcodeMatch.exe.bak"

:: Install new version
move /Y ".update\BarcodeMatch_new.exe" "BarcodeMatch.exe"

:: Restart app
start "" "BarcodeMatch.exe"
```

---

### **Option 3: Silent Background Updates (Complex - 5-7 days)**

**What it does:**
- Download updates in background while app runs
- Apply update on next startup (seamless)
- Automatic rollback if new version fails
- Delta updates (only download changed bytes)

**Pros:**
- Best user experience
- Minimal disruption
- Automatic rollback

**Cons:**
- More complex implementation
- Need sophisticated error handling
- Requires delta update system or full downloads

**Components:**
1. **Background Downloader Thread**
2. **Launcher Process** (separate small .exe)
3. **Health Check System** (detect if new version crashes)
4. **Rollback Manager**

---

## Detailed Implementation Plan (Recommended: Option 2)

### Phase 1: Infrastructure Setup (Day 1)

**1. Create Update Server Structure**
```bash
\\WIN-D62BRA7BHMI\Server\Updates\
├── version.json
├── current\
│   ├── BarcodeMatch.exe
│   └── BarcodeMatch_32bit.exe
└── archive\
    ├── BarcodeMatch_v2.exe
    └── BarcodeMatch_v1.exe
```

**2. Create version.json Format**
```json
{
  "version": "v3",
  "release_date": "2025-11-15",
  "exe_path_64bit": "current/BarcodeMatch.exe",
  "exe_path_32bit": "current/BarcodeMatch_32bit.exe",
  "sha256_64bit": "abc123...",
  "sha256_32bit": "def456...",
  "changelog": "- Fixed session ID mismatch\n- Added dynamic columns\n- Improved error handling",
  "mandatory": false,
  "min_version": "v1"
}
```

**3. Update build_info.py**
```python
# Enhanced version tracking
VERSION = "v3"
BUILD_DATE = "2025-11-15"
BUILD_NUMBER = VERSION  # Keep for backward compatibility

def get_version():
    return VERSION

def get_build_date():
    return BUILD_DATE
```

---

### Phase 2: Updater Module (Day 2)

**File: `updater.py`**
```python
import os
import json
import hashlib
import shutil
import threading
import requests
from pathlib import Path
from build_info import VERSION

class UpdateManager:
    def __init__(self, update_share=r"\\WIN-D62BRA7BHMI\Server\Updates"):
        self.update_share = Path(update_share)
        self.local_update_dir = Path(".update")
        self.current_version = VERSION
        self.is_32bit = sys.maxsize <= 2**32

    def check_for_updates(self):
        """Check if update is available. Returns version info or None."""
        try:
            version_file = self.update_share / "version.json"
            if not version_file.exists():
                return None

            with open(version_file, 'r') as f:
                remote_info = json.load(f)

            if self._compare_versions(remote_info['version'], self.current_version) > 0:
                return remote_info

            return None
        except Exception as e:
            print(f"Update check failed: {e}")
            return None

    def _compare_versions(self, v1, v2):
        """Compare version strings. Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal."""
        # Simple comparison - enhance for semantic versioning if needed
        v1_num = int(v1.replace('v', ''))
        v2_num = int(v2.replace('v', ''))
        return (v1_num > v2_num) - (v1_num < v2_num)

    def download_update(self, version_info, progress_callback=None):
        """Download update file with progress tracking."""
        try:
            # Create update directory
            self.local_update_dir.mkdir(exist_ok=True)

            # Determine which exe to download
            exe_key = 'exe_path_32bit' if self.is_32bit else 'exe_path_64bit'
            sha_key = 'sha256_32bit' if self.is_32bit else 'sha256_64bit'

            remote_exe = self.update_share / version_info[exe_key]
            local_exe = self.local_update_dir / "BarcodeMatch_new.exe"

            # Copy file with progress
            total_size = remote_exe.stat().st_size
            copied = 0

            with open(remote_exe, 'rb') as src:
                with open(local_exe, 'wb') as dst:
                    while True:
                        chunk = src.read(1024 * 1024)  # 1MB chunks
                        if not chunk:
                            break
                        dst.write(chunk)
                        copied += len(chunk)

                        if progress_callback:
                            progress_callback(copied, total_size)

            # Verify hash
            if not self._verify_hash(local_exe, version_info[sha_key]):
                raise Exception("Hash verification failed - file may be corrupted")

            return local_exe

        except Exception as e:
            print(f"Download failed: {e}")
            # Clean up partial download
            if local_exe.exists():
                local_exe.unlink()
            raise

    def _verify_hash(self, file_path, expected_hash):
        """Verify file integrity using SHA256."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest() == expected_hash

    def install_update(self):
        """Create batch script and trigger update installation."""
        batch_script = """@echo off
echo Updating BarcodeMatch...
timeout /t 2 /nobreak > nul

:: Backup current version
if exist "BarcodeMatch.exe" (
    echo Creating backup...
    copy /Y "BarcodeMatch.exe" "BarcodeMatch.exe.bak" > nul
)

:: Install new version
echo Installing update...
if exist ".update\\BarcodeMatch_new.exe" (
    move /Y ".update\\BarcodeMatch_new.exe" "BarcodeMatch.exe" > nul
)

:: Cleanup
rmdir /Q ".update" 2>nul

:: Restart application
echo Starting BarcodeMatch...
start "" "BarcodeMatch.exe"
exit
"""

        # Write batch script
        batch_file = Path("update_install.bat")
        with open(batch_file, 'w') as f:
            f.write(batch_script)

        # Execute batch script and exit application
        os.startfile(str(batch_file))
        sys.exit(0)
```

---

### Phase 3: UI Integration (Day 3)

**Add to `gui/app.py` on startup:**
```python
def check_for_updates_on_startup(self):
    """Check for updates in background thread."""
    def check_updates():
        try:
            from updater import UpdateManager
            updater = UpdateManager()

            update_info = updater.check_for_updates()
            if update_info:
                # Show update dialog on main thread
                self.root.after(100, lambda: self._show_update_dialog(update_info, updater))
        except:
            pass  # Silently fail

    threading.Thread(target=check_updates, daemon=True).start()

def _show_update_dialog(self, update_info, updater):
    """Show update notification dialog."""
    from tkinter import messagebox

    message = f"Een nieuwe versie is beschikbaar!\n\n"
    message += f"Huidige versie: {updater.current_version}\n"
    message += f"Nieuwe versie: {update_info['version']}\n\n"
    message += f"Wijzigingen:\n{update_info['changelog']}\n\n"
    message += "Wilt u nu updaten?"

    if messagebox.askyesno("Update Beschikbaar", message):
        self._download_and_install_update(update_info, updater)

def _download_and_install_update(self, update_info, updater):
    """Download and install update with progress dialog."""
    # Create progress window
    progress_window = tk.Toplevel(self.root)
    progress_window.title("Update Downloaden")
    progress_window.geometry("400x150")

    tk.Label(progress_window, text="Update wordt gedownload...").pack(pady=10)

    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_window,
                                   variable=progress_var,
                                   maximum=100)
    progress_bar.pack(pady=10, padx=20, fill='x')

    status_label = tk.Label(progress_window, text="0%")
    status_label.pack()

    def update_progress(current, total):
        percent = (current / total) * 100
        progress_var.set(percent)
        status_label.config(text=f"{percent:.1f}%")
        progress_window.update()

    def download_thread():
        try:
            updater.download_update(update_info, update_progress)
            progress_window.destroy()

            # Confirm installation
            if messagebox.askyesno("Update Gereed",
                                  "Download voltooid. Applicatie zal herstarten om te updaten."):
                updater.install_update()
        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("Update Fout", f"Update mislukt: {e}")

    threading.Thread(target=download_thread, daemon=True).start()
```

---

### Phase 4: Build Process Integration (Day 4)

**Update `build_exe.py` to generate version.json:**
```python
def create_version_json(self, exe_path):
    """Create version.json for update server."""
    import hashlib

    # Calculate SHA256
    sha256 = hashlib.sha256()
    with open(exe_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)

    version_info = {
        "version": self.version,
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "exe_path_64bit": f"current/BarcodeMatch.exe",
        "exe_path_32bit": f"current/BarcodeMatch_32bit.exe",
        f"sha256_{'32bit' if self.is_32bit else '64bit'}": sha256.hexdigest(),
        "changelog": "Enter changelog here",
        "mandatory": False,
        "min_version": "v1"
    }

    version_file = self.dist_dir / "version.json"
    with open(version_file, 'w') as f:
        json.dump(version_info, f, indent=2)

    print(f"Version info created: {version_file}")
```

---

### Phase 5: Testing & Rollback (Day 5)

**Automated Rollback System:**
```python
# Add to main.py startup
def check_version_health():
    """Check if this version started successfully."""
    health_file = Path(".health_check")

    if health_file.exists():
        # Previous version failed to start - rollback!
        print("Health check failed - rolling back to previous version")

        backup_exe = Path("BarcodeMatch.exe.bak")
        if backup_exe.exists():
            shutil.copy(backup_exe, "BarcodeMatch.exe")
            messagebox.showwarning("Update Failed",
                                  "New version failed to start. Restored previous version.")
    else:
        # Create health check file - will be deleted on successful startup
        health_file.touch()

        # Start watchdog timer - delete health file after 30 seconds of successful operation
        def clear_health_check():
            time.sleep(30)
            if health_file.exists():
                health_file.unlink()

        threading.Thread(target=clear_health_check, daemon=True).start()
```

---

## Security Considerations

1. **File Integrity**: SHA256 hashing prevents corrupted downloads
2. **Network Share Security**: Use Windows ACLs to restrict write access to updates folder
3. **Code Signing** (Optional): Sign .exe files for additional trust
4. **Backup System**: Always keep previous version for rollback
5. **Update Source Validation**: Only accept updates from known network share path

---

## Alternative Approaches

### **GitHub Releases Based**
- **Pros**: Free hosting, version control integration, automatic changelog
- **Cons**: Requires internet access, GitHub API rate limits
- **Best for**: Open-source or cloud-connected apps

### **Custom Update Server**
- **Pros**: Full control, can track update analytics
- **Cons**: Need to host/maintain server, more complex
- **Best for**: Large deployments with dedicated IT

### **MSI Installer with Auto-Update**
- **Pros**: Professional installer, Windows Update integration possible
- **Cons**: Complex setup, requires admin rights
- **Best for**: Enterprise deployments

---

## Estimated Timeline

| Phase | Description | Time | Complexity |
|-------|-------------|------|------------|
| 1 | Infrastructure setup | 4 hours | Easy |
| 2 | Updater module | 8 hours | Medium |
| 3 | UI integration | 6 hours | Medium |
| 4 | Build integration | 4 hours | Easy |
| 5 | Testing & rollback | 6 hours | Medium |
| 6 | Documentation | 2 hours | Easy |
| **Total** | | **30 hours** | **Medium** |

**Additional time for robust production system: +10-15 hours**

---

## Maintenance Overhead

- **Per Release**: 15 minutes (build, hash, upload to network share)
- **Version JSON Update**: 5 minutes
- **Testing**: 30 minutes (test update on clean install)

---

## Recommendation

**Implement Option 2 (Automated Download + Manual Install)** because:

1. ✅ Balances ease of use with safety
2. ✅ Leverages existing network infrastructure (file server)
3. ✅ Low maintenance overhead
4. ✅ Rollback capability built-in
5. ✅ No external dependencies or cloud services needed
6. ✅ Works offline (network share only, no internet required)
7. ✅ Users maintain control over when to update

---

## Next Steps

1. **Decision**: Choose update approach (recommend Option 2)
2. **Setup**: Create update directory structure on network share
3. **Implement**: Add updater.py module
4. **Integrate**: Add update check to app startup
5. **Test**: Test on development machine with mock updates
6. **Deploy**: Roll out to production with v3 as first auto-updatable version

---

## Questions to Consider

1. Should updates be **mandatory** after a certain version?
2. How often should app check for updates? (Startup only, daily, weekly?)
3. Should users be able to **postpone** updates?
4. Do you want **silent** background downloads or only on-demand?
5. Should rollback be **automatic** or require user confirmation?

---

*Generated: 2025-11-14*
*For: BarcodeMatch Application*
*Current Version: v2*
