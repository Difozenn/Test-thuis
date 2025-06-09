from flask import Flask, request, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'central_logging.sqlite')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
            user TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/log', methods=['POST'])
def log_event():
    data = request.get_json(force=True)
    event = data.get('event')
    details = data.get('details')
    user = data.get('user', 'unknown')
    timestamp = datetime.now().isoformat()
    if not event:
        return jsonify({'success': False, 'error': 'Missing event'}), 400
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO logs (timestamp, event, details, user) VALUES (?, ?, ?, ?)',
              (timestamp, event, details, user))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

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
    print('logs_html endpoint was called')
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 100')
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    html = '''
    <html>
    <head>
    <!-- DEBUG ADMIN BUTTON TEST -->
    <title>Central Logs</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f7f7f7; }
        table { border-collapse: collapse; width: 98%; margin: 20px auto; background: white; }
        th, td { border: 1px solid #aaa; padding: 8px 10px; text-align: left; }
        th { background: #e0e0e0; }
        tr:nth-child(even) { background: #f2f2f2; }
        caption { font-size: 1.2em; margin: 10px; font-weight: bold; }
    </style>
    </head>
    <body>
    <div style="margin:20px;">
        <input type="text" id="logSearch" onkeyup="filterLogs()" placeholder="Zoek in logs..." style="width:40%;padding:6px;font-size:1em;">
        <button id="adminToggle" onclick="toggleAdmin()" style="margin-left:20px;">ADMIN</button>
        <span id="adminStatus" style="margin-left:10px;color:#888;font-weight:bold;">(Debug logs verborgen)</span>
    </div>
    <table id="logsTable">
    <caption>Laatste 100 logs</caption>
    <tr><th>ID</th><th>Tijdstip</th><th>Event</th><th>Details</th><th>User</th></tr>
    '''
    from datetime import datetime
    for row in rows:
        # Format timestamp as 'YYYY-MM-DD HH:MM'
        ts = row["timestamp"]
        try:
            dt = datetime.fromisoformat(ts)
            ts_fmt = dt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            ts_fmt = ts or ''
        html += f'<tr>'
        html += f'<td>{row["id"]}</td>'
        html += f'<td>{ts_fmt}</td>'
        html += f'<td>{row["event"]}</td>'
        html += f'<td>{row["details"]}</td>'
        html += f'<td>{row["user"]}</td>'
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
    </script>

      var input = document.getElementById('logSearch');
      var filter = input.value.toLowerCase();
      var table = document.getElementById('logsTable');
      var trs = table.getElementsByTagName('tr');
      for (var i = 2; i < trs.length; i++) { // skip header and caption
        var rowText = trs[i].textContent.toLowerCase();
        if (rowText.indexOf(filter) > -1) {
          trs[i].style.display = '';
        } else {
          trs[i].style.display = 'none';
        }
      }
    }
    </script>
    </body></html>
    '''
    return html

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
