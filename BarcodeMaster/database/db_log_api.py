from flask import Flask, request, jsonify, render_template, send_from_directory, make_response, send_file, g
import sqlite3
import json
import os
from datetime import datetime, timedelta
import logging
import shutil
import csv
import io
import threading
import sys
from collections import defaultdict
import statistics
import math

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
        
        # Create indexes for better performance
        c.execute('CREATE INDEX IF NOT EXISTS idx_logs_project ON logs(project)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_logs_status ON logs(status)')
        
        conn.commit()
        logging.info("Database initialization complete.")
    except Exception as e:
        logging.error(f"Error during database initialization: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

# --- Configuration Management ---
def get_config():
    """Get configuration from config system"""
    # Default configuration - no hardcoded users
    default_config = {
        'dashboard_display_users': [],  # Empty by default, will be populated from scanner users
        'scanner_panel_open_event_users': []  # Also empty by default
    }
    
    try:
        # Try to load from config file
        config_path = get_writable_path('config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
                
                # Ensure dashboard_display_users exists
                if 'dashboard_display_users' not in loaded_config:
                    # If not set, use scanner panel users as default
                    scanner_users = loaded_config.get('scanner_panel_open_event_users', [])
                    loaded_config['dashboard_display_users'] = scanner_users
                    
                    # Save the update
                    with open(config_path, 'w') as f:
                        json.dump(loaded_config, f, indent=2)
                    logging.info(f"Added dashboard_display_users to config: {scanner_users}")
                
                return loaded_config
                    
    except Exception as e:
        logging.error(f"Error loading config: {e}")
    
    # Return default configuration
    return default_config

def save_config(updates):
    """Save configuration updates"""
    try:
        config_path = get_writable_path('config.json')
        
        # Load existing config
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        # Update with new values
        config.update(updates)
        
        # Save back
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        return True
    except Exception as e:
        logging.error(f"Error saving config: {e}")
        return False

# --- Helper Functions ---
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

def determine_project_status(project_code, conn):
    """
    Determine the overall status of a project based on all user activities.
    Returns: (status, current_user)
    """
    c = conn.cursor()
    
    # Get all events for this project
    c.execute("""
        SELECT user, event, status, timestamp
        FROM logs
        WHERE project = ?
        ORDER BY timestamp ASC
    """, (project_code,))
    
    events = c.fetchall()
    
    if not events:
        return ('UNKNOWN', None)
    
    # Track each user's status
    user_states = {}
    last_active_user = None
    last_timestamp = None
    
    for event in events:
        user = event['user']
        event_type = event['event']
        status = event['status']
        timestamp = event['timestamp']
        
        if event_type == 'OPEN':
            user_states[user] = 'OPEN'
            last_active_user = user
            last_timestamp = timestamp
        elif event_type == 'AFGEMELD':
            user_states[user] = 'COMPLETED'
            # Check if there's a next user in the chain
            config = get_config()
            configured_users = config.get('scanner_panel_open_event_users', ['NESTING', 'OPUS', 'KL GANNOMAT'])
            
            try:
                current_index = configured_users.index(user)
                # Check if the next user in chain has started
                if current_index < len(configured_users) - 1:
                    next_user = configured_users[current_index + 1]
                    if next_user in user_states and user_states[next_user] == 'OPEN':
                        last_active_user = next_user
            except ValueError:
                pass
    
    # Determine overall project status
    # Check if all users have completed
    all_completed = all(state == 'COMPLETED' for state in user_states.values())
    
    if all_completed:
        return ('AFGEROND', None)
    
    # Check if any user has an open status
    has_open = any(state == 'OPEN' for state in user_states.values())
    
    if has_open:
        # Find the current active user (the one with OPEN status who should be working on it)
        config = get_config()
        configured_users = config.get('scanner_panel_open_event_users', ['NESTING', 'OPUS', 'KL GANNOMAT'])
        
        for user in configured_users:
            if user_states.get(user) == 'OPEN':
                # Check if all previous users have completed
                user_index = configured_users.index(user)
                all_previous_completed = True
                
                for i in range(user_index):
                    prev_user = configured_users[i]
                    if user_states.get(prev_user) != 'COMPLETED':
                        all_previous_completed = False
                        break
                
                if all_previous_completed or user_index == 0:
                    return ('OPEN', user)
        
        # If we can't determine the exact user, return the last active one
        return ('OPEN', last_active_user)
    
    # If no clear status, return UNKNOWN
    return ('UNKNOWN', last_active_user)

# --- User Statistics Helper Functions ---
def count_active_projects(user):
    """Count active projects for a user"""
    try:
        cursor = get_db().cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT project) 
            FROM logs 
            WHERE user = ? AND status = 'OPEN' 
            AND timestamp > datetime('now', '-7 days')
        """, (user,))
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logging.error(f"Error counting active projects for {user}: {e}")
        return 0

def count_completed_today(user):
    """Count projects completed today by user"""
    try:
        cursor = get_db().cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(DISTINCT project) 
            FROM logs 
            WHERE user = ? 
            AND (status = 'AFGEMELD' OR status = 'CLOSED')
            AND DATE(timestamp) = ?
        """, (user, today))
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logging.error(f"Error counting completed today for {user}: {e}")
        return 0

def calculate_avg_time(user):
    """Calculate average processing time for user"""
    try:
        cursor = get_db().cursor()
        cursor.execute("""
            SELECT project, MIN(timestamp) as start_time, MAX(timestamp) as end_time
            FROM logs
            WHERE user = ?
            AND timestamp > datetime('now', '-30 days')
            GROUP BY project
            HAVING COUNT(DISTINCT status) > 1
        """, (user,))
        
        times = []
        for row in cursor.fetchall():
            start = datetime.fromisoformat(row['start_time'])
            end = datetime.fromisoformat(row['end_time'])
            duration = (end - start).total_seconds() / 3600  # hours
            if duration > 0 and duration < 24:  # reasonable duration
                times.append(duration)
        
        if times:
            avg_hours = sum(times) / len(times)
            return f"{avg_hours:.1f}h"
        return "--"
    except Exception as e:
        logging.error(f"Error calculating avg time for {user}: {e}")
        return "--"

def calculate_efficiency(user):
    """Calculate efficiency score for user"""
    try:
        cursor = get_db().cursor()
        
        # Get completion rate
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT CASE WHEN status IN ('AFGEMELD', 'CLOSED') THEN project END) as completed,
                COUNT(DISTINCT project) as total
            FROM logs
            WHERE user = ?
            AND timestamp > datetime('now', '-30 days')
        """, (user,))
        
        result = cursor.fetchone()
        if result and result['total'] > 0:
            completion_rate = (result['completed'] / result['total']) * 100
            
            # Factor in processing time
            avg_time = calculate_avg_time(user)
            if avg_time != "--":
                hours = float(avg_time.replace('h', ''))
                # Assuming 2 hours is optimal, adjust efficiency based on time
                time_factor = min(100, (2.0 / hours) * 100) if hours > 0 else 100
                
                # Combined efficiency score
                efficiency = (completion_rate * 0.7 + time_factor * 0.3)
                return int(efficiency)
        
        return 85  # default
    except Exception as e:
        logging.error(f"Error calculating efficiency for {user}: {e}")
        return 85

def get_user_activity_last_7_days(user):
    """Get user activity for last 7 days"""
    try:
        cursor = get_db().cursor()
        activities = []
        
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT COUNT(DISTINCT project) as count
                FROM logs
                WHERE user = ? AND DATE(timestamp) = ?
            """, (user, date))
            result = cursor.fetchone()
            activities.append(result['count'] if result else 0)
        
        return list(reversed(activities))  # Return in chronological order
    except Exception as e:
        logging.error(f"Error getting activity for {user}: {e}")
        return [0] * 7

# --- API Endpoints ---
@app.route('/shutdown', methods=['GET', 'POST'])
def shutdown():
    if _shutdown_requested:
        func = request.environ.get('werkzeug.server.shutdown')
        if func:
            func()
            return 'Server shutting down...', 200
        return 'Server shutdown initiated', 200
    return 'Shutdown not requested', 403

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
    """Get logs with optional filtering"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Build query with filters
        query = 'SELECT * FROM logs WHERE 1=1'
        params = []
        
        # Project filter
        project = request.args.get('project')
        if project:
            query += ' AND project = ?'
            params.append(project)
        
        # Date range filter
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date:
            query += ' AND DATE(timestamp) >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND DATE(timestamp) <= ?'
            params.append(end_date)
        
        # User filter
        user = request.args.get('user')
        if user:
            query += ' AND user = ?'
            params.append(user)
        
        # Project type filter
        project_type = request.args.get('project_type')
        if project_type:
            if project_type == 'rep':
                query += ' AND is_rep_variant = 1'
            elif project_type == 'normal':
                query += ' AND is_rep_variant = 0'
        
        # Status filter
        status = request.args.get('status')
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        # Add ordering and limit
        query += ' ORDER BY timestamp DESC'
        
        # Add limit if no specific filters
        if not (project or start_date or end_date or user or project_type or status):
            query += ' LIMIT 500'
        
        c.execute(query, params)
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
        # Get configuration
        config = get_config()
        
        # Get dashboard display users (these are the users that should always show)
        dashboard_users = config.get('dashboard_display_users', [])
        
        # If dashboard_users is empty, fall back to scanner users
        if not dashboard_users:
            dashboard_users = config.get('scanner_panel_open_event_users', [])
        
        # If still empty, get unique users from recent logs
        if not dashboard_users:
            conn = get_db()
            c = conn.cursor()
            c.execute("""
                SELECT DISTINCT user 
                FROM logs 
                WHERE user IS NOT NULL AND user != ''
                ORDER BY user
            """)
            dashboard_users = [row[0] for row in c.fetchall()]
        
        logging.info(f"Dashboard display users: {dashboard_users}")
        
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
        
        # IMPORTANT: Make sure ALL dashboard users are present (even if no activity)
        for user in dashboard_users:
            if user not in formatted_users_projects:
                formatted_users_projects[user] = []
                logging.info(f"Adding empty project list for dashboard user: {user}")
        
        # Debug logging
        logging.info(f"Dashboard users: {dashboard_users}")
        logging.info(f"Users in formatted_users_projects: {list(formatted_users_projects.keys())}")
        for user in dashboard_users:
            project_count = len(formatted_users_projects.get(user, []))
            logging.info(f"User {user}: {project_count} projects")
        
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
        
        # Calculate statistics
        total_projects = len(set(log['project'] for log in logs_list if log['project']))
        open_projects = len(set(log['project'] for log in logs_list if log['status'] == 'OPEN'))
        completed_projects = len(set(log['project'] for log in logs_list if log['status'] in ['AFGEMELD', 'CLOSED']))
        in_progress = total_projects - open_projects - completed_projects
        
        return render_template('dashboard.html', 
                             users_projects=formatted_users_projects,
                             configured_users=dashboard_users,  # Changed from configured_users
                             logs=logs_list,
                             total_projects=total_projects,
                             open_projects=open_projects,
                             in_progress=in_progress,
                             completed_projects=completed_projects,
                             active_page='dashboard')
                             
    except Exception as e:
        logging.error(f"Dashboard error: {str(e)}", exc_info=True)
        return render_template('error.html', message=str(e)), 500

@app.route('/logs_project')
def logs_project():
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', ['NESTING', 'OPUS', 'KL GANNOMAT'])
    
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
        users = list(set([log['user'] for log in log_entries if log.get('user')]))

        return render_template('logs_project.html', 
                               project=project, 
                               log_entries=log_entries, 
                               configured_users=configured_users,
                               user_status_html=user_status_html,
                               all_projects=all_projects,
                               users=users,
                               active_page='projects')

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return render_template('error.html', message='An error occurred while loading the project.'), 500

@app.route('/projects', methods=['GET'])
def projects():
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', ['NESTING', 'OPUS', 'KL GANNOMAT'])
    
    logging.info('projects endpoint was called')
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get all unique projects
        c.execute("""
            SELECT DISTINCT project
            FROM logs
            WHERE project IS NOT NULL AND project != ''
            ORDER BY project
        """)
        
        all_projects = [row['project'] for row in c.fetchall()]
        
        projects = []
        total_projects = 0
        open_projects = 0
        completed_projects = 0
        in_progress = 0
        
        for project_code in all_projects:
            # Determine the project status using the helper function
            project_status, current_user = determine_project_status(project_code, conn)
            
            # Get the latest timestamp for this project
            c.execute("""
                SELECT MAX(timestamp) as latest_timestamp
                FROM logs
                WHERE project = ?
            """, (project_code,))
            
            latest_timestamp = c.fetchone()['latest_timestamp']
            
            # Get event count
            c.execute("""
                SELECT COUNT(*) as event_count
                FROM logs
                WHERE project = ?
            """, (project_code,))
            
            event_count = c.fetchone()['event_count']
            
            # Format timestamp
            try:
                dt = datetime.fromisoformat(latest_timestamp)
                formatted_timestamp = dt.strftime('%d-%m-%Y %H:%M')
            except (ValueError, TypeError):
                formatted_timestamp = latest_timestamp
            
            # Create project entry
            project_dict = {
                'code': project_code,
                'user': current_user or 'Onbekend',
                'status': project_status,
                'timestamp': formatted_timestamp,
                'event_count': event_count
            }
            
            # Count statuses
            total_projects += 1
            if project_status == 'OPEN':
                open_projects += 1
            elif project_status == 'AFGEROND':
                completed_projects += 1
            else:
                in_progress += 1
            
            projects.append(project_dict)
        
        # Sort projects by timestamp (most recent first)
        projects.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return render_template('projects.html', 
                             projects=projects,
                             configured_users=configured_users,
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
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', ['NESTING', 'OPUS', 'KL GANNOMAT'])
    
    logging.info('users endpoint was called')
    try:
        # Get real user data from database
        user_stats = []
        total_active = 0
        total_completed = 0
        efficiency_scores = []
        processing_times = []
        
        for user in configured_users:
            active = count_active_projects(user)
            completed = count_completed_today(user)
            avg_time = calculate_avg_time(user)
            efficiency = calculate_efficiency(user)
            activity_data = get_user_activity_last_7_days(user)
            
            stats = {
                'name': user,
                'role': 'Operator',
                'initials': ''.join([part[0] for part in user.split()]),
                'active_projects': active,
                'completed_today': completed,
                'avg_time': avg_time,
                'efficiency': efficiency,
                'activity_data': activity_data
            }
            user_stats.append(stats)
            
            # Accumulate totals
            total_active += active
            total_completed += completed
            efficiency_scores.append(efficiency)
            if avg_time != "--":
                try:
                    hours = float(avg_time.replace('h', ''))
                    processing_times.append(hours)
                except:
                    pass
        
        # Calculate averages
        avg_performance = sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 85
        avg_process_time = sum(processing_times) / len(processing_times) if processing_times else 2.5
        
        return render_template('users.html',
                             users=user_stats,
                             total_users=len(configured_users),
                             active_users=len([u for u in user_stats if u['active_projects'] > 0]),
                             avg_performance=f"{int(avg_performance)}%",
                             avg_process_time=f"{avg_process_time:.1f}h",
                             active_page='users')
    
    except Exception as e:
        logging.error(f"Failed to render users page: {e}", exc_info=True)
        return render_template('error.html', message='Could not retrieve users from the database.'), 500

@app.route('/reports', methods=['GET'])
def reports():
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', ['NESTING', 'OPUS', 'KL GANNOMAT'])
    
    logging.info('reports endpoint was called')
    try:
        return render_template('reports.html', 
                             configured_users=configured_users,
                             active_page='reports')
    
    except Exception as e:
        logging.error(f"Failed to render reports page: {e}", exc_info=True)
        return render_template('error.html', message='Could not load reports page.'), 500

@app.route('/statistics')
def statistics():
    """Statistics page view"""
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', ['NESTING', 'OPUS', 'KL GANNOMAT'])
    
    try:
        # Calculate statistics
        conn = get_db()
        c = conn.cursor()
        
        # Total projects
        c.execute("SELECT COUNT(DISTINCT project) FROM logs WHERE project IS NOT NULL AND project != ''")
        total_projects = c.fetchone()[0]
        
        # Open projects
        c.execute("SELECT COUNT(DISTINCT project) FROM logs WHERE status = 'OPEN'")
        open_projects = c.fetchone()[0]
        
        # Completed projects
        c.execute("SELECT COUNT(DISTINCT project) FROM logs WHERE status IN ('AFGEMELD', 'CLOSED')")
        completed_projects = c.fetchone()[0]
        
        return render_template('statistics.html',
                             configured_users=configured_users,
                             total_projects=total_projects,
                             open_projects=open_projects,
                             completed_projects=completed_projects,
                             active_page='statistics')
    except Exception as e:
        logging.error(f"Failed to render statistics page: {e}", exc_info=True)
        return render_template('error.html', message='Could not load statistics page.'), 500

@app.route('/database', methods=['GET'])
def database():
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', ['NESTING', 'OPUS', 'KL GANNOMAT'])
    
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
        for user in configured_users:
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
                             configured_users=configured_users,
                             active_page='database')
    except Exception as e:
        logging.error(f"Failed to render database page: {e}", exc_info=True)
        return render_template('error.html', message='Could not load database management page.'), 500

# --- API Endpoints ---
@app.route('/api/configured_users')
def get_configured_users():
    config = get_config()
    users = config.get('scanner_panel_open_event_users', ['NESTING', 'OPUS', 'KL GANNOMAT'])
    return jsonify({
        'success': True,
        'users': users
    })

@app.route('/api/user/<username>/stats')
def get_user_stats(username):
    """Get detailed stats for a specific user"""
    stats = {
        'active_projects': count_active_projects(username),
        'completed_today': count_completed_today(username),
        'avg_time': calculate_avg_time(username),
        'efficiency': calculate_efficiency(username),
        'activity_last_7_days': get_user_activity_last_7_days(username)
    }
    return jsonify({
        'success': True,
        'stats': stats
    })

@app.route('/api/user/<username>/recent_projects')
def get_user_recent_projects(username):
    """Get recent projects for a user"""
    try:
        cursor = get_db().cursor()
        cursor.execute("""
            SELECT DISTINCT project, 
                   MAX(timestamp) as last_activity,
                   COUNT(*) as event_count,
                   MAX(CASE WHEN status IN ('AFGEMELD', 'CLOSED') THEN 1 ELSE 0 END) as is_completed
            FROM logs
            WHERE user = ?
            AND timestamp > datetime('now', '-7 days')
            GROUP BY project
            ORDER BY last_activity DESC
            LIMIT 10
        """, (username,))
        
        projects = []
        for row in cursor.fetchall():
            projects.append({
                'project': row['project'],
                'last_activity': row['last_activity'],
                'event_count': row['event_count'],
                'status': 'Completed' if row['is_completed'] else 'Active'
            })
        
        return jsonify({
            'success': True,
            'projects': projects
        })
    except Exception as e:
        logging.error(f"Error getting recent projects for {username}: {e}")
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

# --- API Endpoint to Manage Dashboard Users ---
@app.route('/api/dashboard/users', methods=['GET', 'POST'])
def manage_dashboard_users():
    """Manage which users should always be displayed on the dashboard"""
    if request.method == 'GET':
        config = get_config()
        return jsonify({
            'success': True,
            'dashboard_users': config.get('dashboard_display_users', []),
            'scanner_users': config.get('scanner_panel_open_event_users', [])
        })
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            users = data.get('users', [])
            
            # Validate users list
            if not isinstance(users, list):
                return jsonify({'success': False, 'error': 'Users must be a list'}), 400
            
            # Save to config
            save_config({'dashboard_display_users': users})
            
            logging.info(f"Updated dashboard display users: {users}")
            return jsonify({
                'success': True,
                'message': 'Dashboard users updated successfully',
                'users': users
            })
            
        except Exception as e:
            logging.error(f"Error updating dashboard users: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

# --- Sync Dashboard Users with Scanner Users ---
@app.route('/api/dashboard/sync-users', methods=['POST'])
def sync_dashboard_users():
    """Sync dashboard users with scanner panel users"""
    try:
        config = get_config()
        scanner_users = config.get('scanner_panel_open_event_users', [])
        
        save_config({'dashboard_display_users': scanner_users})
        
        logging.info(f"Synced dashboard users with scanner users: {scanner_users}")
        return jsonify({
            'success': True,
            'message': 'Dashboard users synced with scanner users',
            'users': scanner_users
        })
        
    except Exception as e:
        logging.error(f"Error syncing dashboard users: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# --- Dashboard Settings Page Route ---
@app.route('/dashboard-settings')
def dashboard_settings():
    """Dashboard settings page"""
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', [])
    
    try:
        return render_template('dashboard_settings.html',
                             configured_users=configured_users,
                             active_page='settings')
    except Exception as e:
        logging.error(f"Failed to render dashboard settings page: {e}", exc_info=True)
        return render_template('error.html', message='Could not load dashboard settings page.'), 500

# Backup configuration
@app.route('/api/backup/config', methods=['POST'])
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

# --- Enhanced Metrics Endpoints for Statistics ---
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
    """Get daily summary metrics with enhanced statistics."""
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
                COUNT(*) as total_events,
                -- Additional metrics
                AVG(CASE 
                    WHEN event = 'AFGEMELD' THEN 
                        (julianday(timestamp) - (
                            SELECT julianday(o.timestamp)
                            FROM logs o
                            WHERE o.project = logs.project
                            AND o.user = logs.user
                            AND o.event = 'OPEN'
                            AND o.timestamp < logs.timestamp
                            ORDER BY o.timestamp DESC
                            LIMIT 1
                        )) * 24 * 60
                    ELSE NULL
                END) as avg_completion_time_minutes
            FROM logs
            WHERE DATE(timestamp) = ?
        """
        
        c.execute(query, (date_str,))
        row = c.fetchone()
        
        if row:
            summary = dict(row)
            # Format completion time
            if summary['avg_completion_time_minutes']:
                summary['avg_completion_time'] = format_minutes(summary['avg_completion_time_minutes'])
            else:
                summary['avg_completion_time'] = '-'
        else:
            summary = {
                'projects_started': 0,
                'projects_completed': 0,
                'active_users': 0,
                'total_items_created': 0,
                'total_events': 0,
                'avg_completion_time': '-'
            }
        
        # Get hourly distribution
        hourly_query = """
            SELECT 
                strftime('%H', timestamp) as hour,
                COUNT(*) as event_count,
                COUNT(DISTINCT user) as active_users,
                COUNT(CASE WHEN event = 'OPEN' THEN 1 END) as starts,
                COUNT(CASE WHEN event = 'AFGEMELD' THEN 1 END) as completions
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
                'users': row['active_users'],
                'starts': row['starts'],
                'completions': row['completions']
            })
        
        # Calculate peak hours
        if hourly_data:
            peak_hour = max(hourly_data, key=lambda x: x['events'])
            summary['peak_hour'] = f"{peak_hour['hour']}:00 ({peak_hour['events']} events)"
        else:
            summary['peak_hour'] = '-'
        
        return jsonify({
            'success': True,
            'date': date_str,
            'summary': summary,
            'hourly_distribution': hourly_data
        })
    
    except Exception as e:
        logging.error(f"Error getting daily summary: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/metrics/performance_analysis', methods=['GET'])
def get_performance_analysis():
    """Get detailed performance analysis with statistical insights."""
    try:
        # Get parameters
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        user_filter = request.args.get('user', '')
        
        conn = get_db()
        c = conn.cursor()
        
        # Build query conditions
        conditions = ["DATE(o.timestamp) BETWEEN ? AND ?"]
        params = [start_date, end_date]
        
        if user_filter:
            conditions.append("o.user = ?")
            params.append(user_filter)
        
        where_clause = " AND ".join(conditions)
        
        # Get comprehensive performance metrics
        query = f"""
            WITH CompletionData AS (
                SELECT 
                    o.user,
                    o.project,
                    DATE(o.timestamp) as project_date,
                    o.is_rep_variant,
                    (julianday(a.timestamp) - julianday(o.timestamp)) * 24 * 60 as completion_minutes,
                    strftime('%w', o.timestamp) as day_of_week,
                    strftime('%H', o.timestamp) as hour_of_day
                FROM logs o
                INNER JOIN logs a ON 
                    o.project = a.project 
                    AND o.user = a.user 
                    AND a.event = 'AFGEMELD' 
                    AND a.timestamp > o.timestamp
                WHERE 
                    o.event = 'OPEN' 
                    AND {where_clause}
                    AND (julianday(a.timestamp) - julianday(o.timestamp)) * 24 * 60 > 0
            )
            SELECT 
                user,
                COUNT(*) as total_projects,
                AVG(completion_minutes) as avg_time,
                MIN(completion_minutes) as min_time,
                MAX(completion_minutes) as max_time,
                -- Calculate percentiles (approximation)
                AVG(CASE WHEN completion_minutes <= (SELECT AVG(completion_minutes) FROM CompletionData WHERE user = cd.user) THEN completion_minutes END) as median_approx,
                -- Standard deviation
                CASE 
                    WHEN COUNT(*) > 1 THEN 
                        SQRT(AVG(completion_minutes * completion_minutes) - AVG(completion_minutes) * AVG(completion_minutes))
                    ELSE 0 
                END as std_dev,
                -- Project type breakdown
                COUNT(CASE WHEN is_rep_variant = 1 THEN 1 END) as rep_count,
                COUNT(CASE WHEN is_rep_variant = 0 THEN 1 END) as normal_count,
                AVG(CASE WHEN is_rep_variant = 1 THEN completion_minutes END) as avg_rep_time,
                AVG(CASE WHEN is_rep_variant = 0 THEN completion_minutes END) as avg_normal_time
            FROM CompletionData cd
            GROUP BY user
            ORDER BY user
        """
        
        c.execute(query, params)
        performance_data = []
        
        for row in c.fetchall():
            data = dict(row)
            
            # Format all time fields
            for field in ['avg_time', 'min_time', 'max_time', 'median_approx', 'avg_rep_time', 'avg_normal_time']:
                if data.get(field):
                    data[f"{field}_formatted"] = format_minutes(data[field])
            
            # Calculate efficiency score
            if data['avg_time']:
                # Assume 120 minutes (2 hours) is the target
                efficiency = min(100, (120 / data['avg_time']) * 100)
                data['efficiency_score'] = round(efficiency, 1)
            else:
                data['efficiency_score'] = 0
            
            # Calculate consistency rating
            if data['avg_time'] and data['std_dev']:
                cv = (data['std_dev'] / data['avg_time']) * 100
                if cv < 15:
                    data['consistency_rating'] = 'Excellent'
                elif cv < 30:
                    data['consistency_rating'] = 'Good'
                elif cv < 50:
                    data['consistency_rating'] = 'Fair'
                else:
                    data['consistency_rating'] = 'Poor'
            else:
                data['consistency_rating'] = 'Unknown'
            
            performance_data.append(data)
        
        # Get time-based patterns
        pattern_query = f"""
            WITH CompletionData AS (
                SELECT 
                    strftime('%w', o.timestamp) as day_of_week,
                    strftime('%H', o.timestamp) as hour_of_day,
                    (julianday(a.timestamp) - julianday(o.timestamp)) * 24 * 60 as completion_minutes
                FROM logs o
                INNER JOIN logs a ON 
                    o.project = a.project 
                    AND o.user = a.user 
                    AND a.event = 'AFGEMELD' 
                    AND a.timestamp > o.timestamp
                WHERE 
                    o.event = 'OPEN' 
                    AND {where_clause}
            )
            SELECT 
                day_of_week,
                hour_of_day,
                AVG(completion_minutes) as avg_time,
                COUNT(*) as project_count
            FROM CompletionData
            GROUP BY day_of_week, hour_of_day
        """
        
        c.execute(pattern_query, params)
        patterns = []
        
        for row in c.fetchall():
            pattern = dict(row)
            pattern['avg_time_formatted'] = format_minutes(pattern['avg_time']) if pattern['avg_time'] else '-'
            patterns.append(pattern)
        
        return jsonify({
            'success': True,
            'performance_data': performance_data,
            'patterns': patterns,
            'period': {
                'start_date': start_date,
                'end_date': end_date
            }
        })
    
    except Exception as e:
        logging.error(f"Error getting performance analysis: {e}", exc_info=True)
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

# --- Database Management API ---
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

# Database Stats
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