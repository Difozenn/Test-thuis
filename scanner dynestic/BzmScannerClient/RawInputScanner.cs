using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

namespace BzmScannerClient
{
    /// <summary>
    /// Captures input from a specific USB HID device (barcode scanner) using
    /// the Win32 Raw Input API. Works even when the application is not focused.
    /// </summary>
    public class RawInputScanner : IDisposable
    {
        // --- Win32 Constants ---
        private const int WM_INPUT = 0x00FF;
        private const int RID_INPUT = 0x10000003;
        private const int RIM_TYPEKEYBOARD = 1;
        private const int RIDEV_INPUTSINK = 0x00000100;
        private const int RIDI_DEVICENAME = 0x20000007;
        private const int WM_KEYDOWN = 0x0100;

        // --- Win32 Structs ---
        [StructLayout(LayoutKind.Sequential)]
        private struct RAWINPUTDEVICELIST
        {
            public IntPtr hDevice;
            public int dwType;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct RAWINPUTDEVICE
        {
            public ushort usUsagePage;
            public ushort usUsage;
            public int dwFlags;
            public IntPtr hwndTarget;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct RAWINPUTHEADER
        {
            public int dwType;
            public int dwSize;
            public IntPtr hDevice;
            public IntPtr wParam;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct RAWKEYBOARD
        {
            public ushort MakeCode;
            public ushort Flags;
            public ushort Reserved;
            public ushort VKey;
            public uint Message;
            public uint ExtraInformation;
        }

        [StructLayout(LayoutKind.Explicit)]
        private struct RAWINPUT
        {
            [FieldOffset(0)]
            public RAWINPUTHEADER header;
            // Keyboard data starts after header (size depends on platform)
        }

        // --- Win32 Imports ---
        [DllImport("user32.dll", SetLastError = true)]
        private static extern uint GetRawInputDeviceList(
            [Out] RAWINPUTDEVICELIST[]? pRawInputDeviceList,
            ref uint puiNumDevices,
            uint cbSize);

        [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern uint GetRawInputDeviceInfo(
            IntPtr hDevice,
            uint uiCommand,
            StringBuilder? pData,
            ref uint pcbSize);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool RegisterRawInputDevices(
            RAWINPUTDEVICE[] pRawInputDevices,
            uint uiNumDevices,
            uint cbSize);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern uint GetRawInputData(
            IntPtr hRawInput,
            uint uiCommand,
            IntPtr pData,
            ref uint pcbSize,
            uint cbSizeHeader);

        [DllImport("user32.dll")]
        private static extern int MapVirtualKey(int uCode, int uMapType);

        // --- Public API ---

        /// <summary>Fired when a complete barcode is scanned (Enter detected).</summary>
        public event Action<string>? BarcodeScanned;

        /// <summary>Fired on each keystroke from the scanner device.</summary>
        public event Action<char>? KeyPressed;

        private IntPtr _scannerDeviceHandle = IntPtr.Zero;
        private readonly StringBuilder _buffer = new();
        private bool _registered;

        /// <summary>
        /// Returns all connected keyboard-type HID devices.
        /// Key = device handle, Value = device name/path.
        /// </summary>
        public static List<DeviceInfo> GetKeyboardDevices()
        {
            var result = new List<DeviceInfo>();

            uint numDevices = 0;
            uint size = (uint)Marshal.SizeOf(typeof(RAWINPUTDEVICELIST));
            GetRawInputDeviceList(null, ref numDevices, size);

            if (numDevices == 0)
                return result;

            var deviceList = new RAWINPUTDEVICELIST[numDevices];
            GetRawInputDeviceList(deviceList, ref numDevices, size);

            foreach (var device in deviceList)
            {
                if (device.dwType != RIM_TYPEKEYBOARD)
                    continue;

                string name = GetDeviceName(device.hDevice);
                if (string.IsNullOrEmpty(name))
                    continue;

                result.Add(new DeviceInfo
                {
                    Handle = device.hDevice,
                    DevicePath = name,
                    DisplayName = BuildDisplayName(name)
                });
            }

            return result;
        }

        private static string GetDeviceName(IntPtr hDevice)
        {
            uint size = 0;
            GetRawInputDeviceInfo(hDevice, RIDI_DEVICENAME, null, ref size);
            if (size == 0) return "";

            var sb = new StringBuilder((int)size);
            GetRawInputDeviceInfo(hDevice, RIDI_DEVICENAME, sb, ref size);
            return sb.ToString();
        }

        private static string BuildDisplayName(string devicePath)
        {
            // Device paths look like: \\?\HID#VID_1234&PID_5678#...
            // Extract VID/PID for a friendlier display
            string upper = devicePath.ToUpperInvariant();
            string vid = "", pid = "";

            int vidIdx = upper.IndexOf("VID_");
            if (vidIdx >= 0 && vidIdx + 8 <= upper.Length)
                vid = upper.Substring(vidIdx, 8);

            int pidIdx = upper.IndexOf("PID_");
            if (pidIdx >= 0 && pidIdx + 8 <= upper.Length)
                pid = upper.Substring(pidIdx, 8);

            if (!string.IsNullOrEmpty(vid))
                return $"{vid} {pid}  ({devicePath.Substring(0, Math.Min(60, devicePath.Length))}...)";

            return devicePath.Length > 70
                ? devicePath.Substring(0, 67) + "..."
                : devicePath;
        }

        /// <summary>
        /// Set which device to listen to and register for raw input.
        /// </summary>
        public void SelectDevice(IntPtr deviceHandle, IntPtr windowHandle)
        {
            _scannerDeviceHandle = deviceHandle;
            Register(windowHandle);
        }

        /// <summary>
        /// Select device by its device path string (for restoring from config).
        /// </summary>
        public bool SelectDeviceByPath(string devicePath, IntPtr windowHandle)
        {
            var devices = GetKeyboardDevices();
            foreach (var d in devices)
            {
                if (d.DevicePath.Equals(devicePath, StringComparison.OrdinalIgnoreCase))
                {
                    SelectDevice(d.Handle, windowHandle);
                    return true;
                }
            }
            return false;
        }

        private void Register(IntPtr windowHandle)
        {
            var rid = new RAWINPUTDEVICE[]
            {
                new RAWINPUTDEVICE
                {
                    usUsagePage = 0x01,       // Generic Desktop
                    usUsage     = 0x06,       // Keyboard
                    dwFlags     = RIDEV_INPUTSINK,  // Receive input even when not focused
                    hwndTarget  = windowHandle
                }
            };

            _registered = RegisterRawInputDevices(rid, 1,
                (uint)Marshal.SizeOf(typeof(RAWINPUTDEVICE)));
        }

        /// <summary>
        /// Call this from the form's WndProc when msg == WM_INPUT.
        /// Returns true if the message was handled.
        /// </summary>
        public bool ProcessRawInput(Message m)
        {
            if (m.Msg != WM_INPUT || !_registered)
                return false;

            // Get required buffer size
            uint size = 0;
            uint headerSize = (uint)Marshal.SizeOf(typeof(RAWINPUTHEADER));
            GetRawInputData(m.LParam, RID_INPUT, IntPtr.Zero, ref size, headerSize);

            if (size == 0)
                return false;

            IntPtr buffer = Marshal.AllocHGlobal((int)size);
            try
            {
                if (GetRawInputData(m.LParam, RID_INPUT, buffer, ref size, headerSize) != size)
                    return false;

                var header = Marshal.PtrToStructure<RAWINPUTHEADER>(buffer);

                // Only process keyboard input from our selected scanner device
                if (header.dwType != RIM_TYPEKEYBOARD)
                    return false;

                if (_scannerDeviceHandle != IntPtr.Zero && header.hDevice != _scannerDeviceHandle)
                    return false;

                // Read keyboard data (located right after the header)
                var kbd = Marshal.PtrToStructure<RAWKEYBOARD>(buffer + (int)headerSize);

                // Only process key-down events
                if (kbd.Message != WM_KEYDOWN)
                    return true; // still consume key-up from scanner

                int vKey = kbd.VKey;

                // Enter key = end of barcode
                if (vKey == (int)Keys.Enter)
                {
                    string barcode = _buffer.ToString().Trim();
                    _buffer.Clear();

                    if (!string.IsNullOrEmpty(barcode))
                        BarcodeScanned?.Invoke(barcode);

                    return true;
                }

                // Convert virtual key to character
                char c = VKeyToChar(vKey, kbd.MakeCode);
                if (c != '\0')
                {
                    _buffer.Append(c);
                    KeyPressed?.Invoke(c);
                }

                return true;
            }
            finally
            {
                Marshal.FreeHGlobal(buffer);
            }
        }

        private static char VKeyToChar(int vKey, int scanCode)
        {
            // Number keys 0-9
            if (vKey >= (int)Keys.D0 && vKey <= (int)Keys.D9)
                return (char)('0' + (vKey - (int)Keys.D0));

            // Letter keys A-Z (return uppercase — scanners usually send uppercase)
            if (vKey >= (int)Keys.A && vKey <= (int)Keys.Z)
                return (char)('A' + (vKey - (int)Keys.A));

            // Numpad 0-9
            if (vKey >= (int)Keys.NumPad0 && vKey <= (int)Keys.NumPad9)
                return (char)('0' + (vKey - (int)Keys.NumPad0));

            // Common characters in file paths and barcodes
            return vKey switch
            {
                (int)Keys.OemPeriod   => '.',
                (int)Keys.OemMinus    => '-',
                (int)Keys.Oemplus     => '+',
                (int)Keys.OemQuestion => '/',
                (int)Keys.OemPipe     => '\\',
                (int)Keys.Oem1        => ';',
                (int)Keys.Oem7        => '\'',
                (int)Keys.Oemcomma    => ',',
                (int)Keys.Space       => ' ',
                (int)Keys.OemOpenBrackets  => '[',
                (int)Keys.OemCloseBrackets => ']',
                (int)Keys.Oemtilde    => '`',
                _ => MapFallback(vKey)
            };
        }

        private static char MapFallback(int vKey)
        {
            // Use MapVirtualKey as fallback
            int ch = MapVirtualKey(vKey, 2); // MAPVK_VK_TO_CHAR
            if (ch > 0 && ch < 128)
                return (char)ch;
            return '\0';
        }

        /// <summary>True if a scanner device has been selected and registration succeeded.</summary>
        public bool IsListening => _registered && _scannerDeviceHandle != IntPtr.Zero;

        public static int WM_INPUT_MSG => WM_INPUT;

        public void Dispose()
        {
            // Unregister by registering with RIDEV_REMOVE (0x01)
            if (_registered)
            {
                var rid = new RAWINPUTDEVICE[]
                {
                    new RAWINPUTDEVICE
                    {
                        usUsagePage = 0x01,
                        usUsage     = 0x06,
                        dwFlags     = 0x00000001, // RIDEV_REMOVE
                        hwndTarget  = IntPtr.Zero
                    }
                };
                RegisterRawInputDevices(rid, 1, (uint)Marshal.SizeOf(typeof(RAWINPUTDEVICE)));
                _registered = false;
            }
        }
    }

    public class DeviceInfo
    {
        public IntPtr Handle { get; set; }
        public string DevicePath { get; set; } = "";
        public string DisplayName { get; set; } = "";

        public override string ToString() => DisplayName;
    }
}
