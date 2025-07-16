#!/usr/bin/env python3
"""
PDF24 API EXTRACTOR
Use PDF24's free PDF conversion services
"""

import requests
import os
import time
import json

def upload_to_pdf24(pdf_path: str):
    """Upload PDF to PDF24 for conversion"""
    
    print("📤 Uploading to PDF24...")
    
    try:
        # PDF24 upload endpoint
        upload_url = "https://developer-api.pdf24.org/upload"
        
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            
            response = requests.post(upload_url, files=files, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            file_id = result.get('fileId')
            print(f"✅ Upload successful, File ID: {file_id}")
            return file_id
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def convert_with_pdf24(file_id: str):
    """Convert PDF to Excel using PDF24 API"""
    
    print("🔄 Converting with PDF24...")
    
    try:
        # PDF24 conversion endpoint
        convert_url = "https://developer-api.pdf24.org/convert"
        
        payload = {
            'fileId': file_id,
            'outputFormat': 'xlsx',
            'options': {
                'preserveFormatting': True,
                'extractTables': True,
                'singleSheet': True
            }
        }
        
        response = requests.post(convert_url, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('jobId')
            print(f"✅ Conversion started, Job ID: {job_id}")
            return job_id
        else:
            print(f"❌ Conversion failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    
    except Exception as e:
        print(f"❌ Conversion error: {e}")
        return None

def check_pdf24_status(job_id: str):
    """Check PDF24 conversion status"""
    
    print("⏳ Checking conversion status...")
    
    for attempt in range(30):  # Wait up to 5 minutes
        try:
            status_url = f"https://developer-api.pdf24.org/status/{job_id}"
            response = requests.get(status_url, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                status = result.get('status')
                
                if status == 'completed':
                    download_url = result.get('downloadUrl')
                    print("✅ Conversion completed!")
                    return download_url
                elif status == 'failed':
                    print("❌ Conversion failed")
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
    
    print("⏰ Conversion timeout")
    return None

def download_from_pdf24(download_url: str, output_file: str):
    """Download converted file from PDF24"""
    
    print("💾 Downloading converted file...")
    
    try:
        response = requests.get(download_url, timeout=60)
        
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Download successful: {output_file}")
            return output_file
        else:
            print(f"❌ Download failed: {response.status_code}")
            return None
    
    except Exception as e:
        print(f"❌ Download error: {e}")
        return None

def try_pdf24_direct_api():
    """Try PDF24 direct API approach"""
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return None
    
    print("🔧 TESTING PDF24 API")
    print("=" * 50)
    
    # Upload file
    file_id = upload_to_pdf24(pdf_path)
    if not file_id:
        return None
    
    # Convert file
    job_id = convert_with_pdf24(file_id)
    if not job_id:
        return None
    
    # Check status and get download URL
    download_url = check_pdf24_status(job_id)
    if not download_url:
        return None
    
    # Download result
    output_file = pdf_path.replace('.PDF', '_pdf24.xlsx').replace('.pdf', '_pdf24.xlsx')
    result_file = download_from_pdf24(download_url, output_file)
    
    return result_file

def try_pdf24_web_automation():
    """Try automating PDF24 web interface"""
    
    print("🌐 TRYING PDF24 WEB AUTOMATION")
    print("=" * 50)
    
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
        
        if not os.path.exists(pdf_path):
            print(f"❌ PDF not found: {pdf_path}")
            return None
        
        print("🚀 Starting browser automation...")
        
        # Setup Chrome driver
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=options)
        
        try:
            # Navigate to PDF24 converter
            driver.get("https://tools.pdf24.org/en/pdf-to-excel")
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            
            # Find file upload element
            upload_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            
            # Upload file
            print("📤 Uploading file...")
            upload_element.send_keys(os.path.abspath(pdf_path))
            
            # Wait for upload to complete and conversion to start
            print("⏳ Waiting for conversion...")
            time.sleep(30)  # Give time for conversion
            
            # Look for download button
            download_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[download], button[download]"))
            )
            
            # Get download URL
            download_url = download_button.get_attribute('href')
            
            if download_url:
                print("✅ Conversion completed!")
                
                # Download the file
                output_file = pdf_path.replace('.PDF', '_pdf24_web.xlsx').replace('.pdf', '_pdf24_web.xlsx')
                
                response = requests.get(download_url, timeout=60)
                if response.status_code == 200:
                    with open(output_file, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ File downloaded: {output_file}")
                    return output_file
            
            print("❌ Could not find download link")
            return None
        
        finally:
            driver.quit()
    
    except ImportError:
        print("❌ Selenium not available")
        return None
    except Exception as e:
        print(f"❌ Web automation error: {e}")
        return None

def try_pdf24_simple_post():
    """Try simple POST to PDF24 tools"""
    
    print("📡 TRYING PDF24 SIMPLE POST")
    print("=" * 50)
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return None
    
    try:
        # Try posting directly to PDF24 tools
        url = "https://tools.pdf24.org/en/pdf-to-excel"
        
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            data = {
                'outputFormat': 'xlsx',
                'preserveFormatting': 'true'
            }
            
            response = requests.post(url, files=files, data=data, timeout=120)
        
        if response.status_code == 200:
            # Check if response is Excel file
            if response.headers.get('content-type', '').startswith('application/vnd.openxmlformats'):
                output_file = pdf_path.replace('.PDF', '_pdf24_simple.xlsx').replace('.pdf', '_pdf24_simple.xlsx')
                
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ Simple POST successful: {output_file}")
                return output_file
            else:
                print("❌ Response is not Excel file")
                print(f"Content-Type: {response.headers.get('content-type')}")
                return None
        else:
            print(f"❌ Simple POST failed: {response.status_code}")
            return None
    
    except Exception as e:
        print(f"❌ Simple POST error: {e}")
        return None

def test_pdf24_methods():
    """Test all PDF24 methods"""
    
    print("📊 TESTING PDF24 EXTRACTION METHODS")
    print("=" * 70)
    
    methods = [
        ("PDF24 Simple POST", try_pdf24_simple_post),
        ("PDF24 Direct API", try_pdf24_direct_api),
        ("PDF24 Web Automation", try_pdf24_web_automation),
    ]
    
    for method_name, method_func in methods:
        print(f"\n📊 Testing {method_name}...")
        
        try:
            result_file = method_func()
            
            if result_file and os.path.exists(result_file):
                file_size = os.path.getsize(result_file)
                print(f"✅ Success: {result_file} ({file_size} bytes)")
                
                # Analyze the result
                try:
                    import pandas as pd
                    df = pd.read_excel(result_file)
                    print(f"   Content: {len(df)} rows × {len(df.columns)} columns")
                    
                    content = df.to_string().lower()
                    if 'nesting' in content:
                        print("   ✅ Contains 'nesting'")
                    if 'aantal onderdelen' in content:
                        print("   ✅ Contains 'aantal onderdelen'")
                    
                except Exception as e:
                    print(f"   Analysis failed: {e}")
                
                return result_file
            else:
                print(f"❌ {method_name} failed")
        
        except Exception as e:
            print(f"❌ {method_name} error: {e}")
    
    print("\n❌ All PDF24 methods failed")
    return None

if __name__ == "__main__":
    result = test_pdf24_methods()
    
    if result:
        print(f"\n✅ PDF24 extraction successful!")
        print(f"Result: {result}")
    else:
        print("\n❌ PDF24 extraction failed")
        print("PDF24 might require authentication or have CORS restrictions.")