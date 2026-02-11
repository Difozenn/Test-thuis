# Network Path Troubleshooting Guide

## Issue: Excel files not opening from database on network locations

### Symptoms
- Double-clicking a log entry in the database panel doesn't open the Excel file
- Error message: "Netwerkpad niet toegankelijk" (Network path not accessible)
- The file exists on the server but the application can't find it
- The folder shows under "Network locations" instead of "This PC"

### Common Causes

#### 1. **Mapped Drive vs UNC Path Mismatch**
Different computers may access the same network location differently:

- **Computer A** uses: `Y:\Projects\MO12345\file.xlsx` (mapped drive)
- **Computer B** uses: `\\server\share\Projects\MO12345\file.xlsx` (UNC path)

When the database stores a path from Computer A, Computer B can't find it because the `Y:` drive doesn't exist there.

#### 2. **Drive Not Mapped**
If the database contains a path like `Y:\...` but the Y: drive is not mapped on your computer, Windows cannot access the file.

#### 3. **Network Location Not Connected**
The network share may not be accessible due to:
- Network connectivity issues
- Permissions problems
- Server being offline

### Solutions

#### Solution 1: Map the Network Drive Consistently
Ensure all computers use the same drive letter for the network location:

1. Open **File Explorer**
2. Right-click on **This PC** → **Map network drive**
3. Choose the same drive letter (e.g., `Y:`) on all computers
4. Enter the network path (e.g., `\\server\share\Projects`)
5. Check "Reconnect at sign-in"
6. Click **Finish**

#### Solution 2: Use UNC Paths in the Database
Configure the application to store UNC paths instead of mapped drives:

1. When browsing for files, use the UNC path format: `\\server\share\folder\file.xlsx`
2. Avoid using mapped drive letters in the configuration

#### Solution 3: Check Network Access
Verify you can access the network location:

1. Open **File Explorer**
2. In the address bar, type the path shown in the error message
3. Press Enter
4. If you can't access it:
   - Check your network connection
   - Verify you have permissions
   - Contact your IT administrator

### Diagnostic Information

The application now provides detailed diagnostic information when a path is not accessible:

- **Original path**: The path as stored in the database
- **Normalized path**: The path after Windows path normalization
- **Type**: Whether it's a UNC path or mapped drive

This information appears in the error dialog and in the console output (for debugging).

### Debug Output

When double-clicking a log entry, the application prints detailed debug information to the console:

```
[PATH DEBUG] Original: 'Y:\Projects\MO12345'
[PATH DEBUG] Normalized: 'Y:\Projects\MO12345'
[PATH DEBUG] Exists: False
[PATH DEBUG] Mapped drive 'Y:' not accessible
[PATH DEBUG] Drive may not be mapped on this computer
```

This helps identify whether the issue is:
- A missing mapped drive
- An inaccessible UNC path
- A path format issue

### Best Practices

1. **Consistent Drive Mapping**: Use the same drive letters across all computers
2. **UNC Paths**: Prefer UNC paths for better compatibility
3. **Test Access**: Always verify network access before assuming a path issue
4. **Document Mappings**: Keep a record of which network locations use which drive letters

### Technical Details

The application now includes path normalization that:
- Handles forward slashes vs backslashes
- Removes trailing slashes and spaces
- Attempts to resolve paths even if the format differs slightly
- Provides detailed error messages with diagnostic information

### Still Having Issues?

If the problem persists after trying these solutions:

1. Check the console output for detailed path information
2. Verify the exact path in Windows Explorer
3. Ensure the network location is accessible
4. Contact your system administrator for network access issues
5. Consider using the Import panel to re-import the project with the correct path
