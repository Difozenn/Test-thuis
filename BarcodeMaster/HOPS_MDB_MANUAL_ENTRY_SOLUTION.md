# HOPS and MDB Processing for Manual Entry and Edited Scans

## Overview
This document explains how HOPS (OPUS) and MDB (KL GANNOMAT) processing works for manual entry and edited scans in the BarcodeMaster system.

## Problem Statement
When users manually enter data or edit scanned items for OPUS (HOPS_PROCESSING) or KL GANNOMAT (MDB_PROCESSING), the system needs to:
1. Generate Excel files with generic items (like other processing types)
2. Store these files in the correct database paths
3. Create proper directory structures (for HOPS)
4. Send appropriate database events for tracking

## Solution Architecture

### 1. New Generator Functions (excel_processing_functions.py)

#### `generate_hops_for_manual_entry()`
- **Purpose**: Creates HOPS directory structure and Excel file for manual entry
- **Location**: Creates directory in OPUS/KORPUS path (e.g., `Y:/OPUS/KORPUS/`)
- **Directory Format**: `MMDD_ProjectName` (e.g., `1013_MO6798_Vestiaire_(16-16)`)
- **Excel File**: Created inside the project directory with same name
- **Content**: 
  - Main sheet: `Items` with Item and Status columns
  - Hidden metadata sheet: `_ProjectInfo` with project details
- **Returns**: Full path to generated Excel file

**Example Output:**
```
Y:/OPUS/KORPUS/1013_MO6798_Vestiaire_(16-16)/1013_MO6798_Vestiaire_(16-16).xlsx
```

#### `generate_mdb_for_manual_entry()`
- **Purpose**: Creates MDB Excel file for manual entry
- **Location**: KL GANNOMAT path (e.g., `Y:/Kl_Gannomat/backend/jobs/`)
- **File Format**: `MMDD_ProjectName.xlsx` (e.g., `1013_MO6798_Vestiaire_(16-16).xlsx`)
- **Content**: 
  - Main sheet: `Items` with Item and Status columns (matching MDB format)
  - Hidden metadata sheet: `_ProjectInfo` with project details and type marker
- **Returns**: Full path to generated Excel file
- **Note**: Creates Excel as placeholder since actual MDB file creation requires Access/ODBC

**Example Output:**
```
Y:/Kl_Gannomat/backend/jobs/1013_MO6798_Vestiaire_(16-16).xlsx
```

### 2. Integration with Manual Entry (scanner_panel.py)

The `_process_manual_entry()` function now handles HOPS and MDB processing:

```python
# Import new generators
from services.excel_processing_functions import (
    generate_hops_for_manual_entry,
    generate_mdb_for_manual_entry
)

# Generate files based on processing type
if processing_type == 'HOPS_PROCESSING':
    excel_path = generate_hops_for_manual_entry(
        items_list, mo_number, so_number, customer_name, project_code
    )
elif processing_type == 'MDB_PROCESSING':
    excel_path = generate_mdb_for_manual_entry(
        items_list, mo_number, so_number, customer_name, project_code
    )
```

### 3. Database Event Flow

When manual entry or edited scan is processed:

1. **Excel Generation**: Files are created in appropriate directories
2. **BACKGROUND_WORK_FOUND**: Callback sent with item count
3. **OPEN Event**: Sent to database API with:
   - `file_path`: Path to generated Excel
   - `item_count`: Number of items
   - `project`: Project code
   - `user`: OPUS or KL GANNOMAT
   - `processing_type`: HOPS_PROCESSING or MDB_PROCESSING
4. **BEZIG Event**: Sent when user starts processing

### 4. File Structure Examples

#### HOPS Manual Entry
```
Y:/OPUS/KORPUS/
└── 1013_MO6798_Vestiaire_(16-16)/
    └── 1013_MO6798_Vestiaire_(16-16).xlsx
        ├── [Items] Sheet
        │   ├── Item 1
        │   ├── Item 2
        │   └── ...
        └── [_ProjectInfo] Sheet (hidden)
            ├── project_name: MO6798_Vestiaire_(16-16)
            ├── mo_number: MO6798
            ├── so_number: S03673
            ├── customer_name: Frank Celis
            ├── created_by: BarcodeMaster
            └── directory: Y:/OPUS/KORPUS/1013_MO6798_Vestiaire_(16-16)
```

#### MDB Manual Entry
```
Y:/Kl_Gannomat/backend/jobs/
└── 1013_MO6798_Vestiaire_(16-16).xlsx
    ├── [Items] Sheet
    │   ├── Item 1
    │   ├── Item 2
    │   └── ...
    └── [_ProjectInfo] Sheet (hidden)
        ├── project_name: MO6798_Vestiaire_(16-16)
        ├── mo_number: MO6798
        ├── so_number: S03673
        ├── customer_name: Frank Celis
        ├── created_by: BarcodeMaster
        └── type: MDB_MANUAL
```

## Use Cases

### Use Case 1: Manual Entry for OPUS
1. User opens manual entry dialog
2. Enters project code: `MO6798_Vestiaire_(16-16)`
3. Selects OPUS user with 30 items
4. System creates:
   - Directory: `Y:/OPUS/KORPUS/1013_MO6798_Vestiaire_(16-16)/`
   - Excel: `1013_MO6798_Vestiaire_(16-16).xlsx` with 30 generic items
5. Database receives OPEN event with file path and item count
6. User can now process these items normally

### Use Case 2: Edited Scan for KL GANNOMAT
1. User scans barcode for existing project
2. System extracts data and shows confirmation popup
3. User clicks "Bewerken" (Edit)
4. Modifies KL GANNOMAT item count from 0 to 15
5. Confirms changes
6. System creates:
   - Excel: `Y:/Kl_Gannomat/backend/jobs/1013_MO6798_Vestiaire_(16-16).xlsx` with 15 items
7. Database receives updated OPEN event
8. User can process these items

### Use Case 3: Mixed Processing Types
1. User enters manual data for multiple users:
   - NESTING: 66 items (no Excel needed)
   - ACCURA: 55 items → Excel in Y:/Stuklijsten/
   - OPUS: 30 items → Directory + Excel in Y:/OPUS/KORPUS/
   - KL GANNOMAT: 1 item → Excel in Y:/Kl_Gannomat/backend/jobs/
2. System generates all files in parallel
3. Each user gets separate OPEN event with correct file path
4. All items tracked in database

## Configuration Requirements

### Database Settings (via API)
The system requires these paths to be configured in the database:

```json
{
  "user_paths": {
    "OPUS": "Y:/OPUS/KORPUS",
    "KL GANNOMAT": "Y:/Kl_Gannomat/backend/jobs"
  }
}
```

### User Processing Type Mapping
```json
{
  "scanner_user_to_processing_type_map": {
    "OPUS": "HOPS_PROCESSING",
    "KL GANNOMAT": "MDB_PROCESSING"
  }
}
```

## Benefits

1. **Consistency**: HOPS and MDB now work the same way as other processing types
2. **Traceability**: All files stored in correct database paths with metadata
3. **Flexibility**: Users can manually enter or edit data for any processing type
4. **Database Integration**: All events properly logged for reporting and tracking
5. **Generic Items**: System creates placeholder items that users can process normally

## Technical Details

### Generic Item Format
For manual entry, items are created as:
- `Item 1`, `Item 2`, `Item 3`, etc.
- Each with empty Status column for user to fill during processing

### Metadata Preservation
All generated files include hidden metadata sheet with:
- Project identification (MO, SO, customer)
- Creation source (BarcodeMaster)
- File location (for HOPS)
- Processing type marker (for MDB)

### Error Handling
- If directory creation fails, error logged and user notified
- If Excel generation fails, warning shown but other users still processed
- Missing configuration (paths) results in clear error message

## Future Enhancements

1. **Actual MDB File Creation**: Integrate with Access/ODBC to create real .mdb files
2. **HOP File Generation**: Create actual .hop files instead of just Excel
3. **Template Support**: Allow custom item templates instead of generic items
4. **Bulk Import**: Import item lists from external files
5. **Validation**: Check for duplicate projects before creating files

## Testing Checklist

- [ ] Manual entry for OPUS creates directory and Excel
- [ ] Manual entry for KL GANNOMAT creates Excel in correct path
- [ ] Edited scans update item counts correctly
- [ ] Database receives all OPEN events with file paths
- [ ] Files contain correct metadata
- [ ] Multiple users can be processed simultaneously
- [ ] Error handling works for missing paths
- [ ] Generic items are properly formatted
- [ ] Status column is empty and editable
- [ ] Files are accessible by background import service

## Related Files

- `services/excel_processing_functions.py`: Generator functions
- `gui/panels/scanner_panel.py`: Manual entry and edit processing
- `services/background_import_service.py`: Automatic HOPS/MDB processing
- `database/db_log_api.py`: Database event handling
