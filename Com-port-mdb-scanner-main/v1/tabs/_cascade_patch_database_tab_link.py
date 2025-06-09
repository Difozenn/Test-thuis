# This patch should be manually added to scanner.py after the tab instantiation loop in COMPortComparator.__init__
def apply_database_tab_patch(main_app):
    print(f"[DEBUG] apply_database_tab_patch called. id(main_app): {id(main_app)}")
    if hasattr(main_app, 'tab_instances'):
        print(f"[DEBUG] main_app.tab_instances keys: {list(main_app.tab_instances.keys())}")
    if hasattr(main_app, 'tab_instances') and "Database" in main_app.tab_instances:
        main_app.database_tab = main_app.tab_instances["Database"]
        print("[DEBUG] Patched: main_app.database_tab set")
    else:
        print("[DEBUG] Patch failed: 'Database' not in tab_instances")
