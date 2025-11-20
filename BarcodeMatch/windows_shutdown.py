"""
Windows Shutdown Handler - Detects Windows shutdown/logoff events
"""

import sys
import ctypes
import ctypes.wintypes
import threading

class WindowsShutdownHandler:
    """Handles Windows shutdown/logoff events using Win32 API"""

    def __init__(self, shutdown_callback):
        self.shutdown_callback = shutdown_callback
        self.window_handle = None
        self.message_thread = None
        self.running = False

    def start(self):
        """Start listening for Windows shutdown messages"""
        if sys.platform != 'win32':
            print("[SHUTDOWN] Not on Windows, skipping Windows shutdown handler")
            return

        self.running = True
        self.message_thread = threading.Thread(target=self._message_loop, daemon=True)
        self.message_thread.start()
        print("[SHUTDOWN] Windows shutdown handler started")

    def stop(self):
        """Stop listening for messages"""
        self.running = False
        if self.window_handle:
            try:
                # Post WM_QUIT to exit message loop
                ctypes.windll.user32.PostMessageW(self.window_handle, 0x0012, 0, 0)
            except:
                pass

    def _message_loop(self):
        """Windows message loop to detect shutdown events"""
        try:
            # Define Windows constants
            WM_QUERYENDSESSION = 0x0011
            WM_ENDSESSION = 0x0016
            WM_CLOSE = 0x0010
            WM_DESTROY = 0x0002
            WM_QUIT = 0x0012

            # Define WNDPROC callback type
            WNDPROC = ctypes.WINFUNCTYPE(
                ctypes.c_long,
                ctypes.wintypes.HWND,
                ctypes.c_uint,
                ctypes.wintypes.WPARAM,
                ctypes.wintypes.LPARAM
            )

            # Window procedure to handle messages
            def wndproc(hwnd, msg, wparam, lparam):
                if msg == WM_QUERYENDSESSION:
                    # Windows is asking if we can shut down
                    print("[SHUTDOWN] WM_QUERYENDSESSION received - Windows shutdown initiated")
                    # Call shutdown callback immediately
                    try:
                        self.shutdown_callback()
                    except Exception as e:
                        print(f"[SHUTDOWN ERROR] Callback failed: {e}")
                    # Return True to allow shutdown
                    return 1

                elif msg == WM_ENDSESSION:
                    # Windows is shutting down NOW
                    if wparam:
                        print("[SHUTDOWN] WM_ENDSESSION received - Windows shutting down NOW")
                        # Last chance to save state
                        try:
                            self.shutdown_callback()
                        except:
                            pass
                    return 0

                elif msg == WM_CLOSE:
                    ctypes.windll.user32.PostQuitMessage(0)
                    return 0

                elif msg == WM_DESTROY:
                    ctypes.windll.user32.PostQuitMessage(0)
                    return 0

                # Default message handling
                return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

            # Create WNDCLASS structure
            class WNDCLASS(ctypes.Structure):
                _fields_ = [
                    ('style', ctypes.c_uint),
                    ('lpfnWndProc', WNDPROC),
                    ('cbClsExtra', ctypes.c_int),
                    ('cbWndExtra', ctypes.c_int),
                    ('hInstance', ctypes.wintypes.HINSTANCE),
                    ('hIcon', ctypes.wintypes.HICON),
                    ('hCursor', ctypes.wintypes.HANDLE),
                    ('hbrBackground', ctypes.wintypes.HBRUSH),
                    ('lpszMenuName', ctypes.wintypes.LPCWSTR),
                    ('lpszClassName', ctypes.wintypes.LPCWSTR)
                ]

            # Get module handle
            hinstance = ctypes.windll.kernel32.GetModuleHandleW(None)

            # Create window class
            wndclass = WNDCLASS()
            wndclass.style = 0
            wndclass.lpfnWndProc = WNDPROC(wndproc)
            wndclass.cbClsExtra = 0
            wndclass.cbWndExtra = 0
            wndclass.hInstance = hinstance
            wndclass.hIcon = 0
            wndclass.hCursor = 0
            wndclass.hbrBackground = 0
            wndclass.lpszMenuName = None
            wndclass.lpszClassName = "BarcodeMatchShutdownHandler"

            # Register window class
            if not ctypes.windll.user32.RegisterClassW(ctypes.byref(wndclass)):
                print("[SHUTDOWN ERROR] Failed to register window class")
                return

            # Create invisible window
            self.window_handle = ctypes.windll.user32.CreateWindowExW(
                0,  # Extended style
                "BarcodeMatchShutdownHandler",  # Class name
                "BarcodeMatch Shutdown Handler",  # Window title
                0,  # Window style (invisible)
                0, 0, 0, 0,  # Position and size
                0,  # Parent window
                0,  # Menu
                hinstance,  # Instance
                None  # Param
            )

            if not self.window_handle:
                print("[SHUTDOWN ERROR] Failed to create window")
                return

            print("[SHUTDOWN] Windows message handler window created")

            # Message loop
            msg = ctypes.wintypes.MSG()
            while self.running:
                bret = ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if bret == 0:  # WM_QUIT
                    break
                elif bret == -1:  # Error
                    print("[SHUTDOWN ERROR] GetMessage failed")
                    break
                else:
                    ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                    ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

            print("[SHUTDOWN] Windows message loop ended")

        except Exception as e:
            print(f"[SHUTDOWN ERROR] Message loop failed: {e}")
            import traceback
            traceback.print_exc()