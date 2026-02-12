#!/usr/bin/env python3
"""
Import old bestelberekening_DD_MM_YYYY.xlsx files into the history database.
Run once to backfill history, then the app keeps it updated automatically.

Usage:
    python import_history.py                      # scan current directory
    python import_history.py C:/pad/naar/exports  # scan specific folder
    python import_history.py --force              # delete existing + re-import
    python import_history.py C:/pad --force       # specific folder + force
"""

import sys
import glob
import os

from history_db import HistoryDB


def main():
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv

    folder = args[0] if args else "."
    folder = os.path.abspath(folder)

    pattern = os.path.join(folder, "bestelberekening_*.xlsx")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"Geen bestelberekening_*.xlsx bestanden gevonden in:\n  {folder}")
        return

    print(f"Gevonden: {len(files)} bestanden in {folder}")

    db = HistoryDB()

    if force:
        existing = db.get_snapshot_count()
        db.delete_all_snapshots()
        print(f"  --force: {existing} bestaande snapshots verwijderd\n")
    else:
        print()

    imported = 0
    skipped = 0

    for filepath in files:
        basename = os.path.basename(filepath)
        result = db.import_xlsx(filepath)
        if result:
            print(f"  + {basename}  (datum: {result})")
            imported += 1
        else:
            print(f"  - {basename}  (overgeslagen, al in DB of ongeldig)")
            skipped += 1

    db.close()

    print(f"\nKlaar: {imported} geïmporteerd, {skipped} overgeslagen")
    print(f"Totaal snapshots in DB: {imported + skipped}")


if __name__ == "__main__":
    main()
