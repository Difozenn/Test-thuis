"""
Firebird holzher_KAM.gdb - Standalone Module
Connects to a local Firebird database and manages the TEILE table.

Requirements:
    pip install fdb
    Firebird 2.x client library (fbclient.dll / libfbclient.so) must be installed
"""

import os
import sys
from datetime import datetime

try:
    # Patch for old Firebird 2.x client libraries that lack fb_shutdown_callback.
    # fdb tries to bind this function during connect(), but it only exists in
    # Firebird 2.5+. Since it's bound near the end of __init__ (after all essential
    # API functions), we can safely catch and skip the error.
    import fdb.ibase as _ibase
    _orig_api_init = _ibase.fbclient_API.__init__

    def _patched_api_init(self, fb_library_name=None):
        try:
            _orig_api_init(self, fb_library_name)
        except AttributeError as e:
            if "fb_shutdown_callback" not in str(e):
                raise
            # fb_shutdown_callback is optional - not needed for basic operations

    _ibase.fbclient_API.__init__ = _patched_api_init
    import fdb
except ImportError:
    print("ERROR: 'fdb' package not installed. Run: pip install fdb")
    sys.exit(1)


class FirebirdKAM:
    """Interface to the holzher_KAM.gdb Firebird database."""

    def __init__(self, db_path=None, host=None, port=None, user="SYSDBA", password="masterkey"):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "holzher_KAM.gdb")
        self.db_path = db_path
        self.host = host or ""
        self.port = port
        self.user = user
        self.password = password
        self.conn = None

    def _build_dsn(self):
        """Build Firebird DSN string. Format: host/port:path or just path for local."""
        if self.host:
            if self.port:
                return f"{self.host}/{self.port}:{self.db_path}"
            return f"{self.host}:{self.db_path}"
        return self.db_path

    def connect(self):
        """Open a connection to the Firebird database."""
        if self.conn is not None:
            return

        # Only check file exists for local connections
        if not self.host and not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        dsn = self._build_dsn()
        self.conn = fdb.connect(
            dsn=dsn,
            user=self.user,
            password=self.password,
            charset="UTF8",
        )
        print(f"Connected to {dsn}")

    def disconnect(self):
        """Close the database connection."""
        if self.conn is not None:
            self.conn.close()
            self.conn = None
            print("Disconnected.")

    def list_columns(self, table="TEILE"):
        """Return a list of (column_name, type_name, nullable) for the given table.

        nullable is True if the column allows NULL, False if NOT NULL.
        """
        self._require_connection()
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT rf.RDB$FIELD_NAME, f.RDB$FIELD_TYPE, f.RDB$FIELD_LENGTH,
                   f.RDB$FIELD_SCALE, f.RDB$FIELD_SUB_TYPE,
                   rf.RDB$NULL_FLAG, f.RDB$NULL_FLAG,
                   rf.RDB$DEFAULT_SOURCE
            FROM RDB$RELATION_FIELDS rf
            JOIN RDB$FIELDS f ON rf.RDB$FIELD_SOURCE = f.RDB$FIELD_NAME
            WHERE rf.RDB$RELATION_NAME = ?
            ORDER BY rf.RDB$FIELD_POSITION
            """,
            (table.upper().ljust(31),),
        )
        rows = cur.fetchall()
        cur.close()

        # Map Firebird internal type codes to readable names
        type_map = {
            7: "SMALLINT",
            8: "INTEGER",
            10: "FLOAT",
            12: "DATE",
            13: "TIME",
            14: "CHAR",
            16: "BIGINT",
            27: "DOUBLE PRECISION",
            35: "TIMESTAMP",
            37: "VARCHAR",
            261: "BLOB",
        }

        columns = []
        for row in rows:
            col_name = row[0].strip()
            type_code = row[1]
            type_name = type_map.get(type_code, f"UNKNOWN({type_code})")
            # NOT NULL if either the field-level or relation-level flag is set
            rel_null_flag = row[5]  # rf.RDB$NULL_FLAG
            field_null_flag = row[6]  # f.RDB$NULL_FLAG
            nullable = not (rel_null_flag == 1 or field_null_flag == 1)
            has_default = row[7] is not None
            columns.append((col_name, type_name, nullable, has_default))

        return columns

    def list_tables(self):
        """Return a list of user table names in the database."""
        self._require_connection()
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT RDB$RELATION_NAME
            FROM RDB$RELATIONS
            WHERE RDB$SYSTEM_FLAG = 0 AND RDB$VIEW_BLR IS NULL
            ORDER BY RDB$RELATION_NAME
            """
        )
        tables = [row[0].strip() for row in cur.fetchall()]
        cur.close()
        return tables

    def insert_teil(self, data: dict):
        """Insert a row into the TEILE table.

        Args:
            data: dict of {column_name: value}. Column names must match
                  the database exactly (including spaces).

        Example:
            db.insert_teil({
                "VlowID": "V001",
                "TeileID": "TEST-001",
                "Teilelaenge": 2500,
                "Teilebreite": 600,
                "Teiledicke": 19,
                "Kante1": 1,
                "Kante1 Status": 0,
                "Kante1 Programm": "PRG1",
                "Abstapelplatz": 1,
                "DateTime": datetime.now(),
            })
        """
        self._require_connection()

        if not data:
            raise ValueError("No column values provided")

        columns = []
        values = []
        for col, val in data.items():
            # Double-quote all column names to handle spaces safely
            columns.append(f'"{col}"')
            values.append(val)

        col_list = ", ".join(columns)
        placeholders = ", ".join("?" for _ in values)
        sql = f"INSERT INTO TEILE ({col_list}) VALUES ({placeholders})"

        cur = self.conn.cursor()
        try:
            cur.execute(sql, values)
            self.conn.commit()
            print(f"Inserted row into TEILE ({len(columns)} columns)")
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def count_rows(self, table="TEILE"):
        """Return the number of rows in a table."""
        self._require_connection()
        cur = self.conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        cur.close()
        return count

    def _require_connection(self):
        if self.conn is None:
            raise RuntimeError("Not connected. Call connect() first.")


def main():
    """CLI test interface."""
    import argparse

    parser = argparse.ArgumentParser(description="Firebird holzher_KAM.gdb tool")
    parser.add_argument("--db", default=None, help="Path to .gdb file (default: ./holzher_KAM.gdb)")
    parser.add_argument("--user", default="SYSDBA", help="Database user (default: SYSDBA)")
    parser.add_argument("--password", default="masterkey", help="Database password (default: masterkey)")
    parser.add_argument("--tables", action="store_true", help="List all tables")
    parser.add_argument("--columns", metavar="TABLE", nargs="?", const="TEILE", help="List columns (default table: TEILE)")
    parser.add_argument("--count", metavar="TABLE", nargs="?", const="TEILE", help="Count rows (default table: TEILE)")
    parser.add_argument("--test-insert", action="store_true", help="Insert a test row into TEILE")
    args = parser.parse_args()

    db = FirebirdKAM(db_path=args.db, user=args.user, password=args.password)

    try:
        db.connect()

        # Default action: list TEILE columns
        if not any([args.tables, args.columns, args.count, args.test_insert]):
            args.columns = "TEILE"

        if args.tables:
            tables = db.list_tables()
            print(f"\nTables ({len(tables)}):")
            for t in tables:
                print(f"  {t}")

        if args.columns:
            table = args.columns
            columns = db.list_columns(table)
            required = [c for c in columns if not c[2] and not c[3]]
            optional = [c for c in columns if c[2] or c[3]]
            print(f"\nColumns in {table} ({len(columns)} total, {len(required)} required):")
            print(f"  {'COLUMN':<30} {'TYPE':<20} {'REQUIRED'}")
            print(f"  {'-'*30} {'-'*20} {'-'*10}")
            for name, dtype, nullable, has_default in columns:
                if not nullable and not has_default:
                    req = "REQUIRED"
                elif not nullable and has_default:
                    req = "has default"
                else:
                    req = ""
                print(f"  {name:<30} {dtype:<20} {req}")

        if args.count:
            table = args.count
            n = db.count_rows(table)
            print(f"\n{table}: {n} rows")

        if args.test_insert:
            print("\nInserting test row into TEILE...")
            db.insert_teil({
                "VlowID": "TEST-999",
                "TeileID": "TEST-001",
                "Teilelaenge": 2500,
                "Teilebreite": 600,
                "Teiledicke": 19,
                "Abstapelplatz": 1,
            })
            n = db.count_rows("TEILE")
            print(f"TEILE now has {n} rows")

    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except fdb.DatabaseError as e:
        print(f"DATABASE ERROR: {e}")
        sys.exit(1)
    finally:
        db.disconnect()


def gui():
    """Simple tkinter GUI for connecting and inserting into TEILE."""
    import tkinter as tk
    from tkinter import messagebox, filedialog

    db = None

    def update_status(msg, error=False):
        status_var.set(msg)
        status_label.config(fg="red" if error else "green")

    def do_connect():
        nonlocal db
        path = db_path_var.get().strip()
        if not path:
            messagebox.showerror("Error", "No database path set")
            return
        try:
            if db is not None:
                db.disconnect()
            host = host_var.get().strip() or None
            port = port_var.get().strip() or None
            if port:
                try:
                    port = int(port)
                except ValueError:
                    messagebox.showerror("Error", "Port must be a number")
                    return
            db = FirebirdKAM(db_path=path, host=host, port=port,
                             user=user_var.get(), password=pass_var.get())
            db.connect()
            connect_btn.config(text="Reconnect")
            send_btn.config(state=tk.NORMAL)
            n = db.count_rows("TEILE")
            update_status(f"Connected  —  TEILE has {n} rows")
        except Exception as e:
            db = None
            send_btn.config(state=tk.DISABLED)
            update_status(str(e), error=True)

    def do_disconnect():
        nonlocal db
        if db is not None:
            db.disconnect()
            db = None
        connect_btn.config(text="Connect")
        send_btn.config(state=tk.DISABLED)
        update_status("Disconnected")

    def browse_db():
        path = filedialog.askopenfilename(
            title="Select Firebird database",
            filetypes=[("Firebird DB", "*.gdb *.fdb"), ("All files", "*.*")],
        )
        if path:
            db_path_var.set(path)

    def do_send():
        if db is None:
            messagebox.showerror("Error", "Not connected")
            return

        # Validate required field
        vlow = fields["VlowID"][0].get().strip()
        if not vlow:
            messagebox.showerror("Error", "VlowID is required")
            return

        # Build data dict from filled-in fields (empty = NULL = skip)
        data = {}
        for col_name, (entry, col_type) in fields.items():
            val = entry.get().strip()
            if not val:
                continue
            if col_type == "number":
                try:
                    val = int(val)
                except ValueError:
                    messagebox.showerror("Error", f"{col_name} must be a number")
                    return
            data[col_name] = val

        try:
            db.insert_teil(data)
            n = db.count_rows("TEILE")
            update_status(f"Sent!  —  TEILE now has {n} rows")
        except Exception as e:
            update_status(f"Insert failed: {e}", error=True)

    # --- Window ---
    root = tk.Tk()
    root.title("Firebird KAM - TEILE")
    root.resizable(False, False)

    # --- Connection frame ---
    conn_frame = tk.LabelFrame(root, text="Connection", padx=10, pady=5)
    conn_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

    default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "holzher_KAM.gdb")

    tk.Label(conn_frame, text="Host / IP:").grid(row=0, column=0, sticky=tk.W)
    host_var = tk.StringVar(value="")
    tk.Entry(conn_frame, textvariable=host_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5)
    tk.Label(conn_frame, text="(blank = local)").grid(row=0, column=2, sticky=tk.W)

    tk.Label(conn_frame, text="Port:").grid(row=1, column=0, sticky=tk.W)
    port_var = tk.StringVar(value="3050")
    tk.Entry(conn_frame, textvariable=port_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5)

    tk.Label(conn_frame, text="Database:").grid(row=2, column=0, sticky=tk.W)
    db_path_var = tk.StringVar(value=default_db)
    tk.Entry(conn_frame, textvariable=db_path_var, width=50).grid(row=2, column=1, padx=5)
    tk.Button(conn_frame, text="...", command=browse_db, width=3).grid(row=2, column=2)

    tk.Label(conn_frame, text="User:").grid(row=3, column=0, sticky=tk.W)
    user_var = tk.StringVar(value="SYSDBA")
    tk.Entry(conn_frame, textvariable=user_var, width=20).grid(row=3, column=1, sticky=tk.W, padx=5)

    tk.Label(conn_frame, text="Password:").grid(row=4, column=0, sticky=tk.W)
    pass_var = tk.StringVar(value="masterkey")
    tk.Entry(conn_frame, textvariable=pass_var, width=20, show="*").grid(row=4, column=1, sticky=tk.W, padx=5)

    btn_frame = tk.Frame(conn_frame)
    btn_frame.grid(row=5, column=0, columnspan=3, pady=5)
    connect_btn = tk.Button(btn_frame, text="Connect", command=do_connect, width=12)
    connect_btn.pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Disconnect", command=do_disconnect, width=12).pack(side=tk.LEFT, padx=5)

    # --- Data entry frame ---
    data_frame = tk.LabelFrame(root, text="TEILE Data", padx=10, pady=5)
    data_frame.pack(fill=tk.X, padx=10, pady=5)

    # All 22 TEILE columns: (db_name, type, required)
    column_defs = [
        ("VlowID",           "text",   True),
        ("TeileID",          "text",   False),
        ("Teilelaenge",      "number", False),
        ("Teilebreite",      "number", False),
        ("Teiledicke",       "number", False),
        ("Kante1",           "number", False),
        ("Kante1 Status",    "number", False),
        ("Kante1 Programm",  "text",   False),
        ("Kante2",           "number", False),
        ("Kante2 Status",    "number", False),
        ("Kante2 Programm",  "text",   False),
        ("Kante3",           "number", False),
        ("Kante3 Status",    "number", False),
        ("Kante3 Programm",  "text",   False),
        ("Kante4",           "number", False),
        ("Kante4 Status",    "number", False),
        ("Kante4 Programm",  "text",   False),
        ("Abstapelplatz",    "number", False),
        ("Report Status",    "number", False),
        ("ObjectID",         "number", False),
        ("DateTime",         "text",   False),
        ("OrgStackPosition", "number", False),
    ]

    fields = {}  # {col_name: (entry_widget, col_type)}
    half = (len(column_defs) + 1) // 2  # 11 left, 11 right
    for i, (col_name, col_type, required) in enumerate(column_defs):
        label_text = col_name
        if required:
            label_text += " *"
        row = i % half
        col_offset = 0 if i < half else 3
        tk.Label(data_frame, text=label_text).grid(row=row, column=col_offset, sticky=tk.W, pady=1)
        entry = tk.Entry(data_frame, width=20)
        entry.grid(row=row, column=col_offset + 1, padx=5, pady=1)
        fields[col_name] = (entry, col_type)
    # Separator between left and right columns
    tk.Frame(data_frame, width=10).grid(row=0, column=2, rowspan=half)

    # --- Send button ---
    send_btn = tk.Button(root, text="Send to TEILE", command=do_send, width=20, height=2, state=tk.DISABLED)
    send_btn.pack(pady=10)

    # --- Status bar ---
    status_var = tk.StringVar(value="Not connected")
    status_label = tk.Label(root, textvariable=status_var, fg="gray", anchor=tk.W)
    status_label.pack(fill=tk.X, padx=10, pady=(0, 10))

    root.mainloop()

    # Clean up on close
    if db is not None:
        db.disconnect()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        gui()
