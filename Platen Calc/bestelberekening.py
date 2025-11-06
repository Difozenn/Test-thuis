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

# Import existing calculator
from material_calculator import MaterialCalculator


class ModernTheme:
    """Modern enterprise color scheme and styling"""

    # Colors
    PRIMARY = "#1a73e8"  # Google Blue
    PRIMARY_DARK = "#1557b0"
    SECONDARY = "#34a853"  # Success Green
    WARNING = "#fbbc04"
    DANGER = "#ea4335"

    BG_MAIN = "#ffffff"
    BG_SECONDARY = "#f8f9fa"
    BG_TERTIARY = "#e8eaed"

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
        self.calculation_results = []

        # Load settings from config
        self.load_config()

        # Setup modern styles
        self.setup_styles()

        # Build UI
        self.setup_ui()

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

        # Header section
        header_frame = tk.Frame(main_container, bg=ModernTheme.BG_MAIN, relief="flat", bd=1)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        header_content = tk.Frame(header_frame, bg=ModernTheme.BG_MAIN)
        header_content.pack(fill=tk.X, padx=30, pady=20)

        # Title and subtitle
        title_label = ttk.Label(
            header_content,
            text="Bestelberekening",
            style="Title.TLabel"
        )
        title_label.pack(anchor=tk.W)

        subtitle_label = ttk.Label(
            header_content,
            text="Bestelberekening",
            style="Subtitle.TLabel"
        )
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))

        # Tabs container
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

        self.notebook.add(self.tab1, text="  1. Orders  ")
        self.notebook.add(self.tab2, text="  2. Magazijn  ")
        self.notebook.add(self.tab3, text="  3. Instellingen  ")
        self.notebook.add(self.tab4, text="  4. Berekening  ")

        # Build each tab
        self.build_tab1_orders()
        self.build_tab2_magazijn()
        self.build_tab3_instellingen()
        self.build_tab4_berekening()

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
        container = tk.Frame(self.tab1, bg=ModernTheme.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

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
        ).pack(anchor=tk.W, pady=(5, 25))

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

        self.orders_folder_var = tk.StringVar(value="Stuklijsten")
        folder_entry = tk.Entry(
            path_frame,
            textvariable=self.orders_folder_var,
            font=ModernTheme.FONT_NORMAL,
            relief="solid",
            bd=1,
            bg=ModernTheme.BG_MAIN
        )
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        browse_btn = tk.Button(
            path_frame,
            text="Bladeren...",
            command=self.browse_orders_folder,
            bg=ModernTheme.BG_TERTIARY,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_NORMAL,
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2"
        )
        browse_btn.pack(side=tk.LEFT)

        scan_btn = tk.Button(
            folder_inner,
            text="Scan Orders",
            command=self.scan_orders,
            bg=ModernTheme.PRIMARY,
            fg="white",
            font=ModernTheme.FONT_NORMAL,
            relief="flat",
            padx=30,
            pady=10,
            cursor="hand2"
        )
        scan_btn.pack(pady=(15, 0))

        # Quick actions
        actions_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        actions_frame.pack(fill=tk.X, pady=(15, 15))

        tk.Button(
            actions_frame,
            text="Selecteer Alles",
            command=self.select_all_orders,
            bg=ModernTheme.BG_TERTIARY,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_SMALL,
            relief="flat",
            padx=15,
            pady=6,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            actions_frame,
            text="Deselecteer Alles",
            command=self.deselect_all_orders,
            bg=ModernTheme.BG_TERTIARY,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_SMALL,
            relief="flat",
            padx=15,
            pady=6,
            cursor="hand2"
        ).pack(side=tk.LEFT)

        # Results section
        tk.Label(
            container,
            text="Gevonden Projecten",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_HEADER
        ).pack(anchor=tk.W, pady=(0, 10))

        # Table with horizontal scroll
        table_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        table_frame.pack(fill=tk.BOTH, expand=True)

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
        container = tk.Frame(self.tab2, bg=ModernTheme.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

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
        ).pack(anchor=tk.W, pady=(5, 25))

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

        load_btn = tk.Button(
            file_inner,
            text="Selecteer Magazijn CSV",
            command=self.load_magazijn_data,
            bg=ModernTheme.PRIMARY,
            fg="white",
            font=ModernTheme.FONT_NORMAL,
            relief="flat",
            padx=30,
            pady=10,
            cursor="hand2"
        )
        load_btn.pack()

        # Results section
        tk.Label(
            container,
            text="Magazijn Voorraad (HOOFD NR)",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_HEADER
        ).pack(anchor=tk.W, pady=(20, 10))

        # Table
        table_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        table_frame.pack(fill=tk.BOTH, expand=True)

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
        container = tk.Frame(self.tab3, bg=ModernTheme.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

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
        ).pack(anchor=tk.W, pady=(5, 25))

        # Rendement section
        rendement_card = tk.Frame(container, bg=ModernTheme.BG_SECONDARY, relief="flat")
        rendement_card.pack(fill=tk.X, pady=(0, 20))

        rendement_inner = tk.Frame(rendement_card, bg=ModernTheme.BG_SECONDARY)
        rendement_inner.pack(fill=tk.BOTH, padx=30, pady=25)

        tk.Label(
            rendement_inner,
            text="Globaal Rendement %",
            bg=ModernTheme.BG_SECONDARY,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_HEADER
        ).pack(anchor=tk.W, pady=(0, 15))

        rendement_frame = tk.Frame(rendement_inner, bg=ModernTheme.BG_SECONDARY)
        rendement_frame.pack(fill=tk.X)

        tk.Label(
            rendement_frame,
            text="Rendement %:",
            bg=ModernTheme.BG_SECONDARY,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_NORMAL,
            anchor=tk.W,
            width=20
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

        tk.Button(
            rendement_inner,
            text="Rendement Toepassen",
            command=self.apply_rendement,
            bg=ModernTheme.PRIMARY,
            fg="white",
            font=ModernTheme.FONT_NORMAL,
            relief="flat",
            padx=25,
            pady=8,
            cursor="hand2"
        ).pack(pady=(15, 0))

        # Safety margins section
        tk.Label(
            container,
            text="Veiligheidsvoorraad per Materiaal",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_HEADER
        ).pack(anchor=tk.W, pady=(20, 10))

        # Action buttons
        actions_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        actions_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Button(
            actions_frame,
            text="Laad Magazijn Materialen",
            command=self.load_safety_materials,
            bg=ModernTheme.PRIMARY,
            fg="white",
            font=ModernTheme.FONT_NORMAL,
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            actions_frame,
            text="Opslaan",
            command=self.save_config,
            bg=ModernTheme.SECONDARY,
            fg="white",
            font=ModernTheme.FONT_NORMAL,
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2"
        ).pack(side=tk.LEFT)

        # Table for safety margins
        table_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        table_frame.pack(fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal")

        self.safety_tree = ttk.Treeview(
            table_frame,
            columns=["Mat.ID", "IDs", "Materiaal", "Veiligheidsvoorraad (m²)", "Rendement %"],
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
        self.safety_tree.heading("Veiligheidsvoorraad (m²)", text="Veiligheidsvoorraad (m²)")
        self.safety_tree.heading("Rendement %", text="Rendement %")

        self.safety_tree.column("Mat.ID", width=80, anchor=tk.CENTER)
        self.safety_tree.column("IDs", width=120, anchor=tk.W)
        self.safety_tree.column("Materiaal", width=280, anchor=tk.W)
        self.safety_tree.column("Veiligheidsvoorraad (m²)", width=180, anchor=tk.E)
        self.safety_tree.column("Rendement %", width=120, anchor=tk.E)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.safety_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind double-click to edit
        self.safety_tree.bind('<Double-1>', self.edit_safety_margin)

    def build_tab4_berekening(self):
        """Build Calculation tab"""
        container = tk.Frame(self.tab4, bg=ModernTheme.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

        # Header with buttons
        header_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            header_frame,
            text="Bestelberekening",
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_HEADER
        ).pack(side=tk.LEFT)

        button_container = tk.Frame(header_frame, bg=ModernTheme.BG_MAIN)
        button_container.pack(side=tk.RIGHT)

        calc_btn = tk.Button(
            button_container,
            text="Berekenen",
            command=self.calculate,
            bg=ModernTheme.PRIMARY,
            fg="white",
            font=ModernTheme.FONT_NORMAL,
            relief="flat",
            padx=25,
            pady=8,
            cursor="hand2"
        )
        calc_btn.pack(side=tk.LEFT, padx=(0, 10))

        export_btn = tk.Button(
            button_container,
            text="Exporteer CSV",
            command=self.export_csv,
            bg=ModernTheme.SECONDARY,
            fg="white",
            font=ModernTheme.FONT_NORMAL,
            relief="flat",
            padx=25,
            pady=8,
            cursor="hand2"
        )
        export_btn.pack(side=tk.LEFT)

        # Results table
        table_frame = tk.Frame(container, bg=ModernTheme.BG_MAIN)
        table_frame.pack(fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal")

        columns = [
            "Materiaal",
            "Netto (m²)",
            "R%",
            "Bruto m²",
            "Veiligh. (m²)",
            "Stock (m²)",
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

        self.calc_tree.column("Materiaal", width=350, anchor=tk.W)
        self.calc_tree.column("Netto (m²)", width=120, anchor=tk.E)
        self.calc_tree.column("R%", width=80, anchor=tk.E)
        self.calc_tree.column("Bruto m²", width=120, anchor=tk.E)
        self.calc_tree.column("Veiligh. (m²)", width=140, anchor=tk.E)
        self.calc_tree.column("Stock (m²)", width=120, anchor=tk.E)
        self.calc_tree.column("Saldo (m²)", width=140, anchor=tk.E)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.calc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure tags for color coding
        self.calc_tree.tag_configure('need_order', foreground=ModernTheme.DANGER)
        self.calc_tree.tag_configure('overstock', foreground=ModernTheme.SECONDARY)
        self.calc_tree.tag_configure('total', background=ModernTheme.BG_TERTIARY, font=ModernTheme.FONT_HEADER)

    # === EVENT HANDLERS ===

    def browse_orders_folder(self):
        """Browse for orders folder"""
        folder = filedialog.askdirectory(
            title="Selecteer Map met Excel Bestanden",
            initialdir=self.orders_folder_var.get()
        )
        if folder:
            self.orders_folder_var.set(folder)

    def scan_orders(self):
        """Scan orders and calculate netto m²"""
        folder = self.orders_folder_var.get()

        if not Path(folder).exists():
            messagebox.showerror("Fout", f"Map niet gevonden: {folder}")
            return

        self.status_var.set("Orders scannen...")
        self.root.update()

        try:
            calculator = MaterialCalculator(folder)
            files = calculator.scan_folder()

            if not files:
                messagebox.showwarning("Waarschuwing", "Geen Excel bestanden gevonden!")
                self.status_var.set("Geen bestanden gevonden")
                return

            # Process files and build file_data structure
            self.file_data = []
            all_materials_dict = defaultdict(float)

            for file_path in files:
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
            self.build_orders_table()

            self.status_var.set(f"✓ {len(files)} bestanden gescand, {len(self.all_materials)} materialen gevonden")
            messagebox.showinfo(
                "Succes",
                f"Orders gescand!\n\n{len(files)} bestanden\n{len(self.all_materials)} unieke materialen"
            )

        except Exception as e:
            messagebox.showerror("Fout", f"Fout bij scannen:\n{e}")
            self.status_var.set("Fout bij scannen")

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

    def load_magazijn_data(self):
        """Load magazijn stock from CSV"""
        csv_file = filedialog.askopenfilename(
            title="Selecteer ContentResult CSV",
            filetypes=[("CSV bestanden", "*.csv"), ("Alle bestanden", "*.*")]
        )

        if not csv_file:
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

            # Log cleanup if any entries were removed
            total_orphaned = len(orphaned_safety) + len(orphaned_rendement)
            if total_orphaned > 0:
                print(f"Config cleanup: Removed {len(orphaned_safety)} orphaned safety margins, {len(orphaned_rendement)} orphaned rendement entries")

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
                    self.safety_margins = config.get('safety_margins', {})
                    self.material_rendement = config.get('material_rendement', {})
            except Exception as e:
                print(f"Fout bij laden config: {e}")

    def save_config(self):
        """Save configuration to JSON file"""
        import json

        try:
            config = {
                'rendement_pct': self.settings['rendement_pct'],
                'safety_margins': self.safety_margins,
                'material_rendement': self.material_rendement
            }

            with open("bestelberekening_config.json", 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

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
        current_safety = values[3]
        current_rendement = values[4]

        # Create edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Instellingen - {material_name}")
        dialog.geometry("500x280")
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
        safety_entry.focus()
        safety_entry.select_range(0, tk.END)

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

                if new_safety < 0:
                    messagebox.showerror("Fout", "Veiligheidsvoorraad kan niet negatief zijn!")
                    return

                if new_rendement <= 0 or new_rendement > 100:
                    messagebox.showerror("Fout", "Rendement moet tussen 0 en 100% zijn!")
                    return

                # Update dicts
                self.safety_margins[material_id] = new_safety
                self.material_rendement[material_id] = new_rendement

                # Update table
                self.safety_tree.item(item, values=(
                    material_id,
                    ids_display,
                    material_name,
                    f"{new_safety:.2f}",
                    f"{new_rendement:.1f}"
                ))

                dialog.destroy()
                self.status_var.set(f"✓ Instellingen voor {material_name} bijgewerkt")

            except ValueError:
                messagebox.showerror("Fout", "Ongeldige waarde! Gebruik alleen getallen.")

        button_frame = tk.Frame(main, bg=ModernTheme.BG_MAIN)
        button_frame.pack()

        tk.Button(
            button_frame,
            text="Opslaan",
            command=save,
            bg=ModernTheme.PRIMARY,
            fg="white",
            font=ModernTheme.FONT_NORMAL,
            relief="flat",
            padx=25,
            pady=8,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            button_frame,
            text="Annuleren",
            command=dialog.destroy,
            bg=ModernTheme.BG_TERTIARY,
            fg=ModernTheme.TEXT_PRIMARY,
            font=ModernTheme.FONT_NORMAL,
            relief="flat",
            padx=25,
            pady=8,
            cursor="hand2"
        ).pack(side=tk.LEFT)

        # Bind Enter key
        entry.bind('<Return>', lambda e: save())

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
                # Formula: stock - (bruto + safety) = saldo (positive = surplus, negative = deficit)
                rendement_decimal = rendement_pct / 100.0
                bruto_m2 = netto_m2 / rendement_decimal
                needed_m2 = bruto_m2 + safety_m2
                saldo_m2 = stock_m2 - needed_m2  # Positive = surplus, Negative = need to order

                # Store result
                result = {
                    'material': material,
                    'netto': netto_m2,
                    'rendement': rendement_decimal,
                    'bruto': bruto_m2,
                    'stock': stock_m2,
                    'safety': safety_m2,
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
                    f"{netto_m2:.2f}",
                    f"{rendement_decimal:.2f}",
                    f"{bruto_m2:.2f}",
                    f"{safety_m2:.2f}",
                    f"{stock_m2:.2f}",
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

            self.status_var.set(f"✓ Berekening voltooid: {len(all_materials)} materialen ({len(excluded_materials)} uitgesloten)")

        except Exception as e:
            messagebox.showerror("Fout", f"Fout bij berekenen:\n{e}")
            self.status_var.set("Fout bij berekenen")

    def export_csv(self):
        """Export results to Excel with color coding"""
        if not self.calculation_results:
            messagebox.showwarning("Waarschuwing", "Voer eerst de berekening uit!")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"bestelberekening_{timestamp}.xlsx"

        filename = filedialog.asksaveasfilename(
            title="Exporteer Bestelberekening",
            initialfile=default_filename,
            defaultextension=".xlsx",
            filetypes=[("Excel bestanden", "*.xlsx"), ("Alle bestanden", "*.*")]
        )

        if filename:
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

                text_format = workbook.add_format({
                    'border': 1
                })

                # Write headers
                headers = ['Materiaal', 'Netto (m²)', 'R%', 'Bruto m²', 'm² veiligheidsvoorraad', 'm² huidige stock', 'Saldo m²']
                for col, header in enumerate(headers):
                    worksheet.write(0, col, header, header_format)

                # Set column widths
                worksheet.set_column(0, 0, 30)  # Materiaal
                worksheet.set_column(1, 6, 15)  # Numbers

                # Write data with color coding
                row = 1
                for result in self.calculation_results:
                    worksheet.write(row, 0, result['material'], text_format)
                    worksheet.write(row, 1, result['netto'], normal_format)
                    worksheet.write(row, 2, result['rendement'], normal_format)
                    worksheet.write(row, 3, result['bruto'], normal_format)
                    worksheet.write(row, 4, result['safety'], normal_format)
                    worksheet.write(row, 5, result['stock'], normal_format)

                    # Apply color coding to "Saldo" column
                    saldo = result['bestellen']  # Note: key still named 'bestellen' in result dict
                    if saldo < 0:
                        worksheet.write(row, 6, saldo, red_format)  # Deficit - RED (need to order)
                    elif saldo > 0:
                        worksheet.write(row, 6, saldo, green_format)  # Surplus - GREEN
                    else:
                        worksheet.write(row, 6, saldo, normal_format)

                    row += 1

                workbook.close()

                self.status_var.set(f"✓ Geëxporteerd naar {Path(filename).name}")
                messagebox.showinfo("Succes", f"Bestelberekening geëxporteerd naar:\n{filename}")

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
