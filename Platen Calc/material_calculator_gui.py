#!/usr/bin/env python3
"""
Material Calculator - GUI Version
User-friendly graphical interface for the material calculator
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime
import threading
import json
import sys

# Import the main calculator
from material_calculator import MaterialCalculator

CONFIG_FILE = "platen_calc_config.json"


class MaterialCalculatorGUI:
    """GUI Application for Material Calculator"""

    def __init__(self, root):
        self.root = root
        self.root.title("Material Calculator - Platen Calc")
        self.root.geometry("900x700")

        self.calculator = None
        self.files = []

        # Load saved paths from config
        self.config = self.load_config()

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface"""

        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # --- Folder Selection ---
        row = 0
        ttk.Label(main_frame, text="Folder Path:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )

        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=row, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        folder_frame.columnconfigure(0, weight=1)

        self.folder_var = tk.StringVar(value=self.config.get('folder_path', 'Stuklijsten'))
        ttk.Entry(folder_frame, textvariable=self.folder_var).grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(folder_frame, text="Browse...", command=self.browse_folder).grid(
            row=0, column=1
        )

        # --- Filters Section ---
        row += 1
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )

        row += 1
        ttk.Label(main_frame, text="Filters:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )

        # Filename pattern
        row += 1
        ttk.Label(main_frame, text="Filename pattern:").grid(row=row, column=0, sticky=tk.W)
        self.filename_pattern_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.filename_pattern_var).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=5
        )
        ttk.Label(main_frame, text="(e.g., S03548 or .*Meylemans.*)").grid(
            row=row, column=2, sticky=tk.W
        )

        # Date from
        row += 1
        ttk.Label(main_frame, text="Date from:").grid(row=row, column=0, sticky=tk.W)
        self.date_from_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.date_from_var).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=5
        )
        ttk.Label(main_frame, text="(YYYY-MM-DD)").grid(row=row, column=2, sticky=tk.W)

        # Date to
        row += 1
        ttk.Label(main_frame, text="Date to:").grid(row=row, column=0, sticky=tk.W)
        self.date_to_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.date_to_var).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=5
        )
        ttk.Label(main_frame, text="(YYYY-MM-DD)").grid(row=row, column=2, sticky=tk.W)

        # Customer
        row += 1
        ttk.Label(main_frame, text="Customer:").grid(row=row, column=0, sticky=tk.W)
        self.customer_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.customer_var).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=5
        )

        # Project number
        row += 1
        ttk.Label(main_frame, text="Project number:").grid(row=row, column=0, sticky=tk.W)
        self.project_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.project_var).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=5
        )
        ttk.Label(main_frame, text="(e.g., S03548)").grid(row=row, column=2, sticky=tk.W)

        # Exclude pattern
        row += 1
        ttk.Label(main_frame, text="Exclude pattern:").grid(row=row, column=0, sticky=tk.W)
        self.exclude_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.exclude_var).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=5
        )
        ttk.Label(main_frame, text="(e.g., test|temp)").grid(row=row, column=2, sticky=tk.W)

        # --- Action Buttons ---
        row += 1
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )

        row += 1
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)

        ttk.Button(button_frame, text="Scan Folder", command=self.scan_folder, width=15).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Process Files", command=self.process_files, width=15).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Export CSV", command=self.export_csv, width=15).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Clear", command=self.clear_output, width=15).pack(
            side=tk.LEFT, padx=5
        )

        # --- Output Area ---
        row += 1
        ttk.Label(main_frame, text="Output:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5)
        )

        row += 1
        self.output_text = scrolledtext.ScrolledText(
            main_frame, height=20, width=80, wrap=tk.WORD, font=('Consolas', 9)
        )
        self.output_text.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # Configure row weights for resizing
        main_frame.rowconfigure(row, weight=1)

        # Status bar
        row += 1
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E))

    def browse_folder(self):
        """Open folder browser dialog"""
        folder = filedialog.askdirectory(
            title="Select Folder with Excel Files",
            initialdir=self.folder_var.get()
        )
        if folder:
            self.folder_var.set(folder)
            self.save_config()

    def load_config(self):
        """Load saved paths from config file"""
        config_file = Path(CONFIG_FILE)
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_config(self):
        """Save paths to config file"""
        try:
            self.config['folder_path'] = self.folder_var.get()
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get_filters(self):
        """Get filter settings from UI"""
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

    def log(self, message):
        """Log message to output area"""
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.root.update_idletasks()

    def clear_output(self):
        """Clear the output area"""
        self.output_text.delete(1.0, tk.END)
        self.status_var.set("Ready")

    def scan_folder(self):
        """Scan folder for files"""
        self.clear_output()
        folder = self.folder_var.get()

        try:
            self.calculator = MaterialCalculator(folder)
            self.files = self.calculator.scan_folder()

            self.log(f"Found {len(self.files)} files in '{folder}'")

            # Apply filters
            filters = self.get_filters()
            if filters:
                self.log("\nApplying filters...")
                self.files = self.calculator.apply_filters(self.files, filters)
                self.log(f"After filters: {len(self.files)} files")

            if self.files:
                self.log("\nFiles to process:")
                for i, f in enumerate(self.files[:20], 1):  # Show first 20
                    self.log(f"  {i}. {f.name}")
                if len(self.files) > 20:
                    self.log(f"  ... and {len(self.files) - 20} more")

            self.status_var.set(f"Ready to process {len(self.files)} files")

        except Exception as e:
            messagebox.showerror("Error", f"Error scanning folder: {e}")
            self.log(f"ERROR: {e}")
            self.status_var.set("Error")

    def process_files(self):
        """Process the files"""
        if not self.calculator or not self.files:
            messagebox.showwarning("Warning", "Please scan folder first!")
            return

        self.log("\n" + "="*70)
        self.log("Processing files...")
        self.log("="*70)

        self.status_var.set("Processing...")

        # Process in a separate thread to keep GUI responsive
        def process_thread():
            try:
                for idx, file_path in enumerate(self.files, 1):
                    self.log(f"\n[{idx}/{len(self.files)}] {file_path.name}")

                    file_materials = self.calculator.extract_material_data(file_path)

                    if file_materials:
                        for material, amount in file_materials.items():
                            self.calculator.material_totals[material] += amount

                        self.calculator.file_details.append({
                            'filename': file_path.name,
                            'materials': dict(file_materials),
                            'total_m2': sum(file_materials.values())
                        })

                        self.log(f"  ✓ {len(file_materials)} materials, {sum(file_materials.values()):.2f} m²")
                    else:
                        self.log(f"  ⚠ No data")

                # Show summary
                self.show_summary()

            except Exception as e:
                self.log(f"\nERROR: {e}")
                messagebox.showerror("Error", f"Error processing files: {e}")

            self.status_var.set("Processing complete")

        thread = threading.Thread(target=process_thread)
        thread.daemon = True
        thread.start()

    def show_summary(self):
        """Display summary of results"""
        self.log("\n" + "="*70)
        self.log("MATERIAL TOTALS")
        self.log("="*70)

        if not self.calculator.material_totals:
            self.log("No materials found!")
            return

        sorted_materials = sorted(
            self.calculator.material_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )

        self.log(f"\n{'Material':<40} {'Netto (m²)':>15}")
        self.log('-'*70)

        total_area = 0
        for material, area in sorted_materials:
            self.log(f"{material:<40} {area:>15.2f}")
            total_area += area

        self.log('-'*70)
        self.log(f"{'TOTAL':<40} {total_area:>15.2f}")
        self.log('='*70)

        self.log(f"\n✓ Processed: {len(self.calculator.processed_files)} files")
        if self.calculator.skipped_files:
            self.log(f"⚠ Skipped: {len(self.calculator.skipped_files)} files")

    def export_csv(self):
        """Export results to CSV"""
        if not self.calculator or not self.calculator.material_totals:
            messagebox.showwarning("Warning", "No data to export! Process files first.")
            return

        # Ask for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"material_totals_{timestamp}.csv"

        filename = filedialog.asksaveasfilename(
            title="Save CSV",
            initialfile=default_filename,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if filename:
            try:
                import csv
                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')

                    writer.writerow(['Material', 'Netto (m²)'])

                    sorted_materials = sorted(
                        self.calculator.material_totals.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )

                    for material, area in sorted_materials:
                        writer.writerow([material, f"{area:.2f}"])

                    writer.writerow([''])
                    writer.writerow(['TOTAL', f"{sum(self.calculator.material_totals.values()):.2f}"])

                self.log(f"\n✓ Exported to: {filename}")
                messagebox.showinfo("Success", f"Results exported to:\n{filename}")
                self.status_var.set(f"Exported to {Path(filename).name}")

            except Exception as e:
                messagebox.showerror("Error", f"Error exporting: {e}")
                self.log(f"\n✗ Export error: {e}")


def main():
    """Main entry point for GUI"""
    root = tk.Tk()
    app = MaterialCalculatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
