#!/usr/bin/env python3
"""
EXCALIBUR PDF TABLE EXTRACTOR
Using Excalibur for automated PDF table extraction
"""

import subprocess
import os
import requests
import time
import json

def install_excalibur():
    """Install Excalibur if not already installed"""
    
    print("🔧 Installing Excalibur...")
    
    try:
        # Check if excalibur is already installed
        result = subprocess.run(['excalibur', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Excalibur already installed")
            return True
    except FileNotFoundError:
        pass
    
    try:
        # Install excalibur via pip
        print("   Installing excalibur-py...")
        result = subprocess.run(['pip', 'install', 'excalibur-py[all]'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Excalibur installed successfully")
            return True
        else:
            print(f"❌ Excalibur installation failed: {result.stderr}")
            return False
    
    except Exception as e:
        print(f"❌ Excalibur installation error: {e}")
        return False

def start_excalibur_server():
    """Start Excalibur web server"""
    
    print("🚀 Starting Excalibur server...")
    
    try:
        # Start excalibur server in background
        process = subprocess.Popen(['excalibur', 'webserver'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        
        # Give server time to start
        time.sleep(5)
        
        # Check if server is running
        try:
            response = requests.get('http://localhost:5000', timeout=10)
            if response.status_code == 200:
                print("✅ Excalibur server running at http://localhost:5000")
                return process
            else:
                print(f"❌ Server not responding: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Server connection failed: {e}")
            return None
    
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def upload_pdf_to_excalibur(pdf_path: str):
    """Upload PDF to Excalibur via API"""
    
    print(f"📤 Uploading PDF to Excalibur: {os.path.basename(pdf_path)}")
    
    try:
        url = 'http://localhost:5000/api/upload'
        
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            file_id = result.get('file_id')
            print(f"✅ PDF uploaded successfully, ID: {file_id}")
            return file_id
        else:
            print(f"❌ Upload failed: {response.status_code}")
            return None
    
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def extract_tables_with_excalibur(file_id: str):
    """Extract tables using Excalibur API"""
    
    print("📊 Extracting tables with Excalibur...")
    
    try:
        # Get extraction job
        url = f'http://localhost:5000/api/extract/{file_id}'
        
        # Start extraction
        response = requests.post(url, json={
            'flavor': 'lattice',  # Use lattice for tables with borders
            'pages': 'all'
        }, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            print(f"✅ Extraction job started, ID: {job_id}")
            
            # Poll for completion
            return wait_for_extraction(job_id)
        else:
            print(f"❌ Extraction failed: {response.status_code}")
            return None
    
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        return None

def wait_for_extraction(job_id: str):
    """Wait for extraction job to complete"""
    
    print("⏳ Waiting for extraction to complete...")
    
    for attempt in range(30):  # Wait up to 5 minutes
        try:
            url = f'http://localhost:5000/api/job/{job_id}'
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                status = result.get('status')
                
                if status == 'completed':
                    print("✅ Extraction completed!")
                    return result.get('tables', [])
                elif status == 'failed':
                    print("❌ Extraction failed")
                    return None
                else:
                    print(f"   Status: {status}...")
                    time.sleep(10)
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return None
        
        except Exception as e:
            print(f"❌ Status check error: {e}")
            return None
    
    print("⏰ Extraction timeout")
    return None

def download_excalibur_results(file_id: str, output_dir: str = '.'):
    """Download extraction results"""
    
    print("💾 Downloading extraction results...")
    
    try:
        url = f'http://localhost:5000/api/download/{file_id}/csv'
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            output_file = os.path.join(output_dir, f'excalibur_{file_id}.zip')
            
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Results downloaded: {output_file}")
            return output_file
        else:
            print(f"❌ Download failed: {response.status_code}")
            return None
    
    except Exception as e:
        print(f"❌ Download error: {e}")
        return None

def try_excalibur_cmdline(pdf_path: str):
    """Try Excalibur command line interface if available"""
    
    print("🔄 Trying Excalibur command line...")
    
    try:
        import excalibur
        
        # Use excalibur python API directly
        csv_file = pdf_path.replace('.PDF', '_excalibur.csv').replace('.pdf', '_excalibur.csv')
        
        # Extract tables
        tables = excalibur.read_pdf(pdf_path, pages='all', flavor='lattice')
        
        if tables:
            # Combine all tables
            import pandas as pd
            all_data = []
            
            for i, table in enumerate(tables):
                df = table.df
                df['_table_num'] = i + 1
                df['_page'] = table.page
                all_data.append(df)
            
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                combined_df.to_csv(csv_file, index=False)
                
                print(f"✅ Excalibur command line successful: {csv_file}")
                print(f"   Extracted {len(tables)} tables, {len(combined_df)} rows")
                return csv_file
        
        print("❌ No tables extracted")
        return None
    
    except ImportError:
        print("   Excalibur not available as Python library")
        return None
    except Exception as e:
        print(f"   Excalibur command line failed: {e}")
        return None

def test_excalibur_extraction():
    """Test Excalibur PDF table extraction"""
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print("🔥 TESTING EXCALIBUR PDF TABLE EXTRACTION")
    print("=" * 70)
    
    # Method 1: Try command line interface first
    result_file = try_excalibur_cmdline(pdf_path)
    
    if result_file:
        print(f"\n🎯 SUCCESS: {result_file}")
        return result_file
    
    # Method 2: Try web server interface
    if not install_excalibur():
        print("❌ Cannot install Excalibur")
        return None
    
    server_process = start_excalibur_server()
    
    if not server_process:
        print("❌ Cannot start Excalibur server")
        return None
    
    try:
        # Upload and extract
        file_id = upload_pdf_to_excalibur(pdf_path)
        
        if file_id:
            tables = extract_tables_with_excalibur(file_id)
            
            if tables:
                result_file = download_excalibur_results(file_id)
                print(f"\n🎯 SUCCESS: {result_file}")
                return result_file
        
        print("❌ Excalibur extraction failed")
        return None
    
    finally:
        # Clean up server
        if server_process:
            print("🛑 Stopping Excalibur server...")
            server_process.terminate()
            server_process.wait()

if __name__ == "__main__":
    result = test_excalibur_extraction()
    
    if result:
        print(f"\n✅ Excalibur extraction completed!")
        print(f"Result file: {result}")
        print("You can now analyze this file for exact counts.")
    else:
        print("\n❌ Excalibur extraction failed")
        print("Consider trying other methods or manual conversion.")