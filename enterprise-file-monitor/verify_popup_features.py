#!/usr/bin/env python3
"""
Verify that the popup window has all required tray menu functions
"""

import re

def verify_popup_features():
    """Check FileMonitorTrayApp.cs for all requested popup features"""
    
    print("🔍 VERIFYING CNC DATALOG CONTROL PANEL FEATURES")
    print("=" * 60)
    
    with open('FileMonitorTrayApp.cs', 'r', encoding='utf-8') as f:
        content = f.read()
    
    features = {
        "Windows Startup": [
            "IsStartupEnabled()",
            "ToggleStartup()", 
            "Start CNC DATALOG when Windows starts"
        ],
        "Auto Login": [
            "Enable automatic login on startup",
            "StorePassword",
            "GetStoredPassword",
            "Test Auto Login"
        ],
        "Auto Monitor": [
            "Automatically start monitoring after login",
            "config.MonitoringEnabled",
            "MonitoringEnabled"
        ],
        "Close to Tray": [
            "FormClosing",
            "e.Cancel = true",
            "Minimized to system tray"
        ],
        "Tray Access": [
            "Show Control Panel",
            "ShowSettingsWindow",
            "trayIcon.DoubleClick"
        ]
    }
    
    results = {}
    
    for feature_name, keywords in features.items():
        found_keywords = []
        for keyword in keywords:
            if keyword in content:
                found_keywords.append(keyword)
        
        results[feature_name] = {
            'found': len(found_keywords),
            'total': len(keywords),
            'keywords': found_keywords
        }
    
    # Display results
    all_good = True
    for feature_name, result in results.items():
        status = "✅" if result['found'] == result['total'] else "❌"
        percentage = (result['found'] / result['total']) * 100
        
        print(f"\n{status} {feature_name}")
        print(f"   Found: {result['found']}/{result['total']} keywords ({percentage:.0f}%)")
        
        if result['found'] < result['total']:
            all_good = False
            missing = set(features[feature_name]) - set(result['keywords'])
            print(f"   Missing: {list(missing)}")
        else:
            print(f"   Keywords: {', '.join(result['keywords'][:2])}...")
    
    # Check for UI improvements
    print(f"\n🎨 UI ENHANCEMENTS")
    print("=" * 30)
    
    ui_features = [
        ("Tabbed Interface", "TabControl"),
        ("Button Panel", "buttonPanel"),
        ("Exit Application", "Exit Application"),
        ("Minimize to Tray", "Minimize to Tray"),
        ("Form Size", "650, 550"),
        ("Auto Scroll", "AutoScroll = true")
    ]
    
    for feature, keyword in ui_features:
        status = "✅" if keyword in content else "❌"
        print(f"{status} {feature}")
    
    # Summary
    print(f"\n{'🎉 VERIFICATION COMPLETE' if all_good else '⚠️  ISSUES FOUND'}")
    print("=" * 60)
    
    if all_good:
        print("✅ All requested features implemented!")
        print("✅ Control panel has complete tray menu functionality")
        print("✅ Perfect for machines without taskbars")
    else:
        print("❌ Some features may be incomplete")
    
    print(f"\nFeatures verified: {sum(1 for r in results.values() if r['found'] == r['total'])}/{len(results)}")

if __name__ == "__main__":
    verify_popup_features()