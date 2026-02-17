#!/usr/bin/env python3
"""Quick test to verify all critical imports work"""

print("Testing critical imports...")

try:
    import tkinter as tk
    print("✓ tkinter")
except ImportError as e:
    print(f"✗ tkinter: {e}")

try:
    import pandas as pd
    print(f"✓ pandas {pd.__version__}")
except ImportError as e:
    print(f"✗ pandas: {e}")

try:
    import numpy as np
    print(f"✓ numpy {np.__version__}")
except ImportError as e:
    print(f"✗ numpy: {e}")

try:
    import keyboard
    print("✓ keyboard")
except ImportError as e:
    print(f"✗ keyboard: {e}")

try:
    import serial
    print("✓ pyserial")
except ImportError as e:
    print(f"✗ pyserial: {e}")

try:
    import openpyxl
    print(f"✓ openpyxl {openpyxl.__version__}")
except ImportError as e:
    print(f"✗ openpyxl: {e}")

try:
    import pyodbc
    print("✓ pyodbc")
except ImportError as e:
    print(f"✗ pyodbc: {e}")

try:
    import PIL
    print(f"✓ Pillow {PIL.__version__}")
except ImportError as e:
    print(f"✗ Pillow: {e}")

try:
    import requests
    print(f"✓ requests {requests.__version__}")
except ImportError as e:
    print(f"✗ requests: {e}")

print("\nNow testing if main.py can run...")
try:
    import main
    print("✓ main.py imports successfully")
except Exception as e:
    print(f"✗ main.py failed: {e}")