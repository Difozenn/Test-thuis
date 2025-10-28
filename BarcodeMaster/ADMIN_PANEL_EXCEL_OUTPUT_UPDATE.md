# Admin Panel Excel Output Tab Update

## Changes Made

### Added OPUS and KL GANNOMAT to Excel Output Tab

The Excel Output tab in the Admin Panel now displays **all 6 users** that generate Excel files:

1. **ACCURA** - Regular output directory
2. **BOERE** - Regular output directory  
3. **MASSIEF** (GR GANNOMAT) - Regular output directory
4. **HANDWERK** - Regular output directory
5. **OPUS** - Uses User Path (read-only reference)
6. **KL GANNOMAT** - Uses User Path (read-only reference)

## How It Works

### Regular Users (ACCURA, BOERE, MASSIEF, HANDWERK)
- Have dedicated output directories configured via `{user}_output_dir` setting
- Browse button allows changing the output path
- Files are generated in these configured directories

### Special Users (OPUS, KL GANNOMAT)
- Use their **User Paths** (configured in User Configuration tab) as output directories
- Display shows the current User Path value (read-only)
- Button shows "ℹ️ User Path" (disabled) to indicate it's a reference
- Files are generated directly in their User Path directories:
  - **OPUS**: Creates subdirectories in `Y:/OPUS/KORPUS/`
  - **KL GANNOMAT**: Creates files in `Y:/Kl_Gannomat/backend/jobs/`

## UI Layout

```
Excel Output Directory Configuratie
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ️ Info text explaining that OPUS and KL GANNOMAT use User Paths

ACCURA Output Directory:     [C:/ACCURA                    ] [Browse]
BOERE Output Directory:      [C:/BOERE                     ] [Browse]
MASSIEF Output Directory:    [C:/MASSIEF                   ] [Browse]
HANDWERK Output Directory:   [C:/HANDWERK                  ] [Browse]
OPUS Output Directory:       [Y:/OPUS/KORPUS               ] [ℹ️ User Path]
KL GANNOMAT Output Directory:[Y:/Kl_Gannomat/backend/jobs  ] [ℹ️ User Path]

Directory Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ ACCURA directory bestaat: C:/ACCURA
✓ BOERE directory bestaat: C:/BOERE
✓ MASSIEF directory bestaat: C:/MASSIEF
✓ HANDWERK directory bestaat: C:/HANDWERK
✓ OPUS directory bestaat: Y:/OPUS/KORPUS
✓ KL GANNOMAT directory bestaat: Y:/Kl_Gannomat/backend/jobs
```

## Info Text Update

The info label now includes:

```
Configureer de output directories voor alle gebruikers die Excel bestanden genereren.
Deze directories worden gebruikt wanneer Excel bestanden worden gegenereerd uit de import processing.

ℹ️ OPUS en KL GANNOMAT gebruiken hun User Paths (geconfigureerd in User Configuration tab) als output directories.

⚠️ Deze instellingen worden opgeslagen in de database en worden automatisch gebackupt.
```

## Configuration Relationship

### For Regular Users
```
Database Setting: accura_output_dir
Used By: generate_excel_for_accura()
Example: C:/ACCURA/
```

### For OPUS
```
Database Setting: user_paths['OPUS']
Used By: generate_hops_for_manual_entry()
Example: Y:/OPUS/KORPUS/
Creates: Y:/OPUS/KORPUS/1013_MO6798_Vestiaire_(16-16)/
```

### For KL GANNOMAT
```
Database Setting: user_paths['KL GANNOMAT']
Used By: generate_mdb_for_manual_entry()
Example: Y:/Kl_Gannomat/backend/jobs/
Creates: Y:/Kl_Gannomat/backend/jobs/1013_MO6798_Vestiaire_(16-16).xlsx
```

## Why This Design?

### Separate Output Directories (ACCURA, BOERE, etc.)
- These users generate Excel files from scanned data
- Output location is separate from input Excel files
- Allows flexibility in organizing generated files

### User Paths as Output (OPUS, KL GANNOMAT)
- These users work with file-based databases (HOP files, MDB files)
- Files must be created in the same directory structure where they're processed
- Manual entry mimics the structure of scanned data
- Maintains consistency with automatic processing workflow

## Status Checking

The status update function checks all 6 users and displays:
- ✓ Green text if directory exists
- ⚠️ Warning if directory doesn't exist
- Works for both regular output directories and user paths

## Code Changes

### File: `admin_panel.py`

1. **Updated excel_users list** (2 locations):
   ```python
   excel_users = ['ACCURA', 'BOERE', 'MASSIEF', 'HANDWERK', 'OPUS', 'KL GANNOMAT']
   ```

2. **Added conditional logic** for OPUS and KL GANNOMAT:
   ```python
   if user in ['OPUS', 'KL GANNOMAT']:
       # Get path from user_paths instead of output_dir
       user_paths = settings.get('user_paths', {})
       path_value = user_paths.get(user, 'Not configured in User Paths')
       # Show as read-only with info button
   else:
       # Regular output directory with browse button
   ```

3. **Updated info label** to explain the difference

## Benefits

1. **Complete Visibility**: All Excel-generating users shown in one place
2. **Clear Distinction**: Visual difference between configurable and reference paths
3. **Consistency**: Status checking works for all users
4. **User Guidance**: Info text explains why OPUS/KL GANNOMAT are different
5. **No Confusion**: Disabled button prevents attempts to change User Paths from wrong location

## Testing

To verify the changes work correctly:

1. ✅ Open Admin Panel → Excel Output tab
2. ✅ Verify all 6 users are displayed
3. ✅ Verify OPUS and KL GANNOMAT show User Path values
4. ✅ Verify OPUS and KL GANNOMAT buttons are disabled
5. ✅ Verify other users have working Browse buttons
6. ✅ Verify status shows correct directory existence
7. ✅ Change User Path in User Configuration tab
8. ✅ Verify Excel Output tab reflects the change
9. ✅ Test manual entry for OPUS - file created in User Path
10. ✅ Test manual entry for KL GANNOMAT - file created in User Path

## Related Documentation

- See `HOPS_MDB_MANUAL_ENTRY_SOLUTION.md` for complete HOPS/MDB processing details
- See User Configuration tab for changing User Paths
