#!/usr/bin/env python3
"""
BarcodeMaster Application Entry Point

This is the main entry point for the BarcodeMaster application.
It uses a clean startup manager to handle initialization in an organized way.
"""

import sys
import os

# Ensure we can import our startup manager
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from startup_manager import StartupManager
except ImportError as e:
    print(f"Fatal Error: Could not import startup manager: {e}")
    print("Please ensure all files are present and try again.")
    sys.exit(1)


def main():
    """Main application entry point."""
    startup_manager = StartupManager()
    startup_manager.start()


if __name__ == "__main__":
    main()
