from flask import Flask, request, jsonify, render_template, send_from_directory, make_response, send_file
import sqlite3
import json
import os
from datetime import datetime, timedelta
import logging
from flask import g
import shutil
import csv
import io
import threading
import sys
from datetime import datetime, timedelta, date
from sqlalchemy import func
from sqlalchemy.orm import Session

# Add project root to path to allow imports from sibling directories
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import path utilities for proper path handling
from path_utils import get_writable_path, get_resource_path

# --- Setup logging to writable location ---
log_dir = get_writable_path('database')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'db_log_api.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# --- Service Imports ---
from services.background_import_service import BackgroundImportService

# --- Flask App Setup ---
# Use the 'templates' directory in the same folder as this script
template_dir = get_resource_path('database/templates')
app = Flask(__name__, template_folder=template_dir)

# --- Service Initialization ---
background_service = BackgroundImportService()

# --- Global shutdown control ---
_server_thread = None
_shutdown_requested = False
_server = None

def stop_api_server():
    """Stop the running API server."""
    global _shutdown_requested, _server
    _shutdown_requested = True
    logging.info("Shutdown requested for DB API server")
    
    # If using waitress server, shut it down
    if _server:
        try:
            _server.close()
            logging.info("Waitress server closed")
        except Exception as e:
            logging.error(f"Error closing waitress server: {e}")
    
    # Try to trigger Flask shutdown via request (development server)
    try:
        import requests
        requests.get('http://localhost:5001/shutdown', timeout=1)
    except:
        pass

# --- Database Setup ---
DB_PATH = get_writable_path('database/central_logging.sqlite')

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
    # Ensure database directory exists
    db_dir = os.path.dirname(DB_PATH)
    os.makedirs(db_dir, exist_ok=True)
    
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
                file_path TEXT,
                item_count INTEGER
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
        if 'item_count' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN item_count INTEGER')
            logging.info("Added 'item_count' column to logs table.")
        
        conn.commit()
        logging.info("Database initialization complete.")
    except Exception as e:
        logging.error(f"Error during database initialization: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

# --- Helper function to format minutes ---
def format_minutes(minutes):
    """Format minutes into a readable string."""
    if minutes is None:
        return '-'
    
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    
    if hours > 0:
        return f"{hours}u {mins}m"
    else:
        return f"{mins}m"

# --- Shutdown endpoint ---
@app.route('/shutdown', methods=['GET', 'POST'])
def shutdown():
    if _shutdown_requested:
        func = request.environ.get('werkzeug.server.shutdown')
        if func:
            func()
            return 'Server shutting down...', 200
        return 'Server shutdown initiated', 200
    return 'Shutdown not requested', 403

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
    file_path = data.get('file_path', '') # Default to empty string if not provided
    item_count = data.get('item_count', None)  # New field
    timestamp = datetime.now().isoformat()
    status = ''

    try:
        conn = get_db()
        c = conn.cursor()

        if event == 'OPEN':
            status = 'OPEN'
            # Trigger the background import service for OPUS/GANNOMAT processing
            # This is done after the initial log is committed.
            # The service itself runs its tasks in separate threads.
            logging.info(f"Event OPEN received for {user} on {project}. Triggering background import service.")
            background_service.trigger_import_for_event(
                user_type=user,
                project_code=project,
                event_details=details,
                timestamp=timestamp
            )
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
            'INSERT INTO logs (timestamp, event, details, project, user, status, base_mo_code, is_rep_variant, file_path, item_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (timestamp, event, details, project, user, status, base_mo_code, is_rep_variant, file_path, item_count)
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Log entry created.'}), 201
    except sqlite3.Error as e:
        logging.error(f"Database error on /log: {e}", exc_info=True)
        return jsonify({'error': 'Database operation failed'}), 500

@app.route('/update_file_path', methods=['POST'])
def update_file_path():
    """Update the file_path for an existing OPEN event."""
    data = request.get_json(force=True)
    logging.info(f"[db_log_api] /update_file_path called with data: {data}")

    project = data.get('project')
    user = data.get('user')
    file_path = data.get('file_path')
    
    if not all([project, user, file_path]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    try:
        conn = get_db()
        c = conn.cursor()
        
        # Update the most recent OPEN event for this user/project combination
        c.execute('''
            UPDATE logs 
            SET file_path = ? 
            WHERE id = (
                SELECT id FROM logs 
                WHERE event = 'OPEN' 
                AND status = 'OPEN' 
                AND user = ? 
                AND project = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            )
        ''', (file_path, user, project))
        
        conn.commit()
        
        if c.rowcount > 0:
            logging.info(f"Updated file_path for OPEN event: user={user}, project={project}, path={file_path}")
            return jsonify({'success': True, 'message': 'File path updated successfully'}), 200
        else:
            logging.warning(f"No OPEN event found to update for user={user}, project={project}")
            return jsonify({'success': False, 'error': 'No matching OPEN event found'}), 404
            
    except sqlite3.Error as e:
        logging.error(f"Database error on /update_file_path: {e}", exc_info=True)
        return jsonify({'error': 'Database operation failed'}), 500

@app.route('/update_item_count', methods=['POST'])
def update_item_count():
    """Update the item_count for an existing OPEN event."""
    data = request.get_json(force=True)
    logging.info(f"[db_log_api] /update_item_count called with data: {data}")

    project = data.get('project')
    user = data.get('user')
    item_count = data.get('item_count', 0)
    
    if not all([project, user]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    try:
        conn = get_db()
        c = conn.cursor()
        
        # Update the most recent OPEN event for this user/project combination
        c.execute('''
            UPDATE logs 
            SET item_count = ? 
            WHERE id = (
                SELECT id FROM logs 
                WHERE event = 'OPEN' 
                AND status = 'OPEN' 
                AND user = ? 
                AND project = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            )
        ''', (item_count, user, project))
        
        conn.commit()
        
        if c.rowcount > 0:
            logging.info(f"Updated item_count for OPEN event: user={user}, project={project}, count={item_count}")
            return jsonify({'success': True, 'message': 'Item count updated successfully'}), 200
        else:
            logging.warning(f"No OPEN event found to update for user={user}, project={project}")
            return jsonify({'success': False, 'error': 'No matching OPEN event found'}), 404
            
    except sqlite3.Error as e:
        logging.error(f"Database error on /update_item_count: {e}", exc_info=True)
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
            # Fetch all logs if no specific project is requested, similar to dashboard
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
        logging.info(f"DELETE FROM logs statement executed successfully.")
        return jsonify({'success': True, 'message': 'All logs cleared successfully.'}), 200
    except sqlite3.Error as e:
        logging.error(f"Database error on /clear_logs: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Database operation failed to clear logs.'}), 500

@app.route('/favicon.ico')
def favicon():
    # Try to find favicon in resources
    favicon_path = get_resource_path('database/static/favicon.ico')
    if os.path.exists(favicon_path):
        return send_from_directory(os.path.dirname(favicon_path), 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    else:
        return '', 204  # No content

# --- HTML Serving Endpoints ---
@app.route('/')
@app.route('/dashboard')
def dashboard():
    try:
        # Get today's date
        today = datetime.now().date()
        
        conn = get_db()
        c = conn.cursor()
        
        # Query all OPEN projects (regardless of date) and today's AFGEMELD projects
        c.execute("""
            SELECT * FROM logs 
            WHERE 
                (status = 'OPEN' AND event = 'OPEN')  -- All open projects regardless of date
                OR (DATE(timestamp) = ? AND event = 'AFGEMELD')  -- Today's completed projects
            ORDER BY timestamp DESC
        """, (today.isoformat(),))
        
        logs_for_display = c.fetchall()
        
        # Group by user, keeping track of all projects
        users_projects = {}
        
        for log in logs_for_display:
            log_dict = dict(log)
            user = log_dict.get('user')
            project = log_dict.get('project')
            
            if user and project:
                if user not in users_projects:
                    users_projects[user] = {}
                
                # Format timestamp properly
                timestamp_str = log_dict.get('timestamp', '')
                try:
                    dt = datetime.fromisoformat(timestamp_str)
                    # Show date if not today
                    if dt.date() != today:
                        formatted_time = dt.strftime('%d-%m %H:%M')
                    else:
                        formatted_time = dt.strftime('%H:%M')
                except:
                    formatted_time = '--'
                
                # Add or update project info - use the latest status for each project
                if project not in users_projects[user] or log_dict.get('event') == 'AFGEMELD':
                    users_projects[user][project] = {
                        'project_code': project,
                        'status': log_dict.get('status', ''),
                        'timestamp': formatted_time,
                        'user': user,
                        'raw_timestamp': timestamp_str  # Keep raw timestamp for sorting
                    }
        
        # Convert to format expected by template
        formatted_users_projects = {}
        for user, projects in users_projects.items():
            formatted_users_projects[user] = list(projects.values())
            # Sort by status (OPEN first) then by timestamp (newest first)
            formatted_users_projects[user].sort(
                key=lambda x: (
                    0 if x['status'] == 'OPEN' else 1,  # OPEN projects first
                    x['raw_timestamp']  # Then by timestamp
                ),
                reverse=True
            )
            # Remove raw_timestamp from final output
            for project in formatted_users_projects[user]:
                project.pop('raw_timestamp', None)
        
        # Make sure all expected users are present (even if no activity)
        expected_users = ['NESTING', 'OPUS', 'KL GANNOMAT']
        for user in expected_users:
            if user not in formatted_users_projects:
                formatted_users_projects[user] = []
        
        # Get all logs for the recent projects list and JavaScript processing
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        c.execute("""
            SELECT * FROM logs 
            WHERE timestamp >= ? 
            ORDER BY timestamp DESC
        """, (seven_days_ago,))
        
        recent_logs = c.fetchall()
        
        # Also include ALL logs for JavaScript to process properly
        # This ensures the client-side has all the data it needs
        c.execute("""
            SELECT * FROM logs 
            WHERE 
                (status = 'OPEN' AND event = 'OPEN')  -- All open projects
                OR (timestamp >= ?)  -- Or recent logs
            ORDER BY timestamp DESC
            LIMIT 1000
        """, (seven_days_ago,))
        
        all_relevant_logs = c.fetchall()
        
        logs_list = []
        for log in all_relevant_logs:
            log_dict = dict(log)
            logs_list.append({
                'project': log_dict.get('project'),
                'user': log_dict.get('user'),
                'status': log_dict.get('status'),
                'timestamp': log_dict.get('timestamp'),
                'event': log_dict.get('event')
            })
        
        return render_template('dashboard.html', 
                             users_projects=formatted_users_projects,
                             logs=logs_list,
                             active_page='dashboard')
                             
    except Exception as e:
        logging.error(f"Dashboard error: {str(e)}", exc_info=True)
        return render_template('error.html', message=str(e)), 500

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

        user_status_html = '<table class="table"><thead><tr><th>User</th><th>Status</th><th>Last Updated</th></tr></thead><tbody>'
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

        # Get unique users for filter
        c.execute("SELECT DISTINCT user FROM logs WHERE user IS NOT NULL AND user != '' ORDER BY user")
        users = [row['user'] for row in c.fetchall()]

        return render_template('logs_project.html', 
                               project=project, 
                               log_entries=log_entries, 
                               user_status_html=user_status_html,
                               all_projects=all_projects,
                               users=users,
                               active_page='projects')

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return render_template('error.html', message='An error occurred while loading the project.'), 500

@app.route('/projects', methods=['GET'])
def projects():
    logging.info('projects endpoint was called')
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get all unique projects with their latest status and info
        projects_query = """
            WITH ProjectStatus AS (
                SELECT 
                    project,
                    user,
                    status,
                    timestamp,
                    event,
                    ROW_NUMBER() OVER(PARTITION BY project ORDER BY timestamp DESC) as rn
                FROM logs
                WHERE project IS NOT NULL AND project != ''
            ),
            ProjectCounts AS (
                SELECT 
                    project,
                    COUNT(*) as event_count
                FROM logs
                WHERE project IS NOT NULL AND project != ''
                GROUP BY project
            )
            SELECT DISTINCT
                ps.project as code,
                ps.user,
                ps.status,
                ps.timestamp,
                pc.event_count
            FROM ProjectStatus ps
            JOIN ProjectCounts pc ON ps.project = pc.project
            WHERE ps.rn = 1
            ORDER BY ps.timestamp DESC
        """
        
        c.execute(projects_query)
        projects = []
        
        total_projects = 0
        open_projects = 0
        completed_projects = 0
        in_progress = 0
        
        for row in c.fetchall():
            project_dict = dict(row)
            
            # Format timestamp
            try:
                dt = datetime.fromisoformat(project_dict['timestamp'])
                project_dict['timestamp'] = dt.strftime('%d-%m-%Y %H:%M')
            except (ValueError, TypeError):
                pass
            
            # Count statuses
            total_projects += 1
            status = project_dict.get('status', '').upper()
            if status == 'OPEN':
                open_projects += 1
            elif status == 'AFGEMELD' or status == 'CLOSED':
                completed_projects += 1
            else:
                in_progress += 1
                
            projects.append(project_dict)
        
        return render_template('projects.html', 
                             projects=projects,
                             total_projects=total_projects,
                             open_projects=open_projects,
                             completed_projects=completed_projects,
                             in_progress=in_progress,
                             active_page='projects')
    
    except Exception as e:
        logging.error(f"Failed to render projects page: {e}", exc_info=True)
        return render_template('error.html', message='Could not retrieve projects from the database.'), 500

@app.route('/users', methods=['GET'])
def users():
    logging.info('users endpoint was called')
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get user statistics
        users_query = """
            WITH UserStats AS (
                SELECT 
                    user,
                    COUNT(CASE WHEN status = 'OPEN' THEN 1 END) as active_projects,
                    COUNT(CASE WHEN status = 'AFGEMELD' AND DATE(timestamp) = DATE('now') THEN 1 END) as completed_today,
                    COUNT(*) as total_events
                FROM logs
                WHERE user IS NOT NULL AND user != ''
                GROUP BY user
            ),
            UserTiming AS (
                SELECT 
                    user,
                    AVG(
                        CASE 
                            WHEN status = 'AFGEMELD' THEN 
                                (julianday(timestamp) - julianday(
                                    (SELECT timestamp FROM logs l2 
                                     WHERE l2.project = logs.project 
                                     AND l2.user = logs.user 
                                     AND l2.status = 'OPEN' 
                                     AND l2.timestamp < logs.timestamp
                                     ORDER BY l2.timestamp DESC LIMIT 1)
                                )) * 24
                            ELSE NULL 
                        END
                    ) as avg_process_hours
                FROM logs
                WHERE user IS NOT NULL AND user != ''
                GROUP BY user
            )
            SELECT 
                us.user as name,
                us.active_projects,
                us.completed_today,
                us.total_events,
                COALESCE(ut.avg_process_hours, 0) as avg_time_hours,
                CASE 
                    WHEN us.user = 'NESTING' THEN 'Operator'
                    WHEN us.user = 'OPUS' THEN 'Operator'
                    WHEN us.user = 'KL GANNOMAT' THEN 'Supervisor'
                    ELSE 'Operator'
                END as role
            FROM UserStats us
            LEFT JOIN UserTiming ut ON us.user = ut.user
            ORDER BY 
                CASE us.user 
                    WHEN 'NESTING' THEN 1 
                    WHEN 'OPUS' THEN 2 
                    WHEN 'KL GANNOMAT' THEN 3 
                    ELSE 4 
                END
        """
        
        c.execute(users_query)
        users_list = []
        
        total_users = 0
        active_users = 0
        total_process_time = 0
        users_with_time = 0
        
        for row in c.fetchall():
            user_dict = dict(row)
            
            # Calculate initials
            name_parts = user_dict['name'].split()
            if len(name_parts) >= 2:
                user_dict['initials'] = name_parts[0][0] + name_parts[-1][0]
            else:
                user_dict['initials'] = user_dict['name'][:2].upper()
            
            # Format average time
            avg_hours = user_dict.get('avg_time_hours', 0) or 0
            if avg_hours > 0:
                user_dict['avg_time'] = f"{avg_hours:.1f}u"
                total_process_time += avg_hours
                users_with_time += 1
            else:
                user_dict['avg_time'] = '-'
            
            # Calculate efficiency (sample calculation)
            if user_dict['completed_today'] > 0:
                user_dict['efficiency'] = min(95, 80 + (user_dict['completed_today'] * 2))
            else:
                user_dict['efficiency'] = 75
            
            total_users += 1
            if user_dict['active_projects'] > 0:
                active_users += 1
                
            users_list.append(user_dict)
        
        # Calculate averages
        avg_process_time = f"{(total_process_time / users_with_time):.1f}u" if users_with_time > 0 else "0u"
        avg_performance = "85%"  # Sample value
        
        return render_template('users.html',
                             users=users_list,
                             total_users=total_users,
                             active_users=active_users,
                             avg_process_time=avg_process_time,
                             avg_performance=avg_performance,
                             active_page='users')
    
    except Exception as e:
        logging.error(f"Failed to render users page: {e}", exc_info=True)
        return render_template('error.html', message='Could not retrieve users from the database.'), 500

@app.route('/reports', methods=['GET'])
def reports():
    logging.info('reports endpoint was called')
    try:
        return render_template('reports.html', active_page='reports')
    
    except Exception as e:
        logging.error(f"Failed to render reports page: {e}", exc_info=True)
        return render_template('error.html', message='Could not load reports page.'), 500

@app.route('/statistics')
def statistics():
    """Statistics page view"""
    try:
        return render_template('statistics.html', active_page='statistics')
    except Exception as e:
        logging.error(f"Failed to render statistics page: {e}", exc_info=True)
        return render_template('error.html', message='Could not load statistics page.'), 500

@app.route('/api/report/generate', methods=['POST'])
def generate_report_data():
    """API endpoint to generate report data based on selected criteria"""
    try:
        data = request.get_json()
        report_type = data.get('report_type', 'workflow')
        period = data.get('period', 'week')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        conn = get_db()
        c = conn.cursor()
        
        # Build date filter
        date_filter = ""
        if period == 'week':
            date_filter = "AND datetime(timestamp) >= datetime('now', '-7 days')"
        elif period == 'month':
            date_filter = "AND datetime(timestamp) >= datetime('now', '-1 month')"
        elif period == 'year':
            date_filter = "AND datetime(timestamp) >= datetime('now', '-1 year')"
        elif period == 'custom' and start_date and end_date:
            date_filter = f"AND DATE(timestamp) BETWEEN '{start_date}' AND '{end_date}'"
        
        if report_type == 'workflow':
            # Generate workflow analysis report
            query = f"""
                WITH ProjectFlow AS (
                    SELECT 
                        project,
                        user,
                        status,
                        timestamp,
                        LAG(timestamp) OVER (PARTITION BY project ORDER BY timestamp) as prev_timestamp,
                        LAG(user) OVER (PARTITION BY project ORDER BY timestamp) as prev_user
                    FROM logs
                    WHERE project IS NOT NULL AND project != ''
                    {date_filter}
                    ORDER BY project, timestamp
                )
                SELECT 
                    project,
                    GROUP_CONCAT(user || ':' || 
                        CASE 
                            WHEN prev_timestamp IS NOT NULL THEN 
                                ROUND((julianday(timestamp) - julianday(prev_timestamp)) * 24, 2)
                            ELSE '0'
                        END, '|') as user_times,
                    MIN(timestamp) as start_time,
                    MAX(timestamp) as end_time,
                    MAX(status) as final_status
                FROM ProjectFlow
                GROUP BY project
                ORDER BY MIN(timestamp) DESC
                LIMIT 100
            """
            
            c.execute(query)
            report_data = []
            
            for row in c.fetchall():
                project_data = dict(row)
                # Parse user times
                user_times = project_data['user_times'].split('|') if project_data['user_times'] else []
                project_data['user_flow'] = [ut.split(':') for ut in user_times if ut]
                report_data.append(project_data)
                
            return jsonify({
                'success': True,
                'data': report_data,
                'report_type': report_type,
                'period': period
            })
        
        # Add other report types here...
        
    except Exception as e:
        logging.error(f"Failed to generate report: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/database/reset', methods=['POST'])
def reset_database():
    try:
        # Create a backup before reset
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_dir = get_writable_path('database/backups')
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f'pre_reset_{timestamp}.sqlite')
        shutil.copy2(DB_PATH, backup_path)
        
        conn = get_db()
        c = conn.cursor()
        
        # Delete all records
        c.execute('DELETE FROM logs')
        
        # Reset autoincrement
        c.execute('DELETE FROM sqlite_sequence WHERE name="logs"')
        
        conn.commit()
        
        logging.info("Database reset completed")
        return jsonify({
            'success': True,
            'backup_created': backup_path
        })
    except Exception as e:
        logging.error(f"Error resetting database: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/database/export', methods=['GET'])
def export_database():
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get all records
        c.execute('SELECT * FROM logs ORDER BY id')
        rows = c.fetchall()
        
        # Get column names
        columns = [description[0] for description in c.description]
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(columns)
        
        # Write data
        for row in rows:
            writer.writerow(row)
        
        # Create response
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename=database_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response.headers["Content-Type"] = "text/csv"
        
        return response
    except Exception as e:
        logging.error(f"Error exporting database: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/database/import', methods=['POST'])
def import_database():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        conn = get_db()
        c = conn.cursor()
        
        imported_count = 0
        for row in csv_reader:
            # Insert record (adjust columns as needed)
            c.execute('''
                INSERT INTO logs (timestamp, event, details, project, user, status, base_mo_code, is_rep_variant, file_path, item_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row.get('timestamp'),
                row.get('event'),
                row.get('details'),
                row.get('project'),
                row.get('user'),
                row.get('status'),
                row.get('base_mo_code'),
                row.get('is_rep_variant', 0),
                row.get('file_path'),
                row.get('item_count')
            ))
            imported_count += 1
        
        conn.commit()
        
        logging.info(f"Imported {imported_count} records from CSV")
        return jsonify({
            'success': True,
            'imported_count': imported_count
        })
    except Exception as e:
        logging.error(f"Error importing database: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# Database Logs
@app.route('/api/database/logs', methods=['GET'])
def get_database_logs():
    try:
        logs = []
        
        # Read the log file
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                # Get last 100 lines
                lines = f.readlines()[-100:]
                for line in lines:
                    # Parse log line (adjust format as needed)
                    parts = line.strip().split(' ', 3)
                    if len(parts) >= 4:
                        logs.append({
                            'timestamp': f"{parts[0]} {parts[1]}",
                            'level': parts[2],
                            'message': parts[3]
                        })
        
        return jsonify({
            'success': True,
            'logs': logs
        })
    except Exception as e:
        logging.error(f"Error reading database logs: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/database/logs/download', methods=['GET'])
def download_database_logs():
    try:
        if not os.path.exists(log_path):
            return jsonify({'success': False, 'error': 'Log file not found'}), 404
        
        return send_file(
            log_path,
            as_attachment=True,
            download_name=f'database_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
    except Exception as e:
        logging.error(f"Error downloading logs: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/database/logs/clear', methods=['POST'])
def clear_database_logs():
    try:
        # Backup current log
        if os.path.exists(log_path):
            backup_path = log_path + f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            shutil.copy2(log_path, backup_path)
            
            # Clear the log file
            with open(log_path, 'w') as f:
                f.write('')
        
        logging.info("Database logs cleared")
        return jsonify({'success': True, 'message': 'Logs cleared successfully'})
    except Exception as e:
        logging.error(f"Error clearing logs: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# Backup configuration
@app.route('/api/database/backup-config', methods=['POST'])
def save_backup_config():
    try:
        data = request.get_json()
        schedule = data.get('schedule', 'daily')
        retention = data.get('retention', '30')
        
        # Save to config (you might want to implement this in your config system)
        # For now, we'll just return success
        
        return jsonify({'success': True, 'message': 'Backup configuration saved'})
    except Exception as e:
        logging.error(f"Error saving backup config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# --- Database Management Routes ---
@app.route('/database', methods=['GET'])
def database_management():
    logging.info('database management page was called')
    try:
        # Get today's date
        today = datetime.now().date()
        
        conn = get_db()
        c = conn.cursor()
        
        # Query all OPEN projects (regardless of date) and today's AFGEMELD projects
        c.execute("""
            SELECT * FROM logs 
            WHERE 
                (status = 'OPEN' AND event = 'OPEN')  -- All open projects regardless of date
                OR (DATE(timestamp) = ? AND event = 'AFGEMELD')  -- Today's completed projects
            ORDER BY timestamp DESC
        """, (today.isoformat(),))
        
        logs_for_display = c.fetchall()
        
        # Group by user, keeping track of all projects
        users_projects = {}
        
        for log in logs_for_display:
            log_dict = dict(log)
            user = log_dict.get('user')
            project = log_dict.get('project')
            
            if user and project:
                if user not in users_projects:
                    users_projects[user] = {}
                
                # Format timestamp properly
                timestamp_str = log_dict.get('timestamp', '')
                try:
                    dt = datetime.fromisoformat(timestamp_str)
                    # Show date if not today
                    if dt.date() != today:
                        formatted_time = dt.strftime('%d-%m %H:%M')
                    else:
                        formatted_time = dt.strftime('%H:%M')
                except:
                    formatted_time = '--'
                
                # Add or update project info - use the latest status for each project
                if project not in users_projects[user] or log_dict.get('event') == 'AFGEMELD':
                    users_projects[user][project] = {
                        'project_code': project,
                        'status': log_dict.get('status', ''),
                        'timestamp': formatted_time,
                        'user': user,
                        'raw_timestamp': timestamp_str  # Keep raw timestamp for sorting
                    }
        
        # Convert to format expected by template
        formatted_users_projects = {}
        for user, projects in users_projects.items():
            formatted_users_projects[user] = list(projects.values())
            # Sort by status (OPEN first) then by timestamp (newest first)
            formatted_users_projects[user].sort(
                key=lambda x: (
                    0 if x['status'] == 'OPEN' else 1,  # OPEN projects first
                    x['raw_timestamp']  # Then by timestamp
                ),
                reverse=True
            )
            # Remove raw_timestamp from final output
            for project in formatted_users_projects[user]:
                project.pop('raw_timestamp', None)
        
        # Make sure all expected users are present (even if no activity)
        expected_users = ['NESTING', 'OPUS', 'KL GANNOMAT']
        for user in expected_users:
            if user not in formatted_users_projects:
                formatted_users_projects[user] = []
        
        # Get all logs for the recent projects list and JavaScript processing
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        c.execute("""
            SELECT * FROM logs 
            WHERE timestamp >= ? 
            ORDER BY timestamp DESC
        """, (seven_days_ago,))
        
        recent_logs = c.fetchall()
        
        # Also include ALL logs for JavaScript to process properly
        # This ensures the client-side has all the data it needs
        c.execute("""
            SELECT * FROM logs 
            WHERE 
                (status = 'OPEN' AND event = 'OPEN')  -- All open projects
                OR (timestamp >= ?)  -- Or recent logs
            ORDER BY timestamp DESC
            LIMIT 1000
        """, (seven_days_ago,))
        
        all_relevant_logs = c.fetchall()
        
        logs_list = []
        for log in all_relevant_logs:
            log_dict = dict(log)
            logs_list.append({
                'project': log_dict.get('project'),
                'user': log_dict.get('user'),
                'status': log_dict.get('status'),
                'timestamp': log_dict.get('timestamp'),
                'event': log_dict.get('event')
            })
        
        return render_template('database.html', 
                             users_projects=formatted_users_projects,
                             logs=logs_list,
                             active_page='database')
    except Exception as e:
        logging.error(f"Failed to render database page: {e}", exc_info=True)
        return render_template('error.html', message='Could not load database management page.'), 500

# Database Statistics
@app.route('/api/database/stats', methods=['GET'])
def get_database_stats():
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get total records
        c.execute('SELECT COUNT(*) FROM logs')
        total_records = c.fetchone()[0]
        
        # Get records today
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute('SELECT COUNT(*) FROM logs WHERE DATE(timestamp) = ?', (today,))
        records_today = c.fetchone()[0]
        
        # Get oldest record
        c.execute('SELECT MIN(timestamp) FROM logs')
        oldest_record = c.fetchone()[0]
        
        # Get database file size
        db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
        
        return jsonify({
            'success': True,
            'size': db_size,
            'total_records': total_records,
            'records_today': records_today,
            'oldest_record': oldest_record
        })
    except Exception as e:
        logging.error(f"Error getting database stats: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/database/info', methods=['GET'])
def get_database_info():
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get SQLite version
        c.execute('SELECT sqlite_version()')
        sqlite_version = c.fetchone()[0]
        
        # Get schema version (you might want to track this separately)
        schema_version = "1.0"  # Or retrieve from a settings table
        
        # Get last modified time
        last_modified = datetime.fromtimestamp(os.path.getmtime(DB_PATH)).isoformat() if os.path.exists(DB_PATH) else None
        
        return jsonify({
            'success': True,
            'type': 'SQLite',
            'version': sqlite_version,
            'path': DB_PATH,
            'schema_version': schema_version,
            'last_modified': last_modified
        })
    except Exception as e:
        logging.error(f"Error getting database info: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# Backup Operations
@app.route('/api/database/backup', methods=['POST'])
def create_backup():
    try:
        # Create backups directory if it doesn't exist
        backup_dir = get_writable_path('database/backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_filename = f'backup_{timestamp}.sqlite'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy database file
        shutil.copy2(DB_PATH, backup_path)
        
        logging.info(f"Database backup created: {backup_path}")
        return jsonify({
            'success': True,
            'filename': backup_filename,
            'path': backup_path
        })
    except Exception as e:
        logging.error(f"Error creating backup: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/database/backups', methods=['GET'])
def list_backups():
    try:
        backup_dir = get_writable_path('database/backups')
        backups = []
        
        if os.path.exists(backup_dir):
            for filename in os.listdir(backup_dir):
                if filename.endswith('.sqlite'):
                    filepath = os.path.join(backup_dir, filename)
                    stat = os.stat(filepath)
                    backups.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({
            'success': True,
            'backups': backups
        })
    except Exception as e:
        logging.error(f"Error listing backups: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/database/restore', methods=['POST'])
def restore_backup():
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'success': False, 'error': 'No filename provided'}), 400
        
        backup_dir = get_writable_path('database/backups')
        backup_path = os.path.join(backup_dir, filename)
        
        if not os.path.exists(backup_path):
            return jsonify({'success': False, 'error': 'Backup file not found'}), 404
        
        # Create a backup of current database before restoring
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        pre_restore_backup = os.path.join(backup_dir, f'pre_restore_{timestamp}.sqlite')
        shutil.copy2(DB_PATH, pre_restore_backup)
        
        # Restore the backup
        shutil.copy2(backup_path, DB_PATH)
        
        logging.info(f"Database restored from backup: {filename}")
        return jsonify({'success': True, 'message': 'Database restored successfully'})
    except Exception as e:
        logging.error(f"Error restoring backup: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# Database Maintenance
@app.route('/api/database/optimize', methods=['POST'])
def optimize_database():
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Run PRAGMA optimize
        c.execute('PRAGMA optimize')
        
        # Get statistics before and after
        c.execute('PRAGMA page_count')
        page_count = c.fetchone()[0]
        c.execute('PRAGMA page_size')
        page_size = c.fetchone()[0]
        
        conn.commit()
        
        logging.info("Database optimized successfully")
        return jsonify({
            'success': True,
            'page_count': page_count,
            'page_size': page_size,
            'total_size': page_count * page_size
        })
    except Exception as e:
        logging.error(f"Error optimizing database: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/database/vacuum', methods=['POST'])
def vacuum_database():
    try:
        # VACUUM requires a new connection
        conn = sqlite3.connect(DB_PATH)
        conn.execute('VACUUM')
        conn.close()
        
        logging.info("Database VACUUM completed successfully")
        return jsonify({'success': True, 'message': 'VACUUM completed successfully'})
    except Exception as e:
        logging.error(f"Error during VACUUM: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/database/analyze', methods=['POST'])
def analyze_database():
    try:
        conn = get_db()
        conn.execute('ANALYZE')
        conn.commit()
        
        logging.info("Database ANALYZE completed successfully")
        return jsonify({'success': True, 'message': 'ANALYZE completed successfully'})
    except Exception as e:
        logging.error(f"Error during ANALYZE: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/database/integrity-check', methods=['POST'])
def check_database_integrity():
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Run integrity check
        c.execute('PRAGMA integrity_check')
        result = c.fetchall()
        
        # If result is [('ok',)], database is fine
        is_ok = len(result) == 1 and result[0][0] == 'ok'
        
        return jsonify({
            'success': True,
            'result': 'ok' if is_ok else str(result),
            'is_ok': is_ok
        })
    except Exception as e:
        logging.error(f"Error checking database integrity: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# Data Management
@app.route('/api/database/cleanup', methods=['POST'])
def cleanup_old_records():
    try:
        data = request.get_json()
        days = data.get('days', 365)
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        conn = get_db()
        c = conn.cursor()
        
        # Count records to be deleted
        c.execute('SELECT COUNT(*) FROM logs WHERE timestamp < ?', (cutoff_date,))
        count = c.fetchone()[0]
        
        # Delete old records
        c.execute('DELETE FROM logs WHERE timestamp < ?', (cutoff_date,))
        conn.commit()
        
        logging.info(f"Deleted {count} records older than {days} days")
        return jsonify({
            'success': True,
            'deleted_count': count
        })
    except Exception as e:
        logging.error(f"Error cleaning up old records: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/database/cleanup-projects', methods=['POST'])
def cleanup_projects():
    try:
        data = request.get_json()
        pattern = data.get('pattern', '')
        
        if not pattern:
            return jsonify({'success': False, 'error': 'No pattern provided'}), 400
        
        # Replace * with % for SQL LIKE pattern
        sql_pattern = pattern.replace('*', '%')
        
        conn = get_db()
        c = conn.cursor()
        
        # Count records to be deleted
        c.execute('SELECT COUNT(*) FROM logs WHERE project LIKE ?', (sql_pattern,))
        count = c.fetchone()[0]
        
        # Delete matching records
        c.execute('DELETE FROM logs WHERE project LIKE ?', (sql_pattern,))
        conn.commit()
        
        logging.info(f"Deleted {count} records for projects matching '{pattern}'")
        return jsonify({
            'success': True,
            'deleted_count': count
        })
    except Exception as e:
        logging.error(f"Error cleaning up projects: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# --- New Metrics Endpoints ---
@app.route('/api/metrics/project_completion_times', methods=['GET'])
def get_project_completion_times():
    """Get average project completion times per user with historical trends."""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get completion times with moving averages
        query = """
            WITH ProjectCompletions AS (
                SELECT 
                    o.user,
                    o.project,
                    o.timestamp as start_time,
                    a.timestamp as end_time,
                    o.base_mo_code,
                    o.is_rep_variant,
                    (julianday(a.timestamp) - julianday(o.timestamp)) * 24 * 60 as completion_minutes,
                    DATE(o.timestamp) as project_date
                FROM logs o
                INNER JOIN logs a ON 
                    o.project = a.project 
                    AND o.user = a.user 
                    AND a.event = 'AFGEMELD' 
                    AND a.timestamp > o.timestamp
                WHERE 
                    o.event = 'OPEN' 
                    AND o.user IS NOT NULL 
                    AND o.user != ''
            ),
            UserStats AS (
                SELECT 
                    user,
                    COUNT(*) as total_completed,
                    AVG(completion_minutes) as avg_minutes,
                    MIN(completion_minutes) as min_minutes,
                    MAX(completion_minutes) as max_minutes,
                    -- Standard deviation for consistency analysis
                    CASE 
                        WHEN COUNT(*) > 1 THEN 
                            SQRT(AVG(completion_minutes * completion_minutes) - AVG(completion_minutes) * AVG(completion_minutes))
                        ELSE 0 
                    END as std_dev,
                    -- Separate averages for REP and non-REP projects
                    AVG(CASE WHEN is_rep_variant = 1 THEN completion_minutes END) as avg_minutes_rep,
                    AVG(CASE WHEN is_rep_variant = 0 THEN completion_minutes END) as avg_minutes_normal,
                    COUNT(CASE WHEN is_rep_variant = 1 THEN 1 END) as count_rep,
                    COUNT(CASE WHEN is_rep_variant = 0 THEN 1 END) as count_normal
                FROM ProjectCompletions
                WHERE completion_minutes > 0 -- Filter out invalid data
                GROUP BY user
            ),
            RecentTrends AS (
                SELECT 
                    user,
                    AVG(completion_minutes) as recent_avg_minutes,
                    COUNT(*) as recent_count
                FROM ProjectCompletions
                WHERE project_date >= date('now', '-7 days')
                    AND completion_minutes > 0
                GROUP BY user
            )
            SELECT 
                u.user,
                u.total_completed,
                u.avg_minutes,
                u.min_minutes,
                u.max_minutes,
                u.std_dev,
                u.avg_minutes_rep,
                u.avg_minutes_normal,
                u.count_rep,
                u.count_normal,
                r.recent_avg_minutes,
                r.recent_count,
                -- Performance trend (recent vs overall)
                CASE 
                    WHEN r.recent_avg_minutes IS NOT NULL AND u.avg_minutes > 0 THEN
                        ((u.avg_minutes - r.recent_avg_minutes) / u.avg_minutes) * 100
                    ELSE NULL
                END as improvement_percentage
            FROM UserStats u
            LEFT JOIN RecentTrends r ON u.user = r.user
            ORDER BY 
                CASE u.user 
                    WHEN 'NESTING' THEN 1 
                    WHEN 'OPUS' THEN 2 
                    WHEN 'KL GANNOMAT' THEN 3 
                    ELSE 4 
                END
        """
        
        c.execute(query)
        user_metrics = []
        
        for row in c.fetchall():
            metrics = dict(row)
            
            # Format times
            for field in ['avg_minutes', 'min_minutes', 'max_minutes', 'avg_minutes_rep', 
                         'avg_minutes_normal', 'recent_avg_minutes']:
                if metrics.get(field):
                    metrics[f"{field.replace('_minutes', '_time')}"] = format_minutes(metrics[field])
                else:
                    metrics[f"{field.replace('_minutes', '_time')}"] = '-'
            
            # Calculate consistency score (lower std dev = more consistent)
            if metrics['avg_minutes'] and metrics['std_dev']:
                cv = (metrics['std_dev'] / metrics['avg_minutes']) * 100  # Coefficient of variation
                if cv < 20:
                    metrics['consistency'] = 'Zeer consistent'
                elif cv < 40:
                    metrics['consistency'] = 'Consistent'
                elif cv < 60:
                    metrics['consistency'] = 'Variabel'
                else:
                    metrics['consistency'] = 'Zeer variabel'
            else:
                metrics['consistency'] = 'Onbekend'
            
            # Format improvement percentage
            if metrics['improvement_percentage'] is not None:
                if metrics['improvement_percentage'] > 0:
                    metrics['trend'] = f"↑ {metrics['improvement_percentage']:.1f}% sneller"
                    metrics['trend_class'] = 'positive'
                elif metrics['improvement_percentage'] < 0:
                    metrics['trend'] = f"↓ {abs(metrics['improvement_percentage']):.1f}% langzamer"
                    metrics['trend_class'] = 'negative'
                else:
                    metrics['trend'] = '→ Geen verandering'
                    metrics['trend_class'] = 'neutral'
            else:
                metrics['trend'] = 'Onvoldoende data'
                metrics['trend_class'] = 'unknown'
            
            user_metrics.append(metrics)
        
        return jsonify({
            'success': True,
            'metrics': user_metrics
        })
    
    except Exception as e:
        logging.error(f"Error getting project completion times: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/metrics/project_history/<user>', methods=['GET'])
def get_user_project_history(user):
    """Get detailed project history for a specific user."""
    try:
        days = int(request.args.get('days', 30))
        
        conn = get_db()
        c = conn.cursor()
        
        query = """
            SELECT 
                o.project,
                o.base_mo_code,
                o.is_rep_variant,
                o.timestamp as start_time,
                a.timestamp as end_time,
                (julianday(a.timestamp) - julianday(o.timestamp)) * 24 * 60 as completion_minutes,
                DATE(o.timestamp) as project_date
            FROM logs o
            LEFT JOIN logs a ON 
                o.project = a.project 
                AND o.user = a.user 
                AND a.event = 'AFGEMELD' 
                AND a.timestamp > o.timestamp
            WHERE 
                o.event = 'OPEN' 
                AND o.user = ?
                AND DATE(o.timestamp) >= date('now', '-' || ? || ' days')
            ORDER BY o.timestamp DESC
        """
        
        c.execute(query, (user, days))
        projects = []
        
        for row in c.fetchall():
            project = dict(row)
            
            # Format times
            if project['completion_minutes']:
                project['completion_time'] = format_minutes(project['completion_minutes'])
                project['status'] = 'Voltooid'
            else:
                # Calculate elapsed time for open projects
                elapsed = (datetime.now() - datetime.fromisoformat(project['start_time'])).total_seconds() / 60
                project['completion_time'] = format_minutes(elapsed) + ' (lopend)'
                project['status'] = 'Open'
            
            # Format timestamps
            project['start_time'] = datetime.fromisoformat(project['start_time']).strftime('%d-%m %H:%M')
            if project['end_time']:
                project['end_time'] = datetime.fromisoformat(project['end_time']).strftime('%d-%m %H:%M')
            
            projects.append(project)
        
        return jsonify({
            'success': True,
            'user': user,
            'projects': projects,
            'days': days
        })
    
    except Exception as e:
        logging.error(f"Error getting user project history: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/metrics/expected_completion/<project>', methods=['GET'])
def get_expected_completion_time(project):
    """Get expected completion time for a project based on historical data."""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get project info and current status
        project_query = """
            SELECT 
                user,
                timestamp as start_time,
                base_mo_code,
                is_rep_variant
            FROM logs
            WHERE 
                project = ? 
                AND event = 'OPEN'
                AND status = 'OPEN'
            ORDER BY timestamp DESC
            LIMIT 1
        """
        
        c.execute(project_query, (project,))
        project_info = c.fetchone()
        
        if not project_info:
            return jsonify({'success': False, 'error': 'Project not found or already completed'}), 404
        
        project_data = dict(project_info)
        user = project_data['user']
        is_rep = project_data['is_rep_variant']
        
        # Get historical average for this user and project type
        history_query = """
            SELECT 
                AVG(completion_minutes) as avg_completion,
                COUNT(*) as sample_size,
                MIN(completion_minutes) as best_time,
                MAX(completion_minutes) as worst_time
            FROM (
                SELECT 
                    (julianday(a.timestamp) - julianday(o.timestamp)) * 24 * 60 as completion_minutes
                FROM logs o
                INNER JOIN logs a ON 
                    o.project = a.project 
                    AND o.user = a.user 
                    AND a.event = 'AFGEMELD' 
                    AND a.timestamp > o.timestamp
                WHERE 
                    o.event = 'OPEN' 
                    AND o.user = ?
                    AND o.is_rep_variant = ?
                    AND (julianday(a.timestamp) - julianday(o.timestamp)) * 24 * 60 > 0
                ORDER BY o.timestamp DESC
                LIMIT 20  -- Use last 20 similar projects
            )
        """
        
        c.execute(history_query, (user, is_rep))
        history = c.fetchone()
        
        if history and history['avg_completion']:
            history_data = dict(history)
            
            # Calculate expected completion time
            start_time = datetime.fromisoformat(project_data['start_time'])
            elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
            remaining_minutes = max(0, history_data['avg_completion'] - elapsed_minutes)
            
            expected_completion = datetime.now() + timedelta(minutes=remaining_minutes)
            
            response = {
                'success': True,
                'project': project,
                'user': user,
                'elapsed_time': format_minutes(elapsed_minutes),
                'average_time': format_minutes(history_data['avg_completion']),
                'expected_remaining': format_minutes(remaining_minutes),
                'expected_completion_time': expected_completion.strftime('%H:%M'),
                'confidence': 'Hoog' if history_data['sample_size'] >= 10 else 'Laag',
                'sample_size': history_data['sample_size'],
                'best_case': format_minutes(history_data['best_time']),
                'worst_case': format_minutes(history_data['worst_time'])
            }
        else:
            response = {
                'success': True,
                'project': project,
                'user': user,
                'message': 'Geen historische data beschikbaar voor deze gebruiker/projecttype'
            }
        
        return jsonify(response)
    
    except Exception as e:
        logging.error(f"Error getting expected completion time: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/metrics/workflow_chain', methods=['GET'])
def get_workflow_chain_metrics():
    """Get metrics for the workflow chain (time spent at each station)."""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Analyze workflow patterns
        query = """
            WITH ProjectWorkflow AS (
                SELECT 
                    project,
                    user,
                    event,
                    timestamp,
                    ROW_NUMBER() OVER (PARTITION BY project ORDER BY timestamp) as step_order,
                    LEAD(timestamp) OVER (PARTITION BY project ORDER BY timestamp) as next_timestamp,
                    LEAD(user) OVER (PARTITION BY project ORDER BY timestamp) as next_user
                FROM logs
                WHERE 
                    event IN ('OPEN', 'AFGEMELD')
                    AND project IS NOT NULL
                ORDER BY project, timestamp
            )
            SELECT 
                user as current_user,
                next_user,
                COUNT(*) as transition_count,
                AVG(
                    CASE 
                        WHEN next_timestamp IS NOT NULL THEN 
                            (julianday(next_timestamp) - julianday(timestamp)) * 24 * 60
                        ELSE NULL 
                    END
                ) as avg_transition_minutes
            FROM ProjectWorkflow
            WHERE event = 'OPEN'
            GROUP BY user, next_user
            HAVING next_user IS NOT NULL
        """
        
        c.execute(query)
        transitions = []
        
        for row in c.fetchall():
            transition = dict(row)
            if transition['avg_transition_minutes']:
                hours = int(transition['avg_transition_minutes'] // 60)
                mins = int(transition['avg_transition_minutes'] % 60)
                transition['avg_transition_time'] = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
            else:
                transition['avg_transition_time'] = '-'
            transitions.append(transition)
        
        return jsonify({
            'success': True,
            'transitions': transitions
        })
    
    except Exception as e:
        logging.error(f"Error getting workflow chain metrics: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/metrics/daily_summary', methods=['GET'])
def get_daily_summary():
    """Get daily summary metrics."""
    try:
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        conn = get_db()
        c = conn.cursor()
        
        # Get daily statistics
        query = """
            SELECT 
                COUNT(DISTINCT CASE WHEN event = 'OPEN' THEN project END) as projects_started,
                COUNT(DISTINCT CASE WHEN event = 'AFGEMELD' THEN project END) as projects_completed,
                COUNT(DISTINCT user) as active_users,
                SUM(CASE WHEN event = 'OPEN' THEN item_count ELSE 0 END) as total_items_created,
                COUNT(*) as total_events
            FROM logs
            WHERE DATE(timestamp) = ?
        """
        
        c.execute(query, (date_str,))
        row = c.fetchone()
        
        if row:
            summary = dict(row)
        else:
            summary = {
                'projects_started': 0,
                'projects_completed': 0,
                'active_users': 0,
                'total_items_created': 0,
                'total_events': 0
            }
        
        # Get hourly distribution
        hourly_query = """
            SELECT 
                strftime('%H', timestamp) as hour,
                COUNT(*) as event_count,
                COUNT(DISTINCT user) as active_users
            FROM logs
            WHERE DATE(timestamp) = ?
            GROUP BY hour
            ORDER BY hour
        """
        
        c.execute(hourly_query, (date_str,))
        hourly_data = []
        
        for row in c.fetchall():
            hourly_data.append({
                'hour': int(row['hour']),
                'events': row['event_count'],
                'users': row['active_users']
            })
        
        return jsonify({
            'success': True,
            'date': date_str,
            'summary': summary,
            'hourly_distribution': hourly_data
        })
    
    except Exception as e:
        logging.error(f"Error getting daily summary: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# --- Production Server Setup ---
def run_api_server(host='0.0.0.0', port=5001):
    global _server_thread, _server
    init_db()  # Initialize database once when the server starts
    
    try:
        # Try to use waitress for production
        from waitress import serve
        logging.info(f"Starting database API server with Waitress on http://{host}:{port}")
        _server = serve(app, host=host, port=port, _quiet=True)
    except ImportError:
        # Fall back to Flask development server
        logging.warning("Waitress not available, using Flask development server")
        logging.info(f"Starting database API server on http://{host}:{port}")
        app.run(host=host, port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_api_server()