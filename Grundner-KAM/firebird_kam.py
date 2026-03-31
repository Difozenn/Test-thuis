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


class GrundnerPLC:
    """TCP client for the Grundner Treturn PLC sorting machine.

    Protocol: semicolon-delimited commands over TCP.
    Checksum: XOR all message bytes, then OR with 0x80.
    Tables: 1=Einlagern (32 rows), 22=drawer assignments (110 rows).
    """

    SIDE = 1
    TABLE_EINLAGERN = 1
    TABLE_DRAWERS = 22
    TABLE_STATUS = 101
    EINLAGERN_ROWS = 32
    DRAWER_ROWS = 110

    def __init__(self, host="10.10.150.1", port=10001, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self._lock = threading.Lock()
        self._polling = False
        self._poll_stop = threading.Event()
        self._poll_flags = [0, 0, 0, 0]
        self.logger = logging.getLogger("GrundnerPLC")

    def connect(self):
        if self.sock is not None:
            return
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))
        self.logger.info("PLC connected to %s:%d", self.host, self.port)

    def disconnect(self):
        self.stop_polling()
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
            self.logger.info("PLC disconnected")

    @staticmethod
    def _checksum(msg_bytes):
        """XOR all bytes, then OR with 0x80."""
        xor = 0
        for b in msg_bytes:
            xor ^= b
        return xor | 0x80

    def _send_raw(self, msg):
        """Send message with checksum + LF."""
        if self.sock is None:
            raise RuntimeError("PLC not connected")
        encoded = msg.encode("ascii", errors="replace")
        chk = self._checksum(encoded)
        self.sock.sendall(encoded + bytes([chk, 0x0A]))
        self.logger.debug("PLC> %s [chk=0x%02X]", msg, chk)

    def _recv_line(self, timeout=None):
        """Receive one line from PLC (up to CR+LF or LF). Returns decoded string."""
        if self.sock is None:
            raise RuntimeError("PLC not connected")
        old_timeout = self.sock.gettimeout()
        if timeout is not None:
            self.sock.settimeout(timeout)
        try:
            buf = b""
            while True:
                try:
                    b = self.sock.recv(1)
                except socket.timeout:
                    break
                if not b:
                    break
                buf += b
                if b == b"\n":
                    break
            # Strip trailing CR/LF and checksum byte (last non-CRLF byte)
            raw = buf.rstrip(b"\r\n")
            if raw and (raw[-1] & 0x80):
                raw = raw[:-1]  # strip checksum
            return raw.decode("ascii", errors="replace")
        finally:
            if timeout is not None:
                self.sock.settimeout(old_timeout)

    def _recv_ack(self, timeout=2):
        """Wait for ACK from PLC. Returns True if received."""
        line = self._recv_line(timeout=timeout)
        is_ack = "ACK" in line if line else False
        if not is_ack:
            self.logger.warning("Expected ACK, got: %r", line)
        return is_ack

    def _send_ack(self):
        """Send ACK response to PLC."""
        self._send_raw("ACK...1)")

    def _send_cmd(self, msg):
        """Send command and wait for ACK."""
        self._send_raw(msg)
        return self._recv_ack()

    def read_table(self, table, start_row=1, count=32):
        """Read rows from PLC table. Returns list of (row_number, data_string)."""
        with self._lock:
            cmd = f"#M;{self.SIDE};{table};{start_row};{count};"
            self._send_raw(cmd)
            if not self._recv_ack():
                return []

            rows = []
            for _ in range(count):
                line = self._recv_line()
                if not line:
                    break
                # Parse $M;side;table;row;data...
                if line.startswith("$M;"):
                    parts = line.split(";", 4)
                    if len(parts) >= 5:
                        row_num = int(parts[3])
                        data = parts[4]
                        rows.append((row_num, data))
                self._send_ack()
            return rows

    def write_row_table22(self, row, value):
        """Write a single value to table 22 (drawer assignments).

        Sequence: $Z (select row) → wait ACK → $M (write data) → wait ACK + echo.
        """
        with self._lock:
            # Select row for editing
            select_cmd = f"$Z;{self.SIDE};{self.TABLE_DRAWERS};{row};"
            self._send_raw(select_cmd)
            if not self._recv_ack():
                self.logger.error("No ACK for $Z select row %d", row)
                return False

            # Write the value
            write_cmd = f"$M;{self.SIDE};{self.TABLE_DRAWERS};{row};{value};"
            self._send_raw(write_cmd)
            if not self._recv_ack():
                self.logger.error("No ACK for $M write row %d", row)
                return False

            # PLC echoes back the written data — read and ACK it
            echo = self._recv_line(timeout=2)
            if echo:
                self._send_ack()

            return True

    def clear_einlagern_row(self, row):
        """Clear a row in the Einlagern table (table 1) by writing zeros."""
        with self._lock:
            # 49 zero fields for a full row clear
            zeros = ";".join([""] + ["0"] * 48)
            cmd = f"$M;{self.SIDE};{self.TABLE_EINLAGERN};{row};{zeros};"
            self._send_raw(cmd)
            if not self._recv_ack():
                return False
            # Read echo
            echo = self._recv_line(timeout=2)
            if echo:
                self._send_ack()
            return True

    def finalize(self):
        """Send finalize command ($M;1;0;) after a write session."""
        with self._lock:
            self._send_raw(f"$M;{self.SIDE};0;")
            self._recv_ack(timeout=2)

    def assign_drawer(self, drawer, part_count=1):
        """Assign parts to a drawer on the Treturn.

        This is the key operation: tells the PLC to sort part_count parts
        to the specified drawer number.
        """
        self.logger.info("Assigning %d part(s) to drawer %d", part_count, drawer)
        ok = self.write_row_table22(drawer, part_count)
        if ok:
            self.finalize()
        return ok

    def delete_einlagern_row(self, row, count=1):
        """Delete row(s) from Einlagern table using #X command.

        PLC shifts remaining rows up after deletion — this is how
        production LagerPC clears processed parts.
        """
        with self._lock:
            cmd = f"#X;{self.SIDE};{self.TABLE_EINLAGERN};{row};{count};"
            self._send_raw(cmd)
            return self._recv_ack()

    def send_c2(self):
        """Send C2 carousel control command after drawer assignment."""
        with self._lock:
            self._send_raw(f"C2;{self.SIDE};0;")
            self._recv_ack(timeout=2)

    @staticmethod
    def parse_einlagern_fields(data_string):
        """Parse Einlagern table 1 row data (49 semicolon-separated fields).

        Returns dict or None if row is empty/all-zeros.
        Field 0 = type/TeileID (text, 18-char padded)
        Field 2 = length, Field 3 = width, Field 4 = thickness
        """
        fields = data_string.split(";")
        type_nr = fields[0].strip() if fields else ""
        if not type_nr or all(c in "0 " for c in type_nr):
            return None
        return {
            "type_nr": type_nr,
            "length": fields[2].strip() if len(fields) > 2 else "",
            "width": fields[3].strip() if len(fields) > 3 else "",
            "thickness": fields[4].strip() if len(fields) > 4 else "",
            "raw_fields": fields,
        }

    def write_einlagern_row(self, row, type_nr, length, width, thickness,
                            piece_count=1, place=0):
        """Write part data to Einlagern table 1 so PLC knows dimensions.

        Constructs the 49-field row matching production format:
        type(18chars);0;length;width;thickness;0;piece_count;place;
        0 x 33 fields;1;99;0;0;0;0;0;0
        """
        # Pad type_nr to 18 chars (right-padded with spaces) like production
        type_padded = str(type_nr).ljust(18)

        fields = [""] * 49
        fields[0] = type_padded
        fields[1] = "0"
        fields[2] = str(int(length)) if length else "0"
        fields[3] = str(int(width)) if width else "0"
        fields[4] = str(int(thickness)) if thickness else "0"
        fields[5] = "0"
        fields[6] = str(int(piece_count))
        fields[7] = str(int(place)) if place else "0"
        # Fields 8-40: zeros (internal PLC data)
        for i in range(8, 41):
            fields[i] = "0"
        fields[41] = "1"   # processing flag
        fields[42] = "99"  # priority
        for i in range(43, 49):
            fields[i] = "0"

        data = ";".join(fields)

        with self._lock:
            # Select row for editing
            select_cmd = f"$Z;{self.SIDE};{self.TABLE_EINLAGERN};{row};"
            self._send_raw(select_cmd)
            if not self._recv_ack():
                self.logger.error("No ACK for $Z select Einlagern row %d", row)
                return False

            # Write the data
            write_cmd = f"$M;{self.SIDE};{self.TABLE_EINLAGERN};{row};{data};"
            self._send_raw(write_cmd)
            if not self._recv_ack():
                self.logger.error("No ACK for $M write Einlagern row %d", row)
                return False

            # PLC echoes back — read and ACK it
            echo = self._recv_line(timeout=2)
            if echo:
                self._send_ack()

            return True

    def read_einlagern(self):
        """Read the Einlagern table (table 1, 32 rows)."""
        return self.read_table(self.TABLE_EINLAGERN, 1, self.EINLAGERN_ROWS)

    def read_drawers(self):
        """Read drawer assignments (table 22, 110 rows)."""
        return self.read_table(self.TABLE_DRAWERS, 1, self.DRAWER_ROWS)

    def poll_status(self, flags=None):
        """Send @H status poll. Returns response flags or None."""
        if flags is None:
            flags = self._poll_flags
        f1, f2, f3, f4 = flags
        cmd = f"@H;{self.SIDE};{self.TABLE_STATUS};{f1};{f2};{f3};{f4}"
        with self._lock:
            self._send_raw(cmd)
            # @H doesn't get an ACK in normal polling — just sent continuously

    def start_polling(self, interval=0.5):
        """Start background @H polling to keep connection alive."""
        if self._polling:
            return
        self._poll_stop.clear()
        self._polling = True

        def _poll_loop():
            while not self._poll_stop.is_set():
                try:
                    self.poll_status()
                except Exception as e:
                    self.logger.error("Poll error: %s", e)
                    break
                self._poll_stop.wait(interval)
            self._polling = False

        t = threading.Thread(target=_poll_loop, daemon=True)
        t.start()
        self.logger.info("PLC polling started (%.1fs interval)", interval)

    def stop_polling(self):
        """Stop background polling."""
        if self._polling:
            self._poll_stop.set()
            self._polling = False
            self.logger.info("PLC polling stopped")


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
    plc = None
    polling_active = False
    polling_stop_event = threading.Event()
    auto_plc_active = False
    auto_plc_stop = threading.Event()

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

    # ── Grundner Treturn PLC TCP ────────────────────────────────────
    def do_plc_connect():
        nonlocal plc
        h = plc_host_var.get().strip()
        p = plc_port_var.get().strip()
        if not h or not p:
            log("PLC host and port required")
            return
        try:
            p = int(p)
        except ValueError:
            log("PLC port must be a number")
            return
        try:
            if plc is not None:
                plc.disconnect()
            plc = GrundnerPLC(host=h, port=p)
            plc.connect()
            plc.start_polling()
            plc_status_var.set("Connected")
            log(f"PLC connected to {h}:{p} — polling started")
        except Exception as e:
            plc = None
            plc_status_var.set("Failed")
            log(f"PLC connect failed: {e}")

    def do_plc_disconnect():
        nonlocal plc
        if plc is not None:
            plc.disconnect()
            plc = None
        plc_status_var.set("Disconnected")
        log("PLC disconnected")

    def do_plc_read_einlagern():
        if plc is None:
            log("PLC not connected")
            return
        try:
            plc.stop_polling()
            rows = plc.read_einlagern()
            non_empty = [(r, d) for r, d in rows if d.strip().replace(";", "").replace("0", "").strip()]
            if non_empty:
                for row_num, data in non_empty:
                    log(f"[PLC] Einlagern row {row_num}: {data[:80]}...")
            else:
                log(f"[PLC] Einlagern: all {len(rows)} rows empty")
            plc.start_polling()
        except Exception as e:
            log(f"[PLC] Read error: {e}")

    def do_plc_read_drawers():
        if plc is None:
            log("PLC not connected")
            return
        try:
            plc.stop_polling()
            rows = plc.read_drawers()
            active = [(r, d) for r, d in rows if d.strip() not in ("0", "")]
            if active:
                for row_num, data in active:
                    log(f"[PLC] Drawer {row_num}: {data} parts")
            else:
                log(f"[PLC] All {len(rows)} drawers empty")
            plc.start_polling()
        except Exception as e:
            log(f"[PLC] Read error: {e}")

    def do_plc_safe_test():
        """Safe read-only test: connect, poll, read tables, disconnect.

        Does NOT write anything to the PLC.
        """
        if plc is not None:
            log("[TEST] Already connected — disconnect first")
            return
        h = plc_host_var.get().strip()
        p = plc_port_var.get().strip()
        if not h or not p:
            log("[TEST] Set PLC host and port first")
            return

        def _run_test():
            nonlocal plc
            try:
                p_int = int(p)
                log(f"[TEST] === SAFE PLC TEST START (read-only) ===")

                # Step 1: TCP connect
                log(f"[TEST] Step 1/5: Connecting to {h}:{p_int}...")
                plc = GrundnerPLC(host=h, port=p_int, timeout=5)
                plc.connect()
                log(f"[TEST] Step 1/5: Connected OK")
                root.after(0, lambda: plc_status_var.set("Testing..."))

                # Step 2: Single @H poll
                log(f"[TEST] Step 2/5: Sending @H status poll...")
                plc.poll_status()
                import time
                time.sleep(0.3)
                # Try to read any response the PLC sent back
                try:
                    resp = plc._recv_line(timeout=1)
                    if resp:
                        log(f"[TEST] Step 2/5: PLC response: {resp[:80]}")
                    else:
                        log(f"[TEST] Step 2/5: No response (normal for @H)")
                except Exception:
                    log(f"[TEST] Step 2/5: No response (normal for @H)")

                # Step 3: Read Einlagern table
                log(f"[TEST] Step 3/5: Reading Einlagern table (32 rows)...")
                rows1 = plc.read_einlagern()
                non_empty = [(r, d) for r, d in rows1
                             if d.strip().replace(";", "").replace("0", "").strip()]
                log(f"[TEST] Step 3/5: Got {len(rows1)} rows, {len(non_empty)} non-empty")
                for row_num, data in non_empty[:5]:
                    log(f"[TEST]   Row {row_num}: {data[:80]}")

                # Step 4: Read Drawer table
                log(f"[TEST] Step 4/5: Reading Drawer table (110 rows)...")
                rows22 = plc.read_drawers()
                active = [(r, d) for r, d in rows22 if d.strip() not in ("0", "")]
                log(f"[TEST] Step 4/5: Got {len(rows22)} rows, {len(active)} active drawers")
                for row_num, data in active[:10]:
                    log(f"[TEST]   Drawer {row_num}: {data} parts")

                # Step 5: Disconnect
                log(f"[TEST] Step 5/5: Disconnecting...")
                plc.disconnect()
                plc = None
                root.after(0, lambda: plc_status_var.set("Disconnected"))
                log(f"[TEST] === SAFE PLC TEST COMPLETE ===")

            except Exception as e:
                log(f"[TEST] FAILED: {e}")
                if plc is not None:
                    try:
                        plc.disconnect()
                    except Exception:
                        pass
                    plc = None
                root.after(0, lambda: plc_status_var.set("Test failed"))

        threading.Thread(target=_run_test, daemon=True).start()

    def do_plc_manual_assign():
        """Manually assign a part to a drawer (with confirmation)."""
        if plc is None:
            log("[PLC] Not connected — connect first")
            return
        drawer_str = plc_drawer_var.get().strip()
        if not drawer_str:
            log("[PLC] Enter a drawer number (1-24)")
            return
        try:
            drawer = int(drawer_str)
        except ValueError:
            log("[PLC] Drawer must be a number")
            return
        if drawer < 1 or drawer > 24:
            log(f"[PLC] Drawer {drawer} out of range (1-24)")
            return
        if not messagebox.askyesno("Confirm PLC Write",
                f"Send part to drawer {drawer}?\n\n"
                "This will WRITE to the PLC.\n"
                "Make sure a part is on the belt."):
            log("[PLC] Manual assign cancelled")
            return

        def _do_assign():
            try:
                plc.stop_polling()
                log(f"[PLC] Assigning 1 part to drawer {drawer}...")
                ok = plc.assign_drawer(drawer, part_count=1)
                plc.start_polling()
                if ok:
                    log(f"[PLC] Drawer {drawer} assignment sent OK")
                else:
                    log(f"[PLC] Drawer {drawer} assignment FAILED")
            except Exception as e:
                log(f"[PLC] Assign error: {e}")

        threading.Thread(target=_do_assign, daemon=True).start()

    # ── Automatic PLC table 1 polling (LagerPC replacement) ─────────
    def _fill_form_from_part(part):
        """Fill TEILE Data form fields from a GET_TEILEDATEN result dict."""
        for col_name, (entry, col_type) in fields.items():
            entry.delete(0, tk.END)
            val = part.get(col_name, "")
            if val is not None and val != "":
                entry.insert(0, str(val))

    def _db_lookup(type_nr):
        """Look up a part by type_nr (TeileID/Barcode) in Firebird DB.

        Returns dict of {col: value} or None.
        """
        if db is None or db.conn is None:
            return None
        try:
            cur = db.conn.cursor()
            cur.execute("EXECUTE PROCEDURE GET_TEILEDATEN ?", (type_nr,))
            row = cur.fetchone()
            if cur.description:
                cols = [desc[0].strip() for desc in cur.description]
            else:
                cols = []
            cur.close()
            if row is None:
                return None
            return dict(zip(cols, row))
        except Exception as e:
            log(f"[AUTO] DB lookup error for '{type_nr}': {e}")
            return None

    def do_start_auto_plc():
        """Start automatic table 1 polling — this is the LagerPC replacement.

        Flow per cycle:
        1. Read table 1 from PLC
        2. If non-empty row found: extract type_nr from field 0
        3. GET_TEILEDATEN(type_nr) on Firebird DB -> Abstapelplatz
        4. Delete row 1 from table 1 (#X) — PLC shifts remaining rows up
        5. Write drawer to table 22 -> finalize -> C2
        6. Repeat until table 1 is empty
        7. Send @H keepalive when idle
        """
        nonlocal auto_plc_active
        if plc is None:
            log("[AUTO] PLC not connected — connect first")
            return
        if db is None:
            log("[AUTO] DB not connected — connect to Firebird first")
            return
        if auto_plc_active:
            log("[AUTO] Already running")
            return

        # Stop @H polling — auto loop handles keepalive
        plc.stop_polling()
        auto_plc_stop.clear()
        auto_plc_active = True
        root.after(0, lambda: auto_status_var.set("RUNNING"))
        root.after(0, lambda: auto_start_btn.config(state=tk.DISABLED))
        root.after(0, lambda: auto_stop_btn.config(state=tk.NORMAL))

        def _auto_loop():
            nonlocal auto_plc_active
            log("[AUTO] === LagerPC auto-mode STARTED ===")
            log("[AUTO] Polling table 1 every 1s for scanned parts...")

            while not auto_plc_stop.is_set():
                try:
                    if plc is None or plc.sock is None:
                        log("[AUTO] PLC disconnected — stopping")
                        break
                    if db is None or db.conn is None:
                        log("[AUTO] DB disconnected — stopping")
                        break

                    # Read table 1 (also keeps TCP connection alive)
                    rows = plc.read_einlagern()

                    # Find first non-empty row
                    processed = False
                    for row_num, data in rows:
                        parsed = GrundnerPLC.parse_einlagern_fields(data)
                        if parsed:
                            type_nr = parsed["type_nr"]
                            dims = f"{parsed['length']}x{parsed['width']}x{parsed['thickness']}"
                            log(f"[AUTO] Part in row {row_num}: type={type_nr} ({dims})")

                            # DB lookup
                            part = _db_lookup(type_nr)

                            # Delete row 1 from table 1 (PLC shifts remaining rows up)
                            plc.delete_einlagern_row(1)

                            if part:
                                platz = part.get("Abstapelplatz", 0)
                                teile_id = part.get("TeileID", "?")
                                log(f"[AUTO] -> TeileID={teile_id}, Drawer={platz}")

                                # Update GUI form fields
                                root.after(0, lambda p=part: _fill_form_from_part(p))

                                # Update scan result display
                                laenge = part.get("Teilelaenge", "")
                                breite = part.get("Teilebreite", "")
                                dicke = part.get("Teiledicke", "")
                                result_text = f"AUTO: Platz={platz}  {laenge}x{breite}x{dicke}"
                                root.after(0, lambda t=result_text: (
                                    scan_result_var.set(t),
                                    scan_result_label.config(fg="blue"),
                                ))

                                # Assign drawer
                                try:
                                    drawer = int(platz) if platz else 0
                                except (ValueError, TypeError):
                                    drawer = 0

                                if drawer > 0:
                                    ok = plc.assign_drawer(drawer, part_count=1)
                                    if ok:
                                        plc.send_c2()
                                        log(f"[AUTO] -> Drawer {drawer} assigned OK")
                                    else:
                                        log(f"[AUTO] -> Drawer {drawer} FAILED")
                                else:
                                    log(f"[AUTO] -> No valid drawer (Abstapelplatz={platz})")
                            else:
                                log(f"[AUTO] -> NOT FOUND in DB: {type_nr}")

                            processed = True
                            break  # Process one row per cycle (PLC shifts up)

                    if not processed:
                        # Idle — send @H keepalive
                        plc.poll_status()

                except Exception as e:
                    log(f"[AUTO] Error: {e}")

                auto_plc_stop.wait(1.0)  # 1 second poll interval

            auto_plc_active = False
            root.after(0, lambda: auto_status_var.set("STOPPED"))
            root.after(0, lambda: auto_start_btn.config(state=tk.NORMAL))
            root.after(0, lambda: auto_stop_btn.config(state=tk.DISABLED))
            # Resume @H polling if PLC still connected
            if plc is not None and plc.sock is not None:
                plc.start_polling()
            log("[AUTO] === LagerPC auto-mode STOPPED ===")

        threading.Thread(target=_auto_loop, daemon=True).start()

    def do_stop_auto_plc():
        """Stop the automatic PLC polling loop."""
        nonlocal auto_plc_active
        if not auto_plc_active:
            return
        auto_plc_stop.set()
        log("[AUTO] Stopping...")

    # ── Barcode / QR scan lookup ────────────────────────────────────
    def do_scan_lookup(event=None):
        """Look up a scanned barcode/QR code in the Firebird DB via GET_TEILEDATEN."""
        if db is None:
            log("DB not connected — connect to Firebird first")
            return
        barcode = scan_var.get().strip()
        if not barcode:
            return
        try:
            cur = db.conn.cursor()
            cur.execute("EXECUTE PROCEDURE GET_TEILEDATEN ?", (barcode,))
            row = cur.fetchone()
            if cur.description:
                cols = [desc[0].strip() for desc in cur.description]
            else:
                cols = []
            cur.close()

            if row is None:
                log(f"[SCAN] No match for: {barcode}")
                scan_result_var.set(f"NOT FOUND: {barcode}")
                scan_result_label.config(fg="red")
            else:
                part = dict(zip(cols, row))
                teile_id = part.get("TeileID", "")
                laenge = part.get("Teilelaenge", "")
                breite = part.get("Teilebreite", "")
                dicke = part.get("Teiledicke", "")
                platz = part.get("Abstapelplatz", "")

                edge_info = []
                for k in range(1, 5):
                    ks = part.get(f"Kante{k} Status", 0)
                    kv = part.get(f"Kante{k}", 0)
                    if kv and kv != 0:
                        status_text = {0: "todo", 1: "ready", 2: "busy", 99: "done"}.get(ks, str(ks))
                        edge_info.append(f"K{k}={status_text}")

                result_text = f"Platz={platz}  {laenge}x{breite}x{dicke}  {' '.join(edge_info)}"
                scan_result_var.set(result_text)
                scan_result_label.config(fg="green")
                log(f"[SCAN] {barcode} -> TeileID={teile_id}  {result_text}")

                # Fill all TEILE Data entry fields with matched row
                for col_name, (entry, col_type) in fields.items():
                    entry.delete(0, tk.END)
                    val = part.get(col_name, "")
                    if val is not None and val != "":
                        entry.insert(0, str(val))

                # Send part data + drawer to Grundner Treturn PLC
                # No CBX100 — we provide dimensions via table 1 + drawer via table 22
                if plc is not None:
                    def _plc_send(p=part):
                        try:
                            was_polling = plc._polling
                            plc.stop_polling()

                            p_platz = p.get("Abstapelplatz", 0)
                            p_laenge = p.get("Teilelaenge", 0)
                            p_breite = p.get("Teilebreite", 0)
                            p_dicke = p.get("Teiledicke", 0)
                            p_type = p.get("TeileID", "")

                            # Table 1: part data so PLC knows dimensions for gripper
                            ok1 = plc.write_einlagern_row(
                                row=1,
                                type_nr=p_type,
                                length=p_laenge or 0,
                                width=p_breite or 0,
                                thickness=p_dicke or 0,
                                piece_count=1,
                                place=p_platz or 0,
                            )
                            if ok1:
                                log(f"[SCAN] -> PLC table 1: {p_type} {p_laenge}x{p_breite}x{p_dicke}")
                            else:
                                log(f"[SCAN] -> PLC table 1 FAILED")

                            # Table 22: drawer assignment
                            try:
                                drawer = int(p_platz) if p_platz else 0
                            except (ValueError, TypeError):
                                drawer = 0

                            if drawer > 0:
                                ok2 = plc.assign_drawer(drawer, part_count=1)
                                if ok2:
                                    plc.send_c2()
                                    log(f"[SCAN] -> PLC drawer {drawer} OK")
                                else:
                                    log(f"[SCAN] -> PLC drawer {drawer} FAILED")
                            else:
                                log(f"[SCAN] No valid drawer (Abstapelplatz={p_platz})")

                            if was_polling:
                                plc.start_polling()
                        except Exception as plc_err:
                            log(f"[SCAN] PLC error: {plc_err}")

                    threading.Thread(target=_plc_send, daemon=True).start()

        except Exception as e:
            log(f"[SCAN] Error looking up {barcode}: {e}")
            scan_result_var.set(f"ERROR: {e}")
            scan_result_label.config(fg="red")

        # Clear input and refocus for next scan
        scan_var.set("")
        scan_entry.focus_set()

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

    # --- Grundner Treturn PLC frame ---
    plc_frame = tk.LabelFrame(root, text="Grundner Treturn PLC (sorts parts to drawers)", padx=10, pady=5)
    plc_frame.pack(fill=tk.X, padx=10, pady=5)

    plc_conn_row = tk.Frame(plc_frame)
    plc_conn_row.pack(fill=tk.X)
    tk.Label(plc_conn_row, text="Host:").pack(side=tk.LEFT)
    plc_host_var = tk.StringVar(value="10.10.150.1")
    tk.Entry(plc_conn_row, textvariable=plc_host_var, width=16).pack(side=tk.LEFT, padx=5)
    tk.Label(plc_conn_row, text="Port:").pack(side=tk.LEFT, padx=(10, 0))
    plc_port_var = tk.StringVar(value="10001")
    tk.Entry(plc_conn_row, textvariable=plc_port_var, width=8).pack(side=tk.LEFT, padx=5)
    tk.Button(plc_conn_row, text="Connect", command=do_plc_connect, width=10).pack(side=tk.LEFT, padx=3)
    tk.Button(plc_conn_row, text="Disconnect", command=do_plc_disconnect, width=10).pack(side=tk.LEFT, padx=3)
    plc_status_var = tk.StringVar(value="Disconnected")
    tk.Label(plc_conn_row, textvariable=plc_status_var, fg="gray").pack(side=tk.LEFT, padx=10)

    plc_btn_row = tk.Frame(plc_frame)
    plc_btn_row.pack(fill=tk.X, pady=(3, 0))
    tk.Button(plc_btn_row, text="Safe Test", command=do_plc_safe_test, width=10,
              bg="#fff3cd").pack(side=tk.LEFT, padx=3)
    tk.Button(plc_btn_row, text="Read Einlagern", command=do_plc_read_einlagern, width=14).pack(side=tk.LEFT, padx=3)
    tk.Button(plc_btn_row, text="Read Drawers", command=do_plc_read_drawers, width=14).pack(side=tk.LEFT, padx=3)
    tk.Label(plc_btn_row, text="  Drawer:").pack(side=tk.LEFT, padx=(10, 2))
    plc_drawer_var = tk.StringVar()
    tk.Entry(plc_btn_row, textvariable=plc_drawer_var, width=4).pack(side=tk.LEFT, padx=2)
    tk.Button(plc_btn_row, text="Assign", command=do_plc_manual_assign, width=7,
              bg="#f8d7da").pack(side=tk.LEFT, padx=3)

    # Auto-mode row (LagerPC replacement)
    plc_auto_row = tk.Frame(plc_frame)
    plc_auto_row.pack(fill=tk.X, pady=(3, 0))
    tk.Label(plc_auto_row, text="LagerPC Auto-mode:", font=("Consolas", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
    auto_start_btn = tk.Button(plc_auto_row, text="Start Auto", command=do_start_auto_plc, width=10,
                               bg="#d4edda", font=("Consolas", 9, "bold"))
    auto_start_btn.pack(side=tk.LEFT, padx=3)
    auto_stop_btn = tk.Button(plc_auto_row, text="Stop Auto", command=do_stop_auto_plc, width=10,
                              bg="#f8d7da", font=("Consolas", 9, "bold"), state=tk.DISABLED)
    auto_stop_btn.pack(side=tk.LEFT, padx=3)
    auto_status_var = tk.StringVar(value="STOPPED")
    tk.Label(plc_auto_row, textvariable=auto_status_var, font=("Consolas", 9, "bold"), fg="gray").pack(side=tk.LEFT, padx=10)

    # --- Barcode / QR Scan frame ---
    scan_frame = tk.LabelFrame(root, text="Scan Lookup (USB scanner / manual entry)", padx=10, pady=5)
    scan_frame.pack(fill=tk.X, padx=10, pady=5)

    scan_input_frame = tk.Frame(scan_frame)
    scan_input_frame.pack(fill=tk.X)
    tk.Label(scan_input_frame, text="Barcode / QR:", font=("Consolas", 11)).pack(side=tk.LEFT)
    scan_var = tk.StringVar()
    scan_entry = tk.Entry(scan_input_frame, textvariable=scan_var, width=40, font=("Consolas", 14))
    scan_entry.pack(side=tk.LEFT, padx=10, ipady=4)
    scan_entry.bind("<Return>", do_scan_lookup)
    tk.Button(scan_input_frame, text="Lookup", command=do_scan_lookup, width=10,
              bg="#d4edda", font=("Consolas", 10)).pack(side=tk.LEFT, padx=5)

    scan_result_var = tk.StringVar(value="Scan a barcode or enter TeileID...")
    scan_result_label = tk.Label(scan_frame, textvariable=scan_result_var,
                                  font=("Consolas", 12, "bold"), fg="gray", anchor=tk.W)
    scan_result_label.pack(fill=tk.X, pady=(5, 0))

    # Auto-focus the scan field on startup
    root.after(200, scan_entry.focus_set)

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
    # Also capture HolzherTCP and GrundnerPLC logs
    logging.getLogger("HolzherTCP").addHandler(text_handler)
    logging.getLogger("HolzherTCP").setLevel(logging.DEBUG)
    logging.getLogger("GrundnerPLC").addHandler(text_handler)
    logging.getLogger("GrundnerPLC").setLevel(logging.DEBUG)

    def on_close():
        if auto_plc_active:
            do_stop_auto_plc()
        if polling_active:
            do_stop_polling()
        if plc is not None:
            do_plc_disconnect()
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
