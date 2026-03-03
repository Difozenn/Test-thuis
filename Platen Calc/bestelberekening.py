#!/usr/bin/env python3
"""
Bestelberekening - Enterprise Material Order Calculation System
Professional-grade application for calculating material orders based on requirements and stock
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import csv
import os
import threading

# Import existing calculator
from material_calculator import MaterialCalculator


class ModernTheme:
    """Modern enterprise color scheme and styling"""

    # Colors
    PRIMARY = "#1a73e8"  # Google Blue
    PRIMARY_DARK = "#1557b0"
    PRIMARY_HOVER = "#1765cc"
    SECONDARY = "#34a853"  # Success Green
    SECONDARY_HOVER = "#2d9249"
    WARNING = "#fbbc04"
    DANGER = "#ea4335"
    DANGER_HOVER = "#d33426"

    BG_MAIN = "#ffffff"
    BG_SECONDARY = "#f8f9fa"
    BG_TERTIARY = "#e8eaed"
    BG_TERTIARY_HOVER = "#d3d5d8"

    TEXT_PRIMARY = "#202124"
    TEXT_SECONDARY = "#5f6368"
    TEXT_DISABLED = "#9aa0a6"

    BORDER = "#dadce0"

    # Fonts
    FONT_FAMILY = "Segoe UI"
    FONT_TITLE = (FONT_FAMILY, 16, "bold")
    FONT_HEADER = (FONT_FAMILY, 12, "bold")
    FONT_NORMAL = (FONT_FAMILY, 10)
    FONT_SMALL = (FONT_FAMILY, 9)
    FONT_BUTTON = (FONT_FAMILY, 10)

    @staticmethod
    def create_button(parent, text, command, style="primary", **pack_opts):
        """Create a styled button with hover effects.

        style: 'primary' (blue), 'secondary' (green), 'tertiary' (gray),
               'danger' (red)
        """
        styles = {
            'primary': {
                'bg': ModernTheme.PRIMARY,
                'fg': 'white',
                'hover': ModernTheme.PRIMARY_HOVER,
                'active': ModernTheme.PRIMARY_DARK,
            },
            'secondary': {
                'bg': ModernTheme.SECONDARY,
                'fg': 'white',
                'hover': ModernTheme.SECONDARY_HOVER,
                'active': '#247a3d',
            },
            'tertiary': {
                'bg': ModernTheme.BG_TERTIARY,
                'fg': ModernTheme.TEXT_PRIMARY,
                'hover': ModernTheme.BG_TERTIARY_HOVER,
                'active': '#c4c7ca',
            },
            'danger': {
                'bg': ModernTheme.DANGER,
                'fg': 'white',
                'hover': ModernTheme.DANGER_HOVER,
                'active': '#b92d20',
            },
        }
        s = styles.get(style, styles['primary'])

        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=s['bg'],
            fg=s['fg'],
            activebackground=s['active'],
            activeforeground=s['fg'],
            font=ModernTheme.FONT_BUTTON,
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=22,
            pady=9,
            cursor="hand2",
        )

        def on_enter(e):
            btn.configure(bg=s['hover'])

        def on_leave(e):
            btn.configure(bg=s['bg'])

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        if pack_opts is not None:
            btn.pack(**pack_opts)

        return btn


class BestelberekeningApp:
    """Enterprise-grade Material Order Calculation Application"""

    def __init__(self, root):
        self.root = root
        self.root.title("Bestelberekening")
        self.root.geometry("1600x900")
        self.root.configure(bg=ModernTheme.BG_SECONDARY)

        # Data storage
        self.orders_data = {}  # {material: netto_m2}
        self.file_data = []  # [{filename, materials, included}] - like platen_calc
        self.all_materials = []  # All unique materials
        self.stock_data = {}   # {material: stock_m2}
        self.stock_details = []  # [{id, material, lengte, breedte, dikte, aantal, m2}]
        self.settings = {
            'rendement_pct': 75.0
        }
        self.safety_margins = {}  # {material_id: safety_m2}
        self.material_rendement = {}  # {material_id: rendement_pct} - defaults to global if not set
        self.artikel_nummers = {}  # {material_id: artikel_nummer}
        self.calculation_results = []
        self.in_bestelling = {}  # {material: m2_in_bestelling} - user-editable values

        # Load settings from config
        self.load_config()

        # Init history database for export comparison
        from history_db import HistoryDB
        self.history_db = HistoryDB()

        # Setup modern styles
        self.setup_styles()

        # Build UI
        self.setup_ui()

        # Clean up DB on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_styles(self):
        """Configure modern ttk styles"""
        style = ttk.Style()

        # Use clam theme as base
        style.theme_use('clam')

        # Configure Notebook (tabs)
        style.configure(
            "TNotebook",
            background=ModernTheme.BG_SECONDARY,
            borderwidth=0
        )
        style.configure(
            "TNotebook.Tab",
            background=ModernTheme.BG_TERTIARY,
            foreground=ModernTheme.TEXT_PRIMARY,
            padding=[20, 10],
            font=ModernTheme.FONT_NORMAL
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", ModernTheme.BG_MAIN)],
            foreground=[("selected", ModernTheme.PRIMARY)],
            expand=[("selected", [1, 1, 1, 0])]
        )

        # Configure Frames
        style.configure(
            "Card.TFrame",
            background=ModernTheme.BG_MAIN,
            relief="flat",
            borderwidth=1
        )

        # Configure Labels
        style.configure(
            "Title.TLabel",
            background=ModernTheme.BG_MAIN,
            foreground=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_TITLE
        )
        style.configure(
            "Header.TLabel",
            background=ModernTheme.BG_MAIN,
            foreground=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_HEADER
        )
        style.configure(
            "Subtitle.TLabel",
            background=ModernTheme.BG_MAIN,
            foreground=ModernTheme.TEXT_SECONDARY,
            font=ModernTheme.FONT_SMALL
        )

        # Configure Buttons
        style.configure(
            "Primary.TButton",
            background=ModernTheme.PRIMARY,
            foreground="white",
            borderwidth=0,
            focuscolor='none',
            font=ModernTheme.FONT_NORMAL,
            padding=[20, 10]
        )
        style.map(
            "Primary.TButton",
            background=[("active", ModernTheme.PRIMARY_DARK)]
        )

        # Configure Treeview
        style.configure(
            "Modern.Treeview",
            background=ModernTheme.BG_MAIN,
            foreground=ModernTheme.TEXT_PRIMARY,
            fieldbackground=ModernTheme.BG_MAIN,
            borderwidth=0,
            font=ModernTheme.FONT_NORMAL,
            rowheight=30
        )
        style.configure(
            "Modern.Treeview.Heading",
            background=ModernTheme.BG_TERTIARY,
            foreground=ModernTheme.TEXT_PRIMARY,
            borderwidth=0,
            font=ModernTheme.FONT_HEADER
        )
        style.map(
            "Modern.Treeview",
            background=[("selected", ModernTheme.PRIMARY)],
            foreground=[("selected", "white")]
        )

    def setup_ui(self):
        """Build the main UI"""
        # Main container with padding
        main_container = tk.Frame(self.root, bg=ModernTheme.BG_SECONDARY)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Tabs container - now at the top
        tabs_frame = tk.Frame(main_container, bg=ModernTheme.BG_MAIN, relief="flat", bd=1)
        tabs_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Create notebook
        self.notebook = ttk.Notebook(tabs_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Create tabs
        self.tab1 = tk.Frame(self.notebook, bg=ModernTheme.BG_MAIN)
        self.tab2 = tk.Frame(self.notebook, bg=ModernTheme.BG_MAIN)
        self.tab3 = tk.Frame(self.notebook, bg=ModernTheme.BG_MAIN)
        self.tab4 = tk.Frame(self.notebook, bg=ModernTheme.BG_MAIN)
        self.tab5 = tk.Frame(self.notebook, bg=ModernTheme.BG_MAIN)
        self.tab6 = tk.Frame(self.notebook, bg=ModernTheme.BG_MAIN)

        self.notebook.add(self.tab1, text="  1. Orders  ")
        self.notebook.add(self.tab2, text="  2. Magazijn  ")
        self.notebook.add(self.tab3, text="  3. Instellingen  ")
        self.notebook.add(self.tab4, text="  4. Berekening  ")
        self.notebook.add(self.tab5, text="  5. Historiek  ")
        self.notebook.add(self.tab6, text="  6. Handmagazijn  ")

        # Build each tab
        self.build_tab1_orders()
        self.build_tab2_magazijn()
        self.build_tab3_instellingen()
        self.build_tab4_berekening()
        self.build_tab5_analyse()
        self.build_tab6_handmagazijn()

        # Status bar
        status_frame = tk.Frame(main_container, bg=ModernTheme.BG_MAIN, relief="flat", bd=1)
        status_frame.pack(fill=tk.X)

        self.status_var = tk.StringVar(value="Ready to start")
        status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_SECONDARY,
            font=ModernTheme.FONT_SMALL,
            anchor=tk.W,
            padx=20,
            pady=10
        )
        status_label.pack(fill=tk.X)

    def build_tab1_orders(self):
        """Build Orders tab"""
        # Standard container with consistent padding
        container = tk.Frame(self.tab1, bg=ModernTheme.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Header
        ttk.Label(
            container,
            text="Orders Scannen",
            style="Header.TLabel"
        ).pack(anchor=tk.W)

        ttk.Label(
            container,
            text="Scan Excel bestanden om netto m² per materiaal te berekenen",
            style="Subtitle.TLabel"
        ).pack(anchor=tk.W, pady=(5, 20))

        # Folder selection card
        folder_card = tk.Frame(container, bg=ModernTheme.BG_SECONDARY, relief="flat")
        folder_card.pack(fill=tk.X, pady=(0, 20))

        folder_inner = tk.Frame(folder_card, bg=ModernTheme.BG_SECONDARY)
        folder_inner.pack(fill=tk.X, padx=20, pady=20)

        tk.Label(
            folder_inner,
            text="Map met Excel bestanden",
            bg=ModernTheme.BG_SECONDARY,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_NORMAL
        ).pack(anchor=tk.W, pady=(0, 10))

        path_frame = tk.Frame(folder_inner, bg=ModernTheme.BG_SECONDARY)
        path_frame.pack(fill=tk.X)

        self.orders_folder_var = tk.StringVar(value=self.settings.get('orders_folder', 'Stuklijsten'))
        folder_entry = tk.Entry(
            path_frame,
            textvariable=self.orders_folder_var,
            font=ModernTheme.FONT_NORMAL,
            relief="solid",
            bd=1,
            bg=ModernTheme.BG_MAIN
        )
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        browse_btn = ModernTheme.create_button(
            path_frame, "Bladeren...", self.browse_orders_folder,
            style="tertiary", side=tk.LEFT)

        scan_btn = ModernTheme.create_button(
            folder_inner, "Scan Orders", self.scan_orders,
            style="primary", pady=(15, 0))

        # Progress bar (hidden by default)
        self.orders_progress = ttk.Progressbar(
            folder_inner,
            mode='indeterminate',
            style="TProgressbar"
        )
        self.orders_progress_label = tk.Label(
            folder_inner,
            text="",
            bg=ModernTheme.BG_SECONDARY,
            fg=ModernTheme.TEXT_SECONDARY,
            font=ModernTheme.FONT_SMALL
        )

        # Quick actions
        actions_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        actions_frame.pack(fill=tk.X, pady=(15, 15))

        ModernTheme.create_button(
            actions_frame, "Selecteer Alles", self.select_all_orders,
            style="tertiary", side=tk.LEFT, padx=(0, 10))

        ModernTheme.create_button(
            actions_frame, "Deselecteer Alles", self.deselect_all_orders,
            style="tertiary", side=tk.LEFT)

        # Results section header
        tk.Label(
            container,
            text="Gevonden Projecten",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_HEADER
        ).pack(anchor=tk.W, pady=(15, 10))

        # Table with horizontal scroll - fixed height for consistency
        table_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN, height=400)
        table_frame.pack(fill=tk.BOTH, expand=True)
        table_frame.pack_propagate(False)

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal")

        # Treeview - will be configured dynamically
        self.orders_tree = ttk.Treeview(
            table_frame,
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            style="Modern.Treeview",
            selectmode='browse'
        )

        vsb.config(command=self.orders_tree.yview)
        hsb.config(command=self.orders_tree.xview)

        # Pack scrollbars first, then treeview
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.orders_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind click events for checkbox
        self.orders_tree.bind('<Button-1>', self.on_orders_table_click)
        self.orders_tree.bind('<space>', self.on_orders_table_space)

    def build_tab2_magazijn(self):
        """Build Magazijn tab"""
        # Standard container with consistent padding
        container = tk.Frame(self.tab2, bg=ModernTheme.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Header
        ttk.Label(
            container,
            text="Magazijn Voorraad",
            style="Header.TLabel"
        ).pack(anchor=tk.W)

        ttk.Label(
            container,
            text="Laad huidige voorraad uit ContentResult CSV bestand",
            style="Subtitle.TLabel"
        ).pack(anchor=tk.W, pady=(5, 20))

        # File selection card
        file_card = tk.Frame(container, bg=ModernTheme.BG_SECONDARY, relief="flat")
        file_card.pack(fill=tk.X, pady=(0, 20))

        file_inner = tk.Frame(file_card, bg=ModernTheme.BG_SECONDARY)
        file_inner.pack(fill=tk.X, padx=20, pady=20)

        tk.Label(
            file_inner,
            text="ContentResult CSV Bestand",
            bg=ModernTheme.BG_SECONDARY,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_NORMAL
        ).pack(anchor=tk.W, pady=(0, 10))

        path_frame = tk.Frame(file_inner, bg=ModernTheme.BG_SECONDARY)
        path_frame.pack(fill=tk.X)

        self.magazijn_file_var = tk.StringVar(value=self.settings.get('magazijn_file', 't_temp_ContentResult.csv'))
        file_entry = tk.Entry(
            path_frame,
            textvariable=self.magazijn_file_var,
            font=ModernTheme.FONT_NORMAL,
            relief="solid",
            bd=1,
            bg=ModernTheme.BG_MAIN
        )
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        browse_btn = ModernTheme.create_button(
            path_frame, "Bladeren...", self.browse_magazijn_file,
            style="tertiary", side=tk.LEFT)

        load_btn = ModernTheme.create_button(
            file_inner, "Laad Magazijn", self.load_magazijn_data,
            style="primary", pady=(15, 0))

        # Results section header
        tk.Label(
            container,
            text="Magazijn Voorraad (HOOFD NR)",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_HEADER
        ).pack(anchor=tk.W, pady=(15, 10))

        # Table - fixed height for consistency
        table_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN, height=400)
        table_frame.pack(fill=tk.BOTH, expand=True)
        table_frame.pack_propagate(False)

        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal")

        self.magazijn_tree = ttk.Treeview(
            table_frame,
            columns=["ID", "Mat.ID", "Materiaal", "Lengte", "Breedte", "Dikte", "Aantal", "m²"],
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            style="Modern.Treeview"
        )

        vsb.config(command=self.magazijn_tree.yview)
        hsb.config(command=self.magazijn_tree.xview)

        self.magazijn_tree.heading("ID", text="ID")
        self.magazijn_tree.heading("Mat.ID", text="Mat.ID")
        self.magazijn_tree.heading("Materiaal", text="Materiaal")
        self.magazijn_tree.heading("Lengte", text="Lengte (mm)")
        self.magazijn_tree.heading("Breedte", text="Breedte (mm)")
        self.magazijn_tree.heading("Dikte", text="Dikte (mm)")
        self.magazijn_tree.heading("Aantal", text="Aantal")
        self.magazijn_tree.heading("m²", text="m²")

        self.magazijn_tree.column("ID", width=60, anchor=tk.CENTER)
        self.magazijn_tree.column("Mat.ID", width=70, anchor=tk.CENTER)
        self.magazijn_tree.column("Materiaal", width=300, anchor=tk.W)
        self.magazijn_tree.column("Lengte", width=100, anchor=tk.E)
        self.magazijn_tree.column("Breedte", width=100, anchor=tk.E)
        self.magazijn_tree.column("Dikte", width=80, anchor=tk.E)
        self.magazijn_tree.column("Aantal", width=80, anchor=tk.E)
        self.magazijn_tree.column("m²", width=100, anchor=tk.E)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.magazijn_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def build_tab3_instellingen(self):
        """Build Settings tab"""
        # Standard container with consistent padding
        container = tk.Frame(self.tab3, bg=ModernTheme.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Header
        ttk.Label(
            container,
            text="Instellingen",
            style="Header.TLabel"
        ).pack(anchor=tk.W)

        ttk.Label(
            container,
            text="Configureer rendement en veiligheidsvoorraad per materiaal",
            style="Subtitle.TLabel"
        ).pack(anchor=tk.W, pady=(5, 20))

        # Rendement section - more compact
        rendement_card = tk.Frame(container, bg=ModernTheme.BG_SECONDARY, relief="flat")
        rendement_card.pack(fill=tk.X, pady=(0, 20))

        rendement_inner = tk.Frame(rendement_card, bg=ModernTheme.BG_SECONDARY)
        rendement_inner.pack(fill=tk.BOTH, padx=20, pady=20)

        tk.Label(
            rendement_inner,
            text="Globaal Rendement %",
            bg=ModernTheme.BG_SECONDARY,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_NORMAL
        ).pack(anchor=tk.W, pady=(0, 10))

        rendement_frame = tk.Frame(rendement_inner, bg=ModernTheme.BG_SECONDARY)
        rendement_frame.pack(fill=tk.X)

        tk.Label(
            rendement_frame,
            text="Rendement %:",
            bg=ModernTheme.BG_SECONDARY,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_NORMAL,
            anchor=tk.W,
            width=15
        ).pack(side=tk.LEFT)

        self.rendement_var = tk.StringVar(value="75.0")
        rendement_entry = tk.Entry(
            rendement_frame,
            textvariable=self.rendement_var,
            font=ModernTheme.FONT_NORMAL,
            width=15,
            relief="solid",
            bd=1
        )
        rendement_entry.pack(side=tk.LEFT, padx=(10, 10))

        ModernTheme.create_button(
            rendement_frame, "Rendement Toepassen", self.apply_rendement,
            style="primary", side=tk.LEFT)

        # Safety margins section header
        tk.Label(
            container,
            text="Veiligheidsvoorraad per Materiaal",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_HEADER
        ).pack(anchor=tk.W, pady=(15, 10))

        # Action buttons
        actions_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        actions_frame.pack(fill=tk.X, pady=(0, 15))

        ModernTheme.create_button(
            actions_frame, "Laad Magazijn Materialen", self.load_safety_materials,
            style="primary", side=tk.LEFT, padx=(0, 10))

        ModernTheme.create_button(
            actions_frame, "Opslaan", self.save_config,
            style="secondary", side=tk.LEFT)

        # Table for safety margins - fixed height for consistency
        table_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN, height=400)
        table_frame.pack(fill=tk.BOTH, expand=True)
        table_frame.pack_propagate(False)

        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal")

        self.safety_tree = ttk.Treeview(
            table_frame,
            columns=["Mat.ID", "IDs", "Materiaal", "Artikel Nummer", "Veiligheidsvoorraad (m²)", "Rendement %"],
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            style="Modern.Treeview"
        )

        vsb.config(command=self.safety_tree.yview)
        hsb.config(command=self.safety_tree.xview)

        self.safety_tree.heading("Mat.ID", text="Mat.ID")
        self.safety_tree.heading("IDs", text="IDs")
        self.safety_tree.heading("Materiaal", text="Materiaal")
        self.safety_tree.heading("Artikel Nummer", text="Artikel Nummer")
        self.safety_tree.heading("Veiligheidsvoorraad (m²)", text="Veiligheidsvoorraad (m²)")
        self.safety_tree.heading("Rendement %", text="Rendement %")

        self.safety_tree.column("Mat.ID", width=80, anchor=tk.CENTER)
        self.safety_tree.column("IDs", width=120, anchor=tk.W)
        self.safety_tree.column("Materiaal", width=250, anchor=tk.W)
        self.safety_tree.column("Artikel Nummer", width=130, anchor=tk.W)
        self.safety_tree.column("Veiligheidsvoorraad (m²)", width=180, anchor=tk.E)
        self.safety_tree.column("Rendement %", width=120, anchor=tk.E)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.safety_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind double-click to edit
        self.safety_tree.bind('<Double-1>', self.edit_safety_margin)

    def build_tab4_berekening(self):
        """Build Calculation tab"""
        # Standard container with consistent padding
        container = tk.Frame(self.tab4, bg=ModernTheme.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Header
        ttk.Label(
            container,
            text="Bestelberekening",
            style="Header.TLabel"
        ).pack(anchor=tk.W)

        ttk.Label(
            container,
            text="Bekijk en exporteer de berekende bestelhoeveelheden",
            style="Subtitle.TLabel"
        ).pack(anchor=tk.W, pady=(5, 20))

        # Action buttons
        button_container = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        button_container.pack(fill=tk.X, pady=(0, 15))

        ModernTheme.create_button(
            button_container, "Berekenen", self.calculate,
            style="primary", side=tk.LEFT, padx=(0, 10))

        ModernTheme.create_button(
            button_container, "Exporteer CSV", self.export_csv,
            style="secondary", side=tk.LEFT, padx=(0, 10))

        # Results section header
        tk.Label(
            container,
            text="Berekende Resultaten",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_HEADER
        ).pack(anchor=tk.W, pady=(15, 10))

        # Results table - fixed height for consistency
        table_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN, height=400)
        table_frame.pack(fill=tk.BOTH, expand=True)
        table_frame.pack_propagate(False)

        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal")

        columns = [
            "Materiaal",
            "Artikel Nummer",
            "Netto (m²)",
            "R%",
            "Bruto (m²)",
            "Veiligh. (m²)",
            "Stock (m²)",
            "In Bestelling (m²)",
            "Saldo (m²)"
        ]

        self.calc_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            style="Modern.Treeview"
        )

        vsb.config(command=self.calc_tree.yview)
        hsb.config(command=self.calc_tree.xview)

        # Configure columns
        for col in columns:
            self.calc_tree.heading(col, text=col)

        self.calc_tree.column("Materiaal", width=250, anchor=tk.W)
        self.calc_tree.column("Artikel Nummer", width=130, anchor=tk.W)
        self.calc_tree.column("Netto (m²)", width=100, anchor=tk.E)
        self.calc_tree.column("R%", width=60, anchor=tk.E)
        self.calc_tree.column("Bruto (m²)", width=100, anchor=tk.E)
        self.calc_tree.column("Veiligh. (m²)", width=120, anchor=tk.E)
        self.calc_tree.column("Stock (m²)", width=100, anchor=tk.E)
        self.calc_tree.column("In Bestelling (m²)", width=140, anchor=tk.E)
        self.calc_tree.column("Saldo (m²)", width=120, anchor=tk.E)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.calc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure tags for color coding
        self.calc_tree.tag_configure('need_order', foreground=ModernTheme.DANGER)
        self.calc_tree.tag_configure('overstock', foreground=ModernTheme.SECONDARY)
        self.calc_tree.tag_configure('total', background=ModernTheme.BG_TERTIARY, font=ModernTheme.FONT_HEADER)

        # Bind double-click to edit "In Bestelling" column
        self.calc_tree.bind('<Double-1>', self.edit_in_bestelling)

    def build_tab5_analyse(self):
        """Build Analysis tab — static shell only, Treeview is created dynamically."""
        container = tk.Frame(self.tab5, bg=ModernTheme.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Header
        ttk.Label(
            container,
            text="Stock Saldo Historiek",
            style="Header.TLabel"
        ).pack(anchor=tk.W)

        ttk.Label(
            container,
            text="Stock / Saldo per materiaal per snapshot-datum",
            style="Subtitle.TLabel"
        ).pack(anchor=tk.W, pady=(5, 20))

        # Action buttons
        button_container = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        button_container.pack(fill=tk.X, pady=(0, 15))

        ModernTheme.create_button(
            button_container, "Ververs Analyse", self.refresh_analysis,
            style="primary", side=tk.LEFT, padx=(0, 10))

        ModernTheme.create_button(
            button_container, "Exporteer Historiek", self.export_pivot,
            style="secondary", side=tk.LEFT, padx=(0, 10))

        self.analyse_info_var = tk.StringVar(value="")
        tk.Label(
            button_container,
            textvariable=self.analyse_info_var,
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_SECONDARY,
            font=ModernTheme.FONT_SMALL
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Placeholder frame for the dynamic Treeview
        self.analyse_table_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        self.analyse_table_frame.pack(fill=tk.BOTH, expand=True)

    def refresh_analysis(self):
        """Query the history DB and build a pivot grid with per-cell coloring."""
        for child in self.analyse_table_frame.winfo_children():
            child.destroy()

        pivot = self.history_db.get_pivot_data()
        if pivot is None:
            self.analyse_info_var.set("Geen snapshots gevonden.")
            self.status_var.set("Analyse: geen data")
            messagebox.showinfo(
                "Geen data",
                "Er zijn geen snapshots in de database.\n"
                "Bereken eerst om snapshots op te bouwen."
            )
            return

        dates = pivot['dates']  # oldest first
        materials = pivot['materials']
        artikel_nrs = pivot.get('artikel_nrs', {})

        date_headers = []
        for d in dates:
            parts = d.split('-')
            date_headers.append(f"{parts[2]}-{parts[1]}-{parts[0]}")

        sorted_materials = sorted(materials.keys())
        hdr_font = (ModernTheme.FONT_FAMILY, 9, "bold")
        cell_font = (ModernTheme.FONT_FAMILY, 9)
        hdr_bg = ModernTheme.BG_TERTIARY

        # ── Layout (grid): frozen headers + frozen material column ──
        #   (0,0) corner header   (0,1) date header canvas          (0,2) empty
        #   (1,0) left canvas     (1,1) right canvas (data)         (1,2) vsb
        #   (2,0) empty           (2,1) hsb                         (2,2) empty

        corner_frame = tk.Frame(self.analyse_table_frame, bg=hdr_bg)
        tk.Label(
            corner_frame, text="Materiaal", bg=hdr_bg,
            font=hdr_font, padx=8, pady=4, anchor=tk.W, relief="groove"
        ).grid(row=0, column=0, sticky="nsew")
        tk.Label(
            corner_frame, text="Artikel Nr", bg=hdr_bg,
            font=hdr_font, padx=8, pady=4, anchor=tk.W, relief="groove"
        ).grid(row=0, column=1, sticky="nsew")
        corner_frame.grid_columnconfigure(0, minsize=250)
        corner_frame.grid_columnconfigure(1, minsize=120)
        hdr_canvas = tk.Canvas(
            self.analyse_table_frame, bg=ModernTheme.BG_MAIN, highlightthickness=0
        )
        left_canvas = tk.Canvas(
            self.analyse_table_frame, bg=ModernTheme.BG_MAIN, highlightthickness=0
        )
        right_canvas = tk.Canvas(
            self.analyse_table_frame, bg=ModernTheme.BG_MAIN, highlightthickness=0
        )
        vsb = ttk.Scrollbar(self.analyse_table_frame, orient="vertical")
        hsb = ttk.Scrollbar(self.analyse_table_frame, orient="horizontal")

        corner_frame.grid(row=0, column=0, sticky="nsew")
        hdr_canvas.grid(row=0, column=1, sticky="ew")
        left_canvas.grid(row=1, column=0, sticky="ns")
        right_canvas.grid(row=1, column=1, sticky="nsew")
        vsb.grid(row=1, column=2, sticky="ns")
        hsb.grid(row=2, column=1, sticky="ew")

        self.analyse_table_frame.grid_rowconfigure(1, weight=1)
        self.analyse_table_frame.grid_columnconfigure(1, weight=1)

        # Sync horizontal scroll: header + data
        def _sync_xview(*args):
            right_canvas.xview(*args)
            hdr_canvas.xview(*args)

        hsb.config(command=_sync_xview)

        def _on_right_xscroll(*args):
            hsb.set(*args)
            hdr_canvas.xview_moveto(args[0])

        right_canvas.configure(xscrollcommand=_on_right_xscroll)

        # Sync vertical scroll: material names + data
        def _sync_yview(*args):
            left_canvas.yview(*args)
            right_canvas.yview(*args)

        vsb.config(command=_sync_yview)

        def _on_left_yscroll(*args):
            vsb.set(*args)
            right_canvas.yview_moveto(args[0])

        def _on_right_yscroll(*args):
            vsb.set(*args)
            left_canvas.yview_moveto(args[0])

        left_canvas.configure(yscrollcommand=_on_left_yscroll)
        right_canvas.configure(yscrollcommand=_on_right_yscroll)

        # Inner frames
        hdr_frame = tk.Frame(hdr_canvas, bg=ModernTheme.BG_MAIN)
        hdr_canvas.create_window((0, 0), window=hdr_frame, anchor="nw")

        left_grid = tk.Frame(left_canvas, bg=ModernTheme.BG_MAIN)
        left_canvas.create_window((0, 0), window=left_grid, anchor="nw")

        right_grid = tk.Frame(right_canvas, bg=ModernTheme.BG_MAIN)
        right_canvas.create_window((0, 0), window=right_grid, anchor="nw")

        # Date headers (frozen row, scrolls horizontally)
        for col_idx, dh in enumerate(date_headers):
            tk.Label(
                hdr_frame, text=dh, bg=hdr_bg, font=hdr_font,
                padx=8, pady=4, anchor=tk.CENTER, relief="groove"
            ).grid(row=0, column=col_idx, sticky="nsew")

        # Data rows — use Frame wrappers per row for single outline selection
        row_frames = {}  # row_idx -> (left_row_frame, right_row_frame)
        row_all_widgets = {}  # row_idx -> all clickable widgets
        self._analyse_selected_row = None

        def _select_row(row_idx):
            """Outline the clicked row with a single border per side."""
            prev = self._analyse_selected_row
            if prev is not None and prev in row_frames:
                lf, rf = row_frames[prev]
                lf.configure(highlightthickness=0)
                rf.configure(highlightthickness=0)
            if row_idx == prev:
                self._analyse_selected_row = None
                return
            self._analyse_selected_row = row_idx
            lf, rf = row_frames[row_idx]
            lf.configure(highlightbackground=ModernTheme.PRIMARY, highlightthickness=2)
            rf.configure(highlightbackground=ModernTheme.PRIMARY, highlightthickness=2)

        num_dates = len(dates)

        for row_idx, mat in enumerate(sorted_materials):
            mat_dates = materials[mat]
            row_all_widgets[row_idx] = []

            # Left row frame (material + artikel)
            left_row_frame = tk.Frame(left_grid, bg="white", highlightthickness=0)
            left_row_frame.grid(row=row_idx, column=0, sticky="nsew")
            left_row_frame.grid_columnconfigure(0, minsize=250)
            left_row_frame.grid_columnconfigure(1, minsize=120)

            lbl_mat = tk.Label(
                left_row_frame, text=mat, bg="white", font=cell_font,
                padx=8, pady=3, anchor=tk.W, relief="groove"
            )
            lbl_mat.grid(row=0, column=0, sticky="nsew")

            lbl_art = tk.Label(
                left_row_frame, text=artikel_nrs.get(mat, ''), bg="white", font=cell_font,
                padx=8, pady=3, anchor=tk.W, relief="groove"
            )
            lbl_art.grid(row=0, column=1, sticky="nsew")

            row_all_widgets[row_idx].extend([left_row_frame, lbl_mat, lbl_art])

            # Right row frame (data columns)
            right_row_frame = tk.Frame(right_grid, bg=ModernTheme.BG_MAIN, highlightthickness=0)
            right_row_frame.grid(row=row_idx, column=0, sticky="nsew")
            for ci in range(num_dates):
                right_row_frame.grid_columnconfigure(ci, minsize=130)

            for col_idx, d in enumerate(dates):
                if d in mat_dates:
                    s = mat_dates[d]
                    text = f"{s['stock']:.1f} / {s['saldo']:.1f}"
                    stock_r = round(s['stock'], 1)
                    saldo_r = round(s['saldo'], 1)
                    if saldo_r < 0:
                        bg, fg = '#ffcdd2', '#c62828'
                    elif stock_r == 0 and saldo_r == 0:
                        bg, fg = '#bbdefb', '#1565c0'  # blue: no stock/saldo
                    elif stock_r == saldo_r:
                        bg, fg = '#bbdefb', '#1565c0'  # blue: stock without movement
                    else:
                        bg, fg = '#c8e6c9', '#2e7d32'
                else:
                    text, bg, fg = "", "white", ModernTheme.TEXT_PRIMARY

                lbl_cell = tk.Label(
                    right_row_frame, text=text, bg=bg, fg=fg, font=cell_font,
                    padx=8, pady=3, anchor=tk.CENTER, relief="groove"
                )
                lbl_cell.grid(row=0, column=col_idx, sticky="nsew")
                row_all_widgets[row_idx].append(lbl_cell)

            row_frames[row_idx] = (left_row_frame, right_row_frame)

            # Bind click to all widgets in this row
            for w in row_all_widgets[row_idx]:
                w.bind("<Button-1>", lambda e, r=row_idx: _select_row(r))

        # Column sizing for header row (row frames handle their own column sizing)
        for col_idx in range(num_dates):
            hdr_frame.grid_columnconfigure(col_idx, minsize=130)

        # Finalize sizes and scroll regions
        hdr_frame.update_idletasks()
        left_grid.update_idletasks()
        right_grid.update_idletasks()

        left_w = left_grid.winfo_reqwidth()
        hdr_h = hdr_frame.winfo_reqheight()

        corner_frame.configure(width=left_w)  # match left grid width
        left_canvas.configure(scrollregion=left_canvas.bbox("all"), width=left_w)
        hdr_canvas.configure(scrollregion=hdr_canvas.bbox("all"), height=hdr_h)
        right_canvas.configure(scrollregion=right_canvas.bbox("all"))

        # Mousewheel — bind to every widget so it works wherever the cursor is
        def _on_mousewheel(event):
            _sync_yview("scroll", int(-1 * (event.delta / 120)), "units")

        all_widgets = [left_canvas, right_canvas]
        for widgets in row_all_widgets.values():
            all_widgets.extend(widgets)
        for w in all_widgets:
            w.bind("<MouseWheel>", _on_mousewheel)

        self.analyse_info_var.set(
            f"{len(sorted_materials)} materialen | {len(dates)} snapshots"
        )
        self.status_var.set(f"\u2713 Analyse vernieuwd: {len(sorted_materials)} materialen")

    def export_pivot(self):
        """Export the pivot table to xlsx with the same color coding as on screen."""
        pivot = self.history_db.get_pivot_data()
        if pivot is None:
            messagebox.showinfo("Geen data", "Geen snapshots om te exporteren.")
            return

        dates = pivot['dates']
        materials = pivot['materials']
        artikel_nrs = pivot.get('artikel_nrs', {})
        sorted_materials = sorted(materials.keys())

        date_headers = []
        for d in dates:
            parts = d.split('-')
            date_headers.append(f"{parts[2]}-{parts[1]}-{parts[0]}")

        timestamp = datetime.now().strftime("%d_%m_%Y")
        filename = filedialog.asksaveasfilename(
            title="Exporteer Historiek",
            initialdir=self.settings.get('export_folder', '.'),
            initialfile=f"stock_saldo_historiek_{timestamp}.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel bestanden", "*.xlsx")]
        )
        if not filename:
            return
        self.settings['export_folder'] = str(Path(filename).parent)
        self.save_config(silent=True)

        try:
            import xlsxwriter

            wb = xlsxwriter.Workbook(filename)
            ws = wb.add_worksheet("Stock Saldo Historiek")

            # Formats
            hdr_fmt = wb.add_format({
                'bold': True, 'bg_color': '#1a73e8', 'font_color': 'white',
                'align': 'center', 'border': 1
            })
            green_fmt = wb.add_format({
                'bg_color': '#c8e6c9', 'font_color': '#2e7d32',
                'align': 'center', 'border': 1
            })
            red_fmt = wb.add_format({
                'bg_color': '#ffcdd2', 'font_color': '#c62828',
                'align': 'center', 'border': 1
            })
            blue_fmt = wb.add_format({
                'bg_color': '#bbdefb', 'font_color': '#1565c0',
                'align': 'center', 'border': 1
            })
            empty_fmt = wb.add_format({'border': 1, 'align': 'center'})
            mat_fmt = wb.add_format({'border': 1})

            # Column widths
            ws.set_column(0, 0, 35)   # Materiaal
            ws.set_column(1, 1, 18)   # Artikel Nr
            ws.set_column(2, 1 + len(dates), 18)  # Date columns

            # Header row
            ws.write(0, 0, "Materiaal", hdr_fmt)
            ws.write(0, 1, "Artikel Nr", hdr_fmt)
            for col, dh in enumerate(date_headers, start=2):
                ws.write(0, col, dh, hdr_fmt)

            # Data rows
            for row, mat in enumerate(sorted_materials, start=1):
                ws.write(row, 0, mat, mat_fmt)
                ws.write(row, 1, artikel_nrs.get(mat, ''), mat_fmt)
                mat_dates = materials[mat]

                for col, d in enumerate(dates, start=2):
                    if d in mat_dates:
                        s = mat_dates[d]
                        text = f"{s['stock']:.1f} / {s['saldo']:.1f}"
                        stock_r = round(s['stock'], 1)
                        saldo_r = round(s['saldo'], 1)
                        if saldo_r < 0:
                            fmt = red_fmt
                        elif stock_r == 0 and saldo_r == 0:
                            fmt = blue_fmt
                        elif stock_r == saldo_r:
                            fmt = blue_fmt
                        else:
                            fmt = green_fmt
                        ws.write(row, col, text, fmt)
                    else:
                        ws.write(row, col, "", empty_fmt)

            # Freeze header row + material & artikel columns
            ws.freeze_panes(1, 2)

            wb.close()

            self.status_var.set(f"\u2713 Historiek geëxporteerd: {filename}")
            messagebox.showinfo("Export", f"Historiek geëxporteerd naar:\n{filename}")

        except Exception as e:
            messagebox.showerror("Fout", f"Export mislukt:\n{e}")

    # ── Tab 6: Handmagazijn Historiek ─────────────────────────────────

    def build_tab6_handmagazijn(self):
        """Build Handmagazijn Historiek tab — reststukken m² per materiaal per datum."""
        container = tk.Frame(self.tab6, bg=ModernTheme.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Header
        ttk.Label(
            container,
            text="Handmagazijn Historiek",
            style="Header.TLabel"
        ).pack(anchor=tk.W)

        ttk.Label(
            container,
            text="Reststukken m² per materiaal per datum",
            style="Subtitle.TLabel"
        ).pack(anchor=tk.W, pady=(5, 20))

        # Action buttons
        button_container = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        button_container.pack(fill=tk.X, pady=(0, 15))

        ModernTheme.create_button(
            button_container, "Importeer CSV", self.import_handmagazijn_csvs,
            style="primary", side=tk.LEFT, padx=(0, 10))

        ModernTheme.create_button(
            button_container, "Exporteer", self.export_handmagazijn,
            style="secondary", side=tk.LEFT, padx=(0, 10))

        ModernTheme.create_button(
            button_container, "Ververs", self.refresh_handmagazijn,
            style="tertiary", side=tk.LEFT, padx=(0, 10))

        self.handmagazijn_info_var = tk.StringVar(value="")
        tk.Label(
            button_container,
            textvariable=self.handmagazijn_info_var,
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_SECONDARY,
            font=ModernTheme.FONT_SMALL
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Placeholder frame for the dynamic pivot grid
        self.handmagazijn_table_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        self.handmagazijn_table_frame.pack(fill=tk.BOTH, expand=True)

    def import_handmagazijn_csvs(self):
        """Let the user pick one or more CSV files to import."""
        initial_dir = self.settings.get('handmagazijn_folder', '')
        if not initial_dir or not Path(initial_dir).is_dir():
            initial_dir = None

        files = filedialog.askopenfilenames(
            title="Selecteer Handmagazijn CSV bestand(en)",
            initialdir=initial_dir,
            filetypes=[("CSV bestanden", "*.csv *.Csv"), ("Alle bestanden", "*.*")]
        )
        if not files:
            return

        # Remember the folder for next time
        self.settings['handmagazijn_folder'] = str(Path(files[0]).parent)
        self.save_config(silent=True)

        imported = 0
        already = 0
        invalid = 0
        for filepath in files:
            result = self.history_db.import_handmagazijn_csv(filepath)
            if result == 'EXISTS':
                already += 1
            elif result:
                imported += 1
            else:
                invalid += 1

        self.status_var.set(
            f"\u2713 Handmagazijn import: {imported} nieuw, {already} reeds aanwezig, {invalid} ongeldig"
        )
        if imported > 0:
            parts = [f"{imported} bestand(en) geïmporteerd."]
            if already:
                parts.append(f"{already} overgeslagen (reeds aanwezig).")
            if invalid:
                parts.append(f"{invalid} overgeslagen (geen geldige data).")
            messagebox.showinfo("Import voltooid", "\n".join(parts))
        elif already > 0 and invalid == 0:
            messagebox.showinfo(
                "Geen nieuwe data",
                f"Alle {already} bestanden waren reeds geïmporteerd."
            )
        elif invalid > 0 and already == 0:
            messagebox.showinfo(
                "Geen geldige data",
                f"{invalid} bestand(en) bevatten geen geldige handmagazijn data.\n"
                "(Geen rijen met Referentie nummer tussen 10.000 en 100.000)"
            )
        else:
            parts = []
            if already:
                parts.append(f"{already} reeds geïmporteerd.")
            if invalid:
                parts.append(f"{invalid} zonder geldige data.")
            messagebox.showinfo("Geen nieuwe data", "\n".join(parts))

        self.history_db.backfill_handmagazijn_zeros()
        self.refresh_handmagazijn(show_empty_msg=False)

    def refresh_handmagazijn(self, show_empty_msg=True):
        """Query the history DB and build a pivot grid for handmagazijn data."""
        for child in self.handmagazijn_table_frame.winfo_children():
            child.destroy()

        pivot = self.history_db.get_handmagazijn_pivot()
        if pivot is None:
            self.handmagazijn_info_var.set("Geen snapshots gevonden.")
            self.status_var.set("Handmagazijn: geen data")
            if show_empty_msg:
                messagebox.showinfo(
                    "Geen data",
                    "Er zijn geen handmagazijn snapshots in de database.\n"
                    "Klik op 'Importeer CSV's' om data te laden."
                )
            return

        dates = pivot['dates']  # oldest first (ISO)
        materials = pivot['materials']

        # Format date headers as DD-MM-YYYY for display
        date_headers = []
        for d in dates:
            parts = d.split('-')
            date_headers.append(f"{parts[2]}-{parts[1]}-{parts[0]}")

        sorted_materials = sorted(materials.keys())
        hdr_font = (ModernTheme.FONT_FAMILY, 9, "bold")
        cell_font = (ModernTheme.FONT_FAMILY, 9)
        hdr_bg = ModernTheme.BG_TERTIARY
        totaal_font = (ModernTheme.FONT_FAMILY, 9, "bold")
        totaal_bg = '#e8eaf6'
        totaal_fg = '#283593'

        # ── Layout (grid): totaal row + frozen headers + frozen material column ──
        # Row 0: Totaal m² (frozen)
        # Row 1: Materiaal / date headers (frozen)
        # Row 2: scrollable data
        # Row 3: horizontal scrollbar
        mat_col_width = 250
        totaal_corner = tk.Frame(self.handmagazijn_table_frame, bg=totaal_bg, width=mat_col_width)
        totaal_corner.grid_propagate(False)
        totaal_canvas = tk.Canvas(
            self.handmagazijn_table_frame, bg=totaal_bg, highlightthickness=0
        )

        corner_frame = tk.Frame(self.handmagazijn_table_frame, bg=hdr_bg, width=mat_col_width)
        corner_frame.grid_propagate(False)
        tk.Label(
            corner_frame, text="Materiaal", bg=hdr_bg,
            font=hdr_font, padx=8, pady=4, anchor=tk.W, relief="groove"
        ).pack(fill=tk.BOTH, expand=True)

        hdr_canvas = tk.Canvas(
            self.handmagazijn_table_frame, bg=ModernTheme.BG_MAIN, highlightthickness=0
        )
        left_canvas = tk.Canvas(
            self.handmagazijn_table_frame, bg=ModernTheme.BG_MAIN, highlightthickness=0
        )
        right_canvas = tk.Canvas(
            self.handmagazijn_table_frame, bg=ModernTheme.BG_MAIN, highlightthickness=0
        )
        vsb = ttk.Scrollbar(self.handmagazijn_table_frame, orient="vertical")
        hsb = ttk.Scrollbar(self.handmagazijn_table_frame, orient="horizontal")

        totaal_corner.grid(row=0, column=0, sticky="nsew")
        totaal_canvas.grid(row=0, column=1, sticky="ew")
        corner_frame.grid(row=1, column=0, sticky="nsew")
        hdr_canvas.grid(row=1, column=1, sticky="ew")
        left_canvas.grid(row=2, column=0, sticky="ns")
        right_canvas.grid(row=2, column=1, sticky="nsew")
        vsb.grid(row=2, column=2, sticky="ns")
        hsb.grid(row=3, column=1, sticky="ew")

        self.handmagazijn_table_frame.grid_rowconfigure(2, weight=1)
        self.handmagazijn_table_frame.grid_columnconfigure(1, weight=1)

        # Sync horizontal scroll: totaal + header + data
        def _sync_xview(*args):
            right_canvas.xview(*args)
            hdr_canvas.xview(*args)
            totaal_canvas.xview(*args)

        hsb.config(command=_sync_xview)

        def _on_right_xscroll(*args):
            hsb.set(*args)
            hdr_canvas.xview_moveto(args[0])
            totaal_canvas.xview_moveto(args[0])

        right_canvas.configure(xscrollcommand=_on_right_xscroll)

        # Sync vertical scroll: material names + data
        def _sync_yview(*args):
            left_canvas.yview(*args)
            right_canvas.yview(*args)

        vsb.config(command=_sync_yview)

        def _on_left_yscroll(*args):
            vsb.set(*args)
            right_canvas.yview_moveto(args[0])

        def _on_right_yscroll(*args):
            vsb.set(*args)
            left_canvas.yview_moveto(args[0])

        left_canvas.configure(yscrollcommand=_on_left_yscroll)
        right_canvas.configure(yscrollcommand=_on_right_yscroll)

        # Inner frames
        hdr_frame = tk.Frame(hdr_canvas, bg=ModernTheme.BG_MAIN)
        hdr_canvas.create_window((0, 0), window=hdr_frame, anchor="nw")

        left_grid = tk.Frame(left_canvas, bg=ModernTheme.BG_MAIN)
        left_canvas.create_window((0, 0), window=left_grid, anchor="nw")

        right_grid = tk.Frame(right_canvas, bg=ModernTheme.BG_MAIN)
        right_canvas.create_window((0, 0), window=right_grid, anchor="nw")

        # Date headers
        for col_idx, dh in enumerate(date_headers):
            tk.Label(
                hdr_frame, text=dh, bg=hdr_bg, font=hdr_font,
                padx=8, pady=4, anchor=tk.CENTER, relief="groove"
            ).grid(row=0, column=col_idx, sticky="nsew")

        # Data rows with color coding
        row_frames = {}
        row_all_widgets = {}
        self._handmagazijn_selected_row = None

        def _select_row(row_idx):
            prev = self._handmagazijn_selected_row
            if prev is not None and prev in row_frames:
                lf, rf = row_frames[prev]
                lf.configure(highlightthickness=0)
                rf.configure(highlightthickness=0)
            if row_idx == prev:
                self._handmagazijn_selected_row = None
                return
            self._handmagazijn_selected_row = row_idx
            lf, rf = row_frames[row_idx]
            lf.configure(highlightbackground=ModernTheme.PRIMARY, highlightthickness=2)
            rf.configure(highlightbackground=ModernTheme.PRIMARY, highlightthickness=2)

        num_dates = len(dates)

        # ── Totaal m² row (frozen, above headers) ──
        # Calculate totals and in/out per date
        date_totals = {}
        date_in = {}   # sum of increases per material
        date_out = {}  # sum of decreases per material
        for col_idx, d in enumerate(dates):
            total = 0
            m_in = 0
            m_out = 0
            for mat_dates in materials.values():
                val = mat_dates.get(d, 0)
                total += val
                if col_idx > 0:
                    prev_val = mat_dates.get(dates[col_idx - 1], 0)
                    diff = val - prev_val
                    if diff > 0:
                        m_in += diff
                    elif diff < 0:
                        m_out += abs(diff)
            date_totals[d] = total
            date_in[d] = m_in
            date_out[d] = m_out

        # Left corner: "Totaal m²" label
        tk.Label(
            totaal_corner, text="Totaal m\u00b2", bg=totaal_bg, fg=totaal_fg,
            font=totaal_font, padx=8, pady=4, anchor=tk.W, relief="groove"
        ).pack(fill=tk.BOTH, expand=True)

        # Right: totals per date with in/out indicators (inside totaal_canvas)
        totaal_frame = tk.Frame(totaal_canvas, bg=totaal_bg)
        totaal_canvas.create_window((0, 0), window=totaal_frame, anchor="nw")
        totaal_detail_font = (ModernTheme.FONT_FAMILY, 8)
        for ci in range(num_dates):
            totaal_frame.grid_columnconfigure(ci, minsize=110)
        for col_idx, d in enumerate(dates):
            total_val = date_totals[d]
            cell = tk.Frame(totaal_frame, bg=totaal_bg, relief="groove", borderwidth=2)
            cell.grid(row=0, column=col_idx, sticky="nsew")

            tk.Label(
                cell, text=f"{total_val:.2f}", bg=totaal_bg, fg=totaal_fg,
                font=totaal_font, padx=4, anchor=tk.CENTER
            ).pack(fill=tk.X)

            if col_idx > 0:
                delta_frame = tk.Frame(cell, bg=totaal_bg)
                delta_frame.pack(fill=tk.X)
                m_in = date_in[d]
                m_out = date_out[d]
                if m_in > 0:
                    tk.Label(
                        delta_frame, text=f"\u25b2{m_in:.2f}", bg=totaal_bg,
                        fg='#2e7d32', font=totaal_font
                    ).pack(side=tk.LEFT, expand=True)
                if m_out > 0:
                    tk.Label(
                        delta_frame, text=f"\u25bc{m_out:.2f}", bg=totaal_bg,
                        fg='#c62828', font=totaal_font
                    ).pack(side=tk.LEFT, expand=True)

        # ── Material rows ──
        for row_idx, mat in enumerate(sorted_materials):
            mat_dates = materials[mat]
            row_all_widgets[row_idx] = []

            # Left row frame (material name)
            left_row_frame = tk.Frame(left_grid, bg="white", highlightthickness=0,
                                      width=mat_col_width)
            left_row_frame.grid(row=row_idx, column=0, sticky="nsew")
            left_row_frame.grid_propagate(False)

            lbl_mat = tk.Label(
                left_row_frame, text=mat, bg="white", font=cell_font,
                padx=8, pady=3, anchor=tk.W, relief="groove"
            )
            lbl_mat.pack(fill=tk.BOTH, expand=True)
            row_all_widgets[row_idx].extend([left_row_frame, lbl_mat])

            # Right row frame (data columns)
            right_row_frame = tk.Frame(right_grid, bg=ModernTheme.BG_MAIN, highlightthickness=0)
            right_row_frame.grid(row=row_idx, column=0, sticky="nsew")
            for ci in range(num_dates):
                right_row_frame.grid_columnconfigure(ci, minsize=110)

            for col_idx, d in enumerate(dates):
                if d in mat_dates:
                    m2_val = mat_dates[d]
                    text = f"{m2_val:.2f}"

                    # Color coding: compare to previous date column
                    if col_idx == 0:
                        # First column: blue (no previous to compare)
                        bg, fg = '#bbdefb', '#1565c0'
                    else:
                        prev_date = dates[col_idx - 1]
                        prev_val = mat_dates.get(prev_date, 0)
                        if m2_val > prev_val:
                            bg, fg = '#c8e6c9', '#2e7d32'   # green: increased
                        elif m2_val < prev_val:
                            bg, fg = '#ffcdd2', '#c62828'    # red: decreased
                        else:
                            bg, fg = '#bbdefb', '#1565c0'    # blue: unchanged
                else:
                    text, bg, fg = "", "white", ModernTheme.TEXT_PRIMARY

                lbl_cell = tk.Label(
                    right_row_frame, text=text, bg=bg, fg=fg, font=cell_font,
                    padx=8, pady=3, anchor=tk.CENTER, relief="groove"
                )
                lbl_cell.grid(row=0, column=col_idx, sticky="nsew")
                row_all_widgets[row_idx].append(lbl_cell)

            row_frames[row_idx] = (left_row_frame, right_row_frame)

            # Bind click to all widgets in this row
            for w in row_all_widgets[row_idx]:
                w.bind("<Button-1>", lambda e, r=row_idx: _select_row(r))

        # Column sizing for header row
        for col_idx in range(num_dates):
            hdr_frame.grid_columnconfigure(col_idx, minsize=110)

        # Finalize sizes and scroll regions
        totaal_frame.update_idletasks()
        hdr_frame.update_idletasks()
        left_grid.update_idletasks()
        right_grid.update_idletasks()

        hdr_h = hdr_frame.winfo_reqheight()
        totaal_h = totaal_frame.winfo_reqheight()

        totaal_corner.configure(width=mat_col_width, height=totaal_h)
        totaal_canvas.configure(scrollregion=totaal_canvas.bbox("all"), height=totaal_h)
        corner_frame.configure(width=mat_col_width)
        left_canvas.configure(scrollregion=left_canvas.bbox("all"), width=mat_col_width)
        hdr_canvas.configure(scrollregion=hdr_canvas.bbox("all"), height=hdr_h)
        right_canvas.configure(scrollregion=right_canvas.bbox("all"))

        # Mousewheel
        def _on_mousewheel(event):
            _sync_yview("scroll", int(-1 * (event.delta / 120)), "units")

        all_widgets = [left_canvas, right_canvas]
        for widgets in row_all_widgets.values():
            all_widgets.extend(widgets)
        for w in all_widgets:
            w.bind("<MouseWheel>", _on_mousewheel)

        snapshot_count = self.history_db.get_handmagazijn_snapshot_count()
        self.handmagazijn_info_var.set(
            f"{len(sorted_materials)} materialen | {snapshot_count} snapshots"
        )
        self.status_var.set(
            f"\u2713 Handmagazijn vernieuwd: {len(sorted_materials)} materialen"
        )

    def export_handmagazijn(self):
        """Export the handmagazijn pivot table to xlsx with color coding."""
        pivot = self.history_db.get_handmagazijn_pivot()
        if pivot is None:
            messagebox.showinfo("Geen data", "Geen snapshots om te exporteren.")
            return

        dates = pivot['dates']
        materials = pivot['materials']
        sorted_materials = sorted(materials.keys())

        date_headers = []
        for d in dates:
            parts = d.split('-')
            date_headers.append(f"{parts[2]}-{parts[1]}-{parts[0]}")

        timestamp = datetime.now().strftime("%d_%m_%Y")
        filename = filedialog.asksaveasfilename(
            title="Exporteer Handmagazijn",
            initialdir=self.settings.get('export_folder', '.'),
            initialfile=f"handmagazijn_historiek_{timestamp}.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel bestanden", "*.xlsx")]
        )
        if not filename:
            return
        self.settings['export_folder'] = str(Path(filename).parent)
        self.save_config(silent=True)

        try:
            import xlsxwriter

            wb = xlsxwriter.Workbook(filename)
            ws = wb.add_worksheet("Handmagazijn Historiek")

            # Formats
            hdr_fmt = wb.add_format({
                'bold': True, 'bg_color': '#1a73e8', 'font_color': 'white',
                'align': 'center', 'border': 1
            })
            totaal_fmt = wb.add_format({
                'bold': True, 'bg_color': '#e8eaf6', 'font_color': '#283593',
                'align': 'center', 'valign': 'vcenter', 'border': 1,
                'text_wrap': True
            })
            totaal_label_fmt = wb.add_format({
                'bold': True, 'bg_color': '#e8eaf6', 'font_color': '#283593',
                'border': 1, 'valign': 'vcenter'
            })
            green_fmt = wb.add_format({
                'bg_color': '#c8e6c9', 'font_color': '#2e7d32',
                'align': 'center', 'border': 1, 'num_format': '0.00'
            })
            red_fmt = wb.add_format({
                'bg_color': '#ffcdd2', 'font_color': '#c62828',
                'align': 'center', 'border': 1, 'num_format': '0.00'
            })
            blue_fmt = wb.add_format({
                'bg_color': '#bbdefb', 'font_color': '#1565c0',
                'align': 'center', 'border': 1, 'num_format': '0.00'
            })
            mat_fmt = wb.add_format({'border': 1})

            # Rich string fragment formats (no bg/border — applied via cell format)
            totaal_text_fmt = wb.add_format({
                'bold': True, 'font_color': '#283593', 'font_size': 10
            })
            up_text_fmt = wb.add_format({
                'bold': True, 'font_color': '#2e7d32', 'font_size': 10
            })
            down_text_fmt = wb.add_format({
                'bold': True, 'font_color': '#c62828', 'font_size': 10
            })

            # Column widths
            ws.set_column(0, 0, 35)
            ws.set_column(1, len(dates), 22)

            # Calculate totals and deltas per date
            date_totals = {}
            date_in = {}
            date_out = {}
            for col_idx, d in enumerate(dates):
                total = 0
                m_in = 0
                m_out = 0
                for mat_dates in materials.values():
                    val = mat_dates.get(d, 0)
                    total += val
                    if col_idx > 0:
                        prev_val = mat_dates.get(dates[col_idx - 1], 0)
                        diff = val - prev_val
                        if diff > 0:
                            m_in += diff
                        elif diff < 0:
                            m_out += abs(diff)
                date_totals[d] = total
                date_in[d] = m_in
                date_out[d] = m_out

            # Row 0: Totaal m² with ▲/▼ in one cell (double row height)
            ws.set_row(0, 30)
            ws.write(0, 0, "Totaal m\u00b2", totaal_label_fmt)
            for col, d in enumerate(dates, start=1):
                total_str = f"{date_totals[d]:.2f}"
                if col == 1:
                    ws.write(0, col, total_str, totaal_fmt)
                else:
                    m_in = date_in[d]
                    m_out = date_out[d]
                    parts = [totaal_text_fmt, total_str]
                    delta_parts = []
                    if m_in > 0:
                        delta_parts.extend([up_text_fmt, f"\u25b2{m_in:.2f}"])
                    if m_in > 0 and m_out > 0:
                        delta_parts.extend([totaal_text_fmt, " "])
                    if m_out > 0:
                        delta_parts.extend([down_text_fmt, f"\u25bc{m_out:.2f}"])
                    if delta_parts:
                        parts.extend([totaal_text_fmt, "\n"])
                        parts.extend(delta_parts)
                        ws.write_rich_string(0, col, *parts, totaal_fmt)
                    else:
                        ws.write(0, col, total_str, totaal_fmt)

            # Row 1: Headers
            ws.write(1, 0, "Materiaal", hdr_fmt)
            for col, dh in enumerate(date_headers, start=1):
                ws.write(1, col, dh, hdr_fmt)

            # Data rows
            for row, mat in enumerate(sorted_materials, start=2):
                ws.write(row, 0, mat, mat_fmt)
                mat_dates = materials[mat]

                for col, d in enumerate(dates, start=1):
                    val = mat_dates.get(d, 0)

                    if col == 1:
                        fmt = blue_fmt
                    else:
                        prev_date = dates[col - 2]
                        prev_val = mat_dates.get(prev_date, 0)
                        if val < prev_val:
                            fmt = red_fmt
                        elif val > prev_val:
                            fmt = green_fmt
                        else:
                            fmt = blue_fmt

                    ws.write(row, col, val, fmt)

            # Freeze totaal + header rows and material column
            ws.freeze_panes(2, 1)

            wb.close()

            self.status_var.set(f"\u2713 Handmagazijn ge\u00ebxporteerd: {filename}")
            messagebox.showinfo("Export", f"Handmagazijn ge\u00ebxporteerd naar:\n{filename}")

        except Exception as e:
            messagebox.showerror("Fout", f"Export mislukt:\n{e}")

    # === EVENT HANDLERS ===

    def browse_orders_folder(self):
        """Browse for orders folder"""
        folder = filedialog.askdirectory(
            title="Selecteer Map met Excel Bestanden",
            initialdir=self.orders_folder_var.get()
        )
        if folder:
            self.orders_folder_var.set(folder)
            self.save_config(silent=True)

    def scan_orders(self):
        """Scan orders and calculate netto m²"""
        folder = self.orders_folder_var.get()

        if not Path(folder).exists():
            messagebox.showerror("Fout", f"Map niet gevonden: {folder}")
            return

        # Show progress bar and disable scan button
        self.orders_progress_label.config(text="Orders scannen...")
        self.orders_progress_label.pack(pady=(10, 0))
        self.orders_progress.pack(pady=(5, 0), fill=tk.X)
        self.orders_progress.start(10)

        # Start scanning in a separate thread
        thread = threading.Thread(target=self._scan_orders_thread, args=(folder,))
        thread.daemon = True
        thread.start()

    def _scan_orders_thread(self, folder):
        """Scan orders in a separate thread"""
        try:
            calculator = MaterialCalculator(folder)

            # Update progress
            self.root.after(0, lambda: self.orders_progress_label.config(text="Zoeken naar Excel bestanden..."))
            files = calculator.scan_folder()

            if not files:
                self.root.after(0, lambda: self._scan_complete(False, "Geen Excel bestanden gevonden!"))
                return

            # Process files and build file_data structure
            self.file_data = []
            all_materials_dict = defaultdict(float)

            total_files = len(files)
            for idx, file_path in enumerate(files, 1):
                # Update progress
                self.root.after(0, lambda i=idx, t=total_files, f=file_path.name:
                    self.orders_progress_label.config(text=f"Verwerken ({i}/{t}): {f[:50]}..."))

                materials = calculator.extract_material_data(file_path)

                if materials:
                    self.file_data.append({
                        'filename': file_path.name,
                        'materials': materials,
                        'included': True  # Default: included
                    })

                    # Collect all unique materials
                    for material, amount in materials.items():
                        all_materials_dict[material] += amount

            # Sort materials by total amount
            self.all_materials = sorted(
                all_materials_dict.keys(),
                key=lambda m: all_materials_dict[m],
                reverse=True
            )

            # Build the Excel-like table
            self.root.after(0, self.build_orders_table)

            # Complete
            self.root.after(0, lambda: self._scan_complete(True,
                f"Orders gescand!\n\n{len(files)} bestanden\n{len(self.all_materials)} unieke materialen"))

        except Exception as e:
            self.root.after(0, lambda: self._scan_complete(False, f"Fout bij scannen:\n{e}"))

    def _scan_complete(self, success, message):
        """Complete the scanning process"""
        # Hide progress bar
        self.orders_progress.stop()
        self.orders_progress.pack_forget()
        self.orders_progress_label.pack_forget()

        if success:
            self.status_var.set(f"✓ {len(self.file_data)} bestanden gescand, {len(self.all_materials)} materialen gevonden")
            messagebox.showinfo("Succes", message)
        else:
            self.status_var.set("Fout bij scannen")
            messagebox.showerror("Fout", message)

    def build_orders_table(self):
        """Build Excel-like table with checkbox, filename, and material columns"""
        # Clear existing table
        for item in self.orders_tree.get_children():
            self.orders_tree.delete(item)

        if not self.file_data or not self.all_materials:
            return

        # Define columns: checkbox, filename, then each material
        columns = ["✓", "Project"] + self.all_materials

        # Configure treeview
        self.orders_tree["columns"] = columns
        self.orders_tree["show"] = "tree headings"

        # Configure tree column for row numbers
        self.orders_tree.column("#0", width=50, anchor=tk.CENTER, minwidth=50, stretch=False)
        self.orders_tree.heading("#0", text="#")

        # Configure checkbox column
        self.orders_tree.column("✓", width=50, anchor=tk.CENTER, minwidth=50, stretch=False)
        self.orders_tree.heading("✓", text="✓")

        # Configure filename column
        max_filename_len = max(len(fd['filename']) for fd in self.file_data)
        filename_width = min(max(max_filename_len * 7, 250), 500)
        self.orders_tree.column("Project", width=filename_width, anchor=tk.W, minwidth=250, stretch=False)
        self.orders_tree.heading("Project", text="Project")

        # Configure material columns
        for material in self.all_materials:
            material_name_len = len(material)
            col_width = min(max(material_name_len * 8, 120), 300)
            self.orders_tree.column(material, width=col_width, anchor=tk.E, minwidth=120, stretch=False)
            self.orders_tree.heading(material, text=material)

        # Insert TOTALS row first
        totals_values = ["", "TOTALEN"]
        for material in self.all_materials:
            total = sum(
                fd['materials'].get(material, 0)
                for fd in self.file_data
                if fd['included']
            )
            totals_values.append(f"{total:.2f}")

        self.orders_tree.insert("", "end", text="", values=totals_values, tags=('totals',))

        # Configure totals row style
        self.orders_tree.tag_configure('totals', background=ModernTheme.BG_TERTIARY, font=ModernTheme.FONT_HEADER)

        # Insert separator
        sep_values = ["", "─" * 30] + ["─" * 10] * len(self.all_materials)
        self.orders_tree.insert("", "end", text="", values=sep_values, tags=('separator',))
        self.orders_tree.tag_configure('separator', foreground=ModernTheme.TEXT_DISABLED)

        # Insert data rows
        for idx, file_data in enumerate(self.file_data, 1):
            checkbox = "☑" if file_data['included'] else "☐"
            values = [checkbox, file_data['filename']]

            # Add material values
            for material in self.all_materials:
                amount = file_data['materials'].get(material, 0)
                if amount > 0:
                    values.append(f"{amount:.2f}")
                else:
                    values.append("")

            item_id = self.orders_tree.insert("", "end", text=str(idx), values=values)

            # Store item_id for later reference
            file_data['item_id'] = item_id

        # Populate orders_data for calculation
        self.orders_data = {}
        for material in self.all_materials:
            total = sum(
                fd['materials'].get(material, 0)
                for fd in self.file_data
                if fd['included']
            )
            if total > 0:
                self.orders_data[material] = total

    def update_orders_totals(self):
        """Update the totals row in orders table"""
        # Find totals row (first row)
        for item in self.orders_tree.get_children():
            if 'totals' in self.orders_tree.item(item, 'tags'):
                totals_values = ["", "TOTALEN"]
                for material in self.all_materials:
                    total = sum(
                        fd['materials'].get(material, 0)
                        for fd in self.file_data
                        if fd['included']
                    )
                    totals_values.append(f"{total:.2f}")

                self.orders_tree.item(item, values=totals_values)
                break

        # Update orders_data for calculation
        self.orders_data = {}
        for material in self.all_materials:
            total = sum(
                fd['materials'].get(material, 0)
                for fd in self.file_data
                if fd['included']
            )
            if total > 0:
                self.orders_data[material] = total

    def on_orders_table_click(self, event):
        """Handle table click for checkbox toggle"""
        region = self.orders_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.orders_tree.identify_column(event.x)
            row_id = self.orders_tree.identify_row(event.y)

            # Check if clicked on checkbox column (column #1)
            if column == "#1" and row_id:
                # Don't toggle totals or separator rows
                if 'totals' in self.orders_tree.item(row_id, 'tags') or 'separator' in self.orders_tree.item(row_id, 'tags'):
                    return

                self.toggle_order_checkbox(row_id)

    def on_orders_table_space(self, event):
        """Handle space key for checkbox toggle"""
        selection = self.orders_tree.selection()
        if selection:
            row_id = selection[0]
            if 'totals' not in self.orders_tree.item(row_id, 'tags') and 'separator' not in self.orders_tree.item(row_id, 'tags'):
                self.toggle_order_checkbox(row_id)

    def toggle_order_checkbox(self, row_id):
        """Toggle checkbox for a row"""
        values = list(self.orders_tree.item(row_id, 'values'))

        # Toggle checkbox
        if values[0] == "☑":
            values[0] = "☐"
            included = False
        else:
            values[0] = "☑"
            included = True

        self.orders_tree.item(row_id, values=values)

        # Update file_data
        for fd in self.file_data:
            if fd.get('item_id') == row_id:
                fd['included'] = included
                break

        # Update totals row
        self.update_orders_totals()

    def select_all_orders(self):
        """Select all order files"""
        for fd in self.file_data:
            fd['included'] = True
            if 'item_id' in fd:
                values = list(self.orders_tree.item(fd['item_id'], 'values'))
                values[0] = "☑"
                self.orders_tree.item(fd['item_id'], values=values)

        self.update_orders_totals()
        self.status_var.set("✓ Alle projecten geselecteerd")

    def deselect_all_orders(self):
        """Deselect all order files"""
        for fd in self.file_data:
            fd['included'] = False
            if 'item_id' in fd:
                values = list(self.orders_tree.item(fd['item_id'], 'values'))
                values[0] = "☐"
                self.orders_tree.item(fd['item_id'], values=values)

        self.update_orders_totals()
        self.status_var.set("✓ Alle projecten gedeselecteerd")

    def browse_magazijn_file(self):
        """Browse for magazijn CSV file"""
        csv_file = filedialog.askopenfilename(
            title="Selecteer ContentResult CSV",
            initialdir=Path(self.magazijn_file_var.get()).parent if Path(self.magazijn_file_var.get()).exists() else ".",
            filetypes=[("CSV bestanden", "*.csv"), ("Alle bestanden", "*.*")]
        )
        if csv_file:
            self.magazijn_file_var.set(csv_file)
            self.save_config(silent=True)

    def load_magazijn_data(self):
        """Load magazijn stock from CSV"""
        csv_file = self.magazijn_file_var.get()

        if not csv_file or not Path(csv_file).exists():
            messagebox.showerror("Fout", f"Bestand niet gevonden: {csv_file}")
            return

        self.status_var.set("Magazijn data laden...")
        self.root.update()

        try:
            materials_data = {}
            details_list = []

            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=';')

                for row in reader:
                    if len(row) >= 17:
                        try:
                            row_id = row[0].strip()
                            material_name = row[1].strip()
                            lengte = float(row[2].strip()) if row[2].strip() else 0
                            breedte = float(row[3].strip()) if row[3].strip() else 0
                            dikte = float(row[4].strip()) if row[4].strip() else 0
                            materiaal_id = row[5].strip()  # Column 5: Materiaal ID (Nummer)
                            aantal = float(row[6].strip()) if row[6].strip() else 0
                            hoofd_nr = row[16].strip() if len(row) > 16 else ""

                            if material_name and "HOOFD NR" in hoofd_nr:
                                m2 = (lengte * breedte * aantal) / 1_000_000

                                # Store detailed info
                                details_list.append({
                                    'id': row_id,
                                    'materiaal_id': materiaal_id,  # New: Materiaal ID
                                    'material': material_name,
                                    'lengte': lengte,
                                    'breedte': breedte,
                                    'dikte': dikte,
                                    'aantal': aantal,
                                    'm2': m2
                                })

                                # Aggregate by Materiaal ID instead of material name
                                materials_data[materiaal_id] = materials_data.get(materiaal_id, 0) + m2

                        except (ValueError, IndexError):
                            continue

            self.stock_data = materials_data
            self.stock_details = details_list

            # Clean up config: remove entries for materials not in current magazijn
            current_materiaal_ids = set(detail['materiaal_id'] for detail in details_list)

            # Clean safety margins
            orphaned_safety = [mid for mid in self.safety_margins.keys() if mid not in current_materiaal_ids]
            for mid in orphaned_safety:
                del self.safety_margins[mid]

            # Clean material rendement
            orphaned_rendement = [mid for mid in self.material_rendement.keys() if mid not in current_materiaal_ids]
            for mid in orphaned_rendement:
                del self.material_rendement[mid]

            # Clean artikel nummers
            orphaned_artikel = [mid for mid in self.artikel_nummers.keys() if mid not in current_materiaal_ids]
            for mid in orphaned_artikel:
                del self.artikel_nummers[mid]

            # Log cleanup if any entries were removed
            total_orphaned = len(orphaned_safety) + len(orphaned_rendement) + len(orphaned_artikel)
            if total_orphaned > 0:
                print(f"Config cleanup: Removed {len(orphaned_safety)} orphaned safety margins, {len(orphaned_rendement)} orphaned rendement entries, {len(orphaned_artikel)} orphaned artikel nummers")

            # Update table with detailed view
            for item in self.magazijn_tree.get_children():
                self.magazijn_tree.delete(item)

            # Sort by ID
            sorted_details = sorted(details_list, key=lambda x: int(x['id']) if x['id'].isdigit() else x['id'])

            for detail in sorted_details:
                self.magazijn_tree.insert("", "end", values=(
                    detail['id'],
                    detail['materiaal_id'],
                    detail['material'],
                    f"{detail['lengte']:.0f}",
                    f"{detail['breedte']:.0f}",
                    f"{detail['dikte']:.0f}",
                    f"{detail['aantal']:.0f}",
                    f"{detail['m2']:.2f}"
                ))

            self.status_var.set(f"✓ Magazijn data geladen: {len(details_list)} items, {len(materials_data)} unieke materialen")
            messagebox.showinfo(
                "Succes",
                f"Magazijn data geladen!\n\n{len(details_list)} items met HOOFD NR\n{len(materials_data)} unieke materialen"
            )

        except Exception as e:
            messagebox.showerror("Fout", f"Fout bij laden magazijn:\n{e}")
            self.status_var.set("Fout bij laden")

    def load_config(self):
        """Load configuration from JSON file"""
        import json

        config_file = Path("bestelberekening_config.json")
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.settings['rendement_pct'] = config.get('rendement_pct', 75.0)
                    self.settings['trend_folder'] = config.get('trend_folder', '.')
                    self.settings['orders_folder'] = config.get('orders_folder', 'Stuklijsten')
                    self.settings['magazijn_file'] = config.get('magazijn_file', 't_temp_ContentResult.csv')
                    self.settings['export_folder'] = config.get('export_folder', '.')
                    self.settings['handmagazijn_folder'] = config.get('handmagazijn_folder', '')
                    self.safety_margins = config.get('safety_margins', {})
                    self.material_rendement = config.get('material_rendement', {})
                    self.artikel_nummers = config.get('artikel_nummers', {})
            except Exception as e:
                print(f"Fout bij laden config: {e}")

    def save_config(self, silent=False):
        """Save configuration to JSON file"""
        import json

        try:
            config = {
                'rendement_pct': self.settings['rendement_pct'],
                'trend_folder': self.settings.get('trend_folder', '.'),
                'orders_folder': self.orders_folder_var.get(),
                'magazijn_file': self.magazijn_file_var.get(),
                'export_folder': self.settings.get('export_folder', '.'),
                'handmagazijn_folder': self.settings.get('handmagazijn_folder', ''),
                'safety_margins': self.safety_margins,
                'material_rendement': self.material_rendement,
                'artikel_nummers': self.artikel_nummers
            }

            with open("bestelberekening_config.json", 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            if not silent:
                self.status_var.set("✓ Configuratie opgeslagen")
                messagebox.showinfo("Succes", "Configuratie opgeslagen in bestelberekening_config.json")

        except Exception as e:
            messagebox.showerror("Fout", f"Fout bij opslaan config:\n{e}")

    def apply_rendement(self):
        """Apply rendement setting"""
        try:
            rendement = float(self.rendement_var.get())

            if rendement <= 0 or rendement > 100:
                messagebox.showerror("Fout", "Rendement moet tussen 0 en 100 zijn!")
                return

            self.settings['rendement_pct'] = rendement
            self.status_var.set(f"✓ Rendement toegepast: {rendement}%")
            messagebox.showinfo("Succes", f"Rendement ingesteld op {rendement}%")

        except ValueError:
            messagebox.showerror("Fout", "Ongeldige waarde! Gebruik alleen getallen.")

    def load_safety_materials(self):
        """Load materials from magazijn for safety margin configuration"""
        if not self.stock_details:
            messagebox.showwarning(
                "Waarschuwing",
                "Laad eerst magazijn data in Tab 2!"
            )
            self.notebook.select(1)  # Switch to magazijn tab
            return

        # Clear table
        for item in self.safety_tree.get_children():
            self.safety_tree.delete(item)

        # Group by Materiaal ID (not unique ID)
        unique_materials = {}
        for detail in self.stock_details:
            materiaal_id = detail['materiaal_id']
            material_name = detail['material']
            unique_id = detail['id']

            if materiaal_id not in unique_materials:
                unique_materials[materiaal_id] = {
                    'materiaal_id': materiaal_id,
                    'name': material_name,
                    'count': 0,
                    'ids': []
                }
            unique_materials[materiaal_id]['count'] += 1
            unique_materials[materiaal_id]['ids'].append(unique_id)

        # Sort by Materiaal ID
        sorted_materials = sorted(
            unique_materials.values(),
            key=lambda x: (int(x['materiaal_id']) if x['materiaal_id'].isdigit() else 999999, x['materiaal_id'])
        )

        # Populate table with Materiaal ID grouping
        for mat in sorted_materials:
            materiaal_id = mat['materiaal_id']
            material_name = mat['name']
            item_count = mat['count']
            unique_ids = mat['ids']
            safety_m2 = self.safety_margins.get(materiaal_id, 0.0)
            artikel_nummer = self.artikel_nummers.get(materiaal_id, "")

            # Get rendement % - use material-specific if set, otherwise use global
            rendement_pct = self.material_rendement.get(materiaal_id, self.settings['rendement_pct'])

            # Show material name with count if multiple items
            display_name = f"{material_name} ({item_count} items)" if item_count > 1 else material_name

            # Format IDs as comma-separated list
            ids_display = ", ".join(unique_ids)

            self.safety_tree.insert("", "end", values=(
                materiaal_id,
                ids_display,
                display_name,
                artikel_nummer,
                f"{safety_m2:.2f}",
                f"{rendement_pct:.1f}"
            ))

        self.status_var.set(f"✓ {len(sorted_materials)} materialen geladen voor veiligheidsvoorraad configuratie")

    def edit_safety_margin(self, event):
        """Edit safety margin and rendement % for selected material"""
        selection = self.safety_tree.selection()
        if not selection:
            return

        item = selection[0]
        values = self.safety_tree.item(item, 'values')
        material_id = values[0]
        ids_display = values[1]
        material_name = values[2]
        current_artikel = values[3]
        current_safety = values[4]
        current_rendement = values[5]

        # Create edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Instellingen - {material_name}")
        dialog.geometry("500x350")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        main = tk.Frame(dialog, bg=ModernTheme.BG_MAIN, padx=30, pady=30)
        main.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            main,
            text=f"ID: {material_id}",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_SECONDARY,
            font=ModernTheme.FONT_SMALL
        ).pack(anchor=tk.W)

        tk.Label(
            main,
            text=material_name,
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_HEADER
        ).pack(anchor=tk.W, pady=(0, 20))

        # Artikel Nummer input
        artikel_frame = tk.Frame(main, bg=ModernTheme.BG_MAIN)
        artikel_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(
            artikel_frame,
            text="Artikel Nummer:",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_NORMAL
        ).pack(side=tk.LEFT, padx=(0, 10))

        artikel_var = tk.StringVar(value=current_artikel)
        artikel_entry = tk.Entry(
            artikel_frame,
            textvariable=artikel_var,
            font=ModernTheme.FONT_NORMAL,
            width=20,
            relief="solid",
            bd=1
        )
        artikel_entry.pack(side=tk.LEFT)
        artikel_entry.focus()
        artikel_entry.select_range(0, tk.END)

        # Safety margin input
        safety_frame = tk.Frame(main, bg=ModernTheme.BG_MAIN)
        safety_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(
            safety_frame,
            text="Veiligheidsvoorraad (m²):",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_NORMAL
        ).pack(side=tk.LEFT, padx=(0, 10))

        safety_var = tk.StringVar(value=current_safety)
        safety_entry = tk.Entry(
            safety_frame,
            textvariable=safety_var,
            font=ModernTheme.FONT_NORMAL,
            width=15,
            relief="solid",
            bd=1
        )
        safety_entry.pack(side=tk.LEFT)

        # Rendement % input
        rendement_frame = tk.Frame(main, bg=ModernTheme.BG_MAIN)
        rendement_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            rendement_frame,
            text="Rendement %:",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_NORMAL
        ).pack(side=tk.LEFT, padx=(0, 10))

        rendement_var = tk.StringVar(value=current_rendement)
        rendement_entry = tk.Entry(
            rendement_frame,
            textvariable=rendement_var,
            font=ModernTheme.FONT_NORMAL,
            width=15,
            relief="solid",
            bd=1
        )
        rendement_entry.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            rendement_frame,
            text=f"(Global: {self.settings['rendement_pct']:.1f}%)",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_SECONDARY,
            font=ModernTheme.FONT_SMALL
        ).pack(side=tk.LEFT)

        def save():
            try:
                new_safety = float(safety_var.get())
                new_rendement = float(rendement_var.get())
                new_artikel = artikel_var.get().strip()

                if new_safety < 0:
                    messagebox.showerror("Fout", "Veiligheidsvoorraad kan niet negatief zijn!")
                    return

                if new_rendement <= 0 or new_rendement > 100:
                    messagebox.showerror("Fout", "Rendement moet tussen 0 en 100% zijn!")
                    return

                # Update dicts
                self.safety_margins[material_id] = new_safety
                self.material_rendement[material_id] = new_rendement
                self.artikel_nummers[material_id] = new_artikel

                # Update table
                self.safety_tree.item(item, values=(
                    material_id,
                    ids_display,
                    material_name,
                    new_artikel,
                    f"{new_safety:.2f}",
                    f"{new_rendement:.1f}"
                ))

                dialog.destroy()
                self.status_var.set(f"✓ Instellingen voor {material_name} bijgewerkt")

            except ValueError:
                messagebox.showerror("Fout", "Ongeldige waarde! Gebruik alleen getallen.")

        button_frame = tk.Frame(main, bg=ModernTheme.BG_MAIN)
        button_frame.pack()

        ModernTheme.create_button(
            button_frame, "Opslaan", save,
            style="primary", side=tk.LEFT, padx=(0, 10))

        ModernTheme.create_button(
            button_frame, "Annuleren", dialog.destroy,
            style="tertiary", side=tk.LEFT)

        # Bind Enter key
        artikel_entry.bind('<Return>', lambda e: save())
        safety_entry.bind('<Return>', lambda e: save())
        rendement_entry.bind('<Return>', lambda e: save())

    def edit_in_bestelling(self, event):
        """Edit the In Bestelling (m²) value for selected material"""
        region = self.calc_tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        column = self.calc_tree.identify_column(event.x)
        item = self.calc_tree.identify_row(event.y)

        if not item:
            return

        # Get column index (In Bestelling is column #8)
        col_idx = int(column[1:]) - 1

        # Only allow editing the "In Bestelling (m²)" column (index 7)
        if col_idx != 7:
            return

        # Get current values
        values = self.calc_tree.item(item, 'values')
        material_name = values[0]
        current_in_bestelling = values[7]

        # Create edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"In Bestelling - {material_name}")
        dialog.geometry("450x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        main = tk.Frame(dialog, bg=ModernTheme.BG_MAIN, padx=30, pady=30)
        main.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            main,
            text=material_name,
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_HEADER
        ).pack(anchor=tk.W, pady=(0, 20))

        # Input frame
        input_frame = tk.Frame(main, bg=ModernTheme.BG_MAIN)
        input_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            input_frame,
            text="In Bestelling (m²):",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_NORMAL
        ).pack(side=tk.LEFT, padx=(0, 10))

        value_var = tk.StringVar(value=current_in_bestelling)
        value_entry = tk.Entry(
            input_frame,
            textvariable=value_var,
            font=ModernTheme.FONT_NORMAL,
            width=15,
            relief="solid",
            bd=1
        )
        value_entry.pack(side=tk.LEFT)
        value_entry.focus()
        value_entry.select_range(0, tk.END)

        def save():
            try:
                new_value = float(value_var.get())
                if new_value < 0:
                    messagebox.showerror("Fout", "Waarde kan niet negatief zijn!")
                    return

                # Update the in_bestelling dict
                self.in_bestelling[material_name] = new_value

                # Recalculate just for this material and update the table
                self.update_single_calculation(item, material_name)

                dialog.destroy()
                self.status_var.set(f"✓ In Bestelling voor {material_name} bijgewerkt naar {new_value:.2f} m²")

            except ValueError:
                messagebox.showerror("Fout", "Ongeldige waarde! Gebruik alleen getallen.")

        button_frame = tk.Frame(main, bg=ModernTheme.BG_MAIN)
        button_frame.pack()

        ModernTheme.create_button(
            button_frame, "Opslaan", save,
            style="primary", side=tk.LEFT, padx=(0, 10))

        ModernTheme.create_button(
            button_frame, "Annuleren", dialog.destroy,
            style="tertiary", side=tk.LEFT)

        # Bind Enter key
        value_entry.bind('<Return>', lambda e: save())

    def update_single_calculation(self, item, material_name):
        """Update calculation for a single material after In Bestelling change"""
        # Get current values from the tree
        values = list(self.calc_tree.item(item, 'values'))

        # Recalculate saldo with new in_bestelling value
        netto_m2 = float(values[2])
        rendement = float(values[3])
        bruto_m2 = float(values[4])
        safety_m2 = float(values[5])
        stock_m2 = float(values[6])
        in_bestelling_m2 = self.in_bestelling.get(material_name, 0.0)

        # New saldo calculation
        needed_m2 = bruto_m2 + safety_m2
        saldo_m2 = stock_m2 + in_bestelling_m2 - needed_m2

        # Update values
        values[7] = f"{in_bestelling_m2:.2f}"
        values[8] = f"{saldo_m2:.2f}"

        # Determine tag for color coding
        if saldo_m2 < 0:
            tag = 'need_order'
        elif saldo_m2 > 0:
            tag = 'overstock'
        else:
            tag = ''

        # Update the tree item
        self.calc_tree.item(item, values=values, tags=(tag,))

        # Update the calculation_results list
        for result in self.calculation_results:
            if result['material'] == material_name:
                result['in_bestelling'] = in_bestelling_m2
                result['bestellen'] = saldo_m2
                break

    def _build_full_snapshot_data(self):
        """Build a full snapshot with ALL magazijn materials, not just those with orders."""
        # Start with calculation results (materials with orders/safety)
        seen_ids = set()
        snapshot_data = []

        for r in self.calculation_results:
            mid = r.get('materiaal_id', '')
            seen_ids.add(mid)
            snapshot_data.append({
                'material': r['material'],
                'artikel_nummer': r.get('artikel_nummer', ''),
                'materiaal_id': mid,
                'stock': r['stock'],
                'bestellen': r['bestellen'],  # saldo
                'bruto': r.get('bruto', 0),
            })

        # Add ALL remaining magazijn materials not yet included
        # Group stock_details by materiaal_id
        remaining = {}
        for detail in self.stock_details:
            mid = detail['materiaal_id']
            if mid not in seen_ids:
                if mid not in remaining:
                    remaining[mid] = {
                        'material': detail['material'],
                        'materiaal_id': mid,
                        'stock': 0.0,
                    }
                remaining[mid]['stock'] += detail['m2']

        for mid, info in remaining.items():
            safety = self.safety_margins.get(mid, 0.0)
            snapshot_data.append({
                'material': info['material'],
                'artikel_nummer': self.artikel_nummers.get(mid, ''),
                'materiaal_id': mid,
                'stock': info['stock'],
                'bestellen': info['stock'] - safety,  # saldo = stock - safety (no orders)
                'bruto': 0.0,
            })

        return snapshot_data

    def calculate(self):
        """Perform calculation"""
        if not self.orders_data:
            messagebox.showwarning("Waarschuwing", "Scan eerst de orders (Tab 1)!")
            self.notebook.select(0)
            return

        if not self.stock_details:
            messagebox.showwarning("Waarschuwing", "Laad eerst de magazijn voorraad (Tab 2)!")
            self.notebook.select(1)
            return

        self.status_var.set("Berekening uitvoeren...")
        self.root.update()

        try:
            # Clear table
            for item in self.calc_tree.get_children():
                self.calc_tree.delete(item)

            self.calculation_results = []

            # Get materials that exist in magazijn
            magazijn_materials = set(detail['material'] for detail in self.stock_details)

            # Build complete materials list:
            # 1. Materials from orders that exist in magazijn
            # 2. Materials with veiligheidsvoorraad set (even if no orders)
            materials_to_calculate = set()

            # Add materials from orders that are in magazijn
            for material in self.orders_data.keys():
                if material in magazijn_materials:
                    materials_to_calculate.add(material)

            # Add materials that have veiligheidsvoorraad set in config
            for materiaal_id, safety_value in self.safety_margins.items():
                if safety_value > 0:  # Has veiligheidsvoorraad set
                    # Find material name by Materiaal ID
                    for detail in self.stock_details:
                        if detail['materiaal_id'] == materiaal_id:
                            materials_to_calculate.add(detail['material'])
                            break

            # Sort by netto m2 (orders first, then alphabetically for non-order materials)
            all_materials = sorted(
                materials_to_calculate,
                key=lambda m: (self.orders_data.get(m, 0), m),
                reverse=True
            )

            # Track excluded materials from orders
            excluded_materials = [m for m in self.orders_data.keys() if m not in magazijn_materials]

            for material in all_materials:
                netto_m2 = self.orders_data.get(material, 0.0)  # 0 if no orders

                # Find Materiaal ID for this material name
                materiaal_id = None
                for detail in self.stock_details:
                    if detail['material'] == material:
                        materiaal_id = detail['materiaal_id']
                        break

                # Get stock and safety by Materiaal ID
                stock_m2 = self.stock_data.get(materiaal_id, 0.0) if materiaal_id else 0.0
                safety_m2 = self.safety_margins.get(materiaal_id, 0.0) if materiaal_id else 0.0

                # Get rendement % - use material-specific if set, otherwise use global
                rendement_pct = self.material_rendement.get(materiaal_id, self.settings['rendement_pct']) if materiaal_id else self.settings['rendement_pct']

                # Calculate
                # Formula: stock + in_bestelling - (bruto + safety) = saldo (positive = surplus, negative = deficit)
                rendement_decimal = rendement_pct / 100.0
                bruto_m2 = netto_m2 / rendement_decimal
                in_bestelling_m2 = self.in_bestelling.get(material, 0.0)
                needed_m2 = bruto_m2 + safety_m2
                saldo_m2 = stock_m2 + in_bestelling_m2 - needed_m2  # Positive = surplus, Negative = need to order

                # Get artikel nummer
                artikel_nummer = self.artikel_nummers.get(materiaal_id, "") if materiaal_id else ""

                # Store result
                result = {
                    'material': material,
                    'artikel_nummer': artikel_nummer,
                    'materiaal_id': materiaal_id or '',
                    'netto': netto_m2,
                    'rendement': rendement_decimal,
                    'bruto': bruto_m2,
                    'stock': stock_m2,
                    'safety': safety_m2,
                    'in_bestelling': in_bestelling_m2,
                    'bestellen': saldo_m2
                }
                self.calculation_results.append(result)

                # Color coding: GREEN when positive (surplus), RED when negative (deficit/need to order)
                if saldo_m2 < 0:
                    tag = 'need_order'  # Red - need to order (deficit)
                elif saldo_m2 > 0:
                    tag = 'overstock'  # Green - have surplus
                else:
                    tag = ''

                self.calc_tree.insert("", "end", values=(
                    material,
                    artikel_nummer,
                    f"{netto_m2:.2f}",
                    f"{rendement_decimal:.2f}",
                    f"{bruto_m2:.2f}",
                    f"{safety_m2:.2f}",
                    f"{stock_m2:.2f}",
                    f"{in_bestelling_m2:.2f}",
                    f"{saldo_m2:.2f}"
                ), tags=(tag,))

            # Show warning if some materials were excluded
            if excluded_materials:
                excluded_list = "\n".join(f"  • {m}" for m in excluded_materials)
                messagebox.showwarning(
                    "Materialen uitgesloten",
                    f"De volgende materialen zijn niet in magazijn en worden uitgesloten:\n\n{excluded_list}\n\n"
                    f"Berekend: {len(all_materials)} materialen\n"
                    f"Uitgesloten: {len(excluded_materials)} materialen"
                )

            # Save full snapshot to history DB
            history_msg = ""
            try:
                timestamp = datetime.now().strftime("%d_%m_%Y")
                snapshot_data = self._build_full_snapshot_data()
                self.history_db.save_snapshot(timestamp, snapshot_data)
                snap_count = self.history_db.get_snapshot_count()
                history_msg = f" | {snap_count} snapshots in DB"
            except Exception:
                pass

            self.status_var.set(f"✓ Berekening voltooid: {len(all_materials)} materialen ({len(excluded_materials)} uitgesloten){history_msg}")

        except Exception as e:
            messagebox.showerror("Fout", f"Fout bij berekenen:\n{e}")
            self.status_var.set("Fout bij berekenen")

    def on_closing(self):
        """Clean up resources on window close."""
        try:
            self.history_db.close()
        except Exception:
            pass
        self.root.destroy()

    def export_csv(self):
        """Export results to Excel with color coding and history comparison"""
        if not self.calculation_results:
            messagebox.showwarning("Waarschuwing", "Voer eerst de berekening uit!")
            return

        timestamp = datetime.now().strftime("%d_%m_%Y")
        default_filename = f"bestelberekening_{timestamp}.xlsx"

        filename = filedialog.asksaveasfilename(
            title="Exporteer Bestelberekening",
            initialdir=self.settings.get('export_folder', '.'),
            initialfile=default_filename,
            defaultextension=".xlsx",
            filetypes=[("Excel bestanden", "*.xlsx"), ("Alle bestanden", "*.*")]
        )

        if filename:
            self.settings['export_folder'] = str(Path(filename).parent)
            self.save_config(silent=True)
            try:
                import xlsxwriter

                workbook = xlsxwriter.Workbook(filename)
                worksheet = workbook.add_worksheet('Bestelberekening')

                # Define formats
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#1a73e8',
                    'font_color': 'white',
                    'align': 'center',
                    'valign': 'vcenter',
                    'border': 1
                })

                red_format = workbook.add_format({
                    'bg_color': '#ffebee',
                    'font_color': '#c62828',
                    'num_format': '0.00',
                    'border': 1
                })

                green_format = workbook.add_format({
                    'bg_color': '#e8f5e9',
                    'font_color': '#2e7d32',
                    'num_format': '0.00',
                    'border': 1
                })

                normal_format = workbook.add_format({
                    'num_format': '0.00',
                    'border': 1
                })

                percent_format = workbook.add_format({
                    'num_format': '0.00%',
                    'border': 1
                })

                text_format = workbook.add_format({
                    'border': 1
                })

                # Create editable format for "In Bestelling" column
                editable_format = workbook.add_format({
                    'num_format': '0.00',
                    'border': 1,
                    'bg_color': '#f0f8ff',  # Light blue background to indicate editable
                    'locked': False
                })

                # Set column widths: A-I
                worksheet.set_column(0, 0, 30)   # A: Materiaal
                worksheet.set_column(1, 1, 18)   # B: Artikel Nummer
                worksheet.set_column(2, 8, 15)   # C-I: Numbers

                # Prepare table data (9 columns: A-I)
                table_data = []
                for result in self.calculation_results:
                    table_data.append([
                        result['material'],                    # A
                        result.get('artikel_nummer', ''),      # B
                        result['netto'],                       # C
                        result['rendement'],                   # D
                        result['bruto'],                       # E
                        result['safety'],                      # F
                        result['stock'],                       # G
                        result.get('in_bestelling', 0.0),      # H
                        result['bestellen'],                   # I (Saldo)
                    ])

                # Define table columns
                table_columns = [
                    {'header': 'Materiaal', 'header_format': header_format, 'format': text_format},
                    {'header': 'Artikel Nummer', 'header_format': header_format, 'format': workbook.add_format({'border': 1, 'align': 'right'})},
                    {'header': 'Netto (m\u00b2)', 'header_format': header_format, 'format': normal_format},
                    {'header': 'R%', 'header_format': header_format, 'format': percent_format},
                    {'header': 'Bruto (m\u00b2)', 'header_format': header_format, 'format': normal_format},
                    {'header': 'Veiligh. (m\u00b2)', 'header_format': header_format, 'format': normal_format},
                    {'header': 'Stock (m\u00b2)', 'header_format': header_format, 'format': normal_format},
                    {'header': 'In Bestelling (m\u00b2)', 'header_format': header_format, 'format': editable_format},
                    {'header': 'Saldo (m\u00b2)', 'header_format': header_format, 'format': normal_format},
                ]

                # Create Excel Table
                last_row = max(len(table_data), 1)
                worksheet.add_table(0, 0, last_row, len(table_columns) - 1, {
                    'data': table_data,
                    'columns': table_columns,
                    'style': 'Table Style Medium 2',
                    'name': 'Bestelberekening',
                })

                # Overwrite formula columns with actual formulas + cached values
                for r in range(1, last_row + 1):
                    row_data = table_data[r - 1]

                    # Column I (8): Saldo formula = Stock + In Bestelling - (Bruto + Veiligh)
                    saldo_formula = f'=G{r+1}+H{r+1}-(E{r+1}+F{r+1})'
                    worksheet.write_formula(r, 8, saldo_formula, normal_format, row_data[8])

                # Add conditional formatting
                if table_data:
                    data_range_end = last_row + 1  # 1-based row for range

                    # Saldo column (I): red < 0, green > 0
                    worksheet.conditional_format(f'I2:I{data_range_end}', {
                        'type': 'cell', 'criteria': '<', 'value': 0, 'format': red_format
                    })
                    worksheet.conditional_format(f'I2:I{data_range_end}', {
                        'type': 'cell', 'criteria': '>', 'value': 0, 'format': green_format
                    })

                workbook.close()

                self.status_var.set(f"\u2713 Ge\u00ebxporteerd naar {Path(filename).name}")
                messagebox.showinfo("Succes", f"Bestelberekening ge\u00ebxporteerd naar:\n{filename}")

            except ImportError:
                messagebox.showerror("Fout", "xlsxwriter module niet gevonden!\n\nInstalleer met: pip install xlsxwriter")
            except Exception as e:
                messagebox.showerror("Fout", f"Fout bij exporteren:\n{e}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = BestelberekeningApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
