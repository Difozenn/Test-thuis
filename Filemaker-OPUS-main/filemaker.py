import os
import pandas as pd
from datetime import datetime

def scan_directory(directory):
    """
    Recursively scan a directory and collect file information
    """
    files = []
    
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            try:
                # Get file size in bytes
                size = os.path.getsize(file_path)
                # Get last modified time
                modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                files.append({
                    'Filename': filename,
                    'Full Path': file_path,
                    'Size (bytes)': size,
                    'Last Modified': modified
                })
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
    
    return files

def main():
    # Get the directory to scan
    directory = input("Enter the directory path to scan: ")
    
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist!")
        return
    
    # Scan the directory
    print("Scanning directory...")
    files = scan_directory(directory)
    
    # Create DataFrame
    df = pd.DataFrame(files)
    
    # Generate output filename
    output_file = os.path.join(directory, "data.xlsx")
    
    # Save to Excel
    print(f"Saving to {output_file}...")
    df.to_excel(output_file, index=False)
    print(f"File list has been saved to {output_file}")

if __name__ == "__main__":
    main()
