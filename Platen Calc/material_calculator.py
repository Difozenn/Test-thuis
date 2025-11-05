#!/usr/bin/env python3
"""
Material Calculator - Extract and aggregate material data from Excel files
Scans Excel files in a folder, extracts material usage from the '1 PLATEN' sheet,
calculates m² from Lengte × Breedte columns, and aggregates totals by material type.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple
import re

try:
    import xlrd
except ImportError:
    print("Error: xlrd library not found")
    print("Please install it: pip install xlrd")
    sys.exit(1)


class MaterialCalculator:
    """Main calculator for processing Excel files and extracting material data"""

    def __init__(self, folder_path: str, target_sheet: str = "1 PLATEN"):
        self.folder_path = Path(folder_path)
        self.target_sheet = target_sheet
        self.material_totals: Dict[str, float] = defaultdict(float)
        self.file_details: List[Dict] = []
        self.processed_files: List[str] = []
        self.skipped_files: List[Tuple[str, str]] = []

    def scan_folder(self, pattern: str = "*.xls") -> List[Path]:
        """Scan folder for Excel files matching the pattern"""
        if not self.folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {self.folder_path}")

        files = list(self.folder_path.glob(pattern))
        print(f"\nFound {len(files)} files matching '{pattern}'")
        return files

    def apply_filters(self, files: List[Path], filters: Dict) -> List[Path]:
        """Apply various filters to the file list"""
        filtered = files

        # Filter by filename pattern
        if filters.get('filename_pattern'):
            pattern = filters['filename_pattern']
            filtered = [f for f in filtered if re.search(pattern, f.name, re.IGNORECASE)]
            print(f"  After filename filter '{pattern}': {len(filtered)} files")

        # Filter by date (based on modification time)
        if filters.get('date_from'):
            date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d')
            filtered = [f for f in filtered if datetime.fromtimestamp(f.stat().st_mtime) >= date_from]
            print(f"  After date_from filter: {len(filtered)} files")

        if filters.get('date_to'):
            date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d')
            filtered = [f for f in filtered if datetime.fromtimestamp(f.stat().st_mtime) <= date_to]
            print(f"  After date_to filter: {len(filtered)} files")

        # Filter by customer name (in filename)
        if filters.get('customer'):
            customer = filters['customer']
            filtered = [f for f in filtered if customer.lower() in f.name.lower()]
            print(f"  After customer filter '{customer}': {len(filtered)} files")

        # Filter by project number (S-number in filename)
        if filters.get('project_number'):
            project = filters['project_number']
            filtered = [f for f in filtered if project in f.name]
            print(f"  After project filter '{project}': {len(filtered)} files")

        # Exclude certain patterns
        if filters.get('exclude_pattern'):
            pattern = filters['exclude_pattern']
            filtered = [f for f in filtered if not re.search(pattern, f.name, re.IGNORECASE)]
            print(f"  After exclude filter '{pattern}': {len(filtered)} files")

        return filtered

    def extract_material_data(self, file_path: Path) -> Dict[str, float]:
        """Extract material data from a single Excel file from '1 PLATEN' sheet"""
        materials = defaultdict(float)

        try:
            workbook = xlrd.open_workbook(file_path, formatting_info=False)

            if self.target_sheet not in workbook.sheet_names():
                self.skipped_files.append((file_path.name, f"Sheet '{self.target_sheet}' not found"))
                return materials

            sheet = workbook.sheet_by_name(self.target_sheet)

            # Find the header row (look for "Materiaal" in column A, "lengte" in column C, "Breedte" in column D)
            # Expected at row 6 (index 6)
            header_row = None
            for row_idx in range(min(10, sheet.nrows)):  # Check first 10 rows
                try:
                    cell_a = str(sheet.cell(row_idx, 0).value).strip().lower()
                    cell_c = str(sheet.cell(row_idx, 2).value).strip().lower() if sheet.ncols > 2 else ""
                    cell_d = str(sheet.cell(row_idx, 3).value).strip().lower() if sheet.ncols > 3 else ""

                    if 'materiaal' in cell_a and 'lengte' in cell_c and 'breedte' in cell_d:
                        header_row = row_idx
                        break
                except:
                    continue

            if header_row is None:
                self.skipped_files.append((file_path.name, "Could not find header row with 'Materiaal', 'lengte', 'Breedte'"))
                return materials

            # Extract data starting from the row after header
            for row_idx in range(header_row + 1, sheet.nrows):
                try:
                    # Column A: Materiaal
                    material = sheet.cell(row_idx, 0).value

                    # Skip empty rows
                    if not material or str(material).strip() == '':
                        continue

                    material = str(material).strip()

                    # Column C: Lengte (index 2)
                    lengte_value = sheet.cell(row_idx, 2).value if sheet.ncols > 2 else 0
                    # Column D: Breedte (index 3)
                    breedte_value = sheet.cell(row_idx, 3).value if sheet.ncols > 3 else 0

                    # Convert to float
                    if isinstance(lengte_value, (int, float)):
                        lengte = float(lengte_value)
                    elif isinstance(lengte_value, str):
                        lengte = float(lengte_value.replace(',', '.'))
                    else:
                        continue

                    if isinstance(breedte_value, (int, float)):
                        breedte = float(breedte_value)
                    elif isinstance(breedte_value, str):
                        breedte = float(breedte_value.replace(',', '.'))
                    else:
                        continue

                    # Calculate m²: (lengte × breedte) / 1,000,000
                    if lengte > 0 and breedte > 0:
                        m2 = (lengte * breedte) / 1_000_000
                        materials[material] += m2

                except (ValueError, TypeError, IndexError):
                    # Skip rows with invalid data
                    continue

            self.processed_files.append(file_path.name)
            return materials

        except Exception as e:
            self.skipped_files.append((file_path.name, f"Error: {str(e)}"))
            return materials

    def process_files(self, files: List[Path]) -> None:
        """Process all files and aggregate material totals"""
        print(f"\n{'='*70}")
        print(f"Processing {len(files)} files...")
        print('='*70)

        for idx, file_path in enumerate(files, 1):
            print(f"\n[{idx}/{len(files)}] Processing: {file_path.name}")

            file_materials = self.extract_material_data(file_path)

            if file_materials:
                # Add to global totals
                for material, amount in file_materials.items():
                    self.material_totals[material] += amount

                # Store file details
                self.file_details.append({
                    'filename': file_path.name,
                    'materials': dict(file_materials),
                    'total_m2': sum(file_materials.values())
                })

                print(f"  ✓ Found {len(file_materials)} unique materials, total: {sum(file_materials.values()):.2f} m²")
            else:
                print(f"  ⚠ No data extracted")

    def print_summary(self) -> None:
        """Print summary of processed data"""
        print(f"\n{'='*70}")
        print("PROCESSING SUMMARY")
        print('='*70)
        print(f"✓ Successfully processed: {len(self.processed_files)} files")
        print(f"⚠ Skipped: {len(self.skipped_files)} files")

        if self.skipped_files:
            print("\nSkipped files:")
            for filename, reason in self.skipped_files:
                print(f"  - {filename}: {reason}")

        print(f"\n{'='*70}")
        print("MATERIAL TOTALS")
        print('='*70)

        if not self.material_totals:
            print("No materials found!")
            return

        # Sort materials by total area (descending)
        sorted_materials = sorted(self.material_totals.items(), key=lambda x: x[1], reverse=True)

        print(f"\n{'Material':<40} {'Netto (m²)':>15}")
        print('-'*70)

        total_area = 0
        for material, area in sorted_materials:
            print(f"{material:<40} {area:>15.2f}")
            total_area += area

        print('-'*70)
        print(f"{'TOTAL':<40} {total_area:>15.2f}")
        print('='*70)

    def export_to_csv(self, output_file: str = None) -> str:
        """Export results to CSV file"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"material_totals_{timestamp}.csv"

        output_path = self.folder_path.parent / output_file

        try:
            import csv
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')

                # Write header
                writer.writerow(['Material', 'Netto (m²)'])

                # Write data sorted by area
                sorted_materials = sorted(self.material_totals.items(), key=lambda x: x[1], reverse=True)
                for material, area in sorted_materials:
                    writer.writerow([material, f"{area:.2f}"])

                # Write total
                writer.writerow([''])
                writer.writerow(['TOTAL', f"{sum(self.material_totals.values()):.2f}"])

            print(f"\n✓ Results exported to: {output_path}")
            return str(output_path)

        except Exception as e:
            print(f"\n✗ Error exporting to CSV: {e}")
            return ""

    def export_detailed_csv(self, output_file: str = None) -> str:
        """Export detailed results including per-file breakdown"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"material_details_{timestamp}.csv"

        output_path = self.folder_path.parent / output_file

        try:
            import csv
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')

                # Write summary section
                writer.writerow(['SUMMARY'])
                writer.writerow(['Material', 'Total Netto (m²)'])

                sorted_materials = sorted(self.material_totals.items(), key=lambda x: x[1], reverse=True)
                for material, area in sorted_materials:
                    writer.writerow([material, f"{area:.2f}"])

                writer.writerow(['TOTAL', f"{sum(self.material_totals.values()):.2f}"])
                writer.writerow([''])

                # Write per-file details
                writer.writerow(['PER-FILE DETAILS'])
                writer.writerow([''])

                for file_detail in self.file_details:
                    writer.writerow([f"File: {file_detail['filename']}"])
                    writer.writerow(['Material', 'Netto (m²)'])

                    for material, area in sorted(file_detail['materials'].items(), key=lambda x: x[1], reverse=True):
                        writer.writerow([material, f"{area:.2f}"])

                    writer.writerow(['Subtotal', f"{file_detail['total_m2']:.2f}"])
                    writer.writerow([''])

            print(f"✓ Detailed results exported to: {output_path}")
            return str(output_path)

        except Exception as e:
            print(f"✗ Error exporting detailed CSV: {e}")
            return ""


def interactive_mode():
    """Run the calculator in interactive mode"""
    print("="*70)
    print("MATERIAL CALCULATOR - Interactive Mode")
    print("="*70)

    # Get folder path
    default_folder = "Stuklijsten"
    folder = input(f"\nEnter folder path [{default_folder}]: ").strip()
    if not folder:
        folder = default_folder

    calculator = MaterialCalculator(folder)

    # Get files
    try:
        files = calculator.scan_folder()
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        return

    if not files:
        print("\n✗ No files found!")
        return

    # Ask about filters
    apply_filter = input("\nDo you want to apply filters? (y/n) [n]: ").strip().lower()

    filters = {}
    if apply_filter == 'y':
        print("\nAvailable filters (press Enter to skip):")

        filename_pattern = input("  Filename pattern (regex): ").strip()
        if filename_pattern:
            filters['filename_pattern'] = filename_pattern

        date_from = input("  Date from (YYYY-MM-DD): ").strip()
        if date_from:
            filters['date_from'] = date_from

        date_to = input("  Date to (YYYY-MM-DD): ").strip()
        if date_to:
            filters['date_to'] = date_to

        customer = input("  Customer name: ").strip()
        if customer:
            filters['customer'] = customer

        project = input("  Project number (e.g., S03548): ").strip()
        if project:
            filters['project_number'] = project

        exclude = input("  Exclude pattern (regex): ").strip()
        if exclude:
            filters['exclude_pattern'] = exclude

        if filters:
            files = calculator.apply_filters(files, filters)

    if not files:
        print("\n✗ No files match the filters!")
        return

    # Process files
    calculator.process_files(files)

    # Print summary
    calculator.print_summary()

    # Export options
    export = input("\nExport results to CSV? (y/n) [y]: ").strip().lower()
    if export != 'n':
        calculator.export_to_csv()

        detailed = input("Export detailed breakdown? (y/n) [n]: ").strip().lower()
        if detailed == 'y':
            calculator.export_detailed_csv()


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # Command-line mode (can be extended)
        folder = sys.argv[1]
        calculator = MaterialCalculator(folder)
        files = calculator.scan_folder()
        calculator.process_files(files)
        calculator.print_summary()
        calculator.export_to_csv()
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
