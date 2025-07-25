#!/usr/bin/env python3
"""
MINTJENS Portal Server
Automatically starts the MINTJENS portal on the local network as mintjens.lan
"""

import os
import sys
import socket
import threading
import time
import webbrowser
import json
import base64
import uuid
import mimetypes
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial

try:
    from zeroconf import ServiceInfo, Zeroconf
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    print("Warning: zeroconf not installed. Install with 'pip install zeroconf' for automatic mintjens.lan resolution")

class MintjensHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler with MINTJENS branding and API support"""
    
    def __init__(self, *args, modules_dir=None, **kwargs):
        self.modules_dir = modules_dir
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[MINTJENS Portal] {self.address_string()} - {format%args}")
    
    def end_headers(self):
        """Add custom headers"""
        self.send_header('X-Powered-By', 'MINTJENS Portal Server')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()
    
    def do_GET(self):
        """Handle GET requests including API endpoints"""
        if self.path == '/api/modules':
            self.handle_get_modules()
        elif self.path.startswith('/modules/'):
            # Serve module images
            self.handle_get_module_image()
        else:
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests for API endpoints"""
        if self.path == '/api/modules':
            self.handle_create_module()
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_DELETE(self):
        """Handle DELETE requests for API endpoints"""
        if self.path.startswith('/api/modules/'):
            self.handle_delete_module()
        else:
            self.send_response(404)
            self.end_headers()
    
    def handle_get_modules(self):
        """Get all custom modules"""
        modules_file = os.path.join(self.modules_dir, 'modules.json')
        
        if os.path.exists(modules_file):
            with open(modules_file, 'r') as f:
                modules = json.load(f)
        else:
            modules = []
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(modules).encode())
    
    def handle_get_module_image(self):
        """Serve module images from the modules directory"""
        # Extract filename from path
        filename = os.path.basename(self.path)
        filepath = os.path.join(self.modules_dir, 'images', filename)
        
        if os.path.exists(filepath):
            # Serve the image file
            with open(filepath, 'rb') as f:
                content = f.read()
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(filepath)
            if not content_type:
                content_type = 'application/octet-stream'
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()
    
    def handle_create_module(self):
        """Create a new custom module"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode())
            
            # Generate unique ID
            module_id = 'custom-' + str(uuid.uuid4())[:8]
            
            # Process image data
            image_data = data.get('icon', '')
            image_filename = None
            
            if image_data.startswith('data:image/'):
                # Extract base64 data
                header, base64_data = image_data.split(',', 1)
                # Determine file extension
                mime_match = header.split(':')[1].split(';')[0]
                ext = mimetypes.guess_extension(mime_match) or '.png'
                
                # Save image file
                image_filename = f"{module_id}{ext}"
                image_path = os.path.join(self.modules_dir, 'images', image_filename)
                
                # Decode and save image
                with open(image_path, 'wb') as f:
                    f.write(base64.b64decode(base64_data))
            
            # Create module data
            module = {
                'id': module_id,
                'name': data.get('name', ''),
                'url': data.get('url', ''),
                'icon': f'/modules/{image_filename}' if image_filename else '',
                'custom': True,
                'created': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Load existing modules
            modules_file = os.path.join(self.modules_dir, 'modules.json')
            if os.path.exists(modules_file):
                with open(modules_file, 'r') as f:
                    modules = json.load(f)
            else:
                modules = []
            
            # Add new module
            modules.append(module)
            
            # Save modules
            with open(modules_file, 'w') as f:
                json.dump(modules, f, indent=2)
            
            # Return success response
            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(module).encode())
            
        except Exception as e:
            print(f"Error creating module: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_delete_module(self):
        """Delete a custom module"""
        # Extract module ID from path
        module_id = os.path.basename(self.path)
        
        modules_file = os.path.join(self.modules_dir, 'modules.json')
        
        if os.path.exists(modules_file):
            with open(modules_file, 'r') as f:
                modules = json.load(f)
            
            # Find and remove module
            module_to_delete = None
            for i, module in enumerate(modules):
                if module['id'] == module_id:
                    module_to_delete = modules.pop(i)
                    break
            
            if module_to_delete:
                # Delete image file if exists
                if module_to_delete.get('icon', '').startswith('/modules/'):
                    image_filename = os.path.basename(module_to_delete['icon'])
                    image_path = os.path.join(self.modules_dir, 'images', image_filename)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                
                # Save updated modules
                with open(modules_file, 'w') as f:
                    json.dump(modules, f, indent=2)
                
                self.send_response(204)
                self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

def get_lan_ip():
    """Get the LAN IP address of this machine"""
    try:
        # Create a socket and connect to an external address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def register_mdns(ip_address, port):
    """Register mintjens.lan using mDNS/Zeroconf"""
    if not ZEROCONF_AVAILABLE:
        return None
    
    try:
        zeroconf = Zeroconf()
        
        # Create service info
        info = ServiceInfo(
            "_http._tcp.local.",
            "MINTJENS Portal._http._tcp.local.",
            addresses=[socket.inet_aton(ip_address)],
            port=port,
            properties={'path': '/'},
            server="mintjens.lan."
        )
        
        # Register the service
        zeroconf.register_service(info)
        print(f"✓ Registered mintjens.lan via mDNS")
        return zeroconf
    except Exception as e:
        print(f"Warning: Could not register mDNS: {e}")
        return None

def print_startup_banner(ip_address, port):
    """Print startup information"""
    print("\n" + "="*60)
    print("        MINTJENS PORTAL SERVER")
    print("="*60)
    print(f"\n✓ Server started successfully!")
    print(f"\nAccess the portal using:")
    if port == 80:
        print(f"  • http://{ip_address}")
        print(f"  • http://localhost")
    else:
        print(f"  • http://{ip_address}:{port}")
        print(f"  • http://localhost:{port}")
    
    if ZEROCONF_AVAILABLE:
        if port == 80:
            print(f"  • http://mintjens.lan")
        else:
            print(f"  • http://mintjens.lan:{port}")
    else:
        print(f"\nTo enable mintjens.lan:")
        print(f"  1. Install zeroconf: pip install zeroconf")
        print(f"  2. Or add to hosts file: {ip_address} mintjens.lan")
    
    print(f"\nServing from: {os.path.abspath('.')}")
    print("\nPress Ctrl+C to stop the server")
    print("="*60 + "\n")

def open_browser_delayed(url, delay=2):
    """Open browser after a delay"""
    time.sleep(delay)
    try:
        webbrowser.open(url)
        print(f"✓ Opened browser to {url}")
    except:
        pass

def main():
    """Main server function"""
    # Configuration
    port = 80
    
    # Change to the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Create modules directory structure
    modules_dir = os.path.join(script_dir, 'modules')
    images_dir = os.path.join(modules_dir, 'images')
    
    # Ensure directories exist
    os.makedirs(images_dir, exist_ok=True)
    
    # Get LAN IP
    ip_address = get_lan_ip()
    
    # Create HTTP request handler with modules directory
    handler = partial(MintjensHTTPRequestHandler, directory=script_dir, modules_dir=modules_dir)
    
    # Create and configure server
    try:
        httpd = HTTPServer(('', port), handler)
    except PermissionError:
        print(f"Error: Permission denied for port {port}")
        if port == 80:
            print("\nPort 80 requires administrator privileges.")
            print("Options:")
            print("  1. Run with sudo: sudo python run_server.py")
            print("  2. Use a different port by editing this file")
            print("\nTrying port 8080 instead...")
            port = 8080
            try:
                httpd = HTTPServer(('', port), handler)
            except:
                print("Failed to start on port 8080 as well")
                sys.exit(1)
        else:
            print("Try a different port or run with sudo")
            sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Error: Port {port} is already in use")
            print("Try a different port or stop the other service")
        else:
            print(f"Error starting server: {e}")
        sys.exit(1)
    
    # Register mDNS service
    zeroconf = register_mdns(ip_address, port)
    
    # Print startup information
    print_startup_banner(ip_address, port)
    
    # Open browser in background
    browser_url = f"http://localhost" if port == 80 else f"http://localhost:{port}"
    browser_thread = threading.Thread(target=open_browser_delayed, args=(browser_url, 2))
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start server
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        if zeroconf:
            zeroconf.close()
        httpd.server_close()
        print("✓ Server stopped")
        sys.exit(0)

if __name__ == "__main__":
    main()