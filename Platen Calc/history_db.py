#!/usr/bin/env python3
"""
History DB - SQLite snapshot storage for bestelberekening exports.
Saves a snapshot on each export so the next export can show comparison columns.
"""

import sqlite3
from datetime import datetime
from pathlib import Path


def _to_iso(date_str):
    """Convert DD_MM_YYYY to YYYY-MM-DD for correct chronological sorting."""
    parts = date_str.split('_')
    if len(parts) == 3:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return date_str


class HistoryDB:
    """Minimal SQLite database for storing bestelberekening snapshots."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(__file__).parent / "bestelberekening_history.db"
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS snapshot_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                material TEXT NOT NULL,
                artikel_nummer TEXT,
                materiaal_id TEXT,
                stock_m2 REAL NOT NULL DEFAULT 0,
                saldo_m2 REAL NOT NULL DEFAULT 0,
                bruto_m2 REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_snapshot_rows_snapshot
                ON snapshot_rows(snapshot_id);
        """)
        # Migrate existing DBs: add bruto_m2 column if missing
        try:
            self.conn.execute("ALTER TABLE snapshot_rows ADD COLUMN bruto_m2 REAL NOT NULL DEFAULT 0")
            self.conn.commit()
        except Exception:
            pass  # Column already exists
        self.conn.commit()

    def save_snapshot(self, date_str, results):
        """Save (or replace) a snapshot for the given date.

        Args:
            date_str: Date string like "11_02_2026" (DD_MM_YYYY).
            results: List of dicts with keys: material, artikel_nummer,
                     materiaal_id, stock, bestellen (saldo).
        """
        iso_date = _to_iso(date_str)
        cur = self.conn.cursor()

        # Delete existing snapshot for this date (upsert)
        cur.execute("SELECT id FROM snapshots WHERE snapshot_date = ?", (iso_date,))
        row = cur.fetchone()
        if row:
            cur.execute("DELETE FROM snapshot_rows WHERE snapshot_id = ?", (row[0],))
            cur.execute("DELETE FROM snapshots WHERE id = ?", (row[0],))

        cur.execute(
            "INSERT INTO snapshots (snapshot_date) VALUES (?)",
            (iso_date,)
        )
        snapshot_id = cur.lastrowid

        for r in results:
            cur.execute(
                """INSERT INTO snapshot_rows
                   (snapshot_id, material, artikel_nummer, materiaal_id, stock_m2, saldo_m2, bruto_m2)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    snapshot_id,
                    r['material'],
                    r.get('artikel_nummer', ''),
                    r.get('materiaal_id', ''),
                    r.get('stock', 0),
                    r.get('bestellen', 0),  # saldo
                    r.get('bruto', 0),
                )
            )

        self.conn.commit()

    def get_previous_snapshot(self):
        """Return the most recent snapshot as {material: {'stock': x, 'saldo': y}}.

        Returns None if no snapshots exist.
        """
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id FROM snapshots ORDER BY snapshot_date DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            return None

        snapshot_id = row[0]
        cur.execute(
            "SELECT material, stock_m2, saldo_m2, bruto_m2 FROM snapshot_rows WHERE snapshot_id = ?",
            (snapshot_id,)
        )

        data = {}
        for material, stock, saldo, bruto in cur.fetchall():
            data[material] = {'stock': stock, 'saldo': saldo, 'bruto': bruto}
        return data

    def get_snapshot_count(self):
        """Return the total number of stored snapshots."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM snapshots")
        return cur.fetchone()[0]

    def import_xlsx(self, filepath):
        """Import a bestelberekening_DD_MM_YYYY.xlsx file into the database.

        Reads Materiaal (col A), Stock (col G), and Saldo (col I).
        Extracts the date from the filename.
        Returns the date string on success, None if skipped.
        """
        import re
        import openpyxl

        basename = Path(filepath).name
        match = re.search(r'bestelberekening_(\d{2}_\d{2}_\d{4})', basename)
        if not match:
            return None

        date_str = match.group(1)
        iso_date = _to_iso(date_str)

        # Skip if already in DB
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM snapshots WHERE snapshot_date = ?", (iso_date,))
        if cur.fetchone():
            return None

        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        ws = wb["Bestelberekening"] if "Bestelberekening" in wb.sheetnames else wb.worksheets[0]

        results = []
        first_row = True
        for row in ws.iter_rows(min_col=1, max_col=9, values_only=True):
            if first_row:
                first_row = False
                continue

            material = row[0]   # A: Materiaal
            bruto = row[4]      # E: Bruto (m²)
            stock = row[6]      # G: Stock (m²)
            saldo = row[8]      # I: Saldo (m²)

            if material and stock is not None and saldo is not None:
                try:
                    results.append({
                        'material': str(material),
                        'artikel_nummer': str(row[1] or ''),
                        'materiaal_id': '',
                        'stock': float(stock),
                        'bestellen': float(saldo),
                        'bruto': float(bruto) if bruto is not None else 0.0,
                    })
                except (ValueError, TypeError):
                    continue

        wb.close()

        if results:
            self.save_snapshot(date_str, results)
            return date_str
        return None

    def delete_all_snapshots(self):
        """Delete all snapshots from the database."""
        self.conn.execute("DELETE FROM snapshot_rows")
        self.conn.execute("DELETE FROM snapshots")
        self.conn.commit()

    def get_analysis_data(self):
        """Calculate consumption analysis across all snapshots.

        Returns None if fewer than 3 snapshots exist.
        Otherwise returns a list of dicts with analysis per material.
        """
        cur = self.conn.cursor()

        # Check minimum snapshots
        cur.execute("SELECT COUNT(*) FROM snapshots")
        count = cur.fetchone()[0]
        if count < 3:
            return None

        # Get all snapshots ordered by date
        cur.execute("SELECT id, snapshot_date FROM snapshots ORDER BY snapshot_date ASC")
        snapshots = cur.fetchall()

        oldest_date = snapshots[0][1]
        newest_date = snapshots[-1][1]
        total_snapshots = len(snapshots)

        # Calculate weeks between oldest and newest
        from datetime import datetime
        d_oldest = datetime.strptime(oldest_date, "%Y-%m-%d")
        d_newest = datetime.strptime(newest_date, "%Y-%m-%d")
        days_between = (d_newest - d_oldest).days
        weken_tussen = max(days_between / 7.0, 1)

        # Collect all data per material across all snapshots
        # {material: [{'stock': x, 'saldo': y, 'bruto': z, 'snapshot_idx': i}, ...]}
        material_data = {}

        for snap_idx, (snap_id, snap_date) in enumerate(snapshots):
            cur.execute(
                "SELECT material, stock_m2, saldo_m2, bruto_m2 FROM snapshot_rows WHERE snapshot_id = ?",
                (snap_id,)
            )
            for material, stock, saldo, bruto in cur.fetchall():
                if material not in material_data:
                    material_data[material] = []
                material_data[material].append({
                    'stock': stock,
                    'saldo': saldo,
                    'bruto': bruto,
                    'snapshot_idx': snap_idx,
                })

        # Analyse per material
        results = []
        for material, entries in material_data.items():
            # Sort by snapshot index
            entries.sort(key=lambda e: e['snapshot_idx'])

            stock_oudste = entries[0]['stock']
            stock_nieuwste = entries[-1]['stock']
            stock_nu = stock_nieuwste

            # Verbruik per week
            verbruik_per_week = (stock_oudste - stock_nieuwste) / weken_tussen
            if verbruik_per_week > 0:
                weken_voorraad = stock_nu / verbruik_per_week
            else:
                weken_voorraad = float('inf')

            # Dead stock check: bruto == 0 in ALL snapshots AND stock > 0
            all_bruto_zero = all(e['bruto'] == 0 for e in entries)
            dead_stock = all_bruto_zero and stock_nu > 0

            # Bestelfrequentie: snapshots met bruto > 0 / totaal
            snapshots_met_bruto = sum(1 for e in entries if e['bruto'] > 0)
            bestel_frequentie = snapshots_met_bruto / total_snapshots

            # Service level: snapshots met saldo >= 0 / totaal
            snapshots_met_saldo_ok = sum(1 for e in entries if e['saldo'] >= 0)
            service_level = (snapshots_met_saldo_ok / total_snapshots) * 100

            # Status bepaling
            if dead_stock:
                status = "Dood Stock"
            elif bestel_frequentie >= 0.75:
                status = "Hoog Verbruik"
            elif bestel_frequentie <= 0.25:
                status = "Incidenteel"
            else:
                status = "Normaal"

            results.append({
                'material': material,
                'stock_nu': stock_nu,
                'verbruik_per_week': verbruik_per_week,
                'weken_voorraad': weken_voorraad,
                'status': status,
                'bestel_frequentie': bestel_frequentie,
                'service_level': service_level,
            })

        return results

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
