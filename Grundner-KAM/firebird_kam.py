"""
Firebird holzher_KAM.gdb - Standalone Module
Connects to a local Firebird database and manages the TEILE table.

Requirements:
    pip install fdb
    Firebird 2.x client library (fbclient.dll / libfbclient.so) must be installed
"""

import os
import sys
import socket
import threading
import logging
from datetime import datetime

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

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

    def get_parts_ready_for_edging(self):
        """Return rows from TEILE where any Kante Status = 1 (ready for edging)."""
        self._require_connection()
        cur = self.conn.cursor()
        cur.execute(
            'SELECT * FROM TEILE WHERE "Kante1 Status"=1 OR "Kante2 Status"=1 '
            'OR "Kante3 Status"=1 OR "Kante4 Status"=1'
        )
        cols = [desc[0].strip() for desc in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        return rows

    def set_kantenstatus(self, teile_id, durchlauf, new_status):
        """Call stored procedure Set_Kantenstatus to update an edge status.

        Args:
            teile_id: The TeileID value
            durchlauf: Edge pass number (1-4)
            new_status: New status value (e.g. 2=in progress, 99=done)
        """
        self._require_connection()
        cur = self.conn.cursor()
        try:
            cur.execute(
                f"EXECUTE PROCEDURE Set_Kantenstatus '{teile_id}',{durchlauf},{new_status}"
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def get_completed_parts(self):
        """Return parts with Report Status=0 where all edges are done (99) or unused (Kante=0).

        Uses the exact query from Vlecad_ITD production code.
        """
        self._require_connection()
        cur = self.conn.cursor()
        cur.execute(
            'SELECT * FROM TEILE WHERE "Report Status"=0 '
            'AND ("Kante1"=0 OR ("Kante1" <> 0 AND "Kante1 Status"=99)) '
            'AND ("Kante2"=0 OR ("Kante2" <> 0 AND "Kante2 Status"=99)) '
            'AND ("Kante3"=0 OR ("Kante3" <> 0 AND "Kante3 Status"=99)) '
            'AND ("Kante4"=0 OR ("Kante4" <> 0 AND "Kante4 Status"=99))'
        )
        cols = [desc[0].strip() for desc in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        return rows

    def mark_part_reported(self, vlow_id):
        """Set Report Status=1 for a part (individual part done)."""
        self._require_connection()
        cur = self.conn.cursor()
        try:
            cur.execute('UPDATE TEILE SET "Report Status"=1 WHERE "VlowID"=?', (vlow_id,))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def count_object_parts(self, prefix):
        """Count all parts belonging to an object (by VlowID prefix)."""
        self._require_connection()
        cur = self.conn.cursor()
        cur.execute(
            'SELECT COUNT(*) FROM TEILE WHERE "VlowID" LIKE ?',
            (prefix + "%",),
        )
        count = cur.fetchone()[0]
        cur.close()
        return count

    def count_done_object_parts(self, prefix):
        """Count parts of an object that have Report Status=1 and all edges done.

        Uses the exact query from Vlecad_ITD production code.
        """
        self._require_connection()
        cur = self.conn.cursor()
        cur.execute(
            'SELECT COUNT(*) FROM TEILE WHERE "VlowID" LIKE ? '
            'AND "Report Status"=1 '
            'AND ("Kante1"=0 OR ("Kante1" <> 0 AND "Kante1 Status"=99)) '
            'AND ("Kante2"=0 OR ("Kante2" <> 0 AND "Kante2 Status"=99)) '
            'AND ("Kante3"=0 OR ("Kante3" <> 0 AND "Kante3 Status"=99)) '
            'AND ("Kante4"=0 OR ("Kante4" <> 0 AND "Kante4 Status"=99))',
            (prefix + "%",),
        )
        count = cur.fetchone()[0]
        cur.close()
        return count

    def mark_object_reported(self, prefix):
        """Set Report Status=2 for all parts of an object (whole object done).

        Uses the exact query from Vlecad_ITD production code.
        """
        self._require_connection()
        cur = self.conn.cursor()
        try:
            cur.execute(
                'UPDATE TEILE SET "Report Status"=2 WHERE "VlowID" LIKE ? '
                'AND "Report Status"=1 '
                'AND ("Kante1"=0 OR ("Kante1" <> 0 AND "Kante1 Status"=99)) '
                'AND ("Kante2"=0 OR ("Kante2" <> 0 AND "Kante2 Status"=99)) '
                'AND ("Kante3"=0 OR ("Kante3" <> 0 AND "Kante3 Status"=99)) '
                'AND ("Kante4"=0 OR ("Kante4" <> 0 AND "Kante4 Status"=99))',
                (prefix + "%",),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def get_teiledaten(self, teile_id):
        """Call stored procedure Get_Teiledaten to retrieve part data."""
        self._require_connection()
        cur = self.conn.cursor()
        cur.execute(f"EXECUTE PROCEDURE Get_Teiledaten '{teile_id}'")
        row = cur.fetchone()
        cur.close()
        return row

    def update_abstapelplatz(self, vlow_id, platz):
        """Update the stacking position for a part."""
        self._require_connection()
        cur = self.conn.cursor()
        try:
            cur.execute(
                'UPDATE TEILE SET "Abstapelplatz"=? WHERE "VlowID"=?',
                (platz, vlow_id),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def get_part_by_teileid(self, teile_id):
        """Get the latest part row by TeileID (matches Vlecad_ITD SKIP query)."""
        self._require_connection()
        cur = self.conn.cursor()
        cur.execute(
            'SELECT SKIP ((SELECT count(*) - 1 FROM TEILE WHERE "TeileID"=?)) '
            '* FROM TEILE WHERE "TeileID"=?',
            (teile_id, teile_id),
        )
        if cur.description:
            cols = [desc[0].strip() for desc in cur.description]
            row = cur.fetchone()
            cur.close()
            return dict(zip(cols, row)) if row else None
        cur.close()
        return None

    def reset_incomplete_edges(self, vlow_id):
        """Reset edge statuses that are still in progress (<=2) back to 0."""
        self._require_connection()
        cur = self.conn.cursor()
        try:
            for k in range(1, 5):
                cur.execute(
                    f'UPDATE TEILE SET "Kante{k} Status"=0 '
                    f'WHERE ("Kante{k}" <> 0 AND "Kante{k} Status" <= 2) '
                    f'AND "VlowID"=?',
                    (vlow_id,),
                )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def mark_all_edges_finished(self, vlow_id):
        """Mark all used edges as finished (status=99)."""
        self._require_connection()
        cur = self.conn.cursor()
        try:
            for k in range(1, 5):
                cur.execute(
                    f'UPDATE TEILE SET "Kante{k} Status"=99 '
                    f'WHERE "Kante{k}" <> 0 AND "VlowID"=?',
                    (vlow_id,),
                )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def _require_connection(self):
        if self.conn is None:
            raise RuntimeError("Not connected. Call connect() first.")


class HolzherTCP:
    """TCP client for the Holzher KAM edge bander."""

    def __init__(self, host="192.168.244.99", port=60000, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.logger = logging.getLogger("HolzherTCP")

    def connect(self):
        """Open a TCP connection to the Holzher KAM."""
        if self.sock is not None:
            return
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))
        self.logger.info("TCP connected to %s:%d", self.host, self.port)

    def disconnect(self):
        """Close the TCP connection."""
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
            self.logger.info("TCP disconnected")

    def send_command(self, cmd):
        """Send a plain-text command and return the response line."""
        if self.sock is None:
            raise RuntimeError("TCP not connected")
        self.logger.debug("TCP send: %s", cmd)
        self.sock.sendall((cmd + "\r\n").encode("utf-8"))
        data = b""
        while True:
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break
        response = data.decode("utf-8", errors="replace").strip()
        self.logger.debug("TCP recv: %s", response)
        return response

    def load_program(self, prog, kant_id):
        """Send LOAD_PROGRAM command."""
        return self.send_command(f"LOAD_PROGRAM {prog} {kant_id}")

    def check_program(self, prog):
        """Send CHECK_PROGRAM command."""
        return self.send_command(f"CHECK_PROGRAM {prog}")

    def get_current_program(self):
        """Send GET_CURRENT_PROGRAM command."""
        return self.send_command("GET_CURRENT_PROGRAM")


class CncBarcodeSerial:
    """RS-232 serial output for CNC-barcode to Grundner Treturn.

    Channel B in the original Vlecad_ITD setup — sends the CNC-barcode
    (TeileID) over a COM port so the Grundner knows which part is coming.
    """

    def __init__(self, port="COM1", baudrate=9600, bytesize=8, stopbits=1,
                 parity="N", rtscts=False, xonxoff=False, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.stopbits = stopbits
        self.parity = parity
        self.rtscts = rtscts
        self.xonxoff = xonxoff
        self.timeout = timeout
        self.ser = None
        self.logger = logging.getLogger("CncSerial")

    def connect(self):
        """Open the serial port."""
        if not HAS_SERIAL:
            raise RuntimeError("pyserial not installed. Run: pip install pyserial")
        if self.ser is not None and self.ser.is_open:
            return
        parity_map = {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN,
                      "O": serial.PARITY_ODD, "M": serial.PARITY_MARK,
                      "S": serial.PARITY_SPACE}
        stopbits_map = {1: serial.STOPBITS_ONE, 1.5: serial.STOPBITS_ONE_POINT_FIVE,
                        2: serial.STOPBITS_TWO}
        bytesize_map = {5: serial.FIVEBITS, 6: serial.SIXBITS,
                        7: serial.SEVENBITS, 8: serial.EIGHTBITS}
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=bytesize_map.get(self.bytesize, serial.EIGHTBITS),
            stopbits=stopbits_map.get(self.stopbits, serial.STOPBITS_ONE),
            parity=parity_map.get(self.parity, serial.PARITY_NONE),
            rtscts=self.rtscts,
            xonxoff=self.xonxoff,
            timeout=self.timeout,
        )
        self.logger.info("Serial opened %s @ %d %d%s%s%s",
                         self.port, self.baudrate, self.bytesize, self.parity,
                         self.stopbits,
                         " RTS/CTS" if self.rtscts else (" XON/XOFF" if self.xonxoff else ""))

    def disconnect(self):
        """Close the serial port."""
        if self.ser is not None and self.ser.is_open:
            self.ser.close()
            self.logger.info("Serial closed %s", self.port)
        self.ser = None

    def send_barcode(self, barcode):
        """Send a CNC-barcode string over the serial port (with CR+LF)."""
        if self.ser is None or not self.ser.is_open:
            raise RuntimeError("Serial port not open")
        payload = (barcode + "\r\n").encode("ascii", errors="replace")
        self.ser.write(payload)
        self.logger.info("Serial TX [%s]: %s", self.port, barcode)

    @staticmethod
    def list_ports():
        """Return list of available COM ports (name, description)."""
        if not HAS_SERIAL:
            return []
        return [(p.device, p.description) for p in serial.tools.list_ports.comports()]


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
    """Tkinter GUI for connecting, inserting into TEILE, and running automation loops."""
    import tkinter as tk
    from tkinter import messagebox, filedialog, scrolledtext

    # --- Logging handler that writes to a tkinter ScrolledText widget ---
    class TextHandler(logging.Handler):
        def __init__(self, widget):
            super().__init__()
            self.widget = widget

        def emit(self, record):
            msg = self.format(record) + "\n"
            self.widget.after(0, self._append, msg)

        def _append(self, msg):
            self.widget.configure(state=tk.NORMAL)
            self.widget.insert(tk.END, msg)
            self.widget.see(tk.END)
            self.widget.configure(state=tk.DISABLED)

    # --- State ---
    db = None
    tcp = None
    com_serial = None
    polling_active = False
    polling_stop_event = threading.Event()

    logger = logging.getLogger("KAM_GUI")
    logger.setLevel(logging.DEBUG)

    def update_status(msg, error=False):
        status_var.set(msg)
        status_label.config(fg="red" if error else "green")

    def log(msg):
        logger.info(msg)

    # ── Firebird connection ──────────────────────────────────────────
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
            log(f"DB connected — TEILE has {n} rows")
        except Exception as e:
            db = None
            send_btn.config(state=tk.DISABLED)
            update_status(str(e), error=True)
            log(f"DB connect failed: {e}")

    def do_disconnect():
        nonlocal db
        if polling_active:
            do_stop_polling()
        if db is not None:
            db.disconnect()
            db = None
        connect_btn.config(text="Connect")
        send_btn.config(state=tk.DISABLED)
        update_status("Disconnected")
        log("DB disconnected")

    def browse_db():
        path = filedialog.askopenfilename(
            title="Select Firebird database",
            filetypes=[("Firebird DB", "*.gdb *.fdb"), ("All files", "*.*")],
        )
        if path:
            db_path_var.set(path)

    # ── TCP connection ───────────────────────────────────────────────
    def do_tcp_connect():
        nonlocal tcp
        h = tcp_host_var.get().strip()
        p = tcp_port_var.get().strip()
        if not h or not p:
            messagebox.showerror("Error", "TCP host and port required")
            return
        try:
            p = int(p)
        except ValueError:
            messagebox.showerror("Error", "TCP port must be a number")
            return
        try:
            if tcp is not None:
                tcp.disconnect()
            tcp = HolzherTCP(host=h, port=p)
            tcp.connect()
            log(f"TCP connected to {h}:{p}")
            tcp_status_var.set("Connected")
        except Exception as e:
            tcp = None
            log(f"TCP connect failed: {e}")
            tcp_status_var.set("Failed")

    def do_tcp_disconnect():
        nonlocal tcp
        if tcp is not None:
            tcp.disconnect()
            tcp = None
        tcp_status_var.set("Disconnected")
        log("TCP disconnected")

    def do_tcp_get_current():
        if tcp is None:
            log("TCP not connected")
            return
        try:
            resp = tcp.get_current_program()
            log(f"GET_CURRENT_PROGRAM -> {resp}")
        except Exception as e:
            log(f"TCP error: {e}")

    def do_tcp_check():
        if tcp is None:
            log("TCP not connected")
            return
        prog = tcp_prog_var.get().strip()
        if not prog:
            log("Enter a program name first")
            return
        try:
            resp = tcp.check_program(prog)
            log(f"CHECK_PROGRAM {prog} -> {resp}")
        except Exception as e:
            log(f"TCP error: {e}")

    def do_tcp_load():
        if tcp is None:
            log("TCP not connected")
            return
        prog = tcp_prog_var.get().strip()
        kant = tcp_kant_var.get().strip()
        if not prog or not kant:
            log("Enter program name and kant_id first")
            return
        try:
            resp = tcp.load_program(prog, kant)
            log(f"LOAD_PROGRAM {prog} {kant} -> {resp}")
        except Exception as e:
            log(f"TCP error: {e}")

    # ── COM port serial ─────────────────────────────────────────────
    def do_com_connect():
        nonlocal com_serial
        if not HAS_SERIAL:
            log("pyserial not installed. Run: pip install pyserial")
            return
        port = com_port_var.get().strip()
        if not port:
            messagebox.showerror("Error", "Select a COM port")
            return
        try:
            baud = int(com_baud_var.get())
        except ValueError:
            messagebox.showerror("Error", "Baud rate must be a number")
            return
        try:
            if com_serial is not None:
                com_serial.disconnect()
            com_serial = CncBarcodeSerial(
                port=port,
                baudrate=baud,
                bytesize=int(com_databits_var.get()),
                stopbits=float(com_stopbits_var.get()),
                parity=com_parity_var.get()[0],  # first char: N, E, O
                rtscts=(com_flow_var.get() == "RTS/CTS"),
                xonxoff=(com_flow_var.get() == "XON/XOFF"),
            )
            com_serial.connect()
            com_status_var.set("Connected")
            log(f"COM connected: {port} @ {baud}")
        except Exception as e:
            com_serial = None
            com_status_var.set("Failed")
            log(f"COM connect failed: {e}")

    def do_com_disconnect():
        nonlocal com_serial
        if com_serial is not None:
            com_serial.disconnect()
            com_serial = None
        com_status_var.set("Disconnected")
        log("COM disconnected")

    def do_com_refresh_ports():
        ports = CncBarcodeSerial.list_ports()
        menu = com_port_menu["menu"]
        menu.delete(0, tk.END)
        if ports:
            for dev, desc in ports:
                label = f"{dev}  ({desc})"
                menu.add_command(label=label, command=lambda d=dev: com_port_var.set(d))
            com_port_var.set(ports[0][0])
        else:
            menu.add_command(label="(none)", command=lambda: None)
            com_port_var.set("")
        log(f"Found {len(ports)} COM port(s)")

    def do_com_lookup_send():
        """Look up a VlowID in TEILE and send the part data to Grundner via COM."""
        if db is None:
            log("DB not connected — connect to Firebird first")
            return
        if com_serial is None:
            log("COM not connected — connect COM port first")
            return
        vlow_id = com_lookup_var.get().strip()
        if not vlow_id:
            log("Enter a VlowID to look up")
            return
        try:
            # Look up part by VlowID
            cur = db.conn.cursor()
            cur.execute('SELECT * FROM TEILE WHERE "VlowID"=?', (vlow_id,))
            if cur.description:
                cols = [desc[0].strip() for desc in cur.description]
                row = cur.fetchone()
            else:
                row = None
                cols = []
            cur.close()

            if row is None:
                log(f"VlowID '{vlow_id}' not found in TEILE")
                return

            part = dict(zip(cols, row))

            # Log the found data
            teile_id = part.get("TeileID", "")
            log(f"Found: VlowID={vlow_id}  TeileID={teile_id}  "
                f"{part.get('Teilelaenge','')}x{part.get('Teilebreite','')}x{part.get('Teiledicke','')}  "
                f"Abstapelplatz={part.get('Abstapelplatz','')}  "
                f"Report Status={part.get('Report Status','')}")
            for k in range(1, 5):
                kante = part.get(f"Kante{k}", 0)
                status = part.get(f"Kante{k} Status", 0)
                prog = part.get(f"Kante{k} Programm", "")
                if kante:
                    log(f"  Kante{k}={kante}  Status={status}  Programm={prog}")

            # Send over COM in GDB column order, excluding VlowID
            values = []
            for col, val in zip(cols, row):
                if col == "VlowID":
                    continue
                values.append(str(val) if val is not None else "")
            payload = ";".join(values)
            com_serial.send_barcode(payload)
            log(f"Sent to Grundner ({len(values)} fields): {payload}")

        except Exception as e:
            log(f"Lookup/send failed: {e}")

    def do_com_send_raw():
        """Send raw text over COM (for testing)."""
        if com_serial is None:
            log("COM not connected")
            return
        text = com_raw_var.get().strip()
        if not text:
            log("Enter text to send")
            return
        try:
            com_serial.send_barcode(text)
            log(f"COM raw TX: {text}")
        except Exception as e:
            log(f"COM send failed: {e}")

    # ── Data entry / send ────────────────────────────────────────────
    def do_send():
        if db is None:
            messagebox.showerror("Error", "Not connected")
            return

        vlow = fields["VlowID"][0].get().strip()
        if not vlow:
            messagebox.showerror("Error", "VlowID is required")
            return

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
            log(f"Inserted part {data.get('VlowID', '?')} into TEILE")
        except Exception as e:
            update_status(f"Insert failed: {e}", error=True)
            log(f"Insert failed: {e}")

    # ── Polling loops (background threads) ───────────────────────────
    def procedure1_loop(stop_event):
        """Poll every 1s: pick up parts with Kante Status=1, set to 2."""
        while not stop_event.is_set():
            try:
                if db is not None and db.conn is not None:
                    parts = db.get_parts_ready_for_edging()
                    for part in parts:
                        teile_id = part.get("TeileID", "")
                        vlow_id = part.get("VlowID", "?")
                        for durchlauf in range(1, 5):
                            status_key = f"Kante{durchlauf} Status"
                            if part.get(status_key) == 1:
                                db.set_kantenstatus(teile_id, durchlauf, 2)
                                log(f"[P1] {vlow_id} Kante{durchlauf} Status: 1 -> 2 (in progress)")
            except Exception as e:
                logger.error(f"[P1] Error: {e}")
            stop_event.wait(1)

    def procedure2_loop(stop_event):
        """Poll every 5s: report completed parts and check object completeness."""
        while not stop_event.is_set():
            try:
                if db is not None and db.conn is not None:
                    # Step 1: mark individual parts done (Report Status 0 -> 1)
                    completed = db.get_completed_parts()
                    prefixes_to_check = set()
                    for part in completed:
                        vlow_id = part.get("VlowID", "")
                        db.mark_part_reported(vlow_id)
                        log(f"[P2] {vlow_id} Report Status: 0 -> 1 (part done)")
                        prefix = vlow_id[:35] if len(vlow_id) >= 35 else vlow_id
                        prefixes_to_check.add(prefix)

                    # Step 2: check if whole objects are complete
                    for prefix in prefixes_to_check:
                        total = db.count_object_parts(prefix)
                        done = db.count_done_object_parts(prefix)
                        if total > 0 and total == done:
                            db.mark_object_reported(prefix)
                            log(f"[P2] Object '{prefix}' complete ({total} parts) -> Report Status=2")
            except Exception as e:
                logger.error(f"[P2] Error: {e}")
            stop_event.wait(5)

    def do_start_polling():
        nonlocal polling_active, polling_stop_event
        if db is None:
            messagebox.showerror("Error", "Connect to database first")
            return
        if polling_active:
            log("Polling already running")
            return
        polling_stop_event.clear()
        t1 = threading.Thread(target=procedure1_loop, args=(polling_stop_event,), daemon=True)
        t2 = threading.Thread(target=procedure2_loop, args=(polling_stop_event,), daemon=True)
        t1.start()
        t2.start()
        polling_active = True
        start_btn.config(state=tk.DISABLED)
        stop_btn.config(state=tk.NORMAL)
        log("Polling started (P1 @ 1s, P2 @ 5s)")

    def do_stop_polling():
        nonlocal polling_active
        if not polling_active:
            return
        polling_stop_event.set()
        polling_active = False
        start_btn.config(state=tk.NORMAL)
        stop_btn.config(state=tk.DISABLED)
        log("Polling stopped")

    # ══════════════════════════════════════════════════════════════════
    # Window
    # ══════════════════════════════════════════════════════════════════
    root = tk.Tk()
    root.title("Firebird KAM - TEILE")
    root.resizable(True, True)

    # --- Firebird connection frame ---
    conn_frame = tk.LabelFrame(root, text="Firebird Connection", padx=10, pady=5)
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

    # --- TCP connection frame ---
    tcp_frame = tk.LabelFrame(root, text="Holzher KAM TCP", padx=10, pady=5)
    tcp_frame.pack(fill=tk.X, padx=10, pady=5)

    tk.Label(tcp_frame, text="Host:").grid(row=0, column=0, sticky=tk.W)
    tcp_host_var = tk.StringVar(value="192.168.244.99")
    tk.Entry(tcp_frame, textvariable=tcp_host_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5)

    tk.Label(tcp_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
    tcp_port_var = tk.StringVar(value="60000")
    tk.Entry(tcp_frame, textvariable=tcp_port_var, width=8).grid(row=0, column=3, sticky=tk.W, padx=5)

    tcp_status_var = tk.StringVar(value="Disconnected")
    tk.Label(tcp_frame, textvariable=tcp_status_var, fg="gray").grid(row=0, column=4, padx=10)

    tcp_btn_frame = tk.Frame(tcp_frame)
    tcp_btn_frame.grid(row=1, column=0, columnspan=5, pady=5)
    tk.Button(tcp_btn_frame, text="TCP Connect", command=do_tcp_connect, width=12).pack(side=tk.LEFT, padx=3)
    tk.Button(tcp_btn_frame, text="TCP Disconnect", command=do_tcp_disconnect, width=14).pack(side=tk.LEFT, padx=3)

    # Manual TCP commands
    tcp_cmd_frame = tk.Frame(tcp_frame)
    tcp_cmd_frame.grid(row=2, column=0, columnspan=5, pady=2)
    tk.Button(tcp_cmd_frame, text="GET_CURRENT", command=do_tcp_get_current, width=14).pack(side=tk.LEFT, padx=3)

    tk.Label(tcp_cmd_frame, text="Prog:").pack(side=tk.LEFT, padx=(10, 2))
    tcp_prog_var = tk.StringVar()
    tk.Entry(tcp_cmd_frame, textvariable=tcp_prog_var, width=12).pack(side=tk.LEFT, padx=2)
    tk.Button(tcp_cmd_frame, text="CHECK", command=do_tcp_check, width=7).pack(side=tk.LEFT, padx=3)

    tk.Label(tcp_cmd_frame, text="Kant:").pack(side=tk.LEFT, padx=(10, 2))
    tcp_kant_var = tk.StringVar()
    tk.Entry(tcp_cmd_frame, textvariable=tcp_kant_var, width=6).pack(side=tk.LEFT, padx=2)
    tk.Button(tcp_cmd_frame, text="LOAD", command=do_tcp_load, width=7).pack(side=tk.LEFT, padx=3)

    # --- COM port frame ---
    com_frame = tk.LabelFrame(root, text="COM Port (CNC-Barcode to Grundner)", padx=10, pady=5)
    com_frame.pack(fill=tk.X, padx=10, pady=5)

    tk.Label(com_frame, text="Port:").grid(row=0, column=0, sticky=tk.W)
    com_port_var = tk.StringVar(value="")
    com_port_menu = tk.OptionMenu(com_frame, com_port_var, "(none)")
    com_port_menu.config(width=20)
    com_port_menu.grid(row=0, column=1, sticky=tk.W, padx=5)
    tk.Button(com_frame, text="Refresh", command=do_com_refresh_ports, width=7).grid(row=0, column=2, padx=3)

    tk.Label(com_frame, text="Baud:").grid(row=0, column=3, sticky=tk.W, padx=(10, 0))
    com_baud_var = tk.StringVar(value="9600")
    tk.OptionMenu(com_frame, com_baud_var, "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200").grid(
        row=0, column=4, sticky=tk.W, padx=5)

    tk.Label(com_frame, text="Data:").grid(row=1, column=0, sticky=tk.W)
    com_databits_var = tk.StringVar(value="8")
    tk.OptionMenu(com_frame, com_databits_var, "7", "8").grid(row=1, column=1, sticky=tk.W, padx=5)

    tk.Label(com_frame, text="Stop:").grid(row=1, column=3, sticky=tk.W, padx=(10, 0))
    com_stopbits_var = tk.StringVar(value="1")
    tk.OptionMenu(com_frame, com_stopbits_var, "1", "1.5", "2").grid(row=1, column=4, sticky=tk.W, padx=5)

    tk.Label(com_frame, text="Parity:").grid(row=2, column=0, sticky=tk.W)
    com_parity_var = tk.StringVar(value="None")
    tk.OptionMenu(com_frame, com_parity_var, "None", "Even", "Odd").grid(row=2, column=1, sticky=tk.W, padx=5)

    tk.Label(com_frame, text="Flow:").grid(row=2, column=3, sticky=tk.W, padx=(10, 0))
    com_flow_var = tk.StringVar(value="None")
    tk.OptionMenu(com_frame, com_flow_var, "None", "RTS/CTS", "XON/XOFF").grid(row=2, column=4, sticky=tk.W, padx=5)

    com_status_var = tk.StringVar(value="Disconnected")
    tk.Label(com_frame, textvariable=com_status_var, fg="gray").grid(row=0, column=5, padx=10)

    com_btn_frame = tk.Frame(com_frame)
    com_btn_frame.grid(row=3, column=0, columnspan=6, pady=5)
    tk.Button(com_btn_frame, text="COM Connect", command=do_com_connect, width=12).pack(side=tk.LEFT, padx=3)
    tk.Button(com_btn_frame, text="COM Disconnect", command=do_com_disconnect, width=14).pack(side=tk.LEFT, padx=3)

    # VlowID lookup → send to Grundner
    com_lookup_frame = tk.Frame(com_frame)
    com_lookup_frame.grid(row=4, column=0, columnspan=6, pady=(2, 0))
    tk.Label(com_lookup_frame, text="VlowID:").pack(side=tk.LEFT)
    com_lookup_var = tk.StringVar()
    tk.Entry(com_lookup_frame, textvariable=com_lookup_var, width=40).pack(side=tk.LEFT, padx=5)
    tk.Button(com_lookup_frame, text="Lookup & Send to Grundner", command=do_com_lookup_send,
              width=24, bg="#d4edda").pack(side=tk.LEFT, padx=5)

    # Raw test send
    com_raw_frame = tk.Frame(com_frame)
    com_raw_frame.grid(row=5, column=0, columnspan=6, pady=(2, 0))
    tk.Label(com_raw_frame, text="Raw:").pack(side=tk.LEFT)
    com_raw_var = tk.StringVar()
    tk.Entry(com_raw_frame, textvariable=com_raw_var, width=40).pack(side=tk.LEFT, padx=5)
    tk.Button(com_raw_frame, text="Send Raw", command=do_com_send_raw, width=10).pack(side=tk.LEFT, padx=5)

    # Auto-detect COM ports on startup
    if HAS_SERIAL:
        root.after(100, do_com_refresh_ports)

    # --- Data entry frame ---
    data_frame = tk.LabelFrame(root, text="TEILE Data", padx=10, pady=5)
    data_frame.pack(fill=tk.X, padx=10, pady=5)

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

    fields = {}
    half = (len(column_defs) + 1) // 2
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
    tk.Frame(data_frame, width=10).grid(row=0, column=2, rowspan=half)

    # --- Send + Automation buttons ---
    action_frame = tk.Frame(root)
    action_frame.pack(pady=5)

    send_btn = tk.Button(action_frame, text="Send to TEILE", command=do_send, width=16, height=2, state=tk.DISABLED)
    send_btn.pack(side=tk.LEFT, padx=10)

    auto_frame = tk.LabelFrame(action_frame, text="Automation", padx=5, pady=2)
    auto_frame.pack(side=tk.LEFT, padx=10)
    start_btn = tk.Button(auto_frame, text="Start", command=do_start_polling, width=8, bg="#d4edda")
    start_btn.pack(side=tk.LEFT, padx=3)
    stop_btn = tk.Button(auto_frame, text="Stop", command=do_stop_polling, width=8, bg="#f8d7da", state=tk.DISABLED)
    stop_btn.pack(side=tk.LEFT, padx=3)

    # --- Status bar ---
    status_var = tk.StringVar(value="Not connected")
    status_label = tk.Label(root, textvariable=status_var, fg="gray", anchor=tk.W)
    status_label.pack(fill=tk.X, padx=10)

    # --- Log panel ---
    log_frame = tk.LabelFrame(root, text="Log", padx=5, pady=5)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

    log_text = scrolledtext.ScrolledText(log_frame, height=12, state=tk.DISABLED, wrap=tk.WORD,
                                         font=("Consolas", 9))
    log_text.pack(fill=tk.BOTH, expand=True)

    # Wire up logging to the text widget
    text_handler = TextHandler(log_text)
    text_handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(text_handler)
    # Also capture HolzherTCP and CncSerial logs
    logging.getLogger("HolzherTCP").addHandler(text_handler)
    logging.getLogger("HolzherTCP").setLevel(logging.DEBUG)
    logging.getLogger("CncSerial").addHandler(text_handler)
    logging.getLogger("CncSerial").setLevel(logging.DEBUG)

    def on_close():
        if polling_active:
            do_stop_polling()
        if com_serial is not None:
            do_com_disconnect()
        if tcp is not None:
            do_tcp_disconnect()
        if db is not None:
            db.disconnect()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        gui()
