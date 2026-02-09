import tkinter as tk
from tkinter import PhotoImage
from PIL import Image, ImageTk
import os

# Panel imports for BarcodeMatch
from gui.panels.import_panel import ImportPanel
from gui.panels.scanner_panel import ScannerPanel
from gui.panels.email_panel import EmailPanel
from gui.panels.database_panel import DatabasePanel
from gui.panels.help_panel import HelpPanel
from gui.panels.settings_panel import SettingsPanel
from gui.asset_utils import get_asset_path, asset_exists

MENU_OPTIONS = [
    {"name": "Import", "panel": ImportPanel, "icon": "importeren.png"},
    {"name": "Scanner", "panel": ScannerPanel, "icon": "scanner.png"},
    {"name": "Email", "panel": EmailPanel, "icon": "email.png"},
    {"name": "Database", "panel": DatabasePanel, "icon": "database.png"},
    {"name": "Help", "panel": HelpPanel, "icon": "help.png"},
    {"name": "Settings", "panel": SettingsPanel, "icon": "settings.png"},
]

def create_menu(root, main_app):
    menu_frame = tk.Frame(root, bg="#f0f0f0", height=75)
    menu_frame.pack(side=tk.TOP, fill=tk.X, padx=(5, 0))
    menu_frame.pack_propagate(False)

    # Load icons for each menu option
    icon_imgs = []
    for opt in MENU_OPTIONS:
        icon_path = get_asset_path(opt["icon"])
        if os.path.exists(icon_path):
            try:
                pil_img = Image.open(icon_path).resize((75, 75), Image.LANCZOS)
                icon_img = ImageTk.PhotoImage(pil_img)
            except Exception as e:
                print(f"[ERROR] Failed to load icon {opt['icon']}: {e}")
                icon_img = None
        else:
            print(f"[WARNING] Icon file not found: {icon_path}")
            icon_img = None
        icon_imgs.append(icon_img)
    root.icon_imgs = icon_imgs  # Prevent garbage-collection

    # Track active tab and buttons
    root.active_tab = tk.IntVar(value=0)
    root._tab_buttons = []
    root._active_panel = None

    def update_tabs():
        MENU_BG = "#f0f0f0"
        for idx, (btn, frame) in enumerate(zip(root._tab_buttons, root._tab_frames)):
            if idx == root.active_tab.get():
                # Frame should not be highlighted, button color indicates active state
                frame.config(bg=MENU_BG, highlightbackground=MENU_BG, highlightcolor=MENU_BG, highlightthickness=0)
                btn.config(bg="#d0e0ff", relief=tk.FLAT)
            else:
                frame.config(bg=MENU_BG, highlightbackground=MENU_BG, highlightcolor=MENU_BG, highlightthickness=0)
                btn.config(bg=MENU_BG, relief=tk.FLAT)

    def open_panel_idx(idx):
        # Get the current and new panel names
        current_panel_name = None
        if root._active_panel is not None:
            # Find current panel name
            for opt in MENU_OPTIONS:
                if isinstance(root._active_panel, opt["panel"]):
                    current_panel_name = opt["name"]
                    break
        
        new_panel_name = MENU_OPTIONS[idx]["name"]
        
        # Handle session pause/resume for Scanner panel
        from gui.panels.scanner_panel import ScannerPanel
        
        # NOTE: The Scanner panel's pack_forget() method will handle pausing
        # We don't need to manually call _pause_session here
        
        # Hide any existing panel - this will trigger pack_forget which handles pause
        if root._active_panel is not None:
            try:
                if hasattr(root._active_panel, 'winfo_exists') and root._active_panel.winfo_exists():
                    root._active_panel.pack_forget()  # This calls the overridden pack_forget in ScannerPanel
            except tk.TclError:
                pass  # Widget already destroyed
        
        # Show the persistent panel instance
        panel = main_app.get_panel_by_name(new_panel_name)
        if panel:
            root._active_panel = panel  # Assign before pack!
            panel.pack(fill=tk.BOTH, expand=True)  # This calls the overridden pack() in ScannerPanel which handles resume
            
            # If this is the DatabasePanel, start auto-refresh after packing
            from gui.panels.database_panel import DatabasePanel
            if isinstance(panel, DatabasePanel):
                panel.start_auto_refresh()
                
            root.active_tab.set(idx)
            update_tabs()

    MENU_BG = "#f0f0f0"
    root._tab_buttons = []
    root._tab_frames = []
    for idx, opt in enumerate(MENU_OPTIONS):
        frame = tk.Frame(menu_frame, width=75, height=75, bg=MENU_BG, highlightthickness=0)
        frame.pack_propagate(False)
        frame.pack(side=tk.LEFT, padx=0, pady=0)
        
        # Create button with or without icon
        btn_kwargs = {
            'command': lambda i=idx: open_panel_idx(i),
            'width': 75, 
            'height': 75,
            'bg': MENU_BG,
            'activebackground': "#d0e0ff",
            'activeforeground': "black",
            'relief': tk.FLAT,
            'bd': 0,
            'highlightthickness': 0,
            'takefocus': 0
        }
        
        if icon_imgs[idx]:
            btn_kwargs['image'] = icon_imgs[idx]
        else:
            btn_kwargs['text'] = opt["name"]
            
        btn = tk.Button(frame, **btn_kwargs)
        btn.pack(expand=True, fill=tk.BOTH, padx=0, pady=0)
        root._tab_buttons.append(btn)
        root._tab_frames.append(frame)

    # ============================================================================
    # SPOED WARNING BOX - Enterprise Style
    # ============================================================================

    # Outer container with border effect
    root.spoed_warning_frame = tk.Frame(menu_frame, bg="#dc3545", height=65, width=320)
    root.spoed_warning_frame.pack_propagate(False)

    # Main card with subtle inner shadow effect
    spoed_card = tk.Frame(root.spoed_warning_frame, bg="#fff5f5", height=61, width=316)
    spoed_card.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    spoed_card.pack_propagate(False)

    # Left accent bar (urgent red)
    spoed_accent = tk.Frame(spoed_card, bg="#dc3545", width=4)
    spoed_accent.pack(side=tk.LEFT, fill=tk.Y)

    # Content area
    spoed_content = tk.Frame(spoed_card, bg="#fff5f5")
    spoed_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 8), pady=8)

    # Header row with icon and title
    spoed_header = tk.Frame(spoed_content, bg="#fff5f5")
    spoed_header.pack(fill=tk.X)

    # Warning indicator dot
    spoed_dot = tk.Label(
        spoed_header,
        text="\u25CF",  # Bullet point
        bg="#fff5f5",
        fg="#dc3545",
        font=("Arial", 8)
    )
    spoed_dot.pack(side=tk.LEFT, padx=(0, 4))

    # "URGENT" label
    spoed_title = tk.Label(
        spoed_header,
        text="SPOED",
        bg="#fff5f5",
        fg="#dc3545",
        font=("Segoe UI", 9, "bold")
    )
    spoed_title.pack(side=tk.LEFT)

    # Project name label
    root.spoed_warning_label = tk.Label(
        spoed_content,
        text="",
        bg="#fff5f5",
        fg="#1a1a1a",
        font=("Segoe UI", 10),
        anchor="w"
    )
    root.spoed_warning_label.pack(fill=tk.X, pady=(2, 0))

    # Close button area
    spoed_btn_frame = tk.Frame(spoed_card, bg="#fff5f5")
    spoed_btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8))

    # Close button - minimal style
    root.spoed_close_btn = tk.Button(
        spoed_btn_frame,
        text="\u2715",  # X symbol
        bg="#fff5f5",
        fg="#999999",
        font=("Segoe UI", 11),
        bd=0,
        highlightthickness=0,
        activebackground="#ffe5e5",
        activeforeground="#dc3545",
        cursor="hand2",
        command=lambda: hide_spoed_warning()
    )
    root.spoed_close_btn.pack(expand=True)

    # Track dismissed SPOED projects
    root.dismissed_spoed_projects = set()
    root.current_spoed_project = None

    def show_spoed_warning(project_name):
        """Show SPOED warning for a specific project"""
        if project_name not in root.dismissed_spoed_projects:
            root.current_spoed_project = project_name
            root.spoed_warning_label.config(text=project_name)
            # Pack with fixed width and vertical centering
            root.spoed_warning_frame.pack(side=tk.LEFT, padx=(15, 0), pady=5)
            root.spoed_warning_frame.pack_propagate(False)
            print(f"[SPOED WARNING] Showing warning for project: {project_name}")

    def hide_spoed_warning():
        """Hide the current SPOED warning and mark it as dismissed"""
        if root.current_spoed_project:
            root.dismissed_spoed_projects.add(root.current_spoed_project)
            print(f"[SPOED WARNING] Dismissed warning for project: {root.current_spoed_project}")
        root.spoed_warning_frame.pack_forget()
        root.current_spoed_project = None

    def auto_hide_spoed_warning():
        """Hide the current SPOED warning without marking as dismissed (for AFGEMELD projects)"""
        if root.current_spoed_project:
            print(f"[SPOED WARNING] Auto-hiding warning for AFGEMELD project: {root.current_spoed_project}")
        root.spoed_warning_frame.pack_forget()
        root.current_spoed_project = None

    # Store functions for external access
    root.show_spoed_warning = show_spoed_warning
    root.hide_spoed_warning = hide_spoed_warning
    root.auto_hide_spoed_warning = auto_hide_spoed_warning

    # ============================================================================
    # UPDATE NOTIFICATION BOX - Enterprise Style
    # ============================================================================

    # Outer container with border effect (blue theme)
    root.update_notification_frame = tk.Frame(menu_frame, bg="#0d6efd", height=65, width=300)
    root.update_notification_frame.pack_propagate(False)

    # Main card with light background
    update_card = tk.Frame(root.update_notification_frame, bg="#f0f7ff", height=61, width=296)
    update_card.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    update_card.pack_propagate(False)

    # Left accent bar (info blue)
    update_accent = tk.Frame(update_card, bg="#0d6efd", width=4)
    update_accent.pack(side=tk.LEFT, fill=tk.Y)

    # Content area
    update_content = tk.Frame(update_card, bg="#f0f7ff")
    update_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 8), pady=8)

    # Header row
    update_header = tk.Frame(update_content, bg="#f0f7ff")
    update_header.pack(fill=tk.X)

    # Update indicator dot
    update_dot = tk.Label(
        update_header,
        text="\u25CF",  # Bullet point
        bg="#f0f7ff",
        fg="#0d6efd",
        font=("Arial", 8)
    )
    update_dot.pack(side=tk.LEFT, padx=(0, 4))

    # "UPDATE" label
    update_title = tk.Label(
        update_header,
        text="UPDATE",
        bg="#f0f7ff",
        fg="#0d6efd",
        font=("Segoe UI", 9, "bold")
    )
    update_title.pack(side=tk.LEFT)

    # Version label
    root.update_notification_label = tk.Label(
        update_content,
        text="Nieuwe versie beschikbaar",
        bg="#f0f7ff",
        fg="#1a1a1a",
        font=("Segoe UI", 10),
        anchor="w"
    )
    root.update_notification_label.pack(fill=tk.X, pady=(2, 0))

    # Button area
    update_btn_frame = tk.Frame(update_card, bg="#f0f7ff")
    update_btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=12)

    # Install button - professional style
    root.update_install_btn = tk.Button(
        update_btn_frame,
        text="Installeren",
        bg="#0d6efd",
        fg="white",
        font=("Segoe UI", 9),
        bd=0,
        highlightthickness=0,
        activebackground="#0b5ed7",
        activeforeground="white",
        cursor="hand2",
        padx=12,
        pady=4,
        command=lambda: trigger_update_install()
    )
    root.update_install_btn.pack(expand=True)

    # Store update info
    root.available_update_version = None
    root.update_checker = None

    def show_update_notification(version, changelog=""):
        """Show update notification for a new version"""
        root.available_update_version = version
        root.update_notification_label.config(text=f"Versie {version} beschikbaar")
        # Pack with vertical centering
        root.update_notification_frame.pack(side=tk.LEFT, padx=(15, 0), pady=5)
        root.update_notification_frame.pack_propagate(False)
        print(f"[UPDATE] Showing notification for version: {version}")

    def hide_update_notification():
        """Hide the update notification"""
        root.update_notification_frame.pack_forget()
        root.available_update_version = None
        print("[UPDATE] Notification hidden")

    def trigger_update_install():
        """Trigger the update download and installation"""
        if root.update_checker and root.update_checker.available_update:
            # Disable button and show progress
            root.update_install_btn.config(text="Downloaden...", state=tk.DISABLED)

            def on_progress(progress):
                root.after(0, lambda: root.update_install_btn.config(text=f"{progress}%"))

            def on_complete(success):
                if success:
                    root.after(0, lambda: _execute_update())
                else:
                    root.after(0, lambda: _update_failed())

            root.update_checker.download_and_install_async(
                progress_callback=on_progress,
                completion_callback=on_complete
            )

    def _execute_update():
        """Execute the update after download completes"""
        from tkinter import messagebox

        result = messagebox.askyesno(
            "Update Installeren",
            f"Update {root.available_update_version} is gedownload.\n\n"
            "De applicatie wordt nu afgesloten en opnieuw gestart met de nieuwe versie.\n\n"
            "Doorgaan?",
            icon='info'
        )

        if result and root.update_checker:
            # Execute update (this will close the app)
            root.update_checker.execute_update()
            # Close the application
            root.quit()
            root.destroy()
        else:
            # Reset button
            root.update_install_btn.config(text="Installeren", state=tk.NORMAL)

    def _update_failed():
        """Handle update download failure"""
        from tkinter import messagebox
        messagebox.showerror(
            "Update Mislukt",
            "Kon de update niet downloaden.\n\n"
            "Controleer of het update pad correct is ingesteld in de instellingen."
        )
        root.update_install_btn.config(text="Installeren", state=tk.NORMAL)

    # Store functions for external access
    root.show_update_notification = show_update_notification
    root.hide_update_notification = hide_update_notification

    # Open the Database panel by default
    open_panel_idx(3)
    # Ensure frame backgrounds are set correctly at startup
    update_tabs()