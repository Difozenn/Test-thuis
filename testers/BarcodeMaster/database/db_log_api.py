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

# --- Work Hours Configuration ---
def load_work_hours():
    """Load work hours from config.json if available, otherwise use defaults"""
    default_work_hours = {
        'monday': {'start': 7.5, 'end': 16},      # 07:30-16:00
        'tuesday': {'start': 7.5, 'end': 16},     # 07:30-16:00
        'wednesday': {'start': 7.5, 'end': 16},   # 07:30-16:00
        'thursday': {'start': 7.5, 'end': 16},    # 07:30-16:00
        'friday': {'start': 7.5, 'end': 15},      # 07:30-15:00
        'break_start': 12,    # 12:00
        'break_end': 12.5,    # 12:30
        'work_days': [0, 1, 2, 3, 4]  # Monday to Friday (0=Monday, 6=Sunday)
    }
    
    try:
        config_path = get_writable_path('config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                if 'work_hours' in config:
                    loaded_work_hours = config['work_hours']
                    logging.info(f"Work hours loaded from config: {loaded_work_hours}")
                    return loaded_work_hours
    except Exception as e:
        logging.error(f"Error loading work hours from config: {e}")
    
    logging.info("Using default work hours configuration")
    return default_work_hours

WORK_HOURS = load_work_hours()

def calculate_work_minutes(start_time, end_time, work_hours=WORK_HOURS):
    """Calculate actual work minutes between two timestamps, excluding breaks and non-work hours"""
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time)
    
    total_minutes = 0
    current = start_time
    
    # Day name mapping
    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    while current < end_time:
        # Skip weekends
        if current.weekday() not in work_hours['work_days']:
            current = current.replace(hour=0, minute=0, second=0) + timedelta(days=1)
            continue
        
        # Get day-specific work hours
        day_name = day_names[current.weekday()]
        day_config = work_hours.get(day_name, {'start': 7.5, 'end': 16})  # Default fallback
        
        # Calculate work time for current day
        day_start = current.replace(hour=int(day_config['start']), 
                                   minute=int((day_config['start'] % 1) * 60), second=0)
        day_end = current.replace(hour=int(day_config['end']), 
                                 minute=int((day_config['end'] % 1) * 60), second=0)
        break_start = current.replace(hour=int(work_hours['break_start']), 
                                     minute=int((work_hours['break_start'] % 1) * 60), second=0)
        break_end = current.replace(hour=int(work_hours['break_end']), 
                                   minute=int((work_hours['break_end'] % 1) * 60), second=0)
        
        # Determine actual start and end for this day
        actual_start = max(current, day_start)
        actual_end = min(end_time, day_end)
        
        if actual_start < actual_end:
            # Morning session (before break)
            if actual_start < break_start:
                morning_end = min(actual_end, break_start)
                total_minutes += (morning_end - actual_start).total_seconds() / 60
            
            # Afternoon session (after break)
            if actual_end > break_end:
                afternoon_start = max(actual_start, break_end)
                total_minutes += (actual_end - afternoon_start).total_seconds() / 60
        
        # Move to next day
        current = current.replace(hour=0, minute=0, second=0) + timedelta(days=1)
    
    return round(total_minutes, 2)

def get_current_work_status():
    """Check if current time is within work hours"""
    now = datetime.now()
    
    # Check if it's a work day
    if now.weekday() not in WORK_HOURS['work_days']:
        return False, "Weekend - niet in werktijd"
    
    # Get day-specific work hours
    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    day_name = day_names[now.weekday()]
    day_config = WORK_HOURS.get(day_name, {'start': 7.5, 'end': 16})
    
    # Check time
    current_hour = now.hour + now.minute / 60
    
    if current_hour < day_config['start']:
        start_time = f"{int(day_config['start'])}:{int((day_config['start'] % 1) * 60):02d}"
        return False, f"Te vroeg - werk begint om {start_time}"
    elif current_hour >= day_config['end']:
        end_time = f"{int(day_config['end'])}:{int((day_config['end'] % 1) * 60):02d}"
        return False, f"Te laat - werk eindigt om {end_time}"
    elif WORK_HOURS['break_start'] <= current_hour < WORK_HOURS['break_end']:
        return False, "Pauze tijd"
    else:
        return True, "Binnen werktijd"

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
        
        # Create logs table if it doesn't exist
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
                item_count INTEGER,
                session_id TEXT
            )
        ''')
        
        # Create work_hours_config table
        c.execute('''
            CREATE TABLE IF NOT EXISTS work_hours_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT NOT NULL UNIQUE,
                monday_hours REAL DEFAULT 8.0,
                tuesday_hours REAL DEFAULT 8.0,
                wednesday_hours REAL DEFAULT 8.0,
                thursday_hours REAL DEFAULT 8.0,
                friday_hours REAL DEFAULT 8.0,
                saturday_hours REAL DEFAULT 0.0,
                sunday_hours REAL DEFAULT 0.0,
                start_time TEXT DEFAULT '07:00',
                end_time TEXT DEFAULT '17:00',
                break_start TEXT DEFAULT '12:00',
                break_end TEXT DEFAULT '12:30',
                efficiency_high_threshold REAL DEFAULT 10.0,
                efficiency_medium_threshold REAL DEFAULT 5.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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
        if 'session_id' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN session_id TEXT')
            logging.info("Added 'session_id' column to logs table.")
        if 'nesting_count' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN nesting_count INTEGER DEFAULT 0')
            logging.info("Added 'nesting_count' column to logs table.")
        if 'opdeelzaag_count' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN opdeelzaag_count INTEGER DEFAULT 0')
            logging.info("Added 'opdeelzaag_count' column to logs table.")
        if 'aantal_items' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN aantal_items INTEGER DEFAULT 0')
            logging.info("Added 'aantal_items' column to logs table.")
        if 'aantal_sides' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN aantal_sides INTEGER DEFAULT 0')
            logging.info("Added 'aantal_sides' column to logs table.")
        
        # Create sessions table
        c.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                user TEXT NOT NULL,
                project TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT DEFAULT 'active',
                item_count INTEGER DEFAULT 0,
                work_duration_minutes REAL,
                session_type TEXT DEFAULT 'XLSX_UPDATED',
                UNIQUE(user, project, start_time)
            )
        ''')
        
        # Check and add session_type column to sessions table if it doesn't exist
        c.execute("PRAGMA table_info(sessions)")
        sessions_columns = [column[1] for column in c.fetchall()]
        if 'session_type' not in sessions_columns:
            c.execute('ALTER TABLE sessions ADD COLUMN session_type TEXT DEFAULT "XLSX_UPDATED"')
            logging.info("Added 'session_type' column to sessions table.")
        if 'nesting_count' not in sessions_columns:
            c.execute('ALTER TABLE sessions ADD COLUMN nesting_count INTEGER DEFAULT 0')
            logging.info("Added 'nesting_count' column to sessions table.")
        if 'opdeelzaag_count' not in sessions_columns:
            c.execute('ALTER TABLE sessions ADD COLUMN opdeelzaag_count INTEGER DEFAULT 0')
            logging.info("Added 'opdeelzaag_count' column to sessions table.")
        
        # Create project_sessions table
        c.execute('''
            CREATE TABLE IF NOT EXISTS project_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                total_duration_minutes REAL,
                nesting_duration_minutes REAL,
                opus_duration_minutes REAL,
                gannomat_duration_minutes REAL,
                total_items INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                UNIQUE(project)
            )
        ''')
        
        # Create project_log table for XLSX_UPDATED workflow tracking
        c.execute('''
            CREATE TABLE IF NOT EXISTS project_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                event TEXT NOT NULL,
                user TEXT,
                timestamp TEXT NOT NULL,
                item_count INTEGER DEFAULT 0
            )
        ''')
        
        # Create indexes for better performance
        c.execute('CREATE INDEX IF NOT EXISTS idx_logs_project ON logs(project)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_logs_status ON logs(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_logs_session_id ON logs(session_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_project_sessions_project ON project_sessions(project)')
        
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
        # Using unified scanner_panel_open_event_users for both workflow and display
        'scanner_panel_open_event_users': []  # Also empty by default
    }
    
    try:
        # Try to load from config file
        config_path = get_writable_path('config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
                
                # Ensure scanner_panel_open_event_users exists
                if 'scanner_panel_open_event_users' not in loaded_config:
                    loaded_config['scanner_panel_open_event_users'] = []
                    
                    # Save the update
                    with open(config_path, 'w') as f:
                        json.dump(loaded_config, f, indent=2)
                    logging.info("Added scanner_panel_open_event_users to config")
                
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


    for session in active_sessions:
        if session['user'] in user_states and user_states[session['user']] == 'OPEN':
            user_states[session['user']] = 'WORKING'
            last_active_user = session['user']
    
    # Determine overall project status based on involved users only
    config = get_config()
    all_configured_users = config.get('scanner_panel_open_event_users', [])
    
    # Filter to only users involved in this project
    relevant_users = [u for u in all_configured_users if u in involved_users]
    
    if not relevant_users:
        return ('UNKNOWN', None, involved_users)
    
    # Check if all involved users have completed
    all_completed = all(
        user_states.get(user) == 'COMPLETED' 
        for user in relevant_users
    )
    
    if all_completed:
        return ('AFGEROND', None, involved_users)
    
    # Find the current active user (who should be working)
    for user in relevant_users:
        user_state = user_states.get(user, 'PENDING')
        
        if user_state in ['OPEN', 'WORKING']:
            # Check if all previous users in the chain have completed
            user_index = relevant_users.index(user)
            all_previous_completed = all(
                user_states.get(relevant_users[i]) == 'COMPLETED'
                for i in range(user_index)
            )
            
            if all_previous_completed or user_index == 0:
                return ('OPEN', user, involved_users)
    
    return ('IN_PROGRESS', last_active_user, involved_users)

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

def get_user_work_config(user):
    """Get work hours configuration for a specific user"""
    cursor = get_db().cursor()
    cursor.execute("""
        SELECT * FROM work_hours_config WHERE user = ?
    """, (user,))
    
    config = cursor.fetchone()
    if not config:
        # Create default config
        cursor.execute("""
            INSERT INTO work_hours_config (user) 
            VALUES (?)
        """, (user,))
        get_db().commit()
        return get_default_work_config()
    
    return dict(config)

def get_default_work_config():
    """Get default work hours configuration"""
    return {
        'user': '',
        'monday_hours': 8.0,
        'tuesday_hours': 8.0,
        'wednesday_hours': 8.0,
        'thursday_hours': 8.0,
        'friday_hours': 8.0,
        'saturday_hours': 0.0,
        'sunday_hours': 0.0,
        'start_time': '07:00',
        'end_time': '17:00',
        'break_start': '12:00',
        'break_end': '12:30',
        'efficiency_high_threshold': 10.0,
        'efficiency_medium_threshold': 5.0
    }

def calculate_user_work_minutes(start_time, end_time, user):
    """Calculate work minutes based on user-specific configuration"""
    config = get_user_work_config(user)
    
    # Convert time strings to hours
    start_hour = int(config['start_time'].split(':')[0]) + int(config['start_time'].split(':')[1])/60
    end_hour = int(config['end_time'].split(':')[0]) + int(config['end_time'].split(':')[1])/60
    break_start_hour = int(config['break_start'].split(':')[0]) + int(config['break_start'].split(':')[1])/60
    break_end_hour = int(config['break_end'].split(':')[0]) + int(config['break_end'].split(':')[1])/60
    
    # Build work hours dict
    work_hours = {
        'start': start_hour,
        'end': end_hour,
        'break_start': break_start_hour,
        'break_end': break_end_hour,
        'work_days': []
    }
    
    # Determine work days based on configured hours > 0
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for i, day in enumerate(days):
        if config[f'{day}_hours'] > 0:
            work_hours['work_days'].append(i)
    
    # Use existing calculate_work_minutes function with user-specific hours
    return calculate_work_minutes(start_time, end_time, work_hours)

# Add API endpoints for work hours configuration
@app.route('/api/work_hours/<user>', methods=['GET'])
def get_work_hours(user):
    """Get work hours configuration for a user"""
    try:
        config = get_user_work_config(user)
        return jsonify({
            'success': True,
            'work_hours': config
        })
    except Exception as e:
        logging.error(f"Error getting work hours: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/work_hours/<user>', methods=['POST'])
def update_work_hours(user):
    """Update work hours configuration for a user"""
    try:
        data = request.get_json()
        cursor = get_db().cursor()
        
        # Build update query
        update_fields = []
        values = []
        
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            field = f'{day}_hours'
            if field in data:
                update_fields.append(f"{field} = ?")
                values.append(float(data[field]))
        
        for field in ['start_time', 'end_time', 'break_start', 'break_end']:
            if field in data:
                update_fields.append(f"{field} = ?")
                values.append(data[field])
        
        for field in ['efficiency_high_threshold', 'efficiency_medium_threshold']:
            if field in data:
                update_fields.append(f"{field} = ?")
                values.append(float(data[field]))
        
        if update_fields:
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(user)
            
            query = f"""
                UPDATE work_hours_config 
                SET {', '.join(update_fields)}
                WHERE user = ?
            """
            
            cursor.execute(query, values)
            get_db().commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Error updating work hours: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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

@app.route('/session/start', methods=['POST'])
def start_session():
    """Start a new work session - with work hours validation"""
    data = request.get_json(force=True)
    
    # Check if within work hours
    is_work_time, message = get_current_work_status()
    if not is_work_time:
        return jsonify({
            'success': False, 
            'error': f'Kan geen sessie starten: {message}',
            'work_time': False
        }), 400
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        # Close any active sessions for this user
        c.execute("""
            SELECT start_time FROM sessions 
            WHERE user = ? AND status = 'active'
        """, (data['user'],))
        
        active_session = c.fetchone()
        if active_session:
            work_minutes = calculate_work_minutes(active_session['start_time'], data['timestamp'])
            c.execute("""
                UPDATE sessions 
                SET status = 'completed', 
                    end_time = ?,
                    work_duration_minutes = ?
                WHERE session_id = ? AND status = 'active'
            """, (data['timestamp'], work_minutes, active_session['session_id']))
        
        # Create new session
        session_type = data.get('session_type', 'SCANNER')  # Default to SCANNER for scanner panel
        project = data.get('project', '')  # Get project if provided
        c.execute("""
            INSERT INTO sessions (session_id, user, project, start_time, status, session_type)
            VALUES (?, ?, ?, ?, 'active', ?)
        """, (data['session_id'], data['user'], project, data['timestamp'], session_type))
        
        # IMPORTANT: Also log SESSION_START event in logs table for tracking
        c.execute("""
            INSERT INTO logs (timestamp, event, user, session_id, details)
            VALUES (?, 'SESSION_START', ?, ?, ?)
        """, (data['timestamp'], data['user'], data['session_id'], f"Scanner session started"))
        
        conn.commit()
        logging.info(f"Session started for {data['user']}: {data['session_id']}")
        return jsonify({'success': True, 'session_id': data['session_id']})
        
    except Exception as e:
        logging.error(f"Error starting session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/project_session/start', methods=['POST'])
def start_project_session():
    """Start a new global project session for production time tracking"""
    data = request.get_json(force=True)
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        # Create a project session that will track all projects scanned during this session
        # We'll create individual project entries when projects are actually scanned
        session_id = data['session_id']
        start_time = data['timestamp']
        
        # Log the project session start event
        c.execute("""
            INSERT INTO logs (timestamp, event, user, session_id, details)
            VALUES (?, ?, ?, ?, ?)
        """, (start_time, 'PROJECT_SESSION_START', data['user'], session_id, data.get('details', 'Global project session started')))
        
        conn.commit()
        logging.info(f"Project session started: {session_id}")
        return jsonify({'success': True, 'session_id': session_id})
        
    except Exception as e:
        logging.error(f"Error starting project session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/session/end', methods=['POST'])
def end_session():
    """End an active session"""
    data = request.get_json(force=True)
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        # Get session start time
        c.execute("""
            SELECT start_time FROM sessions 
            WHERE session_id = ? AND status = 'active'
        """, (data['session_id'],))
        
        session = c.fetchone()
        if session:
            # Calculate total work minutes
            total_minutes = calculate_work_minutes(session['start_time'], data['timestamp'])
            
            # Subtract pause duration if provided (convert seconds to minutes)
            pause_duration_minutes = data.get('total_pause_duration', 0) / 60.0
            actual_work_minutes = max(0, total_minutes - pause_duration_minutes)
            
            # Calculate total items processed during this session
            # Get all OPEN events for this user during the session timeframe
            c.execute("""
                SELECT user FROM sessions WHERE session_id = ?
            """, (data['session_id'],))
            session_info = c.fetchone()
            
            total_items = 0
            if session_info:
                user = session_info['user']
                c.execute("""
                    SELECT SUM(COALESCE(item_count, 0)) as total_items
                    FROM logs 
                    WHERE user = ? 
                    AND event = 'OPEN' 
                    AND timestamp >= ?
                    AND timestamp <= ?
                    AND item_count > 0
                """, (user, session['start_time'], data['timestamp']))
                
                result = c.fetchone()
                total_items = result['total_items'] if result and result['total_items'] else 0
            
            c.execute("""
                UPDATE sessions 
                SET status = 'completed', 
                    end_time = ?,
                    work_duration_minutes = ?,
                    item_count = ?
                WHERE session_id = ? AND status = 'active'
            """, (data['timestamp'], actual_work_minutes, total_items, data['session_id']))
            
            conn.commit()
            logging.info(f"Session ended: {data['session_id']}")
            
            # Trigger efficiency update when session ends
            try:
                trigger_efficiency_update_on_session_end()
            except Exception as e:
                logging.warning(f"Failed to update efficiency on session end: {e}")
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
    except Exception as e:
        logging.error(f"Error ending session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/session/xlsx_updated', methods=['POST'])
def xlsx_updated():
    """Handle XLSX update event - start session for secondary user and change status to BEZIG"""
    data = request.get_json(force=True)
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        # Check if session already exists for this user/project
        c.execute("""
            SELECT session_id FROM sessions 
            WHERE user = ? AND project = ? AND status = 'active'
        """, (data['user'], data['project']))
        
        existing = c.fetchone()
        if not existing:
            # Create new ACTIVE session (work is starting now)
            session_id = f"{data['user']}_{data['project']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            c.execute("""
                INSERT INTO sessions (session_id, user, project, start_time, status, item_count, session_type)
                VALUES (?, ?, ?, ?, 'active', 0, 'XLSX_UPDATED')
            """, (session_id, data['user'], data['project'], data['timestamp']))
            
            # Create project session for this specific project using session start time
            # Find the session start time for the current user's active session
            c.execute("""
                SELECT start_time FROM sessions 
                WHERE user = ? AND status = 'active' AND session_type = 'SCANNER'
                ORDER BY start_time DESC LIMIT 1
            """, (data['user'],))
            
            session_result = c.fetchone()
            project_start_time = session_result['start_time'] if session_result else data['timestamp']
            
            # Create project session entry with session start time
            c.execute("""
                INSERT OR IGNORE INTO project_sessions (project, start_time, status)
                VALUES (?, ?, 'active')
            """, (data['project'], project_start_time))
            
            # Update project status from OPEN to BEZIG in project_log table (most recent entry)
            c.execute("""
                UPDATE project_log 
                SET event = 'BEZIG', timestamp = ?, user = ?
                WHERE id = (
                    SELECT id FROM project_log 
                    WHERE project = ? AND event = 'OPEN'
                    ORDER BY id DESC LIMIT 1
                )
            """, (data['timestamp'], data['user'], data['project']))
            
            # Insert BEZIG event in project_log for tracking
            c.execute("""
                INSERT INTO project_log (project, event, user, timestamp, item_count)
                VALUES (?, 'BEZIG', ?, ?, ?)
            """, (data['project'], data['user'], data['timestamp'], data.get('item_count', 0)))
            
            # Update the corresponding OPEN log to BEZIG status (like PROJECT_START does)
            c.execute("""
                UPDATE logs 
                SET status = 'BEZIG'
                WHERE event = 'OPEN' AND status = 'OPEN' AND project = ? AND user = ?
            """, (data['project'], data['user']))
            
            if c.rowcount > 0:
                logging.info(f"Updated {c.rowcount} 'OPEN' log(s) to 'BEZIG' for user '{data['user']}' on project '{data['project']}'.")
            
            # ALSO insert PROJECT_START event into logs table so logs_project page can see the activity
            c.execute("""
                INSERT INTO logs (timestamp, event, details, project, user, status, session_id)
                VALUES (?, 'PROJECT_START', ?, ?, ?, 'BEZIG', ?)
            """, (data['timestamp'], f"XLSX_UPDATED: {data.get('item_count', 0)} items", 
                  data['project'], data['user'], session_id))
            
            conn.commit()
            logging.info(f"XLSX_UPDATED session started for {data['user']} on project {data['project']} - Status changed to BEZIG")
            
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Error handling XLSX update: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/session/manual_start', methods=['POST'])
def start_manual_session():
    """Start a manual session for projects without XLSX processing"""
    try:
        data = request.get_json()
        required_fields = ['user', 'project', 'timestamp']
        
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Generate session ID
        session_id = f"{data['user']}_{data['project']}_{data['timestamp'].replace(':', '').replace('-', '').replace(' ', '_')}"
        
        conn = get_db()
        c = conn.cursor()
        
        # Check if there's already an active session for this user/project
        c.execute("""
            SELECT session_id FROM sessions 
            WHERE user = ? AND project = ? AND status = 'active'
        """, (data['user'], data['project']))
        
        existing_session = c.fetchone()
        if existing_session:
            return jsonify({'success': False, 'error': 'Session already active for this project'}), 400
        
        # Create new manual session
        c.execute("""
            INSERT INTO sessions (session_id, user, project, start_time, status, item_count, session_type)
            VALUES (?, ?, ?, ?, 'active', 0, 'MANUAL')
        """, (session_id, data['user'], data['project'], data['timestamp']))
        
        # Update project status from OPEN to BEZIG in project_log table (most recent entry)
        c.execute("""
            UPDATE project_log 
            SET event = 'BEZIG', timestamp = ?, user = ?
            WHERE id = (
                SELECT id FROM project_log 
                WHERE project = ? AND event = 'OPEN'
                ORDER BY id DESC LIMIT 1
            )
        """, (data['timestamp'], data['user'], data['project']))
        
        conn.commit()
        conn.close()
        
        logging.info(f"Manual session started for {data['user']} on project {data['project']} - Status changed to BEZIG")
        
        return jsonify({'success': True, 'session_id': session_id})
        
    except Exception as e:
        logging.error(f"Error starting manual session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/session/manual_finish', methods=['POST'])
def finish_manual_session():
    """Finish a manual session with final item count"""
    try:
        data = request.get_json()
        required_fields = ['user', 'project', 'item_count', 'timestamp']
        
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Find active manual session
        c.execute("""
            SELECT session_id, start_time FROM sessions 
            WHERE user = ? AND project = ? AND status = 'active' AND session_type = 'MANUAL'
        """, (data['user'], data['project']))
        
        session = c.fetchone()
        if not session:
            return jsonify({'success': False, 'error': 'No active manual session found'}), 400
        
        # Calculate work duration
        work_minutes = calculate_work_minutes(session['start_time'], data['timestamp'])
        
        # Update session with final data
        c.execute("""
            UPDATE sessions 
            SET status = 'completed',
                end_time = ?,
                work_duration_minutes = ?,
                item_count = ?
            WHERE session_id = ?
        """, (data['timestamp'], work_minutes, data['item_count'], session['session_id']))
        
        conn.commit()
        conn.close()
        
        logging.info(f"Manual session finished for {data['user']} on project {data['project']} with {data['item_count']} items")
        
        return jsonify({'success': True, 'work_minutes': work_minutes})
        
    except Exception as e:
        logging.error(f"Error finishing manual session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/session/pause', methods=['POST'])
def pause_session():
    """Pause an active session"""
    try:
        data = request.get_json()
        required_fields = ['session_id', 'timestamp']
        
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Check if session exists and is active
        c.execute("""
            SELECT session_id, user, project FROM sessions 
            WHERE session_id = ? AND status = 'active'
        """, (data['session_id'],))
        
        session = c.fetchone()
        if not session:
            return jsonify({'success': False, 'error': 'Session not found or already ended'}), 404
        
        # Log the pause event
        c.execute("""
            INSERT INTO logs (timestamp, event, user, session_id, project, details)
            VALUES (?, 'SESSION_PAUSE', ?, ?, ?, ?)
        """, (data['timestamp'], session['user'], data['session_id'], session['project'], 
              'Session paused - switched to different panel'))
        
        conn.commit()
        logging.info(f"Session paused: {data['session_id']}")
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Error pausing session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/session/resume', methods=['POST'])
def resume_session():
    """Resume a paused session"""
    try:
        data = request.get_json()
        required_fields = ['session_id', 'timestamp']
        
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Check if session exists and is active
        c.execute("""
            SELECT session_id, user, project FROM sessions 
            WHERE session_id = ? AND status = 'active'
        """, (data['session_id'],))
        
        session = c.fetchone()
        if not session:
            return jsonify({'success': False, 'error': 'Session not found or already ended'}), 404
        
        # Log the resume event
        pause_duration = data.get('total_pause_duration', 0)
        c.execute("""
            INSERT INTO logs (timestamp, event, user, session_id, project, details)
            VALUES (?, 'SESSION_RESUME', ?, ?, ?, ?)
        """, (data['timestamp'], session['user'], data['session_id'], session['project'], 
              f'Session resumed - total pause time: {pause_duration:.1f} seconds'))
        
        conn.commit()
        logging.info(f"Session resumed: {data['session_id']} (total pause: {pause_duration:.1f}s)")
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Error resuming session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
    session_id = data.get('session_id')
    timestamp = data.get('timestamp', datetime.now().isoformat())
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
        elif event == 'PROJECT_START':
            status = 'BEZIG'
            # Update the corresponding OPEN log to BEZIG status
            c.execute(
                'UPDATE logs SET status = ? WHERE event = ? AND status = ? AND lower(project) = ? AND user = ?',
                ('BEZIG', 'OPEN', 'OPEN', project.lower(), user)
            )
            if c.rowcount > 0:
                logging.info(f"Updated {c.rowcount} 'OPEN' log(s) to 'BEZIG' for user '{user}' on project '{project}'.")
        elif event == 'AFGEMELD':
            status = 'AFGEMELD'
            # Find the corresponding 'OPEN' log and update its status to 'CLOSED'
            c.execute(
                'UPDATE logs SET status = ? WHERE event = ? AND status = ? AND lower(project) = ? AND user = ?',
                ('CLOSED', 'OPEN', 'OPEN', project.lower(), user)
            )
            if c.rowcount > 0:
                logging.info(f"Closed {c.rowcount} 'OPEN' log(s) for user '{user}' on project '{project}'.")
            
            # Handle session completion for AFGEMELD events
            # SCANNER sessions (batch) should remain active until manually stopped
            # XLSX_UPDATED/MANUAL sessions should complete on AFGEMELD
            
            # Find active sessions for this user/project
            c.execute("""
                SELECT session_id, start_time, session_type FROM sessions 
                WHERE user = ? AND project = ? AND status = 'active'
            """, (user, project))
            
            active_sessions = c.fetchall()
            for session in active_sessions:
                session_type = session['session_type']
                
                if session_type in ['XLSX_UPDATED', 'MANUAL']:
                    # Complete individual work sessions on AFGEMELD
                    work_minutes = calculate_work_minutes(session['start_time'], timestamp)
                    
                    c.execute("""
                        UPDATE sessions 
                        SET status = 'completed',
                            end_time = ?,
                            work_duration_minutes = ?,
                            item_count = ?
                        WHERE session_id = ? AND status = 'active'
                    """, (timestamp, work_minutes, item_count or 0, session['session_id']))
                    
                    logging.info(f"Completed {session_type} session {session['session_id']} for {user} on project {project}")
                
                elif session_type == 'SCANNER':
                    # SCANNER sessions remain active - do not complete
                    logging.info(f"SCANNER session {session['session_id']} remains active for {user} during AFGEMELD on {project}")
                
                else:
                    # Other session types - complete them
                    work_minutes = calculate_work_minutes(session['start_time'], timestamp)
                    
                    c.execute("""
                        UPDATE sessions 
                        SET status = 'completed',
                            end_time = ?,
                            work_duration_minutes = ?
                        WHERE session_id = ? AND status = 'active'
                    """, (timestamp, work_minutes, session['session_id']))
                    
                    logging.info(f"Completed {session_type} session {session['session_id']} for {user} on project {project}")
            
            # Check if all users have completed for this project
            c.execute("""
                SELECT COUNT(*) as active_count 
                FROM sessions 
                WHERE project = ? AND status = 'active'
            """, (project,))
            
            result = c.fetchone()
            active_count = result['active_count'] if result else 0
            
            if active_count == 0:
                # All users done - complete project session
                c.execute("""
                    UPDATE project_sessions 
                    SET status = 'completed',
                        end_time = ?,
                        total_duration_minutes = (julianday(?) - julianday(start_time)) * 24 * 60
                    WHERE project = ? AND status = 'active'
                """, (timestamp, timestamp, project))
                
                # Calculate individual user durations
                c.execute("""
                    UPDATE project_sessions 
                    SET nesting_duration_minutes = (
                        SELECT SUM(work_duration_minutes) 
                        FROM sessions 
                        WHERE project = ? AND user = 'NESTING'
                    ),
                    opus_duration_minutes = (
                        SELECT SUM(work_duration_minutes) 
                        FROM sessions 
                        WHERE project = ? AND user = 'OPUS'
                    ),
                    gannomat_duration_minutes = (
                        SELECT SUM(work_duration_minutes) 
                        FROM sessions 
                        WHERE project = ? AND user = 'KL GANNOMAT'
                    ),
                    total_items = (
                        SELECT SUM(item_count) 
                        FROM sessions 
                        WHERE project = ?
                    )
                    WHERE project = ?
                """, (project, project, project, project, project))

        # Extract nesting and opdeelzaag counts from item_count for NESTING users
        nesting_count = 0
        opdeelzaag_count = 0
        if user == 'NESTING' and item_count:
            # For NESTING users, item_count contains total, nesting_count and opdeelzaag_count will be filled by PDF parsing
            nesting_count = data.get('nesting_count', 0)
            opdeelzaag_count = data.get('opdeelzaag_count', 0)
        
        # Extract metadata fields
        mo_number = data.get('mo_number')
        so_number = data.get('so_number')
        customer_name = data.get('customer_name')
        color = data.get('color')
        
        c.execute(
            '''INSERT INTO logs (timestamp, event, details, project, user, status, base_mo_code, is_rep_variant, 
               file_path, item_count, nesting_count, opdeelzaag_count, session_id, mo_number, so_number, 
               customer_name, color) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (timestamp, event, details, project, user, status, base_mo_code, is_rep_variant, file_path, 
             item_count, nesting_count, opdeelzaag_count, session_id, mo_number, so_number, customer_name, color)
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Log entry created.'}), 201
    except sqlite3.Error as e:
        logging.error(f"Database error on /log: {e}", exc_info=True)
        return jsonify({'error': 'Database operation failed'}), 500

@app.route('/api/project/<project>/sessions', methods=['GET'])
def get_project_sessions(project):
    """Get all sessions for a specific project"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("""
            SELECT 
                session_id,
                user,
                project,
                start_time,
                end_time,
                status,
                item_count,
                work_duration_minutes
            FROM sessions
            WHERE project = ?
            ORDER BY start_time ASC
        """, (project,))
        
        sessions = []
        for row in c.fetchall():
            sessions.append(dict(row))
        
        return jsonify({
            'success': True,
            'sessions': sessions
        })
        
    except Exception as e:
        logging.error(f"Error getting project sessions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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


@app.route('/project/metadata', methods=['POST'])
def update_project_metadata():
    """Update project metadata including color, MO number, SO number, and customer name."""
    data = request.get_json(force=True)
    logging.info(f"[db_log_api] /project/metadata called with data: {data}")

    project = data.get('project')
    mo_number = data.get('mo_number')
    so_number = data.get('so_number')
    customer_name = data.get('customer_name')
    color = data.get('color')
    
    if not project:
        return jsonify({'success': False, 'error': 'Missing project field'}), 400

    try:
        conn = get_db()
        c = conn.cursor()
        
        # First, check if the logs table has the required columns
        c.execute("PRAGMA table_info(logs)")
        columns = [row[1] for row in c.fetchall()]
        
        # Add missing columns if they don't exist
        if 'mo_number' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN mo_number TEXT')
            logging.info("Added mo_number column to logs table")
        
        if 'so_number' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN so_number TEXT')
            logging.info("Added so_number column to logs table")
            
        if 'customer_name' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN customer_name TEXT')
            logging.info("Added customer_name column to logs table")
            
        if 'color' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN color TEXT')
            logging.info("Added color column to logs table")
        
        # Update all OPEN events for this project with the metadata
        update_fields = []
        update_values = []
        
        if mo_number:
            update_fields.append("mo_number = ?")
            update_values.append(mo_number)
        if so_number:
            update_fields.append("so_number = ?")
            update_values.append(so_number)
        if customer_name:
            update_fields.append("customer_name = ?")
            update_values.append(customer_name)
        if color:
            update_fields.append("color = ?")
            update_values.append(color)
        
        if update_fields:
            update_values.append(project)  # Add project for WHERE clause
            
            update_query = f'''
                UPDATE logs 
                SET {", ".join(update_fields)}
                WHERE project = ? AND event = 'OPEN'
            '''
            
            c.execute(update_query, update_values)
            conn.commit()
            
            updated_count = c.rowcount
            if updated_count > 0:
                logging.info(f"Updated project metadata for {updated_count} records in project {project}")
                return jsonify({'success': True, 'message': f'Updated {updated_count} records'}), 200
            else:
                logging.warning(f"No OPEN events found for project {project}")
                return jsonify({'success': False, 'error': 'No matching project found'}), 404
        else:
            return jsonify({'success': False, 'error': 'No metadata provided'}), 400
            
    except sqlite3.Error as e:
        logging.error(f"Database error on /project/metadata: {e}", exc_info=True)
        return jsonify({'error': 'Database operation failed'}), 500

@app.route('/update_nesting_counts', methods=['POST'])
def update_nesting_counts():
    """Update the nesting_count and opdeelzaag_count for an existing OPEN event."""
    data = request.get_json(force=True)
    logging.info(f"[db_log_api] /update_nesting_counts called with data: {data}")

    project = data.get('project')
    user = data.get('user')
    nesting_count = data.get('nesting_count', 0)
    opdeelzaag_count = data.get('opdeelzaag_count', 0)
    
    # Calculate consolidated item_count
    item_count = nesting_count + opdeelzaag_count
    
    if not all([project, user]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    try:
        conn = get_db()
        c = conn.cursor()
        
        # Update the most recent OPEN event for this user/project combination
        # Update both separate counts (for backward compatibility) and consolidated item_count
        c.execute('''
            UPDATE logs 
            SET nesting_count = ?, opdeelzaag_count = ?, item_count = ?
            WHERE id = (
                SELECT id FROM logs 
                WHERE event = 'OPEN' 
                AND status = 'OPEN'
                AND project = ? 
                AND user = ?
                ORDER BY timestamp DESC 
                LIMIT 1
            )
        ''', (nesting_count, opdeelzaag_count, item_count, project, user))
        
        conn.commit()
        
        if c.rowcount > 0:
            logging.info(f"Updated nesting counts for {user} - {project}: Nesting={nesting_count}, Opdeelzaag={opdeelzaag_count}, Total={item_count}")
            return jsonify({'success': True, 'updated_rows': c.rowcount})
        else:
            logging.warning(f"No OPEN event found to update nesting counts for {user} - {project}")
            return jsonify({'success': False, 'error': 'No OPEN event found to update'}), 404
            
    except Exception as e:
        logging.error(f"Database error on /update_nesting_counts: {e}", exc_info=True)
        return jsonify({'error': 'Database operation failed'}), 500

@app.route('/update_item_count', methods=['POST'])
def update_item_count():
    """Update the item_count for an existing OPEN event (consolidated approach)."""
    data = request.get_json(force=True)
    logging.info(f"[db_log_api] /update_item_count called with data: {data}")

    project = data.get('project')
    user = data.get('user')
    item_count = data.get('item_count', 0)
    
    # For NESTING compatibility, also extract separate counts if provided
    nesting_count = data.get('nesting_count', 0)
    opdeelzaag_count = data.get('opdeelzaag_count', 0)
    
    if not all([project, user]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    try:
        conn = get_db()
        c = conn.cursor()
        
        # Update the most recent OPEN event for this user/project combination
        c.execute('''
            UPDATE logs 
            SET item_count = ?, nesting_count = ?, opdeelzaag_count = ?
            WHERE id = (
                SELECT id FROM logs 
                WHERE event = 'OPEN' 
                AND status IN ('OPEN', 'CLOSED')
                AND project = ? 
                AND user = ?
                ORDER BY timestamp DESC 
                LIMIT 1
            )
        ''', (item_count, nesting_count, opdeelzaag_count, project, user))
        
        conn.commit()
        
        if c.rowcount > 0:
            logging.info(f"Updated item count for {user} - {project}: Total={item_count} (Nesting={nesting_count}, Opdeelzaag={opdeelzaag_count})")
            return jsonify({'success': True, 'updated_rows': c.rowcount})
        else:
            logging.warning(f"No OPEN event found to update item count for {user} - {project}")
            return jsonify({'success': False, 'error': 'No OPEN event found to update'}), 404
            
    except Exception as e:
        logging.error(f"Database error on /update_item_count: {e}", exc_info=True)
        return jsonify({'error': 'Database operation failed'}), 500

@app.route('/update_accura_counts', methods=['POST'])
def update_accura_counts():
    """Update the aantal_items and aantal_sides for an existing OPEN event using consolidated approach."""
    data = request.get_json(force=True)
    logging.info(f"[db_log_api] /update_accura_counts called with data: {data}")

    project = data.get('project')
    user = data.get('user')
    
    # Support both old (aantal_items) and new (item_count) input
    item_count = data.get('item_count', data.get('aantal_items', 0))
    aantal_items = data.get('aantal_items', item_count)  # For backward compatibility
    aantal_sides = data.get('aantal_sides', 0)
    
    if not all([project, user]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    try:
        conn = get_db()
        c = conn.cursor()
        
        # Update the most recent OPEN event for this user/project combination
        # Update both item_count (consolidated) and aantal_items (backward compatibility)
        c.execute('''
            UPDATE logs 
            SET item_count = ?, aantal_items = ?, aantal_sides = ?
            WHERE id = (
                SELECT id FROM logs 
                WHERE event = 'OPEN' 
                AND status = 'OPEN'
                AND project = ? 
                AND user = ?
                ORDER BY timestamp DESC 
                LIMIT 1
            )
        ''', (item_count, aantal_items, aantal_sides, project, user))
        
        conn.commit()
        
        if c.rowcount > 0:
            logging.info(f"Updated accura counts for {user} - {project}: Total={item_count}, Items={aantal_items}, Sides={aantal_sides}")
            return jsonify({'success': True, 'updated_rows': c.rowcount})
        else:
            logging.warning(f"No OPEN event found to update accura counts for {user} - {project}")
            return jsonify({'success': False, 'error': 'No OPEN event found to update'}), 404
            
    except Exception as e:
        logging.error(f"Database error on /update_accura_counts: {e}", exc_info=True)
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
        
        # Clear all project and session data for complete reset
        tables_to_clear = ['logs', 'sessions', 'project_sessions']
        
        for table in tables_to_clear:
            try:
                c.execute(f'DELETE FROM {table}')
                logging.info(f"Cleared table: {table}")
            except sqlite3.Error as table_error:
                logging.warning(f"Could not clear table {table}: {table_error}")
                # Continue with other tables even if one fails
        
        conn.commit()
        logging.info("All database tables cleared successfully.")
        return jsonify({'success': True, 'message': 'All logs and statistics data cleared successfully.'}), 200
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
# Update the dashboard route in db_log_api.py to calculate metrics server-side

@app.route('/')
@app.route('/dashboard')
def dashboard():
    try:
        # Get configuration
        config = get_config()
        
        # Get configured users for display
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
        
        # Query all OPEN/BEZIG projects (regardless of date) and today's AFGEMELD projects
        c.execute("""
            SELECT * FROM logs 
            WHERE 
                ((status = 'OPEN' OR status = 'BEZIG') AND event = 'OPEN')  -- All open/active projects regardless of date
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
                logging.debug(f"Adding empty project list for dashboard user: {user}")
        
        # --- SERVER-SIDE METRICS CALCULATION ---
        # Calculate metrics using the same logic as projects.html
        
        # Get all unique projects
        c.execute("""
            SELECT DISTINCT project
            FROM logs
            WHERE project IS NOT NULL AND project != ''
        """)
        all_projects = [row['project'] for row in c.fetchall()]
        
        total_projects = 0
        active_projects = 0
        completed_today = 0
        
        for project_code in all_projects:
            # Determine the project status using the helper function
            try:
                result = determine_project_status(project_code, conn)
                if len(result) != 2:
                    logging.error(f"determine_project_status returned {len(result)} values for project {project_code}: {result}")
                    continue
                project_status, current_user = result
            except ValueError as e:
                logging.error(f"Error unpacking result for project {project_code}: {e}")
                continue
            
            total_projects += 1
            
            if project_status in ['OPEN', 'BEZIG']:
                active_projects += 1
            elif project_status in ['AFGEMELD', 'AFGEROND']:
                # Check if completed today
                c.execute("""
                    SELECT MAX(timestamp) as latest_timestamp
                    FROM logs
                    WHERE project = ? AND event = 'AFGEMELD'
                """, (project_code,))
                
                result = c.fetchone()
                if result and result['latest_timestamp']:
                    try:
                        dt = datetime.fromisoformat(result['latest_timestamp'])
                        if dt.date() == today:
                            completed_today += 1
                    except:
                        pass
        
        # Calculate daily repairs using is_rep_variant logic
        c.execute("""
            SELECT COUNT(DISTINCT project) as repair_count
            FROM logs
            WHERE is_rep_variant = 1 
            AND event = 'AFGEMELD'
            AND DATE(timestamp) = ?
        """, (today.isoformat(),))
        
        repair_result = c.fetchone()
        repairs_today = repair_result['repair_count'] if repair_result else 0
        
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
                             configured_users=dashboard_users,
                             logs=logs_list,
                             total_projects=total_projects,
                             active_projects=active_projects,
                             completed_today=completed_today,
                             repairs_today=repairs_today,
                             active_page='dashboard')
                             
    except Exception as e:
        logging.error(f"Dashboard error: {str(e)}", exc_info=True)
        return render_template('error.html', message=str(e)), 500
        

# --- API Endpoints ---
@app.route('/api/configured_users')
def get_configured_users():
    config = get_config()
    users = config.get('scanner_panel_open_event_users', [])
    return jsonify({
        'success': True,
        'users': users
    })

@app.route('/api/config')
def get_config_api():
    """Get relevant configuration for frontend use"""
    config = get_config()
    # Return only the necessary config fields for security
    return jsonify({
        'scanner_user_to_processing_type_map': config.get('scanner_user_to_processing_type_map', {}),
        'scanner_panel_open_event_users': config.get('scanner_panel_open_event_users', [])
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
            'users': config.get('scanner_panel_open_event_users', [])
        })
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            users = data.get('users', [])
            
            # Validate users list
            if not isinstance(users, list):
                return jsonify({'success': False, 'error': 'Users must be a list'}), 400
            
            # Save to config
            save_config({'scanner_panel_open_event_users': users})
            
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
        
        # This endpoint is no longer needed since we use one unified array
        return jsonify({'success': True, 'message': 'Using unified scanner_panel_open_event_users array'})
        
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
        
        # Get session-based completion times (actual work time)
        query = """
            WITH ProjectCompletions AS (
                SELECT 
                    s.user,
                    s.project,
                    s.start_time,
                    s.end_time,
                    s.work_duration_minutes as completion_minutes,
                    DATE(s.start_time) as project_date,
                    s.session_type,
                    s.item_count
                FROM sessions s
                WHERE 
                    s.status = 'completed'
                    AND s.user IS NOT NULL 
                    AND s.user != ''
                    AND s.work_duration_minutes > 0
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
                    {dynamic_order_cases}
                    ELSE 999 
                END
        """
        
        # Build dynamic ORDER BY cases based on configured users
        config = get_config()
        configured_users = config.get('scanner_panel_open_event_users', [])
        dynamic_order_cases = ""
        for i, user in enumerate(configured_users, 1):
            dynamic_order_cases += f"WHEN '{user}' THEN {i} "
        
        # Replace placeholder in query
        query = query.format(dynamic_order_cases=dynamic_order_cases)
        
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
                s.project,
                s.start_time,
                s.end_time,
                s.work_duration_minutes as completion_minutes,
                DATE(s.start_time) as project_date,
                s.session_type,
                s.item_count,
                s.status
            FROM sessions s
            WHERE 
                s.user = ?
                AND DATE(s.start_time) >= date('now', '-' || ? || ' days')
            ORDER BY s.start_time DESC
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
        
        # Get historical average from sessions (actual work time)
        history_query = """
            SELECT 
                AVG(work_duration_minutes) as avg_completion,
                COUNT(*) as sample_size,
                MIN(work_duration_minutes) as best_time,
                MAX(work_duration_minutes) as worst_time
            FROM sessions s
            WHERE 
                s.user = ?
                AND s.status = 'completed'
                AND s.work_duration_minutes > 0
            ORDER BY s.start_time DESC
            LIMIT 20  -- Use last 20 sessions
        """
        
        c.execute(history_query, (user,))
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
        
        # Get comprehensive performance metrics from sessions
        session_where_clause = where_clause.replace('o.timestamp', 's.start_time').replace('o.user', 's.user')
        query = f"""
            WITH CompletionData AS (
                SELECT 
                    s.user,
                    s.project,
                    DATE(s.start_time) as project_date,
                    s.session_type,
                    s.work_duration_minutes as completion_minutes,
                    strftime('%w', s.start_time) as day_of_week,
                    strftime('%H', s.start_time) as hour_of_day,
                    s.item_count
                FROM sessions s
                WHERE 
                    s.status = 'completed'
                    AND {session_where_clause}
                    AND s.work_duration_minutes > 0
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
                -- Session type breakdown
                COUNT(CASE WHEN session_type = 'SCANNER' THEN 1 END) as scanner_count,
                COUNT(CASE WHEN session_type = 'XLSX_UPDATED' THEN 1 END) as xlsx_count,
                COUNT(CASE WHEN session_type = 'MANUAL' THEN 1 END) as manual_count,
                AVG(CASE WHEN session_type = 'SCANNER' THEN completion_minutes END) as avg_scanner_time,
                AVG(CASE WHEN session_type = 'XLSX_UPDATED' THEN completion_minutes END) as avg_xlsx_time,
                AVG(CASE WHEN session_type = 'MANUAL' THEN completion_minutes END) as avg_manual_time,
                SUM(item_count) as total_items
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
        
        # Get time-based patterns from sessions
        pattern_query = f"""
            WITH CompletionData AS (
                SELECT 
                    strftime('%w', s.start_time) as day_of_week,
                    strftime('%H', s.start_time) as hour_of_day,
                    s.work_duration_minutes as completion_minutes
                FROM sessions s
                WHERE 
                    s.status = 'completed'
                    AND {session_where_clause}
                    AND s.work_duration_minutes > 0
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
    initialize_efficiency_tracking()  # Initialize efficiency tracking system
    
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
                INSERT INTO logs (timestamp, event, details, project, user, status, base_mo_code, is_rep_variant, file_path, item_count, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                row.get('item_count'),
                row.get('session_id')
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

@app.route('/logs_project')
def logs_project():
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', [])
    
    project = request.args.get('project', '')
    if not project:
        return render_template('error.html', message='Project parameter is missing.'), 400

    logging.info(f"logs_project endpoint called for project: '{project}'")
    try:
        conn = get_db()
        c = conn.cursor()

        c.execute('SELECT * FROM logs WHERE lower(project) = ? AND event != ? ORDER BY id DESC', (project.lower(), 'AUTO_IMPORT'))
        log_entries = [dict(row) for row in c.fetchall()]

        c.execute('''
            SELECT user, status, timestamp as last_updated
            FROM logs l1
            WHERE lower(project) = ? AND user != ''
            AND timestamp = (
                SELECT MAX(timestamp) 
                FROM logs l2 
                WHERE l2.user = l1.user AND lower(l2.project) = lower(l1.project)
            )
            GROUP BY user
        ''', (project.lower(),))
        user_status_rows = c.fetchall()

        # Build dynamic order based on configured users
        config = get_config()
        configured_users = config.get('scanner_panel_open_event_users', [])
        order = {user: i for i, user in enumerate(configured_users)}
        
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

        # Get work hours configuration
        work_hours_config = WORK_HOURS.copy()
        
        # Get sessions data for this project to provide accurate performance metrics
        # Include both project-specific sessions AND batch sessions for users who worked on this project
        c.execute('''
            SELECT 
                session_id,
                user,
                project,
                start_time,
                end_time,
                status,
                item_count,
                work_duration_minutes,
                session_type
            FROM sessions 
            WHERE (
                lower(project) = ? 
                OR (
                    session_type = 'SCANNER' 
                    AND (project IS NULL OR project = '') 
                    AND user IN (
                        SELECT DISTINCT user FROM logs 
                        WHERE lower(project) = ? 
                        AND user IS NOT NULL AND user != ''
                    )
                )
            )
            ORDER BY start_time ASC
        ''', (project.lower(), project.lower()))
        sessions_data = [dict(row) for row in c.fetchall()]
        
        # Get project metadata (SO number, MO number, customer name, color)
        so_number = None
        mo_number = None
        customer_name = None
        color = None
        
        # First try to get metadata from logs table - prioritize records with the most metadata
        c.execute('''
            SELECT DISTINCT so_number, mo_number, customer_name, color, file_path 
            FROM logs 
            WHERE lower(project) = ?
            ORDER BY 
                CASE WHEN so_number IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN mo_number IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN customer_name IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN color IS NOT NULL THEN 1 ELSE 0 END DESC,
                timestamp DESC
            LIMIT 1
        ''', (project.lower(),))
        row = c.fetchone()
        
        if row:
            so_number = row['so_number'] if row['so_number'] else so_number
            mo_number = row['mo_number'] if row['mo_number'] else mo_number
            customer_name = row['customer_name'] if row['customer_name'] else customer_name
            color = row['color'] if row['color'] else color
            
            # If SO number is missing, try to extract from file path
            if not so_number and row['file_path']:
                import re
                match = re.search(r'(S\d+)', row['file_path'])
                if match:
                    so_number = match.group(1)
        
        # Fallback: try to get SO number from PDF database if available
        if not so_number:
            try:
                import sys
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from pdf_database_manager import PDFDatabaseManager
                pdf_manager = PDFDatabaseManager()
                so_number = pdf_manager.get_so_number_for_project(project)
            except Exception as e:
                logging.info(f"Could not get SO number from PDF database: {e}")
        
        # Additional fallback for file path extraction if still no SO number
        if not so_number:
            c.execute('''
                SELECT DISTINCT file_path FROM logs 
                WHERE lower(project) = ? AND file_path IS NOT NULL AND file_path != ''
                LIMIT 1
            ''', (project.lower(),))
            row = c.fetchone()
            if row and row['file_path']:
                import re
                match = re.search(r'(S\d+)', row['file_path'])
                if match:
                    so_number = match.group(1)
        
        return render_template('logs_project.html', 
                               project=project, 
                               so_number=so_number,
                               mo_number=mo_number,
                               customer_name=customer_name,
                               color=color,
                               log_entries=log_entries, 
                               configured_users=configured_users,
                               user_status_html=user_status_html,
                               all_projects=all_projects,
                               users=users,
                               work_hours=work_hours_config,
                               sessions_data=sessions_data,
                               active_page='projects')

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return render_template('error.html', message='An error occurred while loading the project.'), 500

def determine_project_status(project_code, conn):
    """Determine the current status of a project based on user events.
    Simple logic: OPEN event = OPEN status, BEZIG event = BEZIG status, AFGEMELD event = AFGEMELD status
    
    Args:
        project_code (str): The project code to check
        conn: Database connection
        
    Returns:
        tuple: (status, current_user) where status is one of 'OPEN', 'BEZIG', 'AFGEMELD', or 'AFGEROND'
    """
    c = conn.cursor()
    
    # Get configured users from config
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', [])
    
    # Get all events for this project
    c.execute("""
        SELECT timestamp, event, user, status
        FROM logs
        WHERE project = ?
        ORDER BY timestamp DESC
    """, (project_code,))
    
    events = c.fetchall()
    
    if not events:
        return ('ONBEKEND', None)
    
    # Get the most recent event
    latest_event = events[0]
    
    # Track user events by type (most recent event per user per type)
    user_open_events = {}
    user_bezig_events = {}
    user_afgemeld_events = {}
    involved_users = set()
    
    for event in events:
        user = event['user']
        if not user:
            continue
            
        involved_users.add(user)
        
        # Track most recent event of each type per user
        if event['event'] == 'OPEN' and event['status'] == 'OPEN':
            if user not in user_open_events:
                user_open_events[user] = event
        elif event['status'] == 'BEZIG':
            if user not in user_bezig_events:
                user_bezig_events[user] = event
        elif event['event'] == 'AFGEMELD':
            if user not in user_afgemeld_events:
                user_afgemeld_events[user] = event
    
    # Get involved users in workflow order
    active_workflow_order = [user for user in configured_users if user in involved_users]
    
    # Check if all involved users have completed (AFGEMELD)
    all_completed = all(user in user_afgemeld_events for user in active_workflow_order)
    if all_completed and active_workflow_order:
        return ('AFGEROND', None)
    
    # Priority: BEZIG > OPEN > AFGEMELD
    # Check for any user with BEZIG status
    for user in active_workflow_order:
        if user in user_bezig_events:
            return ('BEZIG', user)
    
    # Check for any user with OPEN status  
    for user in active_workflow_order:
        if user in user_open_events:
            return ('OPEN', user)
    
    # If latest event is AFGEMELD, return that
    if latest_event['event'] == 'AFGEMELD':
        return ('AFGEMELD', latest_event['user'])
    
    # Default fallback
    return ('OPEN', latest_event['user'])

# Update the projects route in db_log_api.py

@app.route('/projects', methods=['GET'])
def projects():
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', [])
    
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
        completed_projects = 0
        in_progress = 0
        rep_variant_projects = 0  # New metric to replace open_projects
        
        for project_code in all_projects:
            # Determine the project status using the helper function
            try:
                result = determine_project_status(project_code, conn)
                if len(result) != 2:
                    logging.error(f"determine_project_status returned {len(result)} values for project {project_code}: {result}")
                    continue
                project_status, current_user = result
            except ValueError as e:
                logging.error(f"Error unpacking result for project {project_code}: {e}")
                continue
            
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
            
            # Check if project is a rep variant
            c.execute("""
                SELECT is_rep_variant
                FROM logs
                WHERE project = ? AND is_rep_variant IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 1
            """, (project_code,))
            
            rep_result = c.fetchone()
            is_rep_variant = rep_result and rep_result['is_rep_variant'] == 1
            
            # Create project entry
            project_dict = {
                'code': project_code,
                'user': current_user or 'Onbekend',
                'status': project_status,
                'timestamp': formatted_timestamp,
                'event_count': event_count,
                'is_rep_variant': is_rep_variant
            }
            
            # Count statuses
            total_projects += 1
            if project_status in ['AFGEMELD', 'AFGEROND']:
                completed_projects += 1
            elif project_status in ['OPEN', 'BEZIG']:
                in_progress += 1
            
            # Count rep variant projects
            if is_rep_variant:
                rep_variant_projects += 1
            
            projects.append(project_dict)
        
        # Sort projects by timestamp (most recent first)
        projects.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return render_template('projects.html', 
                             projects=projects,
                             configured_users=configured_users,
                             total_projects=total_projects,
                             rep_variant_projects=rep_variant_projects,  # New metric
                             completed_projects=completed_projects,
                             in_progress=in_progress,
                             active_page='projects')
    
    except Exception as e:
        logging.error(f"Failed to render projects page: {e}", exc_info=True)
        return render_template('error.html', message='Could not retrieve projects from the database.'), 500
        

@app.route('/users', methods=['GET'])
def users():
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', [])
    
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
    configured_users = config.get('scanner_panel_open_event_users', [])
    
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
    """Statistics page view with comprehensive analytics"""
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', [])
    
    try:
        return render_template('statistics.html',
                             configured_users=configured_users,
                             work_hours=WORK_HOURS,
                             active_page='statistics')
    except Exception as e:
        logging.error(f"Failed to render statistics page: {e}", exc_info=True)
        return render_template('error.html', message='Could not load statistics page.'), 500

@app.route('/settings')
def settings():
    """Settings page for work hours configuration"""
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', [])
    
    try:
        return render_template('settings.html',
                             configured_users=configured_users,
                             active_page='settings')
    except Exception as e:
        logging.error(f"Failed to render settings page: {e}", exc_info=True)
        return render_template('error.html', message='Could not load settings page.'), 500

@app.route('/database', methods=['GET'])
def database():
    config = get_config()
    configured_users = config.get('scanner_panel_open_event_users', [])
    
    logging.info('database management page was called')
    try:
        # Get database stats
        conn = get_db()
        c = conn.cursor()
        
        # Get total records
        c.execute('SELECT COUNT(*) FROM logs')
        total_records = c.fetchone()[0]
        
        # Get database file size
        db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
        
        # Get oldest record
        c.execute('SELECT MIN(timestamp) FROM logs')
        oldest_record = c.fetchone()[0]
        
        return render_template('database.html',
                             configured_users=configured_users,
                             db_size=db_size,
                             total_records=total_records,
                             oldest_record=oldest_record,
                             active_page='database')
    
    except Exception as e:
        logging.error(f"Failed to render database page: {e}", exc_info=True)
        return render_template('error.html', message='Could not load database management page.'), 500

# === ENTERPRISE STATISTICS ENDPOINTS ===

@app.route('/api/statistics/productivity-metrics', methods=['GET'])
def get_productivity_metrics():
    """1. Productivity & Throughput Metrics"""
    try:
        # Handle different period types
        period_type = request.args.get('period_type', 'days')
        
        if period_type == 'custom':
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            date_filter = f"AND DATE(timestamp) BETWEEN '{start_date}' AND '{end_date}'"
            period_display = f"{start_date} tot {end_date}"
        elif period_type == 'all':
            date_filter = ""  # No date filter - all data
            period_display = "Alle data"
        else:
            period = request.args.get('period', '30')  # days
            date_filter = f"AND timestamp >= datetime('now', '-{period} days')"
            period_display = f"Laatste {period} dagen"
            
        conn = get_db()
        c = conn.cursor()
        
        # Overall productivity: Items per hour (total items / total project time)
        c.execute(f"""
            WITH ProjectMetrics AS (
                SELECT 
                    ps.project,
                    ps.total_duration_minutes,
                    COALESCE(ps.total_items, 0) as total_items
                FROM project_sessions ps
                WHERE ps.status = 'completed' {date_filter.replace('timestamp', 'ps.start_time')}
            )
            SELECT 
                ROUND(SUM(total_items) * 60.0 / NULLIF(SUM(total_duration_minutes), 0), 2) as overall_items_per_hour,
                SUM(total_items) as total_items,
                ROUND(SUM(total_duration_minutes) / 60.0, 1) as total_hours
            FROM ProjectMetrics
        """)
        
        result = c.fetchone()
        overall_items_per_hour = result[0] if result and result[0] else 0
        total_items = result[1] if result else 0
        total_hours = result[2] if result else 0
        
        # Items per hour per user with proportional time allocation for batch processing
        c.execute(f"""
            WITH MainSessions AS (
                -- Find all main batch sessions (SCANNER sessions without project)
                SELECT user, session_id, start_time, end_time, work_duration_minutes
                FROM sessions 
                WHERE session_type = 'SCANNER' 
                AND project IS NULL 
                AND status = 'completed'
                {date_filter.replace('timestamp', 'start_time')}
            ),
            BatchAllocation AS (
                SELECT 
                    s.user,
                    s.project,
                    s.session_type,
                    s.item_count,
                    s.work_duration_minutes as original_duration,
                    -- For batch processing (SCANNER), calculate proportional time based on batch session
                    CASE 
                        WHEN s.session_type = 'SCANNER' AND s.project IS NOT NULL THEN
                            -- Get project's proportion of total batch items and allocate time proportionally
                            COALESCE(s.item_count, 0) * 1.0 / NULLIF(
                                (SELECT SUM(COALESCE(s2.item_count, 0)) 
                                 FROM sessions s2
                                 JOIN MainSessions ms ON s2.user = ms.user
                                 WHERE s2.session_type = 'SCANNER'
                                 AND s2.project IS NOT NULL
                                 AND s2.status = 'completed'
                                 AND s2.start_time >= ms.start_time 
                                 AND s2.start_time <= ms.end_time
                                 AND ms.user = s.user
                                 AND s.start_time >= ms.start_time 
                                 AND s.start_time <= ms.end_time
                                ), 0
                            ) * (
                                SELECT ms.work_duration_minutes
                                FROM MainSessions ms
                                WHERE ms.user = s.user
                                AND s.start_time >= ms.start_time 
                                AND s.start_time <= ms.end_time
                                LIMIT 1
                            )
                        ELSE 
                            -- For individual work (XLSX_UPDATED/MANUAL), use actual session time
                            s.work_duration_minutes
                    END as allocated_duration_minutes
                FROM sessions s
                WHERE s.status = 'completed' {date_filter.replace('timestamp', 's.start_time')}
            )
            SELECT 
                user,
                ROUND(SUM(COALESCE(item_count, 0)) * 60.0 / NULLIF(SUM(allocated_duration_minutes), 0), 2) as items_per_hour,
                SUM(COALESCE(item_count, 0)) as total_items,
                ROUND(SUM(allocated_duration_minutes) / 60.0, 1) as session_hours,
                SUM(CASE WHEN session_type = 'MANUAL' THEN COALESCE(item_count, 0) ELSE 0 END) as manual_items,
                SUM(CASE WHEN session_type = 'XLSX_UPDATED' THEN COALESCE(item_count, 0) ELSE 0 END) as auto_items
            FROM BatchAllocation
            GROUP BY user
            HAVING SUM(allocated_duration_minutes) > 0
            ORDER BY items_per_hour DESC
        """)
        
        user_productivity = []
        for row in c.fetchall():
            user_productivity.append({
                'user': row[0],
                'items_per_hour': row[1] or 0,
                'total_items': row[2] or 0,
                'session_hours': row[3] or 0,
                'manual_items': row[4] or 0,
                'auto_items': row[5] or 0
            })
        
        # Average time per item (global)
        avg_time_per_item = (total_hours * 60 / total_items) if total_items > 0 else 0
        
        # Productivity trend over time (last 7 days)
        c.execute(f"""
            SELECT 
                DATE(ps.start_time) as date,
                ROUND(SUM(COALESCE(ps.total_items, 0)) * 60.0 / NULLIF(SUM(ps.total_duration_minutes), 0), 2) as daily_items_per_hour,
                SUM(COALESCE(ps.total_items, 0)) as daily_items
            FROM project_sessions ps
            WHERE ps.status = 'completed' 
            AND ps.start_time >= datetime('now', '-7 days')
            GROUP BY DATE(ps.start_time)
            ORDER BY date
        """)
        
        productivity_trend = []
        for row in c.fetchall():
            productivity_trend.append({
                'date': row[0],
                'items_per_hour': row[1] or 0,
                'items': row[2] or 0
            })
        
        return jsonify({
            'success': True,
            'overall_productivity': {
                'items_per_hour': overall_items_per_hour,
                'total_items': total_items,
                'total_hours': total_hours,
                'avg_time_per_item_minutes': round(avg_time_per_item, 1)
            },
            'user_productivity': user_productivity,
            'productivity_trend': productivity_trend,
            'period_display': period_display,
            'period_type': period_type
        })
        
    except Exception as e:
        logging.error(f"Error getting productivity metrics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
        
        return jsonify({
            'success': True,
            'data': {
                'active_sessions': active_sessions,
                'queue_length': queue_length,
                'completed_today': completed_today,
                'avg_completion_time': avg_completion_time,
                'last_updated': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logging.error(f"Error getting real-time metrics: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/statistics/user-efficiency', methods=['GET'])
def get_user_efficiency():
    """2. User Efficiency & Load Distribution"""
    try:
        # Handle different period types
        period_type = request.args.get('period_type', 'days')
        
        if period_type == 'custom':
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            date_filter = f"AND DATE(timestamp) BETWEEN '{start_date}' AND '{end_date}'"
        elif period_type == 'all':
            date_filter = ""  # No date filter - all data
        else:
            period = request.args.get('period', '30')  # days
            date_filter = f"AND timestamp >= datetime('now', '-{period} days')"
            
        conn = get_db()
        c = conn.cursor()
        
        # User efficiency metrics
        c.execute(f"""
            WITH BatchAllocation AS (
                SELECT 
                    s.user,
                    s.session_type,
                    s.item_count,
                    -- For batch processing (SCANNER), calculate proportional time
                    CASE 
                        WHEN s.session_type = 'SCANNER' THEN
                            COALESCE(s.item_count, 0) * 1.0 / NULLIF(
                                (SELECT SUM(COALESCE(s2.item_count, 0)) 
                                 FROM sessions s2 
                                 WHERE s2.user = s.user 
                                 AND s2.session_type = 'SCANNER'
                                 AND s2.status = 'completed'
                                 AND DATE(s2.start_time) = DATE(s.start_time)
                                ), 0
                            ) * (
                                SELECT SUM(s3.work_duration_minutes) 
                                FROM sessions s3 
                                WHERE s3.user = s.user 
                                AND s3.session_type = 'SCANNER'
                                AND s3.status = 'completed'
                                AND DATE(s3.start_time) = DATE(s.start_time)
                            )
                        ELSE 
                            s.work_duration_minutes
                    END as allocated_duration_minutes
                FROM sessions s
                WHERE s.status = 'completed' {date_filter.replace('timestamp', 's.start_time')}
            )
            SELECT 
                user,
                SUM(COALESCE(item_count, 0)) as items_produced,
                ROUND(SUM(allocated_duration_minutes) / 60.0, 1) as session_hours,
                ROUND(SUM(COALESCE(item_count, 0)) * 60.0 / NULLIF(SUM(allocated_duration_minutes), 0), 2) as efficiency_score
            FROM BatchAllocation
            GROUP BY user
            ORDER BY efficiency_score DESC
        """)
        
        user_stats = []
        total_items = 0
        total_session_time = 0
        
        for row in c.fetchall():
            user_data = {
                'user': row[0],
                'items_produced': row[1] or 0,
                'session_hours': row[2] or 0,
                'efficiency_score': row[3] or 0
            }
            user_stats.append(user_data)
            total_items += user_data['items_produced']
            total_session_time += user_data['session_hours']
        
        # Calculate contribution percentages
        for user in user_stats:
            user['item_contribution_percent'] = round((user['items_produced'] / total_items * 100), 1) if total_items > 0 else 0
            user['time_contribution_percent'] = round((user['session_hours'] / total_session_time * 100), 1) if total_session_time > 0 else 0
        
        # Get scatter plot data (session time vs output)
        scatter_data = []
        for user in user_stats:
            scatter_data.append({
                'user': user['user'],
                'x': user['session_hours'],
                'y': user['items_produced'],
                'efficiency': user['efficiency_score']
            })
        
        return jsonify({
            'success': True,
            'user_efficiency': user_stats,
            'scatter_data': scatter_data,
            'totals': {
                'total_items': total_items,
                'total_session_hours': round(total_session_time, 1)
            },
            'period_type': period_type
        })
        
    except Exception as e:
        logging.error(f"Error getting user efficiency: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/statistics/time-insights', methods=['GET'])
def get_time_insights():
    """3. Time-Based Insights"""
    try:
        # Handle different period types
        period_type = request.args.get('period_type', 'days')
        
        if period_type == 'custom':
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            date_filter = f"AND DATE(start_time) BETWEEN '{start_date}' AND '{end_date}'"
        elif period_type == 'all':
            date_filter = ""  # No date filter - all data
        else:
            period = request.args.get('period', '30')  # days
            date_filter = f"AND start_time >= datetime('now', '-{period} days')"
            
        conn = get_db()
        c = conn.cursor()
        
        # Total Idle Time Estimate: Total Project Time - Sum of Session Times
        c.execute(f"""
            SELECT 
                ROUND(SUM(ps.total_duration_minutes) / 60.0, 1) as total_project_hours,
                ROUND(SUM(COALESCE(ps.nesting_duration_minutes, 0) + 
                         COALESCE(ps.opus_duration_minutes, 0) + 
                         COALESCE(ps.gannomat_duration_minutes, 0)) / 60.0, 1) as total_session_hours
            FROM project_sessions ps
            WHERE ps.status = 'completed' {date_filter}
        """)
        
        result = c.fetchone()
        total_project_hours = result[0] if result and result[0] else 0
        total_session_hours = result[1] if result and result[1] else 0
        idle_time_hours = max(0, total_project_hours - total_session_hours)
        
        # Average item time based on active session vs total time
        c.execute(f"""
            SELECT 
                SUM(COALESCE(ps.total_items, 0)) as total_items,
                ROUND(AVG(ps.total_duration_minutes / NULLIF(ps.total_items, 0)), 1) as avg_time_per_item_total,
                ROUND(AVG((COALESCE(ps.nesting_duration_minutes, 0) + 
                          COALESCE(ps.opus_duration_minutes, 0) + 
                          COALESCE(ps.gannomat_duration_minutes, 0)) / NULLIF(ps.total_items, 0)), 1) as avg_time_per_item_active
            FROM project_sessions ps
            WHERE ps.status = 'completed' {date_filter}
            AND ps.total_items > 0
        """)
        
        time_result = c.fetchone()
        total_items = time_result[0] if time_result else 0
        avg_time_per_item_total = time_result[1] if time_result and time_result[1] else 0
        avg_time_per_item_active = time_result[2] if time_result and time_result[2] else 0
        
        # Cumulative session time over time (last 14 days)
        c.execute(f"""
            SELECT 
                DATE(s.start_time) as date,
                s.user,
                ROUND(SUM(s.work_duration_minutes) / 60.0, 1) as daily_hours
            FROM sessions s
            WHERE s.status = 'completed' 
            AND s.start_time >= datetime('now', '-14 days')
            GROUP BY DATE(s.start_time), s.user
            ORDER BY date, s.user
        """)
        
        cumulative_data = []
        daily_totals = {}
        
        for row in c.fetchall():
            date = row[0]
            user = row[1]
            hours = row[2] or 0
            
            if date not in daily_totals:
                daily_totals[date] = 0
            daily_totals[date] += hours
            
            cumulative_data.append({
                'date': date,
                'user': user,
                'hours': hours
            })
        
        # Convert to cumulative format
        cumulative_timeline = []
        running_total = 0
        for date in sorted(daily_totals.keys()):
            running_total += daily_totals[date]
            cumulative_timeline.append({
                'date': date,
                'cumulative_hours': round(running_total, 1),
                'daily_hours': round(daily_totals[date], 1)
            })
        
        # Efficiency breakdown (productive vs idle time)
        productivity_ratio = (total_session_hours / total_project_hours * 100) if total_project_hours > 0 else 0
        idle_ratio = 100 - productivity_ratio
        
        return jsonify({
            'success': True,
            'time_analysis': {
                'total_project_hours': total_project_hours,
                'total_session_hours': total_session_hours,
                'idle_time_hours': round(idle_time_hours, 1),
                'productivity_ratio': round(productivity_ratio, 1),
                'idle_ratio': round(idle_ratio, 1)
            },
            'item_timing': {
                'total_items': total_items,
                'avg_time_per_item_total_minutes': avg_time_per_item_total,
                'avg_time_per_item_active_minutes': avg_time_per_item_active
            },
            'cumulative_timeline': cumulative_timeline,
            'daily_session_data': cumulative_data,
            'period_type': period_type
        })
        
    except Exception as e:
        logging.error(f"Error getting time insights: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/statistics/bottleneck-analysis', methods=['GET'])
def get_bottleneck_analysis():
    """4. Bottleneck Estimation & Detection with Enhanced Handoff Analysis"""
    try:
        # Handle different period types
        period_type = request.args.get('period_type', 'days')
        
        if period_type == 'custom':
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            date_filter = f"AND DATE(timestamp) BETWEEN '{start_date}' AND '{end_date}'"
            session_filter = f"AND DATE(start_time) BETWEEN '{start_date}' AND '{end_date}'"
        elif period_type == 'all':
            date_filter = ""  # No date filter - all data
            session_filter = ""
        else:
            period = request.args.get('period', '30')  # days
            date_filter = f"AND timestamp >= datetime('now', '-{period} days')"
            session_filter = f"AND start_time >= datetime('now', '-{period} days')"
            
        conn = get_db()
        c = conn.cursor()
        
        # Large discrepancy between project time and session time
        c.execute(f"""
            SELECT 
                ps.project,
                ps.total_duration_minutes / 60.0 as project_hours,
                (COALESCE(ps.nesting_duration_minutes, 0) + 
                 COALESCE(ps.opus_duration_minutes, 0) + 
                 COALESCE(ps.gannomat_duration_minutes, 0)) / 60.0 as session_hours,
                ps.total_items,
                ROUND((ps.total_duration_minutes - 
                      (COALESCE(ps.nesting_duration_minutes, 0) + 
                       COALESCE(ps.opus_duration_minutes, 0) + 
                       COALESCE(ps.gannomat_duration_minutes, 0))) / 60.0, 1) as idle_hours
            FROM project_sessions ps
            WHERE ps.status = 'completed' {date_filter}
            AND ps.total_duration_minutes > 0
            ORDER BY idle_hours DESC
        """)
        
        coordination_delays = []
        for row in c.fetchall():
            project_hours = row[1]
            session_hours = row[2]
            idle_hours = row[4]
            efficiency_ratio = (session_hours / project_hours * 100) if project_hours > 0 else 0
            
            coordination_delays.append({
                'project': row[0],
                'project_hours': round(project_hours, 1),
                'session_hours': round(session_hours, 1),
                'idle_hours': idle_hours,
                'efficiency_ratio': round(efficiency_ratio, 1),
                'total_items': row[3] or 0
            })
        
        # High session time but low item count (potential inefficiency)
        c.execute(f"""
            SELECT 
                s.user,
                AVG(s.work_duration_minutes / 60.0) as avg_session_hours,
                AVG(COALESCE(s.item_count, 0)) as avg_items,
                ROUND(AVG(COALESCE(s.item_count, 0) * 60.0 / NULLIF(s.work_duration_minutes, 0)), 2) as avg_efficiency
            FROM sessions s
            WHERE s.status = 'completed' {date_filter.replace('start_time', 's.start_time')}
            GROUP BY s.user
            HAVING AVG(s.work_duration_minutes) > 0
            ORDER BY avg_efficiency ASC
        """)
        
        user_inefficiencies = []
        for row in c.fetchall():
            user_inefficiencies.append({
                'user': row[0],
                'avg_session_hours': round(row[1], 1),
                'avg_items': round(row[2], 1),
                'avg_efficiency': row[3] or 0
            })
        
        # Variance analysis: Expected vs actual performance based on historical data
        # Calculate user-specific historical averages
        c.execute(f"""
            SELECT 
                s.user,
                AVG(COALESCE(s.item_count, 0) * 60.0 / NULLIF(s.work_duration_minutes, 0)) as user_avg_efficiency,
                COUNT(*) as session_count,
                STDEV(COALESCE(s.item_count, 0) * 60.0 / NULLIF(s.work_duration_minutes, 0)) as efficiency_stdev
            FROM sessions s
            WHERE s.status = 'completed' {session_filter.replace('start_time', 's.start_time')}
            AND s.work_duration_minutes > 0
            GROUP BY s.user
        """)
        
        user_historical_data = {}
        for row in c.fetchall():
            user_historical_data[row[0]] = {
                'avg_efficiency': row[1] or 0,
                'session_count': row[2] or 0,
                'stdev': row[3] or 0
            }
        
        # Calculate global historical average (weighted by session count)
        total_weighted_efficiency = sum(data['avg_efficiency'] * data['session_count'] for data in user_historical_data.values())
        total_sessions = sum(data['session_count'] for data in user_historical_data.values())
        global_efficiency = total_weighted_efficiency / total_sessions if total_sessions > 0 else 0
        
        variance_analysis = []
        for user in user_inefficiencies:
            # Use user's own historical average if available, otherwise use global
            user_hist = user_historical_data.get(user['user'], {})
            expected_efficiency = user_hist.get('avg_efficiency', global_efficiency)
            expected_items = user['avg_session_hours'] * expected_efficiency
            
            # Calculate variance from historical expectation
            variance = ((user['avg_items'] - expected_items) / expected_items * 100) if expected_items > 0 else 0
            
            # Determine if variance is significant based on historical standard deviation
            is_significant = abs(variance) > (user_hist.get('stdev', 10) * 2) if user_hist else False
            
            variance_analysis.append({
                'user': user['user'],
                'expected_items': round(expected_items, 1),
                'actual_items': user['avg_items'],
                'variance_percent': round(variance, 1),
                'historical_efficiency': round(expected_efficiency, 2),
                'is_significant': is_significant,
                'session_count': user_hist.get('session_count', 0)
            })
        
        # NEW: Calculate handoff idle times between users using work hours
        c.execute(f"""
            SELECT 
                l1.user as from_user,
                l2.user as to_user,
                l1.timestamp as end_timestamp,
                l2.timestamp as start_timestamp,
                l1.project
            FROM logs l1
            INNER JOIN logs l2 ON l1.project = l2.project
            WHERE (l1.event = 'AFGEMELD' OR l1.event = 'SESSION_END')
            AND l2.event = 'SESSION_START'
            AND l1.user != l2.user
            AND l2.timestamp > l1.timestamp
            AND NOT EXISTS (
                SELECT 1 FROM logs l3 
                WHERE l3.project = l1.project 
                AND l3.timestamp > l1.timestamp 
                AND l3.timestamp < l2.timestamp
                AND (l3.event = 'AFGEMELD' OR l3.event = 'SESSION_END' OR l3.event = 'SESSION_START')
            )
            {date_filter.replace('timestamp', 'l1.timestamp')}
            ORDER BY l1.user, l2.user, l1.timestamp
        """)
        
        # Process handoffs and calculate work-hour-based idle times
        handoff_data = {}
        for row in c.fetchall():
            from_user = row[0]
            to_user = row[1]
            end_timestamp = row[2]
            start_timestamp = row[3]
            project = row[4]
            
            # Calculate actual work minutes between handoff
            idle_minutes = calculate_work_minutes(end_timestamp, start_timestamp)
            
            key = (from_user, to_user)
            if key not in handoff_data:
                handoff_data[key] = []
            handoff_data[key].append(idle_minutes)
        
        # Calculate statistics for each handoff pair
        handoff_analysis = []
        total_handoffs = 0
        total_idle_minutes = 0
        
        for (from_user, to_user), idle_times in handoff_data.items():
            handoff_count = len(idle_times)
            avg_idle = sum(idle_times) / handoff_count if handoff_count > 0 else 0
            max_idle = max(idle_times) if idle_times else 0
            min_idle = min(idle_times) if idle_times else 0
            
            total_handoffs += handoff_count
            total_idle_minutes += avg_idle * handoff_count
            
            handoff_analysis.append({
                'from_user': from_user,
                'to_user': to_user,
                'handoff_count': handoff_count,
                'avg_idle_hours': round(avg_idle / 60, 1),
                'max_idle_hours': round(max_idle / 60, 1),
                'min_idle_hours': round(min_idle / 60, 1),
                'avg_idle_minutes': avg_idle
            })
        
        avg_idle_all_handoffs = total_idle_minutes / total_handoffs if total_handoffs > 0 else 0
        
        # Calculate percentile-based severity thresholds from historical data
        if handoff_analysis:
            idle_times = [h['avg_idle_minutes'] for h in handoff_analysis]
            idle_times.sort()
            
            # Calculate percentiles for severity classification
            percentile_50 = idle_times[int(len(idle_times) * 0.5)] if idle_times else 0
            percentile_75 = idle_times[int(len(idle_times) * 0.75)] if idle_times else 0
            percentile_90 = idle_times[int(len(idle_times) * 0.9)] if idle_times else 0
            
            # Add severity based on historical percentiles
            for handoff in handoff_analysis:
                idle = handoff['avg_idle_minutes']
                if idle >= percentile_90:
                    handoff['severity'] = 'critical'
                elif idle >= percentile_75:
                    handoff['severity'] = 'high'
                elif idle >= percentile_50:
                    handoff['severity'] = 'medium'
                else:
                    handoff['severity'] = 'low'
        
        return jsonify({
            'success': True,
            'coordination_delays': coordination_delays[:10],  # Top 10 projects with delays
            'user_inefficiencies': user_inefficiencies,
            'variance_analysis': variance_analysis,
            'handoff_analysis': handoff_analysis[:10],  # Top 10 handoff bottlenecks
            'handoff_summary': {
                'total_handoffs': total_handoffs,
                'avg_idle_hours': round(avg_idle_all_handoffs / 60, 1),
                'total_idle_days': round(total_idle_minutes / (60 * 8), 1),  # Assuming 8-hour workdays
                'percentile_thresholds': {
                    '50th': round(percentile_50 / 60, 1) if 'percentile_50' in locals() else 0,
                    '75th': round(percentile_75 / 60, 1) if 'percentile_75' in locals() else 0,
                    '90th': round(percentile_90 / 60, 1) if 'percentile_90' in locals() else 0
                }
            },
            'global_efficiency': round(global_efficiency, 2),
            'period_type': period_type
        })
        
    except Exception as e:
        logging.error(f"Error getting bottleneck analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/statistics/predictive-analytics', methods=['GET'])
def get_predictive_analytics():
    """5. Predictive Time Calculator"""
    try:
        target_items = int(request.args.get('target_items', 100))
        
        # Handle different period types for historical data
        period_type = request.args.get('period_type', 'days')
        
        if period_type == 'custom':
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            date_filter = f"AND DATE(start_time) BETWEEN '{start_date}' AND '{end_date}'"
        elif period_type == 'all':
            date_filter = ""  # No date filter - all data
        else:
            period = request.args.get('period', '30')  # days for historical data
            date_filter = f"AND start_time >= datetime('now', '-{period} days')"
        
        conn = get_db()
        c = conn.cursor()
        
        # Calculate historical averages with proportional time allocation
        c.execute(f"""
            WITH BatchAllocation AS (
                SELECT 
                    s.item_count,
                    -- For batch processing (SCANNER), calculate proportional time
                    CASE 
                        WHEN s.session_type = 'SCANNER' THEN
                            COALESCE(s.item_count, 0) * 1.0 / NULLIF(
                                (SELECT SUM(COALESCE(s2.item_count, 0)) 
                                 FROM sessions s2 
                                 WHERE s2.user = s.user 
                                 AND s2.session_type = 'SCANNER'
                                 AND s2.status = 'completed'
                                 AND DATE(s2.start_time) = DATE(s.start_time)
                                ), 0
                            ) * (
                                SELECT SUM(s3.work_duration_minutes) 
                                FROM sessions s3 
                                WHERE s3.user = s.user 
                                AND s3.session_type = 'SCANNER'
                                AND s3.status = 'completed'
                                AND DATE(s3.start_time) = DATE(s.start_time)
                            )
                        ELSE 
                            s.work_duration_minutes
                    END as allocated_duration_minutes
                FROM sessions s
                WHERE s.status = 'completed' 
                AND s.item_count > 0 {date_filter.replace('start_time', 's.start_time')}
            )
            SELECT 
                ROUND(AVG(allocated_duration_minutes / NULLIF(item_count, 0)), 2) as avg_minutes_per_item,
                ROUND(AVG(COALESCE(item_count, 0) * 60.0 / NULLIF(allocated_duration_minutes, 0)), 2) as avg_items_per_hour,
                COUNT(*) as sessions_count,
                SUM(COALESCE(item_count, 0)) as total_items,
                SUM(allocated_duration_minutes) / 60.0 as total_hours
            FROM BatchAllocation
        """)
        
        result = c.fetchone()
        avg_minutes_per_item = result[0] if result and result[0] else 60  # Default to 1 hour per item
        avg_items_per_hour = result[1] if result and result[1] else 1
        sessions_count = result[2] if result else 0
        historical_total_items = result[3] if result else 0
        historical_total_hours = result[4] if result else 0
        
        # Per-user predictions with proportional time allocation
        c.execute(f"""
            WITH BatchAllocation AS (
                SELECT 
                    s.user,
                    s.item_count,
                    -- For batch processing (SCANNER), calculate proportional time
                    CASE 
                        WHEN s.session_type = 'SCANNER' THEN
                            COALESCE(s.item_count, 0) * 1.0 / NULLIF(
                                (SELECT SUM(COALESCE(s2.item_count, 0)) 
                                 FROM sessions s2 
                                 WHERE s2.user = s.user 
                                 AND s2.session_type = 'SCANNER'
                                 AND s2.status = 'completed'
                                 AND DATE(s2.start_time) = DATE(s.start_time)
                                ), 0
                            ) * (
                                SELECT SUM(s3.work_duration_minutes) 
                                FROM sessions s3 
                                WHERE s3.user = s.user 
                                AND s3.session_type = 'SCANNER'
                                AND s3.status = 'completed'
                                AND DATE(s3.start_time) = DATE(s.start_time)
                            )
                        ELSE 
                            s.work_duration_minutes
                    END as allocated_duration_minutes
                FROM sessions s
                WHERE s.status = 'completed' 
                AND s.item_count > 0 {date_filter.replace('start_time', 's.start_time')}
            )
            SELECT 
                user,
                ROUND(AVG(allocated_duration_minutes / NULLIF(item_count, 0)), 2) as user_minutes_per_item,
                ROUND(AVG(COALESCE(item_count, 0) * 60.0 / NULLIF(allocated_duration_minutes, 0)), 2) as user_items_per_hour
            FROM BatchAllocation
            GROUP BY user
            HAVING COUNT(*) >= 3
        """)
        
        user_predictions = []
        for row in c.fetchall():
            user_minutes_per_item = row[1] or avg_minutes_per_item
            user_items_per_hour = row[2] or avg_items_per_hour
            
            estimated_hours = target_items / user_items_per_hour
            estimated_minutes = target_items * user_minutes_per_item
            
            user_predictions.append({
                'user': row[0],
                'items_per_hour': user_items_per_hour,
                'minutes_per_item': user_minutes_per_item,
                'estimated_hours_for_target': round(estimated_hours, 1),
                'estimated_minutes_for_target': round(estimated_minutes, 0)
            })
        
        # Global predictions
        global_estimated_hours = target_items / avg_items_per_hour if avg_items_per_hour > 0 else target_items
        global_estimated_minutes = target_items * avg_minutes_per_item
        
        # Confidence intervals based on historical variance with proportional time allocation
        c.execute(f"""
            WITH BatchAllocation AS (
                SELECT 
                    s.item_count,
                    -- For batch processing (SCANNER), calculate proportional time
                    CASE 
                        WHEN s.session_type = 'SCANNER' THEN
                            COALESCE(s.item_count, 0) * 1.0 / NULLIF(
                                (SELECT SUM(COALESCE(s2.item_count, 0)) 
                                 FROM sessions s2 
                                 WHERE s2.user = s.user 
                                 AND s2.session_type = 'SCANNER'
                                 AND s2.status = 'completed'
                                 AND DATE(s2.start_time) = DATE(s.start_time)
                                ), 0
                            ) * (
                                SELECT SUM(s3.work_duration_minutes) 
                                FROM sessions s3 
                                WHERE s3.user = s.user 
                                AND s3.session_type = 'SCANNER'
                                AND s3.status = 'completed'
                                AND DATE(s3.start_time) = DATE(s.start_time)
                            )
                        ELSE 
                            s.work_duration_minutes
                    END as allocated_duration_minutes
                FROM sessions s
                WHERE s.status = 'completed' 
                AND s.item_count > 0 {date_filter.replace('start_time', 's.start_time')}
            )
            SELECT 
                MIN(COALESCE(item_count, 0) * 60.0 / NULLIF(allocated_duration_minutes, 0)) as min_efficiency,
                MAX(COALESCE(item_count, 0) * 60.0 / NULLIF(allocated_duration_minutes, 0)) as max_efficiency
            FROM BatchAllocation
        """)
        
        efficiency_range = c.fetchone()
        min_efficiency = efficiency_range[0] if efficiency_range and efficiency_range[0] else avg_items_per_hour * 0.5
        max_efficiency = efficiency_range[1] if efficiency_range and efficiency_range[1] else avg_items_per_hour * 1.5
        
        best_case_hours = target_items / max_efficiency if max_efficiency > 0 else global_estimated_hours * 0.7
        worst_case_hours = target_items / min_efficiency if min_efficiency > 0 else global_estimated_hours * 1.5
        
        return jsonify({
            'success': True,
            'target_items': target_items,
            'global_prediction': {
                'estimated_hours': round(global_estimated_hours, 1),
                'estimated_minutes': round(global_estimated_minutes, 0),
                'avg_items_per_hour': avg_items_per_hour,
                'avg_minutes_per_item': avg_minutes_per_item,
                'best_case_hours': round(best_case_hours, 1),
                'worst_case_hours': round(worst_case_hours, 1)
            },
            'user_predictions': user_predictions,
            'historical_data': {
                'sessions_analyzed': sessions_count,
                'total_items': historical_total_items,
                'total_hours': round(historical_total_hours, 1),
                'period_type': period_type
            }
        })
        
    except Exception as e:
        logging.error(f"Error getting predictive analytics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Work Hours Settings API Endpoints
@app.route('/api/settings/work-hours', methods=['GET'])
def get_work_hours_settings():
    """Get current work hours configuration"""
    try:
        # Return current WORK_HOURS configuration
        settings = WORK_HOURS.copy()
        
        # Add time string representations for break times
        break_start_hour = int(settings['break_start'])
        break_start_min = int((settings['break_start'] % 1) * 60)
        settings['break_start_time'] = f"{break_start_hour:02d}:{break_start_min:02d}"
        
        break_end_hour = int(settings['break_end'])
        break_end_min = int((settings['break_end'] % 1) * 60)
        settings['break_end_time'] = f"{break_end_hour:02d}:{break_end_min:02d}"
        
        # Add individual day time strings and hours calculation
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(days):
            if day in settings and isinstance(settings[day], dict):
                # Calculate hours for this day
                day_config = settings[day]
                daily_hours = day_config['end'] - day_config['start'] - (settings['break_end'] - settings['break_start'])
                settings[f'{day}_hours'] = daily_hours
                
                # Add time strings
                start_hour = int(day_config['start'])
                start_min = int((day_config['start'] % 1) * 60)
                settings[f'{day}_start_time'] = f"{start_hour:02d}:{start_min:02d}"
                
                end_hour = int(day_config['end'])
                end_min = int((day_config['end'] % 1) * 60)
                settings[f'{day}_end_time'] = f"{end_hour:02d}:{end_min:02d}"
            else:
                # Weekend or non-work day
                settings[f'{day}_hours'] = 0.0
                settings[f'{day}_start_time'] = "00:00"
                settings[f'{day}_end_time'] = "00:00"
        
        return jsonify({'success': True, 'settings': settings})
        
    except Exception as e:
        logging.error(f"Error getting work hours settings: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/settings/work-hours', methods=['POST'])
def update_work_hours_settings():
    """Update work hours configuration"""
    try:
        data = request.get_json()
        
        # Update global WORK_HOURS configuration
        global WORK_HOURS
        
        # Update per-day work hours
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in days:
            if f'{day}_start' in data and f'{day}_end' in data:
                # Convert time strings to float hours
                start_time = data[f'{day}_start']
                end_time = data[f'{day}_end']
                
                start_hour = float(start_time.split(':')[0]) + float(start_time.split(':')[1]) / 60
                end_hour = float(end_time.split(':')[0]) + float(end_time.split(':')[1]) / 60
                
                WORK_HOURS[day] = {
                    'start': start_hour,
                    'end': end_hour
                }
        
        # Update break times
        if 'break_start_num' in data:
            WORK_HOURS['break_start'] = data['break_start_num']
        if 'break_end_num' in data:
            WORK_HOURS['break_end'] = data['break_end_num']
        if 'break_start' in data:
            # Convert time string to float
            break_start = data['break_start']
            WORK_HOURS['break_start'] = float(break_start.split(':')[0]) + float(break_start.split(':')[1]) / 60
        if 'break_end' in data:
            # Convert time string to float
            break_end = data['break_end']
            WORK_HOURS['break_end'] = float(break_end.split(':')[0]) + float(break_end.split(':')[1]) / 60
        
        # Update work days
        if 'work_days' in data:
            WORK_HOURS['work_days'] = data['work_days']
        
        # Log the configuration update
        logging.info(f"Work hours configuration updated: {WORK_HOURS}")
        
        # Save to config.json file for persistence
        try:
            config_path = get_writable_path('config.json')
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Store work hours in config
            config['work_hours'] = WORK_HOURS
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
                
            logging.info("Work hours configuration saved to config.json")
        except Exception as e:
            logging.error(f"Failed to save work hours to config: {e}")
        
        return jsonify({
            'success': True, 
            'message': 'Werkuren succesvol bijgewerkt',
            'settings': WORK_HOURS
        })
        
    except Exception as e:
        logging.error(f"Error updating work hours settings: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/debug/sessions/<project>', methods=['GET'])
def debug_sessions(project):
    """Debug endpoint to check sessions data for a project"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get all sessions for this project
        c.execute('''
            SELECT 
                session_id,
                user,
                project,
                start_time,
                end_time,
                status,
                item_count,
                work_duration_minutes,
                session_type
            FROM sessions 
            WHERE lower(project) = ? 
            ORDER BY start_time ASC
        ''', (project.lower(),))
        
        sessions = [dict(row) for row in c.fetchall()]
        
        # Get relevant logs for this project
        c.execute('''
            SELECT timestamp, event, user, details, item_count
            FROM logs 
            WHERE lower(project) = ?
            ORDER BY timestamp ASC
        ''', (project.lower(),))
        
        logs = [dict(row) for row in c.fetchall()]
        
        return jsonify({
            'success': True,
            'project': project,
            'sessions_count': len(sessions),
            'logs_count': len(logs),
            'sessions': sessions,
            'logs': logs
        })
        
    except Exception as e:
        logging.error(f"Error in debug sessions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/statistics/workflow-efficiency', methods=['GET'])
def get_workflow_efficiency():
    """Get comprehensive workflow efficiency metrics including idle time analysis"""
    try:
        # Handle period filtering
        period_type = request.args.get('period_type', 'days')
        
        if period_type == 'custom':
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            date_filter = f"AND DATE(timestamp) BETWEEN '{start_date}' AND '{end_date}'"
        elif period_type == 'all':
            date_filter = ""
        else:
            period = request.args.get('period', '30')
            date_filter = f"AND timestamp >= datetime('now', '-{period} days')"
        
        conn = get_db()
        c = conn.cursor()
        
        # Calculate overall workflow efficiency
        c.execute(f"""
            SELECT 
                COUNT(DISTINCT project) as total_projects,
                COUNT(DISTINCT user) as active_users,
                SUM(CASE WHEN event = 'SESSION_START' THEN 1 ELSE 0 END) as total_sessions,
                SUM(CASE WHEN event = 'AFGEMELD' THEN item_count ELSE 0 END) as total_items
            FROM logs
            WHERE 1=1 {date_filter}
        """)
        
        overview = c.fetchone()
        total_projects = overview[0] or 0
        active_users = overview[1] or 0
        total_sessions = overview[2] or 0
        total_items = overview[3] or 0
        
        # Calculate workflow stage times
        c.execute(f"""
            SELECT 
                user,
                COUNT(DISTINCT project) as projects_handled,
                AVG(CASE 
                    WHEN event = 'SESSION_END' OR event = 'AFGEMELD' THEN 
                        CAST((julianday(timestamp) - julianday(
                            (SELECT MAX(timestamp) FROM logs l2 
                             WHERE l2.project = logs.project 
                             AND l2.user = logs.user 
                             AND l2.event IN ('SESSION_START', 'OPEN')
                             AND l2.timestamp < logs.timestamp)
                        )) * 24 * 60 AS REAL)
                    ELSE NULL 
                END) as avg_processing_time,
                SUM(CASE WHEN event = 'AFGEMELD' THEN item_count ELSE 0 END) as items_completed
            FROM logs
            WHERE 1=1 {date_filter}
            GROUP BY user
        """)
        
        user_metrics = []
        for row in c.fetchall():
            user_metrics.append({
                'user': row[0],
                'projects': row[1] or 0,
                'avg_time_hours': round((row[2] or 0) / 60, 1),
                'items': row[3] or 0
            })
        
        # Calculate historical workflow patterns
        c.execute(f"""
            SELECT 
                strftime('%H', timestamp) as hour,
                COUNT(*) as event_count,
                SUM(CASE WHEN event = 'SESSION_START' THEN 1 ELSE 0 END) as sessions_started,
                SUM(CASE WHEN event = 'AFGEMELD' THEN 1 ELSE 0 END) as work_completed
            FROM logs
            WHERE 1=1 {date_filter}
            GROUP BY hour
            ORDER BY hour
        """)
        
        hourly_patterns = []
        for row in c.fetchall():
            hourly_patterns.append({
                'hour': int(row[0]),
                'events': row[1] or 0,
                'sessions': row[2] or 0,
                'completions': row[3] or 0
            })
        
        return jsonify({
            'success': True,
            'overview': {
                'total_projects': total_projects,
                'active_users': active_users,
                'total_sessions': total_sessions,
                'total_items': total_items,
                'avg_items_per_session': round(total_items / total_sessions, 1) if total_sessions > 0 else 0
            },
            'user_metrics': user_metrics,
            'hourly_patterns': hourly_patterns,
            'period_type': period_type
        })
        
    except Exception as e:
        logging.error(f"Error getting workflow efficiency: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/statistics/quality-metrics')
def get_quality_metrics():
    """Get quality metrics including defect rates and rework percentage using rep_variant logic"""
    try:
        # Get date filtering parameters
        period = request.args.get('period', '30')
        period_type = request.args.get('period_type', 'days')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Build date filter
        date_filter = ""
        params = []
        
        if period_type == 'custom' and start_date and end_date:
            date_filter = " AND l.timestamp BETWEEN ? AND ?"
            params.extend([start_date + ' 00:00:00', end_date + ' 23:59:59'])
        elif period_type == 'all':
            # No date filter for 'all'
            pass
        else:
            # Default period-based filtering
            if period_type == 'days':
                period_int = int(period)
            else:
                period_int = 30  # fallback
            date_filter = " AND l.timestamp >= datetime('now', '-{} days')".format(period_int)
        
        conn = get_db()
        c = conn.cursor()
        
        # Overall quality metrics
        quality_query = f"""
            SELECT 
                COUNT(*) as total_items,
                COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) as rework_items,
                COUNT(CASE WHEN l.is_rep_variant = 0 THEN 1 END) as normal_items,
                ROUND((COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) * 100.0 / COUNT(*)), 2) as defect_rate
            FROM logs l
            WHERE l.event = 'AFGEMELD' {date_filter}
        """
        
        c.execute(quality_query, params)
        overall_metrics = c.fetchone()
        
        # Quality metrics by user
        user_quality_query = f"""
            SELECT 
                l.user,
                COUNT(*) as total_items,
                COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) as rework_items,
                ROUND((COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) * 100.0 / COUNT(*)), 2) as defect_rate,
                ROUND(AVG(CASE WHEN l.is_rep_variant = 0 THEN 
                    (julianday(l.timestamp) - julianday(
                        (SELECT MIN(l2.timestamp) FROM logs l2 WHERE l2.project = l.project AND l2.user = l.user AND l2.event = 'OPEN')
                    )) * 24 * 60 END), 2) as avg_normal_minutes,
                ROUND(AVG(CASE WHEN l.is_rep_variant = 1 THEN 
                    (julianday(l.timestamp) - julianday(
                        (SELECT MIN(l2.timestamp) FROM logs l2 WHERE l2.project = l.project AND l2.user = l.user AND l2.event = 'OPEN')
                    )) * 24 * 60 END), 2) as avg_rework_minutes
            FROM logs l
            WHERE l.event = 'AFGEMELD' {date_filter}
            GROUP BY l.user
            HAVING COUNT(*) > 0
            ORDER BY defect_rate DESC
        """
        
        c.execute(user_quality_query, params)
        user_metrics = c.fetchall()
        
        # Quality trends over time (daily)
        trends_query = f"""
            SELECT 
                DATE(l.timestamp) as date,
                COUNT(*) as total_items,
                COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) as rework_items,
                ROUND((COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) * 100.0 / COUNT(*)), 2) as defect_rate
            FROM logs l
            WHERE l.event = 'AFGEMELD' {date_filter}
            GROUP BY DATE(l.timestamp)
            ORDER BY DATE(l.timestamp) DESC
            LIMIT 30
        """
        
        c.execute(trends_query, params)
        quality_trends = c.fetchall()
        
        # Product type quality metrics (based on project patterns)
        product_quality_query = f"""
            SELECT 
                CASE 
                    WHEN l.project LIKE '%_Rep_%' THEN 'Reparatie'
                    WHEN l.project LIKE '%_VL%' THEN 'Vervanging'
                    WHEN l.project LIKE '%Boekenkast%' THEN 'Boekenkast'
                    WHEN l.project LIKE '%Kast%' THEN 'Kast'
                    ELSE 'Overig'
                END as product_type,
                COUNT(*) as total_items,
                COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) as rework_items,
                ROUND((COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) * 100.0 / COUNT(*)), 2) as defect_rate
            FROM logs l
            WHERE l.event = 'AFGEMELD' {date_filter}
            GROUP BY product_type
            HAVING COUNT(*) > 0
            ORDER BY defect_rate DESC
        """
        
        c.execute(product_quality_query, params)
        product_metrics = c.fetchall()
        
        conn.close()
        
        # Format the response
        response = {
            'overall': {
                'total_items': overall_metrics['total_items'] if overall_metrics else 0,
                'rework_items': overall_metrics['rework_items'] if overall_metrics else 0,
                'normal_items': overall_metrics['normal_items'] if overall_metrics else 0,
                'defect_rate': overall_metrics['defect_rate'] if overall_metrics else 0.0,
                'quality_rate': round(100 - (overall_metrics['defect_rate'] if overall_metrics else 0), 2)
            },
            'user_metrics': [
                {
                    'user': row['user'],
                    'total_items': row['total_items'],
                    'rework_items': row['rework_items'],
                    'defect_rate': row['defect_rate'],
                    'quality_rate': round(100 - row['defect_rate'], 2),
                    'avg_normal_minutes': row['avg_normal_minutes'] or 0,
                    'avg_rework_minutes': row['avg_rework_minutes'] or 0
                } for row in user_metrics
            ],
            'trends': [
                {
                    'date': row['date'],
                    'total_items': row['total_items'],
                    'rework_items': row['rework_items'],
                    'defect_rate': row['defect_rate'],
                    'quality_rate': round(100 - row['defect_rate'], 2)
                } for row in quality_trends
            ],
            'product_metrics': [
                {
                    'product_type': row['product_type'],
                    'total_items': row['total_items'],
                    'rework_items': row['rework_items'],
                    'defect_rate': row['defect_rate'],
                    'quality_rate': round(100 - row['defect_rate'], 2)
                } for row in product_metrics
            ]
        }
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"Error getting quality metrics: {e}")
        return jsonify({'error': str(e)}), 500

def create_efficiency_tables():
    """Create user efficiency tracking tables if they don't exist"""
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Create user efficiency targets table
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_efficiency_targets (
                user TEXT PRIMARY KEY,
                target_items_per_hour REAL NOT NULL,
                created_date TEXT NOT NULL,
                updated_date TEXT NOT NULL
            )
        ''')
        
        # Create user efficiency history table
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_efficiency_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT NOT NULL,
                date TEXT NOT NULL,
                actual_items_per_hour REAL NOT NULL,
                total_items INTEGER NOT NULL,
                total_minutes INTEGER NOT NULL,
                UNIQUE(user, date)
            )
        ''')
        
        conn.commit()
        logging.info("User efficiency tables created successfully")
        
    except Exception as e:
        logging.error(f"Error creating efficiency tables: {e}")
    finally:
        if conn:
            conn.close()

@app.route('/api/settings/efficiency-targets', methods=['GET'])
def get_efficiency_targets():
    """Get user efficiency targets from config.json"""
    try:
        config_path = get_writable_path('config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                
                # Get efficiency targets from config
                efficiency_targets = config.get('efficiency_targets', {})
                
                # Convert to expected format for compatibility
                targets = {}
                for user, target_value in efficiency_targets.items():
                    targets[user] = {
                        'target_items_per_hour': target_value,
                        'created_date': config.get('efficiency_targets_created', datetime.now().isoformat()),
                        'updated_date': config.get('efficiency_targets_updated', datetime.now().isoformat())
                    }
                
                return jsonify({'targets': targets})
        else:
            return jsonify({'targets': {}})
            
    except Exception as e:
        logging.error(f"Error getting efficiency targets from config: {e}")
        return jsonify({'targets': {}})

@app.route('/api/settings/efficiency-targets', methods=['POST'])
def update_efficiency_targets():
    """Update user efficiency targets in config.json"""
    try:
        data = request.get_json()
        if not data or 'targets' not in data:
            return jsonify({'error': 'No targets data provided'}), 400
        
        # Validate targets data
        for user, target_value in data['targets'].items():
            if not isinstance(target_value, (int, float)) or target_value < 0:
                return jsonify({'error': f'Invalid target value for user {user}'}), 400
        
        # Load existing config or create new one
        config_path = get_writable_path('config.json')
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        
        # Update efficiency targets in config
        config['efficiency_targets'] = data['targets']
        config['efficiency_targets_updated'] = datetime.now().isoformat()
        
        # Set created date if not exists
        if 'efficiency_targets_created' not in config:
            config['efficiency_targets_created'] = datetime.now().isoformat()
        
        # Save config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logging.info(f"Efficiency targets updated in config: {data['targets']}")
        return jsonify({'success': True, 'message': 'Efficiency targets updated successfully'})
        
    except Exception as e:
        logging.error(f"Error updating efficiency targets: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/efficiency/daily-update', methods=['POST'])
def update_daily_efficiency():
    """Update daily efficiency for all users based on current session data"""
    conn = None
    try:
        conn = create_db_connection()  # Use direct connection
        c = conn.cursor()
        
        # Ensure tables exist
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_efficiency_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT NOT NULL,
                date TEXT NOT NULL,
                actual_items_per_hour REAL NOT NULL,
                total_items INTEGER NOT NULL,
                total_minutes INTEGER NOT NULL,
                UNIQUE(user, date)
            )
        ''')
        
        # Get today's date
        today = datetime.now().date().isoformat()
        
        # Calculate today's efficiency for each user from sessions
        c.execute('''
            WITH BatchAllocation AS (
                SELECT 
                    s.user,
                    s.item_count,
                    -- For batch processing (SCANNER), calculate proportional time
                    CASE 
                        WHEN s.session_type = 'SCANNER' THEN
                            COALESCE(s.item_count, 0) * 1.0 / NULLIF(
                                (SELECT SUM(COALESCE(s2.item_count, 0)) 
                                 FROM sessions s2 
                                 WHERE s2.user = s.user 
                                 AND s2.session_type = 'SCANNER'
                                 AND s2.status = 'completed'
                                 AND DATE(s2.start_time) = DATE(s.start_time)
                                ), 0
                            ) * (
                                SELECT SUM(s3.work_duration_minutes) 
                                FROM sessions s3 
                                WHERE s3.user = s.user 
                                AND s3.session_type = 'SCANNER'
                                AND s3.status = 'completed'
                                AND DATE(s3.start_time) = DATE(s.start_time)
                            )
                        ELSE 
                            s.work_duration_minutes
                    END as allocated_duration_minutes
                FROM sessions s
                WHERE DATE(s.start_time) = ? 
                AND s.status = 'completed'
                AND s.user IS NOT NULL
            )
            SELECT 
                user,
                SUM(COALESCE(item_count, 0)) as total_items,
                SUM(COALESCE(allocated_duration_minutes, 0)) as total_minutes,
                CASE 
                    WHEN SUM(COALESCE(allocated_duration_minutes, 0)) > 0 
                    THEN ROUND((SUM(COALESCE(item_count, 0)) * 60.0) / SUM(COALESCE(allocated_duration_minutes, 0)), 2)
                    ELSE 0 
                END as items_per_hour
            FROM BatchAllocation
            GROUP BY user
            HAVING total_minutes > 0
        ''', (today,))
        
        updated_users = []
        for row in c.fetchall():
            user = row['user']
            total_items = row['total_items']
            total_minutes = row['total_minutes']
            items_per_hour = row['items_per_hour']
            
            # Insert or update daily efficiency
            c.execute('''
                INSERT OR REPLACE INTO user_efficiency_history 
                (user, date, actual_items_per_hour, total_items, total_minutes)
                VALUES (?, ?, ?, ?, ?)
            ''', (user, today, items_per_hour, total_items, total_minutes))
            
            updated_users.append({
                'user': user,
                'items_per_hour': items_per_hour,
                'total_items': total_items,
                'total_minutes': total_minutes
            })
        
        conn.commit()
        
        logging.info(f"Daily efficiency updated for {len(updated_users)} users")
        return jsonify({'success': True, 'updated_users': updated_users})
        
    except Exception as e:
        logging.error(f"Error updating daily efficiency: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/efficiency/history/<user>')
def get_user_efficiency_history(user):
    """Get efficiency history for a specific user"""
    conn = None
    try:
        days = request.args.get('days', 30, type=int)
        
        conn = create_db_connection()  # Use direct connection
        c = conn.cursor()
        
        c.execute('''
            SELECT date, actual_items_per_hour, total_items, total_minutes
            FROM user_efficiency_history
            WHERE user = ?
            AND date >= date('now', '-' || ? || ' days')
            ORDER BY date DESC
        ''', (user, days))
        
        history = []
        for row in c.fetchall():
            history.append({
                'date': row['date'],
                'items_per_hour': row['actual_items_per_hour'],
                'total_items': row['total_items'],
                'total_minutes': row['total_minutes']
            })
        
        return jsonify({'user': user, 'history': history})
        
    except Exception as e:
        logging.error(f"Error getting efficiency history for {user}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/project/<project>/productivity-metrics', methods=['GET'])
def get_project_productivity_metrics(project):
    """Get productivity metrics for a specific project using proportional time allocation"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get project productivity metrics with proper batch session handling
        # First get all users who worked on this project
        c.execute("""
            SELECT DISTINCT user FROM logs 
            WHERE LOWER(project) = LOWER(?) 
            AND user IS NOT NULL AND user != ''
        """, (project,))
        
        project_users = [row[0] for row in c.fetchall()]
        
        if not project_users:
            return jsonify({
                'success': True,
                'project': project,
                'user_productivity': []
            })
        
        user_productivity = []
        
        for user in project_users:
            # Get item count for this user/project from logs
            c.execute("""
                SELECT MAX(COALESCE(item_count, 0)) as project_items
                FROM logs
                WHERE user = ? AND LOWER(project) = LOWER(?)
                AND item_count > 0
            """, (user, project))
            
            result = c.fetchone()
            project_items = result[0] if result and result[0] else 0
            
            # Check for active batch session (project can be NULL or empty string)
            c.execute("""
                SELECT session_id, start_time, work_duration_minutes
                FROM sessions 
                WHERE user = ? AND session_type = 'SCANNER' 
                AND (project IS NULL OR project = '') AND status = 'active'
                ORDER BY start_time DESC
                LIMIT 1
            """, (user,))
            
            active_batch = c.fetchone()
            
            # Check for completed batch sessions that included this project
            c.execute("""
                SELECT 
                    s.session_id,
                    s.start_time,
                    s.end_time,
                    s.work_duration_minutes
                FROM sessions s
                WHERE s.user = ? 
                AND s.session_type = 'SCANNER' 
                AND (s.project IS NULL OR s.project = '') 
                AND s.status = 'completed'
                AND EXISTS (
                    -- Check if this batch session processed this project
                    SELECT 1 FROM logs l
                    WHERE l.user = s.user
                    AND LOWER(l.project) = LOWER(?)
                    AND l.timestamp BETWEEN s.start_time AND s.end_time
                )
                ORDER BY s.end_time DESC
            """, (user, project))
            
            completed_batches = c.fetchall()
            
            # Get individual sessions (XLSX_UPDATED, MANUAL) - both active and completed
            c.execute("""
                SELECT 
                    session_type,
                    work_duration_minutes,
                    item_count,
                    status
                FROM sessions 
                WHERE user = ? AND LOWER(project) = LOWER(?)
                AND session_type IN ('XLSX_UPDATED', 'MANUAL')
                AND status IN ('completed', 'active')
            """, (user, project))
            
            individual_sessions = c.fetchall()
            
            # Calculate metrics
            total_items = project_items
            manual_items = 0
            auto_items = 0
            total_duration_minutes = 0
            status = 'COMPLETED'
            
            # Process individual sessions (only completed ones count toward time/items)
            for session in individual_sessions:
                if session['status'] == 'completed':
                    if session['session_type'] == 'MANUAL':
                        manual_items += session['item_count'] or 0
                    elif session['session_type'] == 'XLSX_UPDATED':
                        auto_items += session['item_count'] or 0
                    total_duration_minutes += session['work_duration_minutes'] or 0
            
            # Process batch sessions with proportional allocation
            if completed_batches:
                for batch in completed_batches:
                    if batch['work_duration_minutes'] and batch['work_duration_minutes'] > 0:
                        # Get total items in this batch
                        c.execute("""
                            SELECT SUM(COALESCE(item_count, 0)) as batch_total
                            FROM logs
                            WHERE user = ?
                            AND timestamp BETWEEN ? AND ?
                            AND item_count > 0
                        """, (user, batch['start_time'], batch['end_time']))
                        
                        batch_result = c.fetchone()
                        batch_total_items = batch_result[0] if batch_result and batch_result[0] else 0
                        
                        # Calculate proportional time for this project
                        if batch_total_items > 0 and project_items > 0:
                            proportion = project_items / batch_total_items
                            allocated_minutes = batch['work_duration_minutes'] * proportion
                            total_duration_minutes += allocated_minutes
            
            # Check if active batch has processed this project
            active_batch_processed_project = False
            if active_batch:
                c.execute("""
                    SELECT COUNT(*) FROM logs l
                    WHERE l.user = ? AND LOWER(l.project) = LOWER(?) 
                    AND l.timestamp >= ?
                """, (user, project, active_batch[1]))  # active_batch[1] is start_time
                
                active_batch_logs = c.fetchone()[0]
                active_batch_processed_project = active_batch_logs > 0
            
            # Determine status: show user if they have OPEN event, but only show data if they have work sessions
            if individual_sessions:
                # User has individual work (XLSX_UPDATED/MANUAL) for this project - always COMPLETED
                status = 'COMPLETED'
            elif completed_batches:
                # User has completed batch work for this project (SCANNER user only)
                status = 'COMPLETED'  
            elif active_batch and active_batch_processed_project:
                # User has active batch session that is processing this project
                status = 'IN_PROGRESS'
            else:
                # User has OPEN event but no work sessions yet - show blank data
                status = 'WAITING'
                total_items = 0
                total_duration_minutes = 0
                manual_items = 0
                auto_items = 0
            
            # Calculate productivity
            if status == 'WAITING':
                # User has OPEN event but no work sessions - show blank
                items_per_hour = '--'
                session_hours = '--'
            elif total_duration_minutes > 0 and total_items > 0:
                items_per_hour = round((total_items * 60.0) / total_duration_minutes, 2)
                session_hours = round(total_duration_minutes / 60.0, 2)
            else:
                items_per_hour = 'IN_PROGRESS' if status == 'IN_PROGRESS' else 0
                session_hours = 'IN_PROGRESS' if status == 'IN_PROGRESS' else 0
            
            user_productivity.append({
                'user': user,
                'items_per_hour': items_per_hour,
                'total_items': total_items,
                'session_hours': session_hours,
                'manual_items': manual_items,
                'auto_items': auto_items,
                'status': status
            })
        
        # Sort by items per hour (IN_PROGRESS last)
        user_productivity.sort(key=lambda x: (
            1 if x['items_per_hour'] == 'IN_PROGRESS' else 0,
            -(x['items_per_hour'] if isinstance(x['items_per_hour'], (int, float)) else 0)
        ))
        
        return jsonify({
            'success': True,
            'project': project,
            'user_productivity': user_productivity
        })
        
    except Exception as e:
        logging.error(f"Error getting project productivity metrics for {project}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

# Scheduled efficiency tracking
import threading
import time

def schedule_daily_efficiency_updates():
    """Schedule daily efficiency updates to run automatically"""
    def run_daily_updates():
        while True:
            try:
                # Wait 24 hours between updates (86400 seconds)
                time.sleep(86400)
                
                # Update daily efficiency for all users
                with app.app_context():
                    logging.info("Running scheduled daily efficiency update")
                    update_daily_efficiency()
                    
            except Exception as e:
                logging.error(f"Error in scheduled efficiency update: {e}")
                # Continue running even if one update fails
                
    # Start the background thread
    scheduler_thread = threading.Thread(target=run_daily_updates, daemon=True)
    scheduler_thread.start()
    logging.info("Daily efficiency update scheduler started")

def trigger_efficiency_update_on_session_end():
    """Trigger efficiency update when sessions are completed"""
    try:
        with app.app_context():
            # Call the daily update endpoint to refresh today's data
            response = update_daily_efficiency()
            if hasattr(response, 'json'):
                result = response.json
                logging.info(f"Efficiency update triggered: {result}")
    except Exception as e:
        logging.error(f"Error triggering efficiency update: {e}")

# User Configuration Management API endpoints
@app.route('/api/settings/user-config', methods=['GET'])
def get_user_config():
    """Get user configuration from config.json, converting from existing arrays if needed"""
    try:
        config_path = get_writable_path('config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                
                # Check if new user format exists
                if 'users' in config:
                    return jsonify({'success': True, 'users': config['users']})
                
                # Convert from existing arrays to new format
                scanner_users = config.get('scanner_panel_open_event_users', [])
                dashboard_users = config.get('dashboard_display_users', [])
                processing_map = config.get('scanner_user_to_processing_type_map', {})
                
                # Create user objects from existing config
                users = []
                all_users = list(set(scanner_users + dashboard_users))
                
                for user_name in all_users:
                    user = {
                        'name': user_name,
                        'active': True,
                        'type': processing_map.get(user_name, 'GEEN_PROCESSING'),
                        'roles': []
                    }
                    
                    if user_name in scanner_users:
                        user['roles'].append('scanner')
                    if user_name in dashboard_users:
                        user['roles'].append('dashboard')
                    
                    users.append(user)
                
                return jsonify({'success': True, 'users': users})
        else:
            return jsonify({'success': True, 'users': []})
    except Exception as e:
        logging.error(f"Error loading user configuration: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings/user-config', methods=['POST'])
def save_user_config():
    """Save user configuration to config.json, updating both new and legacy formats"""
    try:
        data = request.get_json()
        if not data or 'users' not in data:
            return jsonify({'error': 'Users data is required'}), 400
        
        users = data['users']
        
        # Validate users data
        valid_processing_types = ['GEEN_PROCESSING', 'HOPS_PROCESSING', 'MDB_PROCESSING', 'NESTING_PROCESSING', 'ACCURA_PROCESSING', 'BOERE_PROCESSING']
        for user in users:
            if not isinstance(user, dict):
                return jsonify({'error': 'Each user must be an object'}), 400
            if 'name' not in user or not user['name'].strip():
                return jsonify({'error': 'Each user must have a name'}), 400
            if 'active' not in user or not isinstance(user['active'], bool):
                return jsonify({'error': 'Each user must have an active boolean field'}), 400
            if 'type' not in user or user['type'] not in valid_processing_types:
                return jsonify({'error': f'Each user must have a valid processing type: {valid_processing_types}'}), 400
        
        # Load existing config or create new one
        config_path = get_writable_path('config.json')
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        
        # Save new user format
        config['users'] = users
        
        # Update legacy arrays for backward compatibility
        scanner_users = []
        dashboard_users = []
        processing_map = {}
        
        for user in users:
            if user['active']:
                user_name = user['name']
                roles = user.get('roles', ['scanner', 'dashboard'])  # Default to both if not specified
                
                if 'scanner' in roles:
                    scanner_users.append(user_name)
                if 'dashboard' in roles:
                    dashboard_users.append(user_name)
                
                # Only add to processing map if not GEEN_PROCESSING (default)
                if user['type'] != 'GEEN_PROCESSING':
                    processing_map[user_name] = user['type']
        
        # Update legacy config arrays
        config['scanner_panel_open_event_users'] = scanner_users
        config['dashboard_display_users'] = dashboard_users
        config['scanner_user_to_processing_type_map'] = processing_map
        
        # Save config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logging.info(f"User configuration updated: {len(users)} users saved")
        return jsonify({'success': True, 'message': 'User configuration updated successfully'})
        
    except Exception as e:
        logging.error(f"Error saving user configuration: {e}")
        return jsonify({'error': str(e)}), 500

# Initialize efficiency tracking on startup
def initialize_efficiency_tracking():
    """Initialize efficiency tracking system"""
    try:
        create_efficiency_tables()
        # Start the daily scheduler
        schedule_daily_efficiency_updates()
        # Do an initial update for today
        trigger_efficiency_update_on_session_end()
        logging.info("Efficiency tracking system initialized")
    except Exception as e:
        logging.error(f"Error initializing efficiency tracking: {e}")
