#!/usr/bin/env python3
"""
Verify that the build error has been fixed
"""

import re

def verify_build_fix():
    """Check if the CycleCount property is now properly defined"""
    
    print("🔧 VERIFYING BUILD FIX")
    print("=" * 60)
    
    with open('FileMonitorTrayApp.cs', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the error location
    error_line = "double cycleOverheadTime = machineOps.CycleCount * 0.1;"
    
    print("1️⃣ Checking for the line that caused the error:")
    if error_line in content:
        print(f"  ✅ Found: {error_line}")
    else:
        print(f"  ❌ Not found (may have been modified)")
    
    # Check for MachineOperations class
    print("\n2️⃣ Checking MachineOperations class definition:")
    
    # Find the class definition
    class_match = re.search(r'private class MachineOperations\s*\{([^}]+)\}', content, re.DOTALL)
    if class_match:
        class_content = class_match.group(1)
        properties = re.findall(r'public \w+ (\w+)', class_content)
        print(f"  ✅ Found MachineOperations class with properties:")
        for prop in properties:
            print(f"     • {prop}")
        
        # Check for CycleCount
        if "CycleCount" in class_content:
            print(f"  ✅ CycleCount property is defined!")
            
            # Check if it's properly implemented
            if "CycleCount => OtherCycles" in class_content:
                print(f"  ✅ CycleCount is properly aliased to OtherCycles")
            else:
                print(f"  ⚠️  CycleCount exists but implementation unclear")
        else:
            print(f"  ❌ CycleCount property is NOT defined")
    
    # Check all usages of CycleCount
    print("\n3️⃣ Checking all usages of CycleCount:")
    cycle_count_usages = re.findall(r'machineOps\.CycleCount', content)
    print(f"  Found {len(cycle_count_usages)} usage(s) of machineOps.CycleCount")
    
    # Check all usages of OtherCycles
    other_cycles_usages = re.findall(r'ops\.OtherCycles', content)
    print(f"  Found {len(other_cycles_usages)} usage(s) of ops.OtherCycles")
    
    # Verify the fix
    print("\n✅ BUILD FIX VERIFICATION:")
    print("-" * 40)
    
    if "public int CycleCount => OtherCycles;" in content:
        print("✅ FIX APPLIED: CycleCount property added as alias to OtherCycles")
        print("✅ This should resolve the CS1061 compilation error")
        print("\n📋 The property works as follows:")
        print("  • OtherCycles stores the actual count")
        print("  • CycleCount provides read-only access via property")
        print("  • Both can be used interchangeably for reading")
        return True
    else:
        print("❌ FIX NOT FOUND: CycleCount property may still be missing")
        print("\n🔧 Suggested fix:")
        print("  Add to MachineOperations class:")
        print("  public int CycleCount => OtherCycles; // Alias for compatibility")
        return False

if __name__ == "__main__":
    success = verify_build_fix()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 BUILD ERROR SHOULD BE FIXED!")
        print("The project should now compile successfully.")
    else:
        print("⚠️  BUILD ERROR MAY STILL EXIST")
        print("Please verify the fix was applied correctly.")
    
    exit(0 if success else 1)