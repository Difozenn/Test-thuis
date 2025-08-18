#!/usr/bin/env python3
import sys
import subprocess
import os

def split_pdf(input_file, max_pages=100):
    """Split a PDF into chunks of max_pages"""
    
    # Get total pages
    result = subprocess.run(['pdfinfo', input_file], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'Pages:' in line:
            total_pages = int(line.split(':')[1].strip())
            break
    
    print(f"Total pages: {total_pages}")
    
    # Calculate number of parts needed
    num_parts = (total_pages + max_pages - 1) // max_pages
    
    # Create temp directory for individual pages
    temp_dir = "temp_pdf_pages"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Split the PDF using pdfseparate and pdfunite
    for i in range(num_parts):
        start_page = i * max_pages + 1
        end_page = min((i + 1) * max_pages, total_pages)
        
        output_file = input_file.replace('.pdf', f'_part{i+1}.pdf')
        
        # First extract the pages to temp files
        temp_pattern = os.path.join(temp_dir, f"page_%d.pdf")
        cmd_separate = [
            'pdfseparate', 
            '-f', str(start_page), 
            '-l', str(end_page),
            input_file, 
            temp_pattern
        ]
        
        print(f"Extracting pages {start_page}-{end_page}...")
        result = subprocess.run(cmd_separate, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error extracting: {result.stderr}")
            continue
            
        # Now unite the pages into a single PDF
        page_files = [os.path.join(temp_dir, f"page_{p}.pdf") for p in range(start_page, end_page+1)]
        cmd_unite = ['pdfunite'] + page_files + [output_file]
        
        print(f"Creating {output_file}...")
        result = subprocess.run(cmd_unite, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error uniting: {result.stderr}")
        else:
            print(f"Successfully created {output_file}")
            
        # Clean up temp files for this part
        for pf in page_files:
            if os.path.exists(pf):
                os.remove(pf)
    
    # Remove temp directory
    if os.path.exists(temp_dir):
        os.rmdir(temp_dir)
    
    print(f"Split into {num_parts} parts")

if __name__ == "__main__":
    input_file = "Leitz_Lexikon_Editie_7_-_05_Bovenfrezen.pdf"
    split_pdf(input_file)