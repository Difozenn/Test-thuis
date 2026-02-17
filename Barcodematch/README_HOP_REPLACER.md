# HOP File Replacer

A simple Python GUI application to search and replace text in `.hop`, `.hops`, and `.hopx` files.

## Features

- **GUI Interface**: Easy-to-use graphical interface built with tkinter
- **File Selection**: Select individual files or entire folders
- **Search & Replace**: Find and replace any text (default: "_V8" → "_V5")
- **Preview**: See all changes before applying them
- **Export**: Save modified files to a new folder with timestamp
- **Safe**: Original files are never modified - only exports new versions

## Requirements

- Python 3.6 or higher
- tkinter (usually included with Python)

## Installation

No additional packages required! Just ensure you have Python installed.

## Usage

### Running the Application

1. Double-click `hop_file_replacer.py` or run from command line:
   ```
   python hop_file_replacer.py
   ```

### Step-by-Step Guide

1. **Select Files**:
   - Click "Select Files" to choose individual .hop/.hops/.hopx files
   - OR click "Select Folder" to automatically find all HOP files in a directory

2. **Configure Search & Replace** (optional):
   - Default is "_V8" → "_V5"
   - You can change these to any text you want to find and replace

3. **Preview Changes**:
   - Click "Preview Changes" to see what will be modified
   - The preview shows:
     - Which files contain the search text
     - How many replacements will be made in each file
     - Total number of replacements

4. **Export Modified Files**:
   - Click "Apply & Export"
   - Choose a destination folder
   - Modified files will be saved in a timestamped subfolder
   - Original files remain unchanged

5. **Clear** (optional):
   - Click "Clear" to reset and start over

## Example

If you have files with "_V8" in them and want to change to "_V5":

1. Select your .hop files
2. Click "Preview Changes" to verify
3. Click "Apply & Export"
4. Choose where to save the modified files
5. Done! Your new files are ready in the export folder

## Notes

- Original files are **never modified**
- All modified files are exported to a new folder
- The export folder is timestamped (e.g., `hop_replaced_20241203_140530`)
- Files are read with UTF-8 encoding with error handling for compatibility

## Troubleshooting

- **No files found**: Make sure your files have .hop, .hops, or .hopx extensions
- **Can't read file**: Some files may have encoding issues - these will be skipped with an error message
- **No replacements found**: The search text doesn't exist in the selected files

## License

Free to use and modify as needed.
