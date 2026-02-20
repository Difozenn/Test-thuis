"""
Build firebird_kam.py into a 32-bit Windows executable.

Requirements:
    - 32-bit Python 3.x installed (e.g. Python 3.11 x86 from python.org)
    - pip install pyinstaller fdb

Usage:
    python build_32bit.py

    Or specify the 32-bit Python path explicitly:
    C:\Python311-32\python.exe build_32bit.py

Notes:
    - The production machine needs GDS32.DLL (Firebird 32-bit client)
      either in the same folder as the exe or in the system PATH.
    - The .gdb file is NOT bundled — it stays on the production machine.
"""

import os
import sys
import struct
import subprocess
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "firebird_kam.py")
DIST_DIR = os.path.join(SCRIPT_DIR, "dist")
BUILD_DIR = os.path.join(SCRIPT_DIR, "build")
EXE_NAME = "firebird_kam"


def check_python_arch():
    bits = struct.calcsize("P") * 8
    print(f"Python {sys.version}")
    print(f"Architecture: {bits}-bit")
    if bits != 32:
        print(
            f"\nWARNING: This Python is {bits}-bit, not 32-bit!\n"
            "The resulting .exe will be {bits}-bit.\n"
            "\n"
            "To build a 32-bit exe, run this script with 32-bit Python:\n"
            '  "C:\\Python311-32\\python.exe" build_32bit.py\n'
            "\n"
            "Download 32-bit Python from:\n"
            "  https://www.python.org/downloads/ -> Windows installer (32-bit)\n"
        )
        resp = input("Continue anyway? [y/N] ").strip().lower()
        if resp != "y":
            sys.exit(1)


def check_dependencies():
    missing = []
    try:
        import PyInstaller
        print(f"PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        missing.append("pyinstaller")

    try:
        import fdb
        print("fdb found")
    except ImportError:
        missing.append("fdb")

    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print(f"Installing: pip install {' '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)


def build():
    print(f"\nBuilding {MAIN_SCRIPT} ...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", EXE_NAME,
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        "--specpath", SCRIPT_DIR,
        # Hidden imports that PyInstaller might miss
        "--hidden-import", "fdb",
        "--hidden-import", "fdb.ibase",
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.scrolledtext",
        MAIN_SCRIPT,
    ]

    print(f"Command: {' '.join(cmd)}\n")
    subprocess.check_call(cmd)

    exe_path = os.path.join(DIST_DIR, f"{EXE_NAME}.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        bits = struct.calcsize("P") * 8
        print(f"\nBuild successful!")
        print(f"  Output: {exe_path}")
        print(f"  Size:   {size_mb:.1f} MB")
        print(f"  Arch:   {bits}-bit")
        print(f"\nTo deploy, copy the exe to the production machine along with:")
        print(f"  - GDS32.DLL (Firebird client, in same folder or system PATH)")
        print(f"  - Holzher_KAM.Gdb should already be on the production machine")
    else:
        print(f"\nERROR: Expected output not found at {exe_path}")
        sys.exit(1)


def clean():
    """Remove build artifacts (keeps dist/)."""
    spec_file = os.path.join(SCRIPT_DIR, f"{EXE_NAME}.spec")
    for path in [BUILD_DIR, spec_file]:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            print(f"Cleaned: {path}")


if __name__ == "__main__":
    if "--clean" in sys.argv:
        clean()
        sys.exit(0)

    check_python_arch()
    check_dependencies()
    build()
    clean()
    print("\nDone. Build artifacts cleaned, exe is in dist/")
