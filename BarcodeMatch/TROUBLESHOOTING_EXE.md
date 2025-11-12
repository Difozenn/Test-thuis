# BarcodeMatch EXE Troubleshooting Guide

## Problem: EXE doesn't start (nothing happens when double-clicking)

This guide helps diagnose why `BarcodeMatch_32bit.exe` works on some PCs but not others.

---

## Quick Diagnostics

### Step 1: Check for Error Log
After trying to run the exe, check if a file called `barcodematch_error.log` was created in the same folder as the exe. If it exists, open it to see the error details.

### Step 2: Build and Run DEBUG Version
The debug version shows a console window with error messages:

```powershell
# Build the debug version (with console window)
pyinstaller BarcodeMatch_32bit_debug.spec

# Run it - you'll see error messages in the console
.\dist\BarcodeMatch_32bit_DEBUG.exe
```

---

## Common Causes & Solutions

### 1. Missing Visual C++ Redistributables ⭐ MOST COMMON
**Symptoms:** Exe does nothing, no error message

**Solution:** Install Microsoft Visual C++ Redistributables on the problem PC:
- Download from: https://aka.ms/vs/17/release/vc_redist.x86.exe (for 32-bit)
- Or search for "Microsoft Visual C++ Redistributable" on Microsoft's website
- Install both 2015-2022 versions (x86 for 32-bit)

**Why:** Python and many libraries (numpy, pandas) require these runtime libraries.

---

### 2. Antivirus/Windows Defender Blocking
**Symptoms:** Exe does nothing, or briefly appears in Task Manager then disappears

**Solution:**
1. Check Windows Security → Virus & threat protection → Protection history
2. Look for blocked items related to BarcodeMatch
3. Add exception: Windows Security → Virus & threat protection → Manage settings → Exclusions
4. Add the entire BarcodeMatch folder as an exclusion

**Alternative:** Try running as Administrator (right-click exe → Run as administrator)

---

### 3. Missing DLL Dependencies
**Symptoms:** Error about missing DLL files

**Solution:**
1. Use Dependency Walker to check missing DLLs: https://www.dependencywalker.com/
2. Or use `dumpbin /dependents BarcodeMatch_32bit.exe` (requires Visual Studio)
3. Install missing system DLLs

**Common missing DLLs:**
- `VCRUNTIME140.dll` → Install VC++ Redistributable
- `MSVCP140.dll` → Install VC++ Redistributable
- `api-ms-win-*.dll` → Update Windows

---

### 4. Corrupted/Incomplete EXE File
**Symptoms:** File size is different on working vs non-working PC

**Solution:**
1. Check file size - should be ~50-100 MB
2. Re-copy the exe (use USB drive, not network share)
3. Verify file hash matches:
   ```powershell
   Get-FileHash .\BarcodeMatch_32bit.exe -Algorithm SHA256
   ```

---

### 5. Windows Version Incompatibility
**Symptoms:** Exe works on Windows 10 but not Windows 7/8

**Solution:**
- Ensure Windows is updated to latest version
- Windows 7 requires Service Pack 1 + Platform Update
- Consider upgrading to Windows 10/11

---

### 6. 32-bit vs 64-bit Windows Issue
**Symptoms:** 32-bit exe doesn't run on 64-bit Windows

**Solution:**
- 32-bit exe SHOULD work on 64-bit Windows
- If not, try building a 64-bit version instead
- Check if Windows has 32-bit support enabled

---

## Detailed Diagnostics

### Check System Information
Run this on the problem PC:

```powershell
# System info
systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Type"

# Check installed Visual C++ versions
Get-ItemProperty HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* | 
  Where-Object { $_.DisplayName -like "*Visual C++*" } | 
  Select-Object DisplayName, DisplayVersion
```

### Test Python Dependencies Manually
If you have Python installed on the problem PC:

```powershell
python -c "import tkinter; print('tkinter OK')"
python -c "import numpy; print('numpy OK')"
python -c "import pandas; print('pandas OK')"
python -c "import PIL; print('PIL OK')"
```

### Run with Verbose Logging
Set environment variable before running:

```powershell
$env:BARCODEMATCH_DEBUG="true"
.\BarcodeMatch_32bit.exe
```

---

## Building Solutions

### Rebuild with Better Compatibility
Edit `BarcodeMatch_32bit.spec` and change:

```python
# Disable UPX compression (can cause issues)
upx=False,

# Or exclude more files from compression
upx_exclude=['*.dll', '*.pyd', 'python*.dll', 'vcruntime*.dll'],
```

Then rebuild:
```powershell
pyinstaller BarcodeMatch_32bit.spec --clean
```

### Include VC++ Runtime in EXE
Add to spec file `binaries` section:

```python
# Add VC++ runtime DLLs
import glob
vc_redist_path = r'C:\Windows\System32'  # Adjust path
vc_dlls = [
    (os.path.join(vc_redist_path, 'vcruntime140.dll'), '.'),
    (os.path.join(vc_redist_path, 'msvcp140.dll'), '.'),
]
binaries.extend(vc_dlls)
```

---

## Quick Test Checklist for Problem PC

- [ ] Check `barcodematch_error.log` file
- [ ] Run DEBUG version to see console errors
- [ ] Install VC++ Redistributable (x86)
- [ ] Check Windows Defender/Antivirus logs
- [ ] Verify exe file size matches working PC
- [ ] Try running as Administrator
- [ ] Check Windows version and updates
- [ ] Test on a different user account
- [ ] Temporarily disable antivirus and test

---

## Contact Information

If none of these solutions work, collect this information:
1. Contents of `barcodematch_error.log`
2. Output from DEBUG exe console
3. Windows version (`winver` command)
4. Installed VC++ versions (see command above)
5. Antivirus software name and version

---

## Prevention for Future Builds

1. **Always test on a clean VM** without Python installed
2. **Include VC++ installer** with your distribution
3. **Sign the exe** to avoid antivirus false positives
4. **Create installer** using Inno Setup or NSIS that includes dependencies
5. **Document system requirements** clearly
