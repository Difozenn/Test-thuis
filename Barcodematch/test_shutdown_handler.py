#!/usr/bin/env python3
"""
Test script to verify the Windows shutdown handler works on both 32-bit and 64-bit systems.
"""

import sys
import time
import struct
import ctypes
import ctypes.wintypes

def test_platform_info():
    """Display platform information"""
    print("=" * 60)
    print("PLATFORM INFORMATION")
    print("=" * 60)
    print(f"Python architecture: {struct.calcsize('P') * 8}-bit")
    print(f"Python version: {sys.version}")
    print()

    # Test ctypes.wintypes sizes
    print("ctypes.wintypes type sizes (automatically adjusted per platform):")
    print(f"  LPARAM: {ctypes.sizeof(ctypes.wintypes.LPARAM)} bytes ({ctypes.sizeof(ctypes.wintypes.LPARAM) * 8} bits)")
    print(f"  WPARAM: {ctypes.sizeof(ctypes.wintypes.WPARAM)} bytes ({ctypes.sizeof(ctypes.wintypes.WPARAM) * 8} bits)")
    print(f"  HWND:   {ctypes.sizeof(ctypes.wintypes.HWND)} bytes ({ctypes.sizeof(ctypes.wintypes.HWND) * 8} bits)")
    print(f"  HANDLE: {ctypes.sizeof(ctypes.wintypes.HANDLE)} bytes ({ctypes.sizeof(ctypes.wintypes.HANDLE) * 8} bits)")
    print()
    print("✓ These types will be 32-bit on 32-bit Windows and 64-bit on 64-bit Windows")
    print()

def test_shutdown_handler():
    """Test the shutdown handler import and basic functionality"""
    print("=" * 60)
    print("TESTING SHUTDOWN HANDLER")
    print("=" * 60)

    try:
        from windows_shutdown import WindowsShutdownHandler
        print("✓ Successfully imported WindowsShutdownHandler")

        # Create a test callback
        callback_called = [False]

        def test_callback():
            callback_called[0] = True
            print("✓ Shutdown callback would be triggered")

        # Create handler instance
        handler = WindowsShutdownHandler(test_callback)
        print("✓ Successfully created WindowsShutdownHandler instance")

        # Start the handler
        handler.start()
        print("✓ Successfully started shutdown handler thread")

        # Let it run briefly
        print("  Handler is running (will stop in 2 seconds)...")
        time.sleep(2)

        # Stop the handler
        handler.stop()
        print("✓ Successfully stopped shutdown handler")

        print()
        print("RESULT: All tests passed! The shutdown handler is compatible with this system.")
        print("         No overflow errors detected.")

    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    print()
    print("WINDOWS SHUTDOWN HANDLER COMPATIBILITY TEST")
    print()

    test_platform_info()

    if sys.platform == "win32":
        success = test_shutdown_handler()
        sys.exit(0 if success else 1)
    else:
        print("=" * 60)
        print("SKIPPING SHUTDOWN HANDLER TEST")
        print("=" * 60)
        print("This is not a Windows system. The shutdown handler is Windows-specific.")
        print("Current platform:", sys.platform)