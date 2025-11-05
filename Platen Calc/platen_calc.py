#!/usr/bin/env python3
"""
Platen Calculator - Material berekeningen voor Excel bestanden
GUI versie met Excel-achtige tabel weergave
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime
import threading
from collections import defaultdict
from typing import Dict, List

# Import de hoofd calculator
from material_calculator import MaterialCalculator


class PlatenCalcGUI:
    """GUI Applicatie voor Platen Calculator met Excel-achtige tabel"""

    def __init__(self, root):
        self.root = root
        self.root.title("Platen Calculator")
        self.root.geometry("1600x950")

        # Make window resizable
        self.root.minsize(1200, 700)

        self.calculator = None
        self.files = []
        self.file_data = []  # Stores {filename, materials_dict, included}
        self.all_materials = []  # All unique materials across all files
        self.visible_materials = []  # Materials to show in table (filtered)
        self.material_visibility = {}  # Dict of material: visible (bool)

        self.setup_menu()
        self.setup_ui()

    def setup_menu(self):
        """Setup de menu balk"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Acties menu
        acties_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Acties", menu=acties_menu)
        acties_menu.add_command(label="Magazijn Ophalen", command=self.magazijn_ophalen)
        acties_menu.add_separator()
        acties_menu.add_command(label="Bestelberekening", command=self.open_bestelberekening)

    def magazijn_ophalen(self):
        """Magazijn Ophalen functionaliteit - Scan ContentResult CSV bestand"""
        # Ask user to select the CSV file
        csv_file = filedialog.askopenfilename(
            title="Selecteer ContentResult CSV bestand",
            initialdir=self.folder_var.get(),
            filetypes=[
                ("CSV bestanden", "*.csv"),
                ("Alle bestanden", "*.*")
            ]
        )

        if not csv_file:
            self.log("Magazijn Ophalen geannuleerd", 'warning')
            return

        self.log(f"Magazijn Ophalen gestart: {Path(csv_file).name}", 'info')
        self.status_var.set("Magazijn bestand laden...")

        try:
            import csv

            # Read the CSV file
            # Correct format: ID;Materiaal;Lengte;Breedte;Dikte;Nummer;Aantal;...;HOOFD NR field
            materials_data = []
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=';')

                for row in reader:
                    if len(row) >= 17:
                        # Parse the row
                        # Format: ID;Materiaal;Lengte;Breedte;Dikte;Nummer;Aantal;...;HOOFD NR (column 17)
                        try:
                            row_id = row[0].strip()
                            material_name = row[1].strip()
                            lengte = row[2].strip()  # Lengte (Length)
                            breedte = row[3].strip()  # Breedte (Width)
                            dikte = row[4].strip()  # Dikte (Thickness)
                            nummer = row[5].strip()  # Nummer
                            aantal = row[6].strip()  # Aantal (Quantity)
                            # Column 17 (index 16) contains "HOOFD NR      " for main warehouse items
                            hoofd_nr = row[16].strip() if len(row) > 16 else ""

                            # Only include rows with "HOOFD NR" marker
                            if material_name and "HOOFD NR" in hoofd_nr:
                                # Calculate m² = (lengte * breedte * aantal) / 1,000,000
                                try:
                                    lengte_val = float(lengte) if lengte else 0
                                    breedte_val = float(breedte) if breedte else 0
                                    aantal_val = float(aantal) if aantal else 0
                                    m2 = (lengte_val * breedte_val * aantal_val) / 1_000_000
                                except (ValueError, ZeroDivisionError):
                                    m2 = 0

                                materials_data.append({
                                    'id': row_id,
                                    'name': material_name,
                                    'lengte': lengte,
                                    'breedte': breedte,
                                    'dikte': dikte,
                                    'nummer': nummer,
                                    'aantal': aantal,
                                    'm2': m2
                                })
                        except (ValueError, IndexError):
                            continue

            self.log(f"✓ {len(materials_data)} HOOFD NR materialen geladen", 'success')

            # Display results in a new window
            self.show_magazijn_window(materials_data, Path(csv_file).name)

        except Exception as e:
            self.log(f"✗ Fout bij laden magazijn bestand: {e}", 'error')
            messagebox.showerror("Fout", f"Fout bij laden bestand:\n{e}")
            self.status_var.set("Fout bij laden")

    def show_magazijn_window(self, materials_data, filename):
        """Toon magazijn data in een nieuw venster"""
        # Create new window
        mag_window = tk.Toplevel(self.root)
        mag_window.title(f"Magazijn Overzicht - {filename}")
        mag_window.geometry("1100x600")
        mag_window.transient(self.root)

        # Main frame
        main = ttk.Frame(mag_window, padding="10")
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        # Info label
        info_label = ttk.Label(
            main,
            text=f"Magazijn voorraad (HOOFD NR): {len(materials_data)} materialen",
            font=('TkDefaultFont', 10, 'bold')
        )
        info_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        # Create table frame
        table_frame = ttk.Frame(main)
        table_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal")

        # Create treeview with correct columns: ID, Materiaal, Lengte, Breedte, Dikte, Nummer, Aantal, m²
        columns = ["ID", "Materiaal", "Lengte", "Breedte", "Dikte", "Nummer", "Aantal", "m²"]
        tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)

        # Configure columns
        tree.heading("ID", text="ID")
        tree.heading("Materiaal", text="Materiaal")
        tree.heading("Lengte", text="Lengte (mm)")
        tree.heading("Breedte", text="Breedte (mm)")
        tree.heading("Dikte", text="Dikte (mm)")
        tree.heading("Nummer", text="Nummer")
        tree.heading("Aantal", text="Aantal")
        tree.heading("m²", text="m²")

        tree.column("ID", width=60, anchor=tk.CENTER)
        tree.column("Materiaal", width=350, anchor=tk.W)
        tree.column("Lengte", width=100, anchor=tk.E)
        tree.column("Breedte", width=100, anchor=tk.E)
        tree.column("Dikte", width=80, anchor=tk.E)
        tree.column("Nummer", width=80, anchor=tk.E)
        tree.column("Aantal", width=80, anchor=tk.E)
        tree.column("m²", width=100, anchor=tk.E)

        # Insert data
        for item in materials_data:
            tree.insert("", "end", values=(
                item['id'],
                item['name'],
                item['lengte'],
                item['breedte'],
                item['dikte'],
                item['nummer'],
                item['aantal'],
                f"{item['m2']:.2f}"
            ))

        # Grid layout
        tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Button frame
        button_frame = ttk.Frame(main)
        button_frame.grid(row=2, column=0, pady=(10, 0))

        ttk.Button(button_frame, text="Sluiten", command=mag_window.destroy, width=15).pack(side=tk.LEFT, padx=5)

        self.status_var.set(f"Magazijn overzicht weergegeven: {len(materials_data)} HOOFD NR items")
        self.log(f"✓ Magazijn overzicht geopend", 'success')

    def open_bestelberekening(self):
        """Open Bestelberekening window"""
        BestelberekeningWindow(self.root, self.folder_var.get())

    def setup_ui(self):
        """Setup de gebruikersinterface"""

        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights for responsive resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=85)  # Table gets most space (row 3) - 85%
        main_frame.rowconfigure(4, weight=15)  # Log gets less space (row 4) - 15%

        # --- Map Selectie ---
        row = 0
        folder_frame = ttk.LabelFrame(main_frame, text="Map Instellingen", padding="5")
        folder_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        folder_frame.columnconfigure(1, weight=1)

        ttk.Label(folder_frame, text="Map:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))

        path_frame = ttk.Frame(folder_frame)
        path_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        path_frame.columnconfigure(0, weight=1)

        self.folder_var = tk.StringVar(value="Stuklijsten")
        ttk.Entry(path_frame, textvariable=self.folder_var).grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(path_frame, text="Bladeren...", command=self.browse_folder).grid(
            row=0, column=1
        )

        # --- Filters Section ---
        row += 1
        filters_frame = ttk.LabelFrame(main_frame, text="Filters", padding="5")
        filters_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        filters_frame.columnconfigure(1, weight=1)
        filters_frame.columnconfigure(3, weight=1)
        filters_frame.columnconfigure(5, weight=1)

        # Row 1: Filename, Customer, Project
        ttk.Label(filters_frame, text="Bestandsnaam:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.filename_pattern_var = tk.StringVar()
        ttk.Entry(filters_frame, textvariable=self.filename_pattern_var, width=20).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10)
        )

        ttk.Label(filters_frame, text="Klant:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.customer_var = tk.StringVar()
        ttk.Entry(filters_frame, textvariable=self.customer_var, width=20).grid(
            row=0, column=3, sticky=(tk.W, tk.E), padx=(0, 10)
        )

        ttk.Label(filters_frame, text="Project:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.project_var = tk.StringVar()
        ttk.Entry(filters_frame, textvariable=self.project_var, width=20).grid(
            row=0, column=5, sticky=(tk.W, tk.E)
        )

        # Row 2: Date from, Date to, Exclude
        ttk.Label(filters_frame, text="Datum van:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.date_from_var = tk.StringVar()
        ttk.Entry(filters_frame, textvariable=self.date_from_var, width=20).grid(
            row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10), pady=(5, 0)
        )

        ttk.Label(filters_frame, text="Datum tot:").grid(row=1, column=2, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.date_to_var = tk.StringVar()
        ttk.Entry(filters_frame, textvariable=self.date_to_var, width=20).grid(
            row=1, column=3, sticky=(tk.W, tk.E), padx=(0, 10), pady=(5, 0)
        )

        ttk.Label(filters_frame, text="Uitsluiten:").grid(row=1, column=4, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.exclude_var = tk.StringVar()
        ttk.Entry(filters_frame, textvariable=self.exclude_var, width=20).grid(
            row=1, column=5, sticky=(tk.W, tk.E), pady=(5, 0)
        )

        # --- Action Buttons ---
        row += 1
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, pady=(0, 10))

        ttk.Button(button_frame, text="Scan Map", command=self.scan_and_process, width=15).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Selecteer Alles", command=self.select_all, width=15).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Deselecteer Alles", command=self.deselect_all, width=15).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Filter Kolommen", command=self.filter_columns, width=15).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Exporteer CSV", command=self.export_csv, width=15).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Wissen", command=self.clear_all, width=15).pack(
            side=tk.LEFT, padx=5
        )

        # --- Data Table (Excel-like) ---
        row += 1
        table_frame = ttk.LabelFrame(main_frame, text="Materiaal Overzicht", padding="5")
        table_frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Create table with scrollbars
        table_container = ttk.Frame(table_frame)
        table_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        table_container.columnconfigure(0, weight=1)
        table_container.rowconfigure(0, weight=1)

        # Scrollbars
        vsb = ttk.Scrollbar(table_container, orient="vertical")
        hsb = ttk.Scrollbar(table_container, orient="horizontal")

        # Configure style for smaller, more readable font
        style = ttk.Style()
        style.configure("Treeview", font=('Segoe UI', 9), rowheight=22)
        style.configure("Treeview.Heading", font=('Segoe UI', 9, 'bold'))

        # Treeview for table
        self.table = ttk.Treeview(
            table_container,
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectmode='browse',
            height=20
        )

        vsb.config(command=self.table.yview)
        hsb.config(command=self.table.xview)

        # Grid layout
        self.table.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Bind checkbox toggle
        self.table.bind('<Button-1>', self.on_table_click)
        self.table.bind('<space>', self.on_table_space)

        # --- Log Viewer ---
        row += 1
        log_frame = ttk.LabelFrame(main_frame, text="Activiteiten Log", padding="5")
        log_frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=('Consolas', 9), height=3
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=2)

        # Configure tag for different log levels
        self.log_text.tag_config('info', foreground='black')
        self.log_text.tag_config('success', foreground='green')
        self.log_text.tag_config('warning', foreground='orange')
        self.log_text.tag_config('error', foreground='red')

        # Status bar
        row += 1
        self.status_var = tk.StringVar(value="Klaar")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=row, column=0, sticky=(tk.W, tk.E))

    def browse_folder(self):
        """Open map browser dialoog"""
        folder = filedialog.askdirectory(
            title="Selecteer Map met Excel Bestanden",
            initialdir=self.folder_var.get()
        )
        if folder:
            self.folder_var.set(folder)

    def get_filters(self):
        """Haal filter instellingen op uit UI"""
        filters = {}

        if self.filename_pattern_var.get():
            filters['filename_pattern'] = self.filename_pattern_var.get()

        if self.date_from_var.get():
            filters['date_from'] = self.date_from_var.get()

        if self.date_to_var.get():
            filters['date_to'] = self.date_to_var.get()

        if self.customer_var.get():
            filters['customer'] = self.customer_var.get()

        if self.project_var.get():
            filters['project_number'] = self.project_var.get()

        if self.exclude_var.get():
            filters['exclude_pattern'] = self.exclude_var.get()

        return filters

    def log(self, message, level='info'):
        """Log bericht naar output gebied"""
        self.log_text.insert(tk.END, message + "\n", level)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_all(self):
        """Wis de output en tabel"""
        self.log_text.delete(1.0, tk.END)
        self.clear_table()
        self.file_data = []
        self.all_materials = []
        self.status_var.set("Klaar")

    def clear_table(self):
        """Wis de tabel"""
        for item in self.table.get_children():
            self.table.delete(item)
        self.table["columns"] = ()
        self.table.heading("#0", text="")

    def scan_and_process(self):
        """Scan map en verwerk bestanden"""
        self.clear_all()
        folder = self.folder_var.get()

        self.log(f"Scannen van map: {folder}", 'info')
        self.status_var.set("Scannen...")

        def scan_thread():
            try:
                self.calculator = MaterialCalculator(folder)
                self.files = self.calculator.scan_folder()

                self.log(f"✓ {len(self.files)} bestanden gevonden", 'success')

                # Apply filters
                filters = self.get_filters()
                if filters:
                    self.log("Filters toepassen...", 'info')
                    self.files = self.calculator.apply_filters(self.files, filters)
                    self.log(f"✓ Na filters: {len(self.files)} bestanden", 'success')

                if not self.files:
                    self.log("⚠ Geen bestanden gevonden!", 'warning')
                    self.status_var.set("Geen bestanden")
                    return

                # Process all files to extract data
                self.log(f"\nBestanden verwerken...", 'info')
                self.status_var.set(f"Verwerken van {len(self.files)} bestanden...")

                self.file_data = []
                all_materials_dict = defaultdict(float)

                for idx, file_path in enumerate(self.files, 1):
                    if idx % 10 == 0:
                        self.log(f"  Verwerkt: {idx}/{len(self.files)}", 'info')

                    materials = self.calculator.extract_material_data(file_path)

                    if materials:
                        self.file_data.append({
                            'filename': file_path.name,
                            'materials': materials,
                            'included': True  # Default: included
                        })

                        # Collect all unique materials
                        for material, amount in materials.items():
                            all_materials_dict[material] += amount

                self.log(f"✓ Verwerking voltooid: {len(self.file_data)} bestanden met data", 'success')

                # Sort materials by total amount
                self.all_materials = sorted(
                    all_materials_dict.keys(),
                    key=lambda m: all_materials_dict[m],
                    reverse=True
                )

                # Initialize visibility - all materials visible by default
                self.material_visibility = {mat: True for mat in self.all_materials}
                self.visible_materials = self.all_materials.copy()

                self.log(f"✓ {len(self.all_materials)} unieke materialen gevonden", 'success')

                # Build table
                self.build_table()

                self.status_var.set(f"{len(self.file_data)} bestanden geladen - Klaar voor export")

            except Exception as e:
                self.log(f"✗ FOUT: {e}", 'error')
                messagebox.showerror("Fout", f"Fout bij scannen: {e}")
                self.status_var.set("Fout")

        thread = threading.Thread(target=scan_thread, daemon=True)
        thread.start()

    def build_table(self):
        """Bouw de Excel-achtige tabel"""
        self.clear_table()

        if not self.file_data or not self.visible_materials:
            return

        # Define columns: checkbox (✓), filename, then each visible material
        columns = ["✓", "Bestandsnaam"] + self.visible_materials

        # Configure treeview
        self.table["columns"] = columns
        self.table["show"] = "tree headings"  # Show both tree and headings

        # Configure column 0 (tree column) - for row numbers
        self.table.column("#0", width=50, anchor=tk.CENTER, minwidth=50, stretch=False)
        self.table.heading("#0", text="#")

        # Configure checkbox column
        self.table.column("✓", width=50, anchor=tk.CENTER, minwidth=50, stretch=False)
        self.table.heading("✓", text="✓")

        # Configure filename column - calculate width based on longest filename
        max_filename_len = max(len(fd['filename']) for fd in self.file_data) if self.file_data else 20
        filename_width = min(max(max_filename_len * 7, 250), 600)  # Between 250-600px
        self.table.column("Bestandsnaam", width=filename_width, anchor=tk.W, minwidth=250, stretch=False)
        self.table.heading("Bestandsnaam", text="Bestandsnaam")

        # Configure material columns - auto-fit based on material name length
        for material in self.visible_materials:
            # Calculate width based on material name length
            material_name_len = len(material)
            # Minimum 120px, add 8px per character, max 300px
            col_width = min(max(material_name_len * 8, 120), 300)

            # Use full material name for header
            self.table.column(material, width=col_width, anchor=tk.E, minwidth=120, stretch=False)
            self.table.heading(material, text=material)

        # Insert TOTALS row first
        totals_values = ["", "TOTALEN"]
        for material in self.visible_materials:
            total = sum(
                fd['materials'].get(material, 0)
                for fd in self.file_data
                if fd['included']
            )
            totals_values.append(f"{total:.2f}")

        totals_id = self.table.insert("", "end", text="", values=totals_values, tags=('totals',))

        # Configure totals row style
        self.table.tag_configure('totals', background='#e0e0e0', font=('TkDefaultFont', 9, 'bold'))

        # Insert separator
        sep_values = ["", "─" * 40] + ["─" * 10] * len(self.visible_materials)
        self.table.insert("", "end", text="", values=sep_values, tags=('separator',))
        self.table.tag_configure('separator', foreground='gray')

        # Insert data rows
        for idx, file_data in enumerate(self.file_data, 1):
            checkbox = "☑" if file_data['included'] else "☐"
            values = [checkbox, file_data['filename']]

            # Add material values (only visible ones)
            for material in self.visible_materials:
                amount = file_data['materials'].get(material, 0)
                if amount > 0:
                    values.append(f"{amount:.2f}")
                else:
                    values.append("")

            item_id = self.table.insert("", "end", text=str(idx), values=values, tags=(f'row_{idx}',))

            # Store item_id for later reference
            file_data['item_id'] = item_id

        self.log(f"✓ Tabel opgebouwd met {len(self.file_data)} rijen en {len(self.visible_materials)} materiaal kolommen", 'success')

    def on_table_click(self, event):
        """Handle tabel klik voor checkbox toggle"""
        region = self.table.identify("region", event.x, event.y)
        if region == "cell":
            column = self.table.identify_column(event.x)
            row_id = self.table.identify_row(event.y)

            # Check if clicked on checkbox column (column #1)
            if column == "#1" and row_id:
                # Don't toggle totals or separator rows
                if 'totals' in self.table.item(row_id, 'tags') or 'separator' in self.table.item(row_id, 'tags'):
                    return

                self.toggle_checkbox(row_id)

    def on_table_space(self, event):
        """Handle spatie toets voor checkbox toggle"""
        selection = self.table.selection()
        if selection:
            row_id = selection[0]
            # Don't toggle totals or separator rows
            if 'totals' not in self.table.item(row_id, 'tags') and 'separator' not in self.table.item(row_id, 'tags'):
                self.toggle_checkbox(row_id)

    def toggle_checkbox(self, row_id):
        """Toggle checkbox voor een rij"""
        values = list(self.table.item(row_id, 'values'))

        # Toggle checkbox
        if values[0] == "☑":
            values[0] = "☐"
            included = False
        else:
            values[0] = "☑"
            included = True

        self.table.item(row_id, values=values)

        # Update file_data
        for fd in self.file_data:
            if fd.get('item_id') == row_id:
                fd['included'] = included
                break

        # Update totals row
        self.update_totals()

    def update_totals(self):
        """Update de totalen rij"""
        # Find totals row (first row)
        for item in self.table.get_children():
            if 'totals' in self.table.item(item, 'tags'):
                totals_values = ["", "TOTALEN"]
                for material in self.visible_materials:
                    total = sum(
                        fd['materials'].get(material, 0)
                        for fd in self.file_data
                        if fd['included']
                    )
                    totals_values.append(f"{total:.2f}")

                self.table.item(item, values=totals_values)
                break

    def select_all(self):
        """Selecteer alle bestanden"""
        for fd in self.file_data:
            fd['included'] = True
            if 'item_id' in fd:
                values = list(self.table.item(fd['item_id'], 'values'))
                values[0] = "☑"
                self.table.item(fd['item_id'], values=values)

        self.update_totals()
        self.log("✓ Alle bestanden geselecteerd", 'success')

    def deselect_all(self):
        """Deselecteer alle bestanden"""
        for fd in self.file_data:
            fd['included'] = False
            if 'item_id' in fd:
                values = list(self.table.item(fd['item_id'], 'values'))
                values[0] = "☐"
                self.table.item(fd['item_id'], values=values)

        self.update_totals()
        self.log("✓ Alle bestanden gedeselecteerd", 'success')

    def filter_columns(self):
        """Open dialoog om materiaal kolommen te filteren"""
        if not self.all_materials:
            messagebox.showwarning("Waarschuwing", "Geen materialen geladen! Scan eerst de map.")
            return

        # Create filter dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Filter Materiaal Kolommen")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()

        # Main frame
        main = ttk.Frame(dialog, padding="10")
        main.pack(fill=tk.BOTH, expand=True)

        # Info label
        info_label = ttk.Label(
            main,
            text=f"Selecteer welke materialen je wilt tonen ({len(self.all_materials)} totaal):",
            font=('TkDefaultFont', 9, 'bold')
        )
        info_label.pack(pady=(0, 10))

        # Quick action buttons
        button_frame = ttk.Frame(main)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(button_frame, text="Selecteer Alles",
                   command=lambda: self.select_all_materials(material_vars)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Deselecteer Alles",
                   command=lambda: self.deselect_all_materials(material_vars)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Top 10",
                   command=lambda: self.select_top_n_materials(material_vars, 10)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Top 20",
                   command=lambda: self.select_top_n_materials(material_vars, 20)).pack(side=tk.LEFT, padx=5)

        # Scrollable frame for checkboxes
        canvas = tk.Canvas(main, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Create checkboxes for each material
        material_vars = {}
        for idx, material in enumerate(self.all_materials, 1):
            var = tk.BooleanVar(value=self.material_visibility.get(material, True))
            material_vars[material] = var

            cb_frame = ttk.Frame(scrollable_frame)
            cb_frame.pack(fill=tk.X, padx=5, pady=2)

            ttk.Checkbutton(
                cb_frame,
                text=f"{idx}. {material}",
                variable=var
            ).pack(side=tk.LEFT)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button frame at bottom
        bottom_frame = ttk.Frame(main)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))

        def apply_filter():
            # Update visibility dict
            for material, var in material_vars.items():
                self.material_visibility[material] = var.get()

            # Update visible materials list
            self.visible_materials = [m for m in self.all_materials if self.material_visibility[m]]

            # Rebuild table with new columns
            self.build_table()

            visible_count = len(self.visible_materials)
            self.log(f"✓ Kolom filter toegepast: {visible_count}/{len(self.all_materials)} materialen zichtbaar", 'success')
            dialog.destroy()

        def cancel():
            dialog.destroy()

        ttk.Button(bottom_frame, text="Toepassen", command=apply_filter, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="Annuleren", command=cancel, width=15).pack(side=tk.LEFT, padx=5)

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def select_all_materials(self, material_vars):
        """Selecteer alle materialen in filter dialoog"""
        for var in material_vars.values():
            var.set(True)

    def deselect_all_materials(self, material_vars):
        """Deselecteer alle materialen in filter dialoog"""
        for var in material_vars.values():
            var.set(False)

    def select_top_n_materials(self, material_vars, n):
        """Selecteer top N materialen (eerste N in de lijst)"""
        for idx, (material, var) in enumerate(material_vars.items()):
            var.set(idx < n)

    def export_csv(self):
        """Exporteer resultaten naar CSV"""
        if not self.file_data:
            messagebox.showwarning("Waarschuwing", "Geen data om te exporteren! Scan eerst de map.")
            return

        # Filter only included files
        included_files = [fd for fd in self.file_data if fd['included']]

        if not included_files:
            messagebox.showwarning("Waarschuwing", "Geen bestanden geselecteerd voor export!")
            return

        # Ask for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"materiaal_totalen_{timestamp}.csv"

        filename = filedialog.asksaveasfilename(
            title="Opslaan als CSV",
            initialfile=default_filename,
            defaultextension=".csv",
            filetypes=[("CSV bestanden", "*.csv"), ("Alle bestanden", "*.*")]
        )

        if filename:
            try:
                import csv

                # Calculate totals for included files only
                material_totals = defaultdict(float)
                for fd in included_files:
                    for material, amount in fd['materials'].items():
                        material_totals[material] += amount

                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')

                    # Header
                    writer.writerow(['Materiaal', 'Netto (m²)'])

                    # Data sorted by amount
                    sorted_materials = sorted(
                        material_totals.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )

                    for material, amount in sorted_materials:
                        writer.writerow([material, f"{amount:.2f}"])

                    # Total
                    writer.writerow([''])
                    writer.writerow(['TOTAAL', f"{sum(material_totals.values()):.2f}"])
                    writer.writerow([''])
                    writer.writerow(['Aantal bestanden', len(included_files)])

                self.log(f"✓ Geëxporteerd naar: {filename}", 'success')
                self.log(f"  {len(included_files)} bestanden, {len(material_totals)} materialen", 'info')
                messagebox.showinfo("Succes", f"Resultaten geëxporteerd naar:\n{filename}\n\n{len(included_files)} bestanden verwerkt")
                self.status_var.set(f"Geëxporteerd naar {Path(filename).name}")

            except Exception as e:
                messagebox.showerror("Fout", f"Fout bij exporteren: {e}")
                self.log(f"✗ Export fout: {e}", 'error')


class BestelberekeningWindow:
    """Enterprise-grade Bestelberekening window met tabs"""

    def __init__(self, parent, default_folder):
        self.parent = parent
        self.default_folder = default_folder

        # Data storage
        self.orders_data = {}  # {material_name: netto_m2}
        self.stock_data = {}  # {material_name: stock_m2}
        self.settings = {
            'rendement_pct': 75.0,  # Default 75%
            'safety_margin_m2': 0.0,
            'material_overrides': {}  # {material: {rendement, safety}}
        }

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("Bestelberekening - Enterprise Material Planning")
        self.window.geometry("1400x800")
        self.window.transient(parent)

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        """Setup the tabbed interface"""
        # Main container
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Bestelberekening - Material Order Calculation",
            font=('Segoe UI', 14, 'bold')
        )
        title_label.pack(pady=(0, 10))

        # Create notebook (tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self.tab1 = ttk.Frame(self.notebook)
        self.tab2 = ttk.Frame(self.notebook)
        self.tab3 = ttk.Frame(self.notebook)
        self.tab4 = ttk.Frame(self.notebook)

        self.notebook.add(self.tab1, text="① Orders")
        self.notebook.add(self.tab2, text="② Magazijn")
        self.notebook.add(self.tab3, text="③ Instellingen")
        self.notebook.add(self.tab4, text="④ Berekening")

        # Setup each tab
        self.setup_tab1_orders()
        self.setup_tab2_magazijn()
        self.setup_tab3_instellingen()
        self.setup_tab4_berekening()

        # Status bar
        self.status_var = tk.StringVar(value="Klaar om te beginnen")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.pack(fill=tk.X, pady=(10, 0))

    def setup_tab1_orders(self):
        """Tab 1: Scan orders and extract netto m²"""
        frame = ttk.Frame(self.tab1, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(
            frame,
            text="Stap 1: Orders Scannen",
            font=('Segoe UI', 12, 'bold')
        ).pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(
            frame,
            text="Scan Excel bestanden om netto m² per materiaal te berekenen",
            foreground='gray'
        ).pack(anchor=tk.W, pady=(0, 20))

        # Folder selection
        folder_frame = ttk.LabelFrame(frame, text="Map Selectie", padding="10")
        folder_frame.pack(fill=tk.X, pady=(0, 10))

        path_container = ttk.Frame(folder_frame)
        path_container.pack(fill=tk.X)
        path_container.columnconfigure(0, weight=1)

        self.orders_folder_var = tk.StringVar(value=self.default_folder)
        ttk.Entry(path_container, textvariable=self.orders_folder_var).grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(path_container, text="Bladeren...", command=self.browse_orders_folder).grid(
            row=0, column=1
        )

        # Scan button
        ttk.Button(
            folder_frame,
            text="Scan Orders",
            command=self.scan_orders,
            width=20
        ).pack(pady=(10, 0))

        # Results table
        results_frame = ttk.LabelFrame(frame, text="Gevonden Materialen", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Scrollbars
        vsb = ttk.Scrollbar(results_frame, orient="vertical")
        hsb = ttk.Scrollbar(results_frame, orient="horizontal")

        # Treeview
        columns = ["Materiaal", "Netto (m²)"]
        self.orders_tree = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=15
        )

        vsb.config(command=self.orders_tree.yview)
        hsb.config(command=self.orders_tree.xview)

        self.orders_tree.heading("Materiaal", text="Materiaal")
        self.orders_tree.heading("Netto (m²)", text="Netto (m²)")

        self.orders_tree.column("Materiaal", width=500, anchor=tk.W)
        self.orders_tree.column("Netto (m²)", width=150, anchor=tk.E)

        self.orders_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_tab2_magazijn(self):
        """Tab 2: Load magazijn stock data"""
        frame = ttk.Frame(self.tab2, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(
            frame,
            text="Stap 2: Magazijn Voorraad Laden",
            font=('Segoe UI', 12, 'bold')
        ).pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(
            frame,
            text="Laad huidige voorraad uit ContentResult CSV bestand",
            foreground='gray'
        ).pack(anchor=tk.W, pady=(0, 20))

        # File selection
        file_frame = ttk.LabelFrame(frame, text="CSV Bestand", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(
            file_frame,
            text="Selecteer Magazijn CSV",
            command=self.load_magazijn_data,
            width=25
        ).pack()

        # Results table
        results_frame = ttk.LabelFrame(frame, text="Magazijn Voorraad (HOOFD NR)", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Scrollbars
        vsb = ttk.Scrollbar(results_frame, orient="vertical")
        hsb = ttk.Scrollbar(results_frame, orient="horizontal")

        # Treeview
        columns = ["Materiaal", "Stock (m²)"]
        self.magazijn_tree = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=15
        )

        vsb.config(command=self.magazijn_tree.yview)
        hsb.config(command=self.magazijn_tree.xview)

        self.magazijn_tree.heading("Materiaal", text="Materiaal")
        self.magazijn_tree.heading("Stock (m²)", text="Stock (m²)")

        self.magazijn_tree.column("Materiaal", width=500, anchor=tk.W)
        self.magazijn_tree.column("Stock (m²)", width=150, anchor=tk.E)

        self.magazijn_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_tab3_instellingen(self):
        """Tab 3: Configure settings"""
        frame = ttk.Frame(self.tab3, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(
            frame,
            text="Stap 3: Instellingen Configureren",
            font=('Segoe UI', 12, 'bold')
        ).pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(
            frame,
            text="Stel globale parameters in voor de berekening",
            foreground='gray'
        ).pack(anchor=tk.W, pady=(0, 20))

        # Global settings
        settings_frame = ttk.LabelFrame(frame, text="Globale Instellingen", padding="15")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Rendement percentage
        rendement_frame = ttk.Frame(settings_frame)
        rendement_frame.pack(fill=tk.X, pady=5)

        ttk.Label(rendement_frame, text="Rendement %:", width=25).pack(side=tk.LEFT)
        self.rendement_var = tk.StringVar(value="75.0")
        rendement_entry = ttk.Entry(rendement_frame, textvariable=self.rendement_var, width=15)
        rendement_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(rendement_frame, text="(Default: 75% = 0.75)", foreground='gray').pack(side=tk.LEFT)

        # Safety margin
        safety_frame = ttk.Frame(settings_frame)
        safety_frame.pack(fill=tk.X, pady=5)

        ttk.Label(safety_frame, text="Veiligheidsvoorraad (m²):", width=25).pack(side=tk.LEFT)
        self.safety_var = tk.StringVar(value="0.0")
        safety_entry = ttk.Entry(safety_frame, textvariable=self.safety_var, width=15)
        safety_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(safety_frame, text="(Globaal voor alle materialen)", foreground='gray').pack(side=tk.LEFT)

        # Apply button
        ttk.Button(
            settings_frame,
            text="Instellingen Toepassen",
            command=self.apply_settings,
            width=25
        ).pack(pady=(15, 0))

        # Info
        info_frame = ttk.LabelFrame(frame, text="Berekeningsformules", padding="15")
        info_frame.pack(fill=tk.X, pady=(10, 0))

        formulas = [
            "Bruto m² = Netto m² ÷ (Rendement % / 100)",
            "Totaal Stock = Huidige Stock + Veiligheidsvoorraad",
            "Bestellen m² = Bruto m² - Totaal Stock",
            "",
            "Voorbeeld met Rendement 75%:",
            "  Netto: 100 m² → Bruto: 100 ÷ 0.75 = 133.33 m²"
        ]

        for formula in formulas:
            ttk.Label(
                info_frame,
                text=formula,
                font=('Courier New', 9),
                foreground='#0066cc' if '=' in formula else 'gray'
            ).pack(anchor=tk.W, pady=2)

    def setup_tab4_berekening(self):
        """Tab 4: Final calculation and export"""
        frame = ttk.Frame(self.tab4, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            header_frame,
            text="Stap 4: Bestelberekening",
            font=('Segoe UI', 12, 'bold')
        ).pack(side=tk.LEFT)

        # Action buttons
        button_frame = ttk.Frame(header_frame)
        button_frame.pack(side=tk.RIGHT)

        ttk.Button(button_frame, text="Berekenen", command=self.calculate, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Exporteer Excel", command=self.export_excel, width=15).pack(side=tk.LEFT, padx=5)

        # Results table
        results_frame = ttk.Frame(frame)
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbars
        vsb = ttk.Scrollbar(results_frame, orient="vertical")
        hsb = ttk.Scrollbar(results_frame, orient="horizontal")

        # Treeview
        columns = ["Materiaal", "Netto (m²)", "R%", "Bruto m²", "Stock (m²)", "Veiligh. (m²)", "Totaal (m²)", "Bestellen (m²)"]
        self.calc_tree = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        vsb.config(command=self.calc_tree.yview)
        hsb.config(command=self.calc_tree.xview)

        # Configure columns
        self.calc_tree.heading("Materiaal", text="Materiaal")
        self.calc_tree.heading("Netto (m²)", text="Netto (m²)")
        self.calc_tree.heading("R%", text="R%")
        self.calc_tree.heading("Bruto m²", text="Bruto m²")
        self.calc_tree.heading("Stock (m²)", text="Stock (m²)")
        self.calc_tree.heading("Veiligh. (m²)", text="Veiligheidsvoorraad")
        self.calc_tree.heading("Totaal (m²)", text="Totaal m²")
        self.calc_tree.heading("Bestellen (m²)", text="Bestellen m²")

        self.calc_tree.column("Materiaal", width=300, anchor=tk.W)
        self.calc_tree.column("Netto (m²)", width=100, anchor=tk.E)
        self.calc_tree.column("R%", width=70, anchor=tk.E)
        self.calc_tree.column("Bruto m²", width=100, anchor=tk.E)
        self.calc_tree.column("Stock (m²)", width=100, anchor=tk.E)
        self.calc_tree.column("Veiligh. (m²)", width=120, anchor=tk.E)
        self.calc_tree.column("Totaal (m²)", width=100, anchor=tk.E)
        self.calc_tree.column("Bestellen (m²)", width=120, anchor=tk.E)

        self.calc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # Configure tag for negative values
        self.calc_tree.tag_configure('positive', foreground='green')
        self.calc_tree.tag_configure('negative', foreground='red')
        self.calc_tree.tag_configure('total', background='#e0e0e0', font=('TkDefaultFont', 9, 'bold'))

    # Tab 1 Methods
    def browse_orders_folder(self):
        """Browse for orders folder"""
        folder = filedialog.askdirectory(
            title="Selecteer Map met Excel Bestanden",
            initialdir=self.orders_folder_var.get()
        )
        if folder:
            self.orders_folder_var.set(folder)

    def scan_orders(self):
        """Scan orders folder and extract netto m²"""
        folder = self.orders_folder_var.get()
        self.status_var.set("Orders scannen...")

        try:
            calculator = MaterialCalculator(folder)
            files = calculator.scan_folder()

            if not files:
                messagebox.showwarning("Waarschuwing", "Geen Excel bestanden gevonden!")
                self.status_var.set("Geen bestanden gevonden")
                return

            # Process files
            material_totals = defaultdict(float)
            for file_path in files:
                materials = calculator.extract_material_data(file_path)
                for material, amount in materials.items():
                    material_totals[material] += amount

            # Store data
            self.orders_data = dict(material_totals)

            # Update table
            for item in self.orders_tree.get_children():
                self.orders_tree.delete(item)

            sorted_materials = sorted(
                material_totals.items(),
                key=lambda x: x[1],
                reverse=True
            )

            for material, netto_m2 in sorted_materials:
                self.orders_tree.insert("", "end", values=(material, f"{netto_m2:.2f}"))

            self.status_var.set(f"✓ {len(files)} bestanden gescand, {len(material_totals)} materialen gevonden")
            messagebox.showinfo("Succes", f"Orders gescand!\n\n{len(files)} bestanden\n{len(material_totals)} unieke materialen")

        except Exception as e:
            messagebox.showerror("Fout", f"Fout bij scannen orders:\n{e}")
            self.status_var.set("Fout bij scannen")

    # Tab 2 Methods
    def load_magazijn_data(self):
        """Load magazijn CSV data"""
        csv_file = filedialog.askopenfilename(
            title="Selecteer ContentResult CSV bestand",
            initialdir=self.default_folder,
            filetypes=[("CSV bestanden", "*.csv"), ("Alle bestanden", "*.*")]
        )

        if not csv_file:
            return

        self.status_var.set("Magazijn data laden...")

        try:
            import csv

            # Read and process CSV
            materials_data = {}
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=';')

                for row in reader:
                    if len(row) >= 17:
                        try:
                            material_name = row[1].strip()
                            lengte = float(row[2].strip()) if row[2].strip() else 0
                            breedte = float(row[3].strip()) if row[3].strip() else 0
                            aantal = float(row[6].strip()) if row[6].strip() else 0
                            hoofd_nr = row[16].strip() if len(row) > 16 else ""

                            # Only HOOFD NR materials
                            if material_name and "HOOFD NR" in hoofd_nr:
                                m2 = (lengte * breedte * aantal) / 1_000_000
                                # Aggregate if material already exists
                                if material_name in materials_data:
                                    materials_data[material_name] += m2
                                else:
                                    materials_data[material_name] = m2

                        except (ValueError, IndexError):
                            continue

            # Store data
            self.stock_data = materials_data

            # Update table
            for item in self.magazijn_tree.get_children():
                self.magazijn_tree.delete(item)

            sorted_materials = sorted(
                materials_data.items(),
                key=lambda x: x[0]
            )

            for material, stock_m2 in sorted_materials:
                self.magazijn_tree.insert("", "end", values=(material, f"{stock_m2:.2f}"))

            self.status_var.set(f"✓ Magazijn data geladen: {len(materials_data)} materialen")
            messagebox.showinfo("Succes", f"Magazijn data geladen!\n\n{len(materials_data)} materialen met HOOFD NR")

        except Exception as e:
            messagebox.showerror("Fout", f"Fout bij laden magazijn:\n{e}")
            self.status_var.set("Fout bij laden")

    # Tab 3 Methods
    def apply_settings(self):
        """Apply global settings"""
        try:
            rendement = float(self.rendement_var.get())
            safety = float(self.safety_var.get())

            if rendement <= 0 or rendement > 100:
                messagebox.showerror("Fout", "Rendement % moet tussen 0 en 100 zijn!")
                return

            if safety < 0:
                messagebox.showerror("Fout", "Veiligheidsvoorraad kan niet negatief zijn!")
                return

            self.settings['rendement_pct'] = rendement
            self.settings['safety_margin_m2'] = safety

            self.status_var.set(f"✓ Instellingen toegepast: R={rendement}%, Veiligh={safety} m²")
            messagebox.showinfo("Succes", f"Instellingen toegepast!\n\nRendement: {rendement}%\nVeiligheidsvoorraad: {safety} m²")

        except ValueError:
            messagebox.showerror("Fout", "Ongeldige waarden! Gebruik alleen getallen.")

    # Tab 4 Methods
    def calculate(self):
        """Calculate order requirements"""
        if not self.orders_data:
            messagebox.showwarning("Waarschuwing", "Scan eerst de orders (Tab 1)!")
            self.notebook.select(self.tab1)
            return

        self.status_var.set("Berekening uitvoeren...")

        try:
            # Clear table
            for item in self.calc_tree.get_children():
                self.calc_tree.delete(item)

            # Get all unique materials from orders
            all_materials = sorted(self.orders_data.keys(), key=lambda m: self.orders_data[m], reverse=True)

            total_netto = 0
            total_bruto = 0
            total_bestellen = 0

            for material in all_materials:
                netto_m2 = self.orders_data[material]
                rendement_pct = self.settings['rendement_pct']
                safety_m2 = self.settings['safety_margin_m2']
                stock_m2 = self.stock_data.get(material, 0.0)

                # Calculate
                rendement_decimal = rendement_pct / 100.0
                bruto_m2 = netto_m2 / rendement_decimal
                totaal_stock_m2 = stock_m2 + safety_m2
                bestellen_m2 = bruto_m2 - totaal_stock_m2

                # Totals
                total_netto += netto_m2
                total_bruto += bruto_m2
                total_bestellen += bestellen_m2

                # Insert row
                tag = 'positive' if bestellen_m2 < 0 else 'negative' if bestellen_m2 > 0 else ''
                self.calc_tree.insert("", "end", values=(
                    material,
                    f"{netto_m2:.2f}",
                    f"{rendement_decimal:.2f}",
                    f"{bruto_m2:.2f}",
                    f"{stock_m2:.2f}",
                    f"{safety_m2:.2f}",
                    f"{totaal_stock_m2:.2f}",
                    f"{bestellen_m2:.2f}"
                ), tags=(tag,))

            # Add total row
            self.calc_tree.insert("", "end", values=(
                "TOTAAL",
                f"{total_netto:.2f}",
                "",
                f"{total_bruto:.2f}",
                "",
                "",
                "",
                f"{total_bestellen:.2f}"
            ), tags=('total',))

            self.status_var.set(f"✓ Berekening voltooid: {len(all_materials)} materialen")

        except Exception as e:
            messagebox.showerror("Fout", f"Fout bij berekenen:\n{e}")
            self.status_var.set("Fout bij berekenen")

    def export_excel(self):
        """Export calculation to Excel"""
        if not self.calc_tree.get_children():
            messagebox.showwarning("Waarschuwing", "Voer eerst de berekening uit!")
            return

        # Ask for filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"bestelberekening_{timestamp}.csv"

        filename = filedialog.asksaveasfilename(
            title="Exporteer Bestelberekening",
            initialfile=default_filename,
            defaultextension=".csv",
            filetypes=[("CSV bestanden", "*.csv"), ("Alle bestanden", "*.*")]
        )

        if filename:
            try:
                import csv

                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')

                    # Header
                    writer.writerow([
                        'Materiaal',
                        'Netto (m²)',
                        'R%',
                        'Bruto m²',
                        'm² huidige stock',
                        'm² veiligheidsvoorraad',
                        'Totaal m²',
                        'Bestellen m²'
                    ])

                    # Data
                    for item in self.calc_tree.get_children():
                        values = self.calc_tree.item(item, 'values')
                        writer.writerow(values)

                self.status_var.set(f"✓ Geëxporteerd naar {Path(filename).name}")
                messagebox.showinfo("Succes", f"Bestelberekening geëxporteerd naar:\n{filename}")

            except Exception as e:
                messagebox.showerror("Fout", f"Fout bij exporteren:\n{e}")


def main():
    """Hoofd ingang voor GUI"""
    root = tk.Tk()
    app = PlatenCalcGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
