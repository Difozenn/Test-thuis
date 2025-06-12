from flask import Flask, request, jsonify
import sqlite3
import os
from datetime import datetime
import logging

# --- Setup logging to file and console ---
log_path = os.path.join(os.path.dirname(__file__), 'db_log_api.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
# Construct the absolute path to the database file
# This assumes the script is in a subdirectory of the project root.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(project_root, 'database', 'central_logging.sqlite')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            event TEXT,
            details TEXT,
            project TEXT,
            user TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()


@app.route('/init_db', methods=['POST'])
def initialize_database_endpoint():
    try:
        init_db() # Call the existing local init_db function
        logging.info("[db_log_api] /init_db called, database initialized/verified.")
        return jsonify({'success': True, 'message': 'Database initialized successfully.'}), 200
    except Exception as e:
        logging.error(f"[db_log_api] /init_db failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/log', methods=['POST'])
def log_event():
    import traceback
    data = request.get_json(force=True)
    logging.info("[db_log_api] /log called with data:", data)
    event = data.get('event')
    details = data.get('details')
    project = data.get('project', '')
    user = data.get('user', 'unknown')
    timestamp = datetime.now().isoformat()
    if not event:
        logging.info("  [ERROR] Missing event field!")
        return jsonify({'success': False, 'error': 'Missing event'}), 400
    try:
        conn = get_db()
        c = conn.cursor()
        status = ''
        if event == 'OPEN':
            status = 'OPEN'
        elif event == 'AFGEMELD':
            status = 'AFGEMELD'
            # Check if any relevant OPEN logs exist for this project and user
            try:
                c.execute('SELECT id, project, user FROM logs WHERE event = ? AND status = ? AND project IS NOT NULL AND user IS NOT NULL', ('OPEN', 'OPEN'))
                open_logs = c.fetchall()
                matched_project_case = project  # Default to incoming case
                found_open = False
                for row in open_logs:
                    db_project = row['project'] if isinstance(row, sqlite3.Row) else row[1]
                    db_user = row['user'] if isinstance(row, sqlite3.Row) else row[2]
                    if db_project and db_project.lower() == project.lower() and db_user == user:
                        c.execute('UPDATE logs SET status = ? WHERE id = ?', ('AFGEMELD', row['id']))
                        matched_project_case = db_project  # Use the case from the matched OPEN event
                        found_open = True
                project = matched_project_case
                conn.commit()
                if not found_open:
                    # Check if all relevant logs are already closed
                    c.execute('SELECT COUNT(*) FROM logs WHERE project IS NOT NULL AND user IS NOT NULL AND lower(project) = ? AND user = ? AND status = ?', (project.lower(), user, 'AFGEMELD'))
                    closed_count = c.fetchone()[0]
                    if closed_count > 0:
                        logging.info(f"  [INFO] AFGEMELD event ignored: project '{project}' for user '{user}' already closed.")
                        conn.close()
                        return jsonify({'success': False, 'error': 'Project already closed', 'already_closed': True}), 200
            except Exception as e:
                logging.info(f"  [EXCEPTION] Failed to update OPEN logs to AFGEMELD: {e}")
        c.execute('INSERT INTO logs (timestamp, event, details, project, status, user) VALUES (?, ?, ?, ?, ?, ?)',
                  (timestamp, event, details, project, status, user))
        conn.commit()
        conn.close()
        logging.info("  [SUCCESS] Log entry inserted.")
        return jsonify({'success': True})
    except Exception as e:
        logging.info("  [EXCEPTION] Failed to insert log entry!")
        logging.info(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete_log/<int:log_id>', methods=['POST'])
def delete_log_entry(log_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM logs WHERE id = ?', (log_id,))
        conn.commit()
        conn.close()
        logging.info(f"[db_log_api] Log entry with id {log_id} deleted.")
        return jsonify({'success': True, 'message': f'Log entry {log_id} deleted successfully.'}), 200
    except Exception as e:
        logging.error(f"[db_log_api] Failed to delete log entry {log_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 100')
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/logs_html', methods=['GET'])
def logs_html():
    logging.info('logs_html endpoint was called')
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 100')
    rows = c.fetchall()

    # --- Project search logic ---
    search_query = request.args.get('q', '').strip()
    project_results_frame = ''
    if search_query:
        # Get all unique projects matching the search (case-insensitive)
        c2 = conn.cursor()
        c2.execute('SELECT DISTINCT project FROM logs WHERE project IS NOT NULL AND project != ""')
        all_projects = [r[0] for r in c2.fetchall()]
        matches = [p for p in all_projects if search_query.lower() in p.lower()]
        if matches:
            project_results_frame = '<div style="margin:20px;margin-bottom:0;">'
            project_results_frame += '<b>Projecten gevonden:</b><br>'
            project_results_frame += '<table border="1" style="margin-top:8px;width:60%;background:white;"><tr><th>Project</th></tr>'
            for p in matches:
                project_results_frame += f'<tr><td><a href="/logs_project?project={p}">{p}</a></td></tr>'
            project_results_frame += '</table></div>'
        else:
            project_results_frame = '<div style="margin:20px;color:#a00;">Geen projecten gevonden.</div>'
    html = f'''
    <html>
    <head>
    <title>Central Logs</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f7f7f7; }}
        table {{ border-collapse: collapse; width: 98%; margin: 20px auto; background: white; }}
        th, td {{ border: 1px solid #aaa; padding: 8px 10px; text-align: left; }}
        th {{ background: #e0e0e0; }}
        tr:nth-child(even) {{ background: #f2f2f2; }}
        caption {{ font-size: 1.2em; margin: 10px; font-weight: bold; }}
    </style>
    </head>
    <body>
    <form method="get" style="margin:20px;">
        <input type="text" name="q" value="{search_query}" placeholder="Zoek in projectnamen..." style="width:40%;padding:6px;font-size:1em;">
        <button type="submit" style="margin-left:8px;">Zoeken</button>
        <button id="adminToggle" type="button" onclick="toggleAdmin()" style="margin-left:20px;">ADMIN</button>
        <span id="adminStatus" style="margin-left:10px;color:#888;font-size:0.98em;"></span>
    </form>
    {project_results_frame}
    <table id="logsTable">
    <caption>Laatste 100 logs</caption>
    <tr><th>ID</th><th>Tijdstip</th><th>Event</th><th>Details</th><th>Project</th><th>Status</th><th>User</th><th>Acties</th></tr>
    '''
    from datetime import datetime
    import os, re
    for row in rows:
        # Format timestamp as 'YYYY-MM-DD HH:MM'
        ts = row["timestamp"]
        try:
            dt = datetime.fromisoformat(ts)
            ts_fmt = dt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            ts_fmt = ts or ''
        details = row["details"]
        if row["event"] == "AFGEMELD" and details and details.startswith("Project "):
            match = re.match(r"Project (.+?) gesloten op .+", details)
            if match:
                filename = os.path.splitext(os.path.basename(match.group(1)))[0]
                details = filename
        html += f'<tr>'
        html += f'<td>{row["id"]}</td>'
        html += f'<td>{ts_fmt}</td>'
        event_display = 'AFGEMELD' if row["event"] == "AFGEMELD" else row["event"]
        html += f'<td>{event_display}</td>'
        html += f'<td>{details}</td>'
        # Robust project/status access for sqlite3.Row, dict, or tuple
        if isinstance(row, dict):
            project_val = row.get('project', '')
            status_val = row.get('status', '')
        elif hasattr(row, 'keys') and callable(row.keys):
            project_val = row['project']
            status_val = row['status']
        elif isinstance(row, tuple):
            project_val = row[4] if len(row) > 4 else ''
            status_val = row[5] if len(row) > 5 else ''
        else:
            project_val = ''
            status_val = ''
        if project_val:
            html += f'<td><a href="/logs_project?project={project_val}">{project_val}</a></td>'
        else:
            html += f'<td></td>'
        html += f'<td>{status_val}</td>'
        html += f'<td>{row["user"]}</td>'
        html += f'<td><button onclick="deleteLog({row["id"]})" style="padding:3px 6px; font-size:0.9em; cursor:pointer;">Verwijder</button></td>'
        html += '</tr>'
    html += "</table>"
    html += '''
    <script>
    let adminMode = false;
    function toggleAdmin() {
        adminMode = !adminMode;
        document.getElementById('adminStatus').textContent = adminMode ? '(Debug logs zichtbaar)' : '(Debug logs verborgen)';
        filterLogs();
    }
    function filterLogs() {
        let input = document.getElementById('logSearch');
        let filter = input.value.toLowerCase();
        let table = document.getElementById('logsTable');
        let tr = table.getElementsByTagName('tr');
        for (let i = 1; i < tr.length; i++) { // skip header row
            let tdEvent = tr[i].getElementsByTagName('td')[2]; // Event column
            let tdDetails = tr[i].getElementsByTagName('td')[3];
            let tdUser = tr[i].getElementsByTagName('td')[4];
            let show = true;
            if (tdEvent && tdDetails && tdUser) {
                let rowText = (tr[i].textContent || tr[i].innerText).toLowerCase();
                // Hide debug events if not in admin mode
                let eventVal = tdEvent.textContent || tdEvent.innerText;
                if (!adminMode && (eventVal === 'test_connect' || eventVal === 'test_event')) {
                    show = false;
                }
                if (filter && rowText.indexOf(filter) === -1) {
                    show = false;
                }
                tr[i].style.display = show ? '' : 'none';
            }
        }
    }
    // Initial filter on load
    window.onload = function() { filterLogs(); };

    function deleteLog(logId) {
        if (confirm('Weet u zeker dat u dit log wilt verwijderen (ID: ' + logId + ')?')) {
            fetch('/delete_log/' + logId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Log verwijderd!');
                    // Remove the row from the table or reload
                    // For simplicity, we reload. For better UX, remove the row directly.
                    location.reload();
                } else {
                    alert('Fout bij verwijderen log: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Fout bij verwijderen log.');
            });
        }
    }
    </script>
    </body>
    </html>
    '''
    conn.close()
    return html

import traceback

@app.errorhandler(Exception)
def handle_exception(e):
    tb = traceback.format_exc()
    logging.error(f"[Flask ERROR] {tb}")
    return f'<h2>Internal Server Error</h2><pre>{tb}</pre>', 500

@app.route('/logs_project')
def logs_project():
    project = request.args.get('project', '')
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM logs WHERE project = ? ORDER BY id DESC', (project,))
    rows = c.fetchall()
    conn.close()
    html = '''
    <html>
    <head>
    <title>Logs voor project {project}</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f7f7f7; }}
        table {{ border-collapse: collapse; width: 98%; margin: 20px auto; background: white; }}
        th, td {{ border: 1px solid #aaa; padding: 8px 10px; text-align: left; }}
        th {{ background: #e0e0e0; }}
        tr:nth-child(even) {{ background: #f2f2f2; }}
        caption {{ font-size: 1.2em; margin: 10px; font-weight: bold; }}
    </style>
    </head>
    <body>
    <div style="margin:20px;">
        <a href="/logs_html">&larr; Terug naar alle logs</a>
    </div>
    <table id="logsTable">
    <caption>Logs voor project: {project}</caption>
    <tr><th>ID</th><th>Tijdstip</th><th>Event</th><th>Details</th><th>Project</th><th>Status</th><th>User</th></tr>'''.format(project=project)
    from datetime import datetime
    import os, re
    for row in rows:
        try:
            # row is sqlite3.Row, dict, or tuple
            if isinstance(row, dict):
                project_val = row.get('project', '')
            elif hasattr(row, 'keys') and callable(row.keys):
                project_val = row['project']
            elif isinstance(row, tuple):
                project_val = row[4] if len(row) > 4 else ''
            else:
                project_val = ''
        except Exception:
            project_val = ''
        ts = row["timestamp"]
        try:
            dt = datetime.fromisoformat(ts)
            ts_fmt = dt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            ts_fmt = ts or ''
        details = row["details"]
        html += f'<tr>'
        html += f'<td>{row["id"]}</td>'
        html += f'<td>{ts_fmt}</td>'
        html += f'<td>{row["event"]}</td>'
        html += f'<td>{details}</td>'
        html += f'<td>{project}</td>'
        # Robust status access for sqlite3.Row, dict, or tuple
        if isinstance(row, dict):
            status_val = row.get('status', '')
        elif hasattr(row, 'keys') and callable(row.keys):
            status_val = row['status']
        elif isinstance(row, tuple):
            status_val = row[5] if len(row) > 5 else ''
        else:
            status_val = ''
        html += f'<td>{status_val}</td>'
        html += f'<td>{row["user"]}</td>'
        html += '</tr>'
    html += "</table>"

    # --- Per-user status table ---
    conn2 = get_db()
    c2 = conn2.cursor()
    c2.execute('''
        SELECT user, status, MAX(timestamp) as last_updated
        FROM logs
        WHERE project = ?
        GROUP BY user
    ''', (project,))
    user_status_rows = c2.fetchall()
    # Defensive: fetch as dicts if possible
    try:
        desc = [d[0] for d in c2.description]
        user_status_dicts = [dict(zip(desc, row)) for row in user_status_rows]
    except Exception:
        user_status_dicts = user_status_rows
    # Build the per-user status table as HTML string
    # Static sort order: NESTING > OPUS > GANNOMAT > others
    def user_sort_key(row):
        user = row['user'] if isinstance(row, dict) else row[0]
        order = {'NESTING': 0, 'OPUS': 1, 'GANNOMAT': 2}
        return order.get(user, 3), user
    sorted_user_status = sorted(user_status_dicts, key=user_sort_key)
    user_status_table = f'''<h3>Status per gebruiker voor project: {project}</h3>
    <table id="userStatusTable" border="1">
        <thead><tr><th>User</th><th>Latest Status</th><th>Last Updated</th></tr></thead>
        <tbody>
    '''
    for row in sorted_user_status:
        try:
            user = row['user'] if isinstance(row, dict) else row[0]
            status = row['status'] if isinstance(row, dict) else row[1]
            last_updated = row['last_updated'] if isinstance(row, dict) else row[2]
            # Format last_updated like Tijdstip
            try:
                dt = datetime.fromisoformat(last_updated)
                last_updated_fmt = dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                last_updated_fmt = last_updated or ''
        except Exception:
            user, status, last_updated_fmt = '', '', ''
        user_status_table += f'<tr><td>{user}</td><td>{status}</td><td>{last_updated_fmt}</td></tr>'
    user_status_table += '</tbody></table>'

    # --- Main logs table ---
    # Place '← Terug naar alle logs' at the very top
    top_link = '<a href="/logs_html" style="font-size:16px;display:inline-block;margin-bottom:14px;">&larr; Terug naar alle logs</a><br>'
    html = top_link + user_status_table + "<br>" + html
    return html


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001)
