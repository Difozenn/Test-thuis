from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
import json
import os
from datetime import datetime
import logging
from flask import g

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

def create_db_connection():
    """Creates and returns a new database connection."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    return conn

def get_db():
    """
    Opens a new database connection if there is none yet for the current
    application context.
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = create_db_connection()
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database again at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database and ensures the schema is up to date."""
    logging.info(f"Initializing database at {DB_PATH}")
    conn = None  # Initialize conn to None
    try:
        conn = create_db_connection()  # Use direct connection for init
        c = conn.cursor()
        # Create table if it doesn't exist
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
                is_rep_variant INTEGER,
                file_path TEXT
            )
        ''')
        
        # Check and add columns if they don't exist
        c.execute("PRAGMA table_info(logs)")
        columns = [column[1] for column in c.fetchall()]
        if 'base_mo_code' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN base_mo_code TEXT')
            logging.info("Added 'base_mo_code' column to logs table.")
        if 'is_rep_variant' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN is_rep_variant INTEGER')
            logging.info("Added 'is_rep_variant' column to logs table.")
        if 'file_path' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN file_path TEXT')
            logging.info("Added 'file_path' column to logs table.")
        
        conn.commit()
        logging.info("Database initialization complete.")
    except Exception as e:
        logging.error(f"Error during database initialization: {e}", exc_info=True)
    finally:
        if conn:
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

# Database is initialized in run_api_server to avoid running on import.

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
    file_path = data.get('file_path', '') # Default to empty string if not provided
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
            'INSERT INTO logs (timestamp, event, details, project, user, status, base_mo_code, is_rep_variant, file_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (timestamp, event, details, project, user, status, base_mo_code, is_rep_variant, file_path)
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Log entry created.'}), 201
    except sqlite3.Error as e:
        logging.error(f"Database error on /log: {e}", exc_info=True)
        return jsonify({'error': 'Database operation failed'}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    project = request.args.get('project')
    # If 'project' is not provided, we will fetch all logs.
    # The client-side will filter by user.

    try:
        conn = get_db()
        c = conn.cursor()
        if project:
            c.execute('SELECT * FROM logs WHERE project = ? ORDER BY id DESC', (project,))
        else:
            # Fetch all logs if no specific project is requested, similar to logs_html
            # The client panel (DatabasePanel) already filters by user.
            c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 500')
        rows = c.fetchall()
        return jsonify([dict(row) for row in rows])
    except sqlite3.Error as e:
        logging.error(f"Database error on GET /logs: {e}", exc_info=True)
        return jsonify({'error': 'Failed to retrieve logs'}), 500

@app.route('/logs/count', methods=['GET'])
def get_logs_count():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM logs')
        count = c.fetchone()[0]
        return jsonify({'success': True, 'count': count})
    except sqlite3.Error as e:
        logging.error(f"Database error on GET /logs/count: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to retrieve log count'}), 500

@app.route('/delete_log/<int:log_id>', methods=['POST'])
def delete_log(log_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM logs WHERE id = ?', (log_id,))
        conn.commit()
        if c.rowcount > 0:
            logging.info(f"Log ID {log_id} deleted successfully.")
            return jsonify({'success': True, 'message': f'Log ID {log_id} deleted.'})
        else:
            return jsonify({'success': False, 'error': 'Log ID not found.'}), 404
    except sqlite3.Error as e:
        logging.error(f"Failed to delete log ID {log_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Database error.'}), 500

@app.route('/clear_logs', methods=['POST'])
def clear_all_logs():
    logging.info("[db_log_api] /clear_logs POST request received.")
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM logs')
        conn.commit()
        # For DELETE without WHERE, rowcount might not be indicative of actual rows deleted in all SQLite versions
        # or could be -1. It's safer to just log the action.
        logging.info(f"DELETE FROM logs statement executed successfully.")
        return jsonify({'success': True, 'message': 'All logs cleared successfully.'}), 200
    except sqlite3.Error as e:
        logging.error(f"Database error on /clear_logs: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Database operation failed to clear logs.'}), 500


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

        # --- Logic for user-specific project status ---
        # This query gets the last 10 'OPEN' or 'AFGEMELD' projects for each user.
        user_projects_query = """
            WITH RankedLogs AS (
                SELECT
                    user,
                    project,
                    status,
                    timestamp,
                    ROW_NUMBER() OVER(PARTITION BY user ORDER BY timestamp DESC) as rn
                FROM
                    logs
                WHERE
                    status IN ('OPEN', 'AFGEMELD') AND user IS NOT NULL AND user != ''
            )
            SELECT
                user,
                project as project_code,
                status,
                timestamp
            FROM
                RankedLogs
            WHERE
                rn <= 10
            ORDER BY
                user,
                CASE status WHEN 'OPEN' THEN 1 WHEN 'AFGEMELD' THEN 2 ELSE 3 END,
                timestamp DESC;
        """
        c.execute(user_projects_query)
        user_project_rows = c.fetchall()

        # Define the desired order for user frames
        user_order = ['NESTING', 'OPUS', 'KL GANNOMAT']
        
        # Get all unique users from the database to handle cases where a user might not have recent projects
        c.execute("SELECT DISTINCT user FROM logs WHERE user IS NOT NULL AND user != ''")
        db_users = {row['user'] for row in c.fetchall()}
        
        # Create a sorted list of users based on the desired order, including any extra users from the DB
        sorted_unique_users = sorted(db_users, key=lambda u: user_order.index(u) if u in user_order else len(user_order))

        # Initialize users_projects with the sorted user order
        users_projects = {user: [] for user in sorted_unique_users}

        for row in user_project_rows:
            row_dict = dict(row)
            user = row_dict['user']
            
            # Format timestamp for display
            try:
                dt = datetime.fromisoformat(row_dict['timestamp'])
                row_dict['timestamp'] = dt.strftime('%d-%m %H:%M:%S')
            except (ValueError, TypeError):
                pass  # Keep original string if format is wrong

            if user in users_projects:
                users_projects[user].append(row_dict)

        # --- Fetch all unique project codes for the search datalist ---
        c.execute("SELECT DISTINCT project FROM logs WHERE project IS NOT NULL AND project != '' ORDER BY project")
        all_projects = [row['project'] for row in c.fetchall()]

        # --- Fetch all logs for the bottom table ---
        c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 500')
        all_logs_rows = c.fetchall()
        
        logs = []
        for row in all_logs_rows:
            log_dict = dict(row)
            try:
                # Format timestamp for display consistency
                dt = datetime.fromisoformat(log_dict['timestamp'])
                log_dict['timestamp'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                pass
            logs.append(log_dict)

        return render_template('logs_html.html', users_projects=users_projects, logs=logs, all_projects=all_projects)

    except Exception as e:
        logging.error(f"Failed to render logs_html: {e}", exc_info=True)
        if "no such function: ROW_NUMBER" in str(e):
            return render_template('error.html', message='Database version is too old and does not support required features (ROW_NUMBER).'), 500
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

        order = {'NESTING': 0, 'OPUS': 1, 'GANNOMAT': 2}
        def user_sort_key(row):
            user = dict(row).get('user', '')
            return order.get(user, 99), user
        
        sorted_user_status = sorted(user_status_rows, key=user_sort_key)

        user_status_html = '<table><thead><tr><th>User</th><th>Status</th><th>Last Updated</th></tr></thead><tbody>'
        for row_data in sorted_user_status:
            row = dict(row_data)
            status = row.get('status', '')
            status_class = f"status-{status.lower()}" if status else ""
            last_updated_str = row.get('last_updated', '')
            try:
                dt = datetime.fromisoformat(last_updated_str)
                last_updated_fmt = dt.strftime('%d-%m %H:%M')
            except (ValueError, TypeError):
                last_updated_fmt = last_updated_str or ''
            user_status_html += f'<tr><td>{row.get("user", "")}</td><td class="{status_class}">{status}</td><td>{last_updated_fmt}</td></tr>'
        user_status_html += '</tbody></table>'

        # Fetch all unique project codes for the search datalist
        c.execute("SELECT DISTINCT project FROM logs WHERE project IS NOT NULL AND project != '' ORDER BY project")
        all_projects = [row['project'] for row in c.fetchall()]

        return render_template('logs_project.html', 
                               project=project, 
                               log_entries=log_entries, 
                               user_status_html=user_status_html,
                               all_projects=all_projects)

    except Exception as e:
        logging.error(f"An unexpected error occurred during database initialization: {e}", exc_info=True)
        raise



@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Production Server Setup ---
def run_api_server(host='0.0.0.0', port=5000):
    init_db()  # Initialize database once when the server starts
    from waitress import serve
    print(f"Starting database API server on http://{host}:{port}")
    serve(app, host=host, port=port)

if __name__ == '__main__':
    run_api_server()
