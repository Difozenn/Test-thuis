#!/usr/bin/env python3
"""
Simple File Server with Download Support
Run this from any directory to share files over HTTP
"""

import http.server
import socketserver
import os
import sys
import socket
import urllib.parse
import html
import io
import zipfile
from pathlib import Path

class BetterHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests with download support"""
        # Parse the URL - handle special characters properly
        parsed_path = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed_path.path, errors='replace')
        
        # Handle download all as ZIP
        if path == '/__download_all__':
            self.download_directory_as_zip()
            return
            
        # Handle regular file serving with download headers
        translated_path = self.translate_path(path)
        
        if os.path.isfile(translated_path):
            # Force download for files
            self.send_response(200)
            filename = os.path.basename(translated_path)
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(os.path.getsize(translated_path)))
            self.end_headers()
            
            with open(translated_path, 'rb') as f:
                self.copyfile(f, self.wfile)
        else:
            # Serve directory listing with custom template
            if os.path.isdir(translated_path):
                self.list_directory_custom(translated_path)
            else:
                self.send_error(404, "File not found")
    
    def list_directory_custom(self, path):
        """Custom directory listing with download options"""
        try:
            file_list = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return
            
        file_list.sort(key=lambda a: a.lower())
        
        # Create HTML response
        displaypath = html.escape(urllib.parse.unquote(self.path))
        title = f'Directory: {displaypath}'
        
        # Build file list HTML
        files_html = []
        for name in file_list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            
            # Add / for directories
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
                icon = "📁"
            else:
                icon = "📄"
                
            # Get file size
            try:
                size = os.path.getsize(fullname)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024*1024:
                    size_str = f"{size/1024:.1f} KB"
                elif size < 1024*1024*1024:
                    size_str = f"{size/(1024*1024):.1f} MB"
                else:
                    size_str = f"{size/(1024*1024*1024):.1f} GB"
            except:
                size_str = "-"
                
            if os.path.isdir(fullname):
                size_str = "-"
                
            # Use proper URL encoding for special characters
            quoted_link = urllib.parse.quote(linkname, safe='/')
            
            files_html.append(f'''
                <tr>
                    <td>{icon}</td>
                    <td><a href="{quoted_link}">{html.escape(displayname)}</a></td>
                    <td style="text-align: right">{size_str}</td>
                </tr>
            ''')
        
        # Build complete HTML
        html_content = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th {{
            background: #4CAF50;
            color: white;
            padding: 10px;
            text-align: left;
        }}
        td {{
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        a {{
            color: #2196F3;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .download-all {{
            background: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px 0;
            text-decoration: none;
            display: inline-block;
        }}
        .download-all:hover {{
            background: #45a049;
        }}
        .info {{
            background: #e3f2fd;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }}
        .back-link {{
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        
        <div class="info">
            <strong>Server IP:</strong> {self.server.server_address[0]}:{self.server.server_address[1]}<br>
            <strong>Path:</strong> {displaypath}
        </div>
        
        {'<div class="back-link"><a href="../">⬆️ Parent Directory</a></div>' if displaypath != '/' else ''}
        
        <a href="/__download_all__" class="download-all">📦 Download All as ZIP</a>
        
        <table>
            <thead>
                <tr>
                    <th width="30">Type</th>
                    <th>Name</th>
                    <th width="100">Size</th>
                </tr>
            </thead>
            <tbody>
                {''.join(files_html)}
            </tbody>
        </table>
        
        <hr style="margin-top: 30px;">
        <p style="color: #666; font-size: 14px;">
            Python File Server | Files: {len([f for f in file_list if os.path.isfile(os.path.join(path, f))])} | 
            Folders: {len([f for f in file_list if os.path.isdir(os.path.join(path, f))])}
        </p>
    </div>
</body>
</html>
        '''
        
        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(html_content.encode())))
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def download_directory_as_zip(self):
        """Download current directory as ZIP file"""
        current_dir = self.translate_path('/')
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(current_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, current_dir)
                    try:
                        zipf.write(file_path, arcname)
                    except:
                        pass  # Skip files we can't read
        
        # Send ZIP file
        zip_buffer.seek(0)
        zip_data = zip_buffer.read()
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/zip')
        self.send_header('Content-Disposition', 'attachment; filename="download.zip"')
        self.send_header('Content-Length', str(len(zip_data)))
        self.end_headers()
        self.wfile.write(zip_data)

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def main():
    # Parse arguments
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = '.'
    
    # Change to target directory
    try:
        os.chdir(directory)
        serving_dir = os.path.abspath('.')
    except:
        print(f"Error: Cannot access directory '{directory}'")
        sys.exit(1)
    
    # Set up server
    PORT = 8000
    Handler = BetterHTTPRequestHandler
    
    # Find available port
    while True:
        try:
            httpd = socketserver.TCPServer(("", PORT), Handler)
            break
        except OSError:
            PORT += 1
            if PORT > 8100:
                print("No available ports found")
                sys.exit(1)
    
    local_ip = get_local_ip()
    
    print("\n" + "="*60)
    print("🚀 FILE SERVER STARTED")
    print("="*60)
    print(f"\n📁 Serving directory: {serving_dir}")
    print(f"\n🌐 Access from:")
    print(f"   • This PC:     http://localhost:{PORT}")
    print(f"   • Local network: http://{local_ip}:{PORT}")
    print(f"\n📥 Features:")
    print(f"   • Click any file to download")
    print(f"   • Click 'Download All as ZIP' for entire directory")
    print(f"\n⚡ Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped")
        httpd.server_close()

if __name__ == "__main__":
    main()