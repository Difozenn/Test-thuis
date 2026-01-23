#!/usr/bin/env python3
"""
Barcode to Keyboard Wedge
Receives barcode data from Zebra DataWedge IP Output and types it as keyboard input.

Setup:
1. Install Python 3
2. Run: pip install keyboard
3. Run this script as Administrator (required for keyboard simulation)
4. Configure DataWedge on your Zebra device:
   - Enable IP Output
   - Set IP to your PC's IP address (run 'ipconfig' to find it)
   - Set Port to 58627
   - Set Protocol to TCP
"""

import socket
import sys

try:
    import keyboard
except ImportError:
    print("Error: 'keyboard' module not found.")
    print("Please install it by running: pip install keyboard")
    sys.exit(1)

# Configuration
HOST = '0.0.0.0'  # Listen on all network interfaces
PORT = 58627      # Default DataWedge IP Output port
ADD_ENTER = True  # Press Enter after each barcode

def get_local_ip():
    """Get the local IP address to display to user"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Unable to detect"

def main():
    print("=" * 50)
    print("  Barcode to Keyboard Wedge")
    print("=" * 50)
    print()
    print(f"Your PC's IP address: {get_local_ip()}")
    print(f"Listening on port: {PORT}")
    print()
    print("DataWedge settings on your Zebra device:")
    print(f"  - IP Address: {get_local_ip()}")
    print(f"  - Port: {PORT}")
    print("  - Protocol: TCP")
    print()
    print("Waiting for barcode scans... (Press Ctrl+C to stop)")
    print("-" * 50)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
    except OSError as e:
        print(f"Error: Could not bind to port {PORT}")
        print(f"Details: {e}")
        print("\nTry running as Administrator, or check if another program is using this port.")
        sys.exit(1)
    
    server.listen(5)

    try:
        while True:
            conn, addr = server.accept()
            try:
                data = conn.recv(4096).decode('utf-8').strip()
                if data:
                    # Remove any null characters or extra whitespace
                    data = data.replace('\x00', '').strip()
                    print(f"Received: {data}")
                    
                    # Type the barcode data
                    keyboard.write(data)
                    
                    # Optionally press Enter
                    if ADD_ENTER:
                        keyboard.press_and_release('enter')
            except Exception as e:
                print(f"Error processing data: {e}")
            finally:
                conn.close()
    except KeyboardInterrupt:
        print("\n\nStopping server...")
    finally:
        server.close()
        print("Server stopped.")

if __name__ == "__main__":
    main()
