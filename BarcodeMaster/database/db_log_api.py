from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
import json
import os
from datetime import datetime
import logging

# --- Setup logging to file and console ---
log_dir = os.path.dirname(__file__)
log_path = os.path.join(log_dir, 'db_log_api.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# --- Flask App Setup ---
# Use the 'templates' directory in the same folder as this script
template_dir = os.path.abspath(os.path.join(log_dir, 'templates'))
app = Flask(__name__, template_folder=template_dir)

# --- Database Setup ---
DB_PATH = os.path.join(log_dir, 'central_logging.sqlite')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    return conn

def init_db():
    logging.info(f"Initializing database at {DB_PATH}")
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
            status TEXT,
            base_mo_code TEXT,
            is_rep_variant INTEGER
        )
    ''')
    conn.commit()

    try:
        c.execute("PRAGMA table_info(logs)")
        columns = [column[1] for column in c.fetchall()]
        if 'base_mo_code' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN base_mo_code TEXT')
            logging.info("Added 'base_mo_code' column to logs table.")
        if 'is_rep_variant' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN is_rep_variant INTEGER')
            logging.info("Added 'is_rep_variant' column to logs table.")
        conn.commit()
    except Exception as e:
        logging.error(f"Error adding columns to logs table: {e}")
    finally:
        conn.close()

# --- API Endpoints ---
@app.route('/init_db', methods=['POST'])
def initialize_database_endpoint():
    try:
        init_db()
        logging.info("[db_log_api] /init_db called, database initialized/verified.")
        return jsonify({'success': True, 'message': 'Database initialized successfully.'}), 200
    except Exception as e:
        logging.error(f"[db_log_api] /init_db failed: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/log', methods=['POST', 'GET'])
def log_event():
    data = request.get_json(force=True) if request.method == 'POST' else request.args
    logging.info(f"[db_log_api] /log called with data: {data}")

    event = data.get('event')
    if not event:
        return jsonify({'success': False, 'error': 'Missing event'}), 400

    user = data.get('user', 'unknown')
    if event == 'test_connect':
        logging.info(f"  [INFO] Received test_connect from user '{user}'. Connection successful.")
        return jsonify({'success': True})

    details = data.get('details')
    project = data.get('project', '')
    base_mo_code = data.get('base_mo_code', '')
    is_rep_variant = 1 if data.get('is_rep_variant', False) else 0
    timestamp = datetime.now().isoformat()
    status = ''

    try:
        conn = get_db()
        c = conn.cursor()

        if event == 'OPEN':
            status = 'OPEN'
        elif event == 'AFGEMELD':
            status = 'AFGEMELD'
            # Find the corresponding 'OPEN' log and update its status to 'CLOSED'
            c.execute(
                'UPDATE logs SET status = ? WHERE event = ? AND status = ? AND lower(project) = ? AND user = ?',
                ('CLOSED', 'OPEN', 'OPEN', project.lower(), user)
            )
            if c.rowcount > 0:
                logging.info(f"Closed {c.rowcount} 'OPEN' log(s) for user '{user}' on project '{project}'.")

        c.execute(
            'INSERT INTO logs (timestamp, event, details, project, user, status, base_mo_code, is_rep_variant) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (timestamp, event, details, project, user, status, base_mo_code, is_rep_variant)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True}), 201
    except sqlite3.Error as e:
        logging.error(f"Database error on /log: {e}", exc_info=True)
        return jsonify({'error': 'Database operation failed'}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    project = request.args.get('project')
    if not project:
        return jsonify({'error': 'Project parameter is required'}), 400

    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM logs WHERE project = ? ORDER BY id DESC', (project,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    except sqlite3.Error as e:
        logging.error(f"Database error on GET /logs: {e}", exc_info=True)
        return jsonify({'error': 'Failed to retrieve logs'}), 500

@app.route('/delete_log/<int:log_id>', methods=['POST'])
def delete_log(log_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM logs WHERE id = ?', (log_id,))
        conn.commit()
        conn.close()
        if c.rowcount > 0:
            logging.info(f"Log ID {log_id} deleted successfully.")
            return jsonify({'success': True, 'message': f'Log ID {log_id} deleted.'})
        else:
            return jsonify({'success': False, 'error': 'Log ID not found.'}), 404
    except sqlite3.Error as e:
        logging.error(f"Failed to delete log ID {log_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Database error.'}), 500

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# --- HTML Serving Endpoints ---
@app.route('/logs_html', methods=['GET'])
def logs_html():
    logging.info('logs_html endpoint was called')
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 500')
        rows = c.fetchall()
        conn.close()
        log_entries = [dict(row) for row in rows]
        return render_template('logs_html.html', log_entries=log_entries)
    except Exception as e:
        logging.error(f"Failed to render logs_html: {e}", exc_info=True)
        return render_template('error.html', message='Could not retrieve logs from the database.'), 500

@app.route('/logs_project')
def logs_project():
    project = request.args.get('project', '')
    if not project:
        return render_template('error.html', message='Project parameter is missing.'), 400

    logging.info(f"logs_project endpoint called for project: '{project}'")
    try:
        conn = get_db()
        c = conn.cursor()

        c.execute('SELECT * FROM logs WHERE lower(project) = ? ORDER BY id DESC', (project.lower(),))
        log_entries = [dict(row) for row in c.fetchall()]

        c.execute('''
            SELECT user, status, MAX(timestamp) as last_updated
            FROM logs WHERE lower(project) = ? AND user != '' GROUP BY user
        ''', (project.lower(),))
        user_status_rows = c.fetchall()
        conn.close()

        order = {'NESTING': 0, 'OPUS': 1, 'GANNOMAT': 2}
        def user_sort_key(row):
            user = dict(row).get('user', '')
            return order.get(user, 99), user
        
        sorted_user_status = sorted(user_status_rows, key=user_sort_key)

        user_status_html = '<table><thead><tr><th>User</th><th>Status</th><th>Last Updated</th></tr></thead><tbody>'
        for row_data in sorted_user_status:
            row = dict(row_data)
            status = row.get('status', '')
            if status == 'OPEN':
                status = f'<b>{status}</b>'
            last_updated_str = row.get('last_updated', '')
            try:
                dt = datetime.fromisoformat(last_updated_str)
                last_updated_fmt = dt.strftime('%d-%m %H:%M')
            except (ValueError, TypeError):
                last_updated_fmt = last_updated_str or ''
            user_status_html += f'<tr><td>{row.get("user", "")}</td><td>{status}</td><td>{last_updated_fmt}</td></tr>'
        user_status_html += '</tbody></table>'

        return render_template('logs_project.html', 
                               project=project, 
                               log_entries=log_entries, 
                               user_status_html=user_status_html)

    except Exception as e:
        logging.error(f"An unexpected error occurred on /logs_project for {project}: {e}", exc_info=True)
        return render_template('error.html', message='An unexpected error occurred.'), 500


if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        logging.info("Database not found at startup. Initializing...")
        init_db()
    else:
        logging.info("Database found at startup.")

    try:
        logging.info("Starting Flask application...")
        app.run(host='0.0.0.0', port=5001)
    except Exception as e:
        logging.critical(f"CRITICAL: Failed to start Flask app: {e}", exc_info=True)
