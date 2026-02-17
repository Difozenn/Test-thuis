from flask import Flask, request, jsonify, render_template, send_from_directory, make_response, send_file, g, session, redirect, url_for
import sqlite3
import json
import base64
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
import re
import hashlib
from functools import wraps

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
try:
    from services.background_import_service import BackgroundImportService
except ImportError:
    BackgroundImportService = None
    print("Warning: BackgroundImportService not available due to missing dependencies")

# --- Flask App Setup ---
# Use the 'templates' directory in the same folder as this script
template_dir = get_resource_path('database/templates')
app = Flask(__name__, template_folder=template_dir)

# Set up secret key for sessions (generate a random one if not configured)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-key-change-in-production-' + os.urandom(16).hex())

# --- Helper Functions ---
def normalize_project_id(project_name):
    """
    Normalize project name to consistent ID for linking sessions.
    Examples:
    - MO07834_Boekenkast_REP_VL5 -> MO07834_REP
    - MO07834_Boekenkast -> MO07834
    - 0411_MO07834_TV-wand -> MO07834
    """
    if not project_name:
        return None
    
    # Extract MO code
    mo_match = re.search(r'(MO\d{5})', project_name, re.IGNORECASE)
    if not mo_match:
        # Not an MO project, return as-is
        return project_name
    
    base_mo = mo_match.group(1).upper()
    
    # Check if it's a REP variant
    if '_REP' in project_name.upper():
        return f"{base_mo}_REP"
    else:
        return base_mo

# --- Background Work Callback Definition ---
# Store the original scanner panel callback  
original_scanner_callback = None

def register_scanner_callback(callback_func):
    """Register the scanner panel callback"""
    global original_scanner_callback
    original_scanner_callback = callback_func
    logging.info("[CALLBACK] Scanner panel callback registered")

def background_work_callback(message):
    """Callback function to handle background service messages"""
    try:
        logging.info(f"[BACKGROUND_CALLBACK] {message}")
        
        # Forward to original scanner panel callback if it exists
        if original_scanner_callback:
            try:
                original_scanner_callback(message)
                logging.info(f"[BACKGROUND_CALLBACK] Forwarded message to scanner panel: {message}")
            except Exception as e:
                logging.error(f"[BACKGROUND_CALLBACK] Error forwarding to scanner panel: {e}")
        else:
            logging.warning(f"[BACKGROUND_CALLBACK] No scanner panel callback registered, message not forwarded: {message}")
        
        # Parse the message format: BACKGROUND_WORK_FOUND:project:user:count
        if message.startswith('BACKGROUND_WORK_FOUND:'):
            parts = message.split(':')
            if len(parts) >= 4:
                project_code = parts[1]
                user = parts[2]
                item_count = parts[3]
                
                # Use Flask application context for database operations
                with app.app_context():
                    # Log this as a proper event in the database (needed for scanner panel)
                    conn = get_db()
                    c = conn.cursor()
                    timestamp = datetime.now().isoformat()
                    
                    c.execute("""
                        INSERT INTO logs (timestamp, event, user, project, details, mo_number, so_number, customer_name, color)
                        VALUES (?, 'BACKGROUND_WORK_FOUND', ?, ?, ?, NULL, NULL, NULL, NULL)
                    """, (timestamp, user, project_code, f"Work detected: {item_count} items"))
                    
                    conn.commit()
                    logging.info(f"[BACKGROUND_CALLBACK] Logged work found event for {user} on {project_code}: {item_count} items")
                
    except Exception as e:
        logging.error(f"[BACKGROUND_CALLBACK] Error processing message: {e}")

# --- Service Initialization ---
background_service = BackgroundImportService() if BackgroundImportService else None

# Set up the callback immediately after service initialization
if background_service:
    # Store the original callback if it exists (scanner panel sets this first)
    if hasattr(background_service, 'log_callback') and background_service.log_callback:
        original_scanner_callback = background_service.log_callback
        logging.info("[INIT] Preserved original scanner panel callback")
    
    # Set our callback that will forward to the original
    background_service.log_callback = background_work_callback
    logging.info("[INIT] Background service log callback initialized")


# Function to set log callback from external sources (like GUI)
def set_background_service_log_callback(callback):
    """Set the log callback for the background service"""
    global background_service
    if background_service:
        background_service.log_callback = callback

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

def get_current_work_status():
    """Check if current time is within work hours"""
    now = datetime.now()
    
    # Check if today is a holiday first
    try:
        today_str = now.strftime('%Y-%m-%d')
        holidays = get_holidays_for_period(today_str, today_str)
        if today_str in holidays:
            holiday_name = holidays[today_str].get('name', 'Kantoor gesloten')
            return False, f"Feestdag - {holiday_name}"
    except Exception as e:
        logging.warning(f"Could not check holidays: {e}")
    
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
    conn.execute('PRAGMA foreign_keys=ON;')  # Enable foreign key constraints
    return conn

def execute_transaction(conn, operations):
    """Execute multiple database operations in a transaction
    
    Args:
        conn: Database connection
        operations: List of (query, params) tuples
    
    Returns:
        True if successful, False otherwise
    """
    c = conn.cursor()
    try:
        conn.execute('BEGIN TRANSACTION')
        for query, params in operations:
            c.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"Transaction failed: {e}")
        raise

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
                target_items_per_hour REAL DEFAULT 30.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create holidays table for company-wide holiday management
        c.execute('''
            CREATE TABLE IF NOT EXISTS holidays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                type TEXT DEFAULT 'holiday',
                is_recurring BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create login_history table for tracking login attempts and access
        c.execute('''
            CREATE TABLE IF NOT EXISTS login_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                login_time TEXT DEFAULT CURRENT_TIMESTAMP,
                login_success BOOLEAN DEFAULT 1,
                login_type TEXT DEFAULT 'manual',
                session_duration_minutes REAL,
                logout_time TEXT
            )
        ''')

        # Check and add target_items_per_hour to work_hours_config if it doesn't exist
        c.execute("PRAGMA table_info(work_hours_config)")
        work_hours_columns = [column[1] for column in c.fetchall()]
        if 'target_items_per_hour' not in work_hours_columns:
            c.execute('ALTER TABLE work_hours_config ADD COLUMN target_items_per_hour REAL DEFAULT 30.0')
            logging.info("Added 'target_items_per_hour' column to work_hours_config table.")

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
        if 'mo_number' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN mo_number TEXT')
            logging.info("Added 'mo_number' column to logs table.")
        if 'so_number' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN so_number TEXT')
            logging.info("Added 'so_number' column to logs table.")
        if 'color' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN color TEXT')
            logging.info("Added 'color' column to logs table.")
        if 'customer_name' not in columns:
            c.execute('ALTER TABLE logs ADD COLUMN customer_name TEXT')
            logging.info("Added 'customer_name' column to logs table.")
        
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

        # Create app_settings table for storing application configuration in database
        # This allows settings to be backed up with the database instead of config files
        c.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT NOT NULL UNIQUE,
                setting_value TEXT,
                setting_type TEXT DEFAULT 'string',
                description TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT
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
        if 'pause_duration_minutes' not in sessions_columns:
            c.execute('ALTER TABLE sessions ADD COLUMN pause_duration_minutes REAL DEFAULT 0')
            logging.info("Added 'pause_duration_minutes' column to sessions table.")
        if 'pause_start' not in sessions_columns:
            c.execute('ALTER TABLE sessions ADD COLUMN pause_start TEXT')
            logging.info("Added 'pause_start' column to sessions table.")
        if 'project_id' not in sessions_columns:
            c.execute('ALTER TABLE sessions ADD COLUMN project_id TEXT')
            logging.info("Added 'project_id' column to sessions table.")
            # Backfill project_id with normalized values
            try:
                c.execute("SELECT COUNT(*) FROM sessions WHERE project IS NOT NULL")
                if c.fetchone()[0] > 0:
                    # Update each session with normalized project_id
                    c.execute("SELECT session_id, project FROM sessions WHERE project IS NOT NULL")
                    sessions_to_update = c.fetchall()
                    for session in sessions_to_update:
                        normalized_id = normalize_project_id(session['project'])
                        c.execute("UPDATE sessions SET project_id = ? WHERE session_id = ?", 
                                (normalized_id, session['session_id']))
                    logging.info(f"Backfilled project_id for {len(sessions_to_update)} sessions")
            except Exception as e:
                logging.warning(f"Could not backfill project_id: {e}")
        if 'sequence_number' not in sessions_columns:
            c.execute('ALTER TABLE sessions ADD COLUMN sequence_number INTEGER')
            logging.info("Added 'sequence_number' column to sessions table.")
        if 'previous_user' not in sessions_columns:
            c.execute('ALTER TABLE sessions ADD COLUMN previous_user TEXT')
            logging.info("Added 'previous_user' column to sessions table.")
        if 'handoff_delay_minutes' not in sessions_columns:
            c.execute('ALTER TABLE sessions ADD COLUMN handoff_delay_minutes REAL')
            logging.info("Added 'handoff_delay_minutes' column to sessions table.")
        
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
        
        # Create session_projects table for linking SCANNER sessions to multiple projects
        c.execute('''
            CREATE TABLE IF NOT EXISTS session_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                project TEXT NOT NULL,
                added_time TEXT NOT NULL,
                item_count INTEGER DEFAULT 0,
                UNIQUE(session_id, project),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
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

        # Migrate settings from config.json to database (one-time migration)
        # This runs automatically when updating from older versions
        try:
            from config_utils import get_config
            config = get_config()

            # Check if migration has already been done
            c.execute("SELECT COUNT(*) FROM app_settings WHERE setting_key = 'migration_completed'")
            migration_done = c.fetchone()[0] > 0

            if not migration_done and config:
                logging.info("Migrating settings from config.json to database...")

                # Migrate Excel output directories
                excel_users = ['accura', 'boere', 'massief', 'handwerk']
                for user in excel_users:
                    key = f'{user}_output_dir'
                    if key in config:
                        c.execute("""
                            INSERT OR REPLACE INTO app_settings (setting_key, setting_value, setting_type, description)
                            VALUES (?, ?, 'string', ?)
                        """, (key, config[key], f'Excel output directory for {user.upper()}'))
                        logging.info(f"Migrated {key} to database")

                # Migrate user configuration settings
                if 'scanner_panel_open_event_users' in config:
                    import json
                    c.execute("""
                        INSERT OR REPLACE INTO app_settings (setting_key, setting_value, setting_type, description)
                        VALUES ('scanner_panel_open_event_users', ?, 'json', 'List of configured users')
                    """, (json.dumps(config['scanner_panel_open_event_users']),))
                    logging.info("Migrated scanner_panel_open_event_users to database")

                if 'scanner_panel_open_event_user_paths' in config:
                    c.execute("""
                        INSERT OR REPLACE INTO app_settings (setting_key, setting_value, setting_type, description)
                        VALUES ('scanner_panel_open_event_user_paths', ?, 'json', 'User-specific import paths')
                    """, (json.dumps(config['scanner_panel_open_event_user_paths']),))
                    logging.info("Migrated scanner_panel_open_event_user_paths to database")

                if 'scanner_panel_open_event_user_logic_active' in config:
                    c.execute("""
                        INSERT OR REPLACE INTO app_settings (setting_key, setting_value, setting_type, description)
                        VALUES ('scanner_panel_open_event_user_logic_active', ?, 'json', 'User active states')
                    """, (json.dumps(config['scanner_panel_open_event_user_logic_active']),))
                    logging.info("Migrated scanner_panel_open_event_user_logic_active to database")

                if 'scanner_user_to_processing_type_map' in config:
                    c.execute("""
                        INSERT OR REPLACE INTO app_settings (setting_key, setting_value, setting_type, description)
                        VALUES ('scanner_user_to_processing_type_map', ?, 'json', 'User to processing type mapping')
                    """, (json.dumps(config['scanner_user_to_processing_type_map']),))
                    logging.info("Migrated scanner_user_to_processing_type_map to database")

                # Mark migration as complete
                c.execute("""
                    INSERT INTO app_settings (setting_key, setting_value, setting_type, description)
                    VALUES ('migration_completed', 'true', 'boolean', 'Config to database migration completed')
                """)

                logging.info("Settings migration to database completed successfully")
        except Exception as e:
            logging.warning(f"Settings migration encountered an issue (non-fatal): {e}")
            # Don't fail initialization if migration has issues

        conn.commit()
        logging.info("Database initialization complete.")
    except Exception as e:
        logging.error(f"Error during database initialization: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

# --- Authentication Functions ---
# Simple authentication system for local network use
AUTH_USERS = {
    'admin': hashlib.sha256('$mintjensprojectlog1'.encode()).hexdigest(),
}

def check_password(username, password):
    """Check if username and password are valid"""
    if username in AUTH_USERS:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return AUTH_USERS[username] == password_hash
    return False

def track_login(username, ip_address, user_agent, success, login_type='manual'):
    """Track login attempts in the database"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO login_history (username, ip_address, user_agent, login_success, login_type, login_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, ip_address, user_agent, success, login_type, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()

        # Return the ID of the login record for tracking logout later
        return c.lastrowid
    except Exception as e:
        logging.error(f"Error tracking login: {e}")
        return None

def update_logout_time(login_id):
    """Update logout time and session duration for a login record"""
    try:
        conn = get_db()
        c = conn.cursor()

        # Get login time
        c.execute('SELECT login_time FROM login_history WHERE id = ?', (login_id,))
        result = c.fetchone()

        if result:
            login_time = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
            logout_time = datetime.now()
            duration_minutes = (logout_time - login_time).total_seconds() / 60

            c.execute('''
                UPDATE login_history
                SET logout_time = ?, session_duration_minutes = ?
                WHERE id = ?
            ''', (logout_time.strftime('%Y-%m-%d %H:%M:%S'), duration_minutes, login_id))
            conn.commit()
    except Exception as e:
        logging.error(f"Error updating logout time: {e}")

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'user' not in session:
            # For API endpoints, return JSON error
            if request.path.startswith('/api/') or request.path == '/log':
                return jsonify({'error': 'Authentication required'}), 401
            # For web pages, redirect to login
            return redirect(url_for('login', next=request.url))

        # User is logged in, proceed
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""

    # Get client IP address (handle proxies)
    if request.headers.get('X-Forwarded-For'):
        ip_address = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-Ip'):
        ip_address = request.headers.get('X-Real-Ip')
    else:
        ip_address = request.remote_addr

    # Get user agent
    user_agent = request.headers.get('User-Agent', '')[:500]  # Limit length

    # Check for remember me cookie
    if request.method == 'GET':
        remember_token = request.cookies.get('remember_token')
        if remember_token:
            # Verify the token (in production, this should be a secure token stored in database)
            try:
                token_data = json.loads(base64.b64decode(remember_token).decode('utf-8'))
                if 'username' in token_data and 'expires' in token_data:
                    expires = datetime.fromisoformat(token_data['expires'])
                    if expires > datetime.now():
                        # Token is valid, auto-login
                        username = token_data['username']
                        session['user'] = username
                        session['login_id'] = track_login(username, ip_address, user_agent, True, 'cookie')
                        session.permanent = True
                        next_page = request.args.get('next')
                        if next_page and next_page.startswith('/'):
                            return redirect(next_page)
                        return redirect(url_for('dashboard_production_flow'))
            except Exception as e:
                logging.warning(f"Invalid remember token: {e}")

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'

        if check_password(username, password):
            session['user'] = username
            session['login_id'] = track_login(username, ip_address, user_agent, True, 'manual')
            session.permanent = True
            app.permanent_session_lifetime = timedelta(hours=8)  # Session lasts 8 hours

            # Determine redirect destination
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                redirect_url = next_page
            else:
                redirect_url = url_for('dashboard_production_flow')

            # Create response with 302 redirect for password managers
            response = redirect(redirect_url)

            # Set remember me cookie if checkbox was checked
            if remember:
                # Create a token with username and expiry (30 days)
                expires = datetime.now() + timedelta(days=30)
                token_data = {
                    'username': username,
                    'expires': expires.isoformat()
                }
                token = base64.b64encode(json.dumps(token_data).encode('utf-8')).decode('utf-8')
                response.set_cookie('remember_token', token, max_age=30*24*60*60, httponly=True, secure=False)  # secure=True in production

            return response
        else:
            # Track failed login attempt
            track_login(username, ip_address, user_agent, False, 'manual')
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    # Update logout time if we have a login_id
    if 'login_id' in session:
        update_logout_time(session['login_id'])

    session.pop('user', None)
    session.pop('login_id', None)
    response = make_response(redirect(url_for('login')))
    # Clear the remember me cookie
    response.set_cookie('remember_token', '', max_age=0)
    return response

# --- Configuration Management ---
def get_config():
    """Get configuration from config system"""
    # Default configuration - no hardcoded users
    default_config = {
        'scanner_panel_open_event_users': [],
        'available_processing_types': [
            'GEEN_PROCESSING',
            'MDB_PROCESSING',
            'HOPS_PROCESSING',
            'NESTING_PROCESSING',
            'ACCURA_PROCESSING',
            'BOERE_PROCESSING',
            'MASSIEF_PROCESSING',
            'HANDWERK_PROCESSING',
            'AFWERKING_PROCESSING'
        ],
        'excel_processing_types': [
            'NESTING_PROCESSING',
            'ACCURA_PROCESSING',
            'BOERE_PROCESSING',
            'MASSIEF_PROCESSING',
            'HANDWERK_PROCESSING',
            'AFWERKING_PROCESSING'
        ]
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

def get_setting_from_db(setting_key, fallback_to_config=True, default_value=None):
    """
    Get a setting from the database, with optional fallback to config file.

    Args:
        setting_key: The key to look up
        fallback_to_config: If True and key not in database, try config file
        default_value: Default value if not found anywhere

    Returns:
        The setting value, or default_value if not found
    """
    try:
        conn = get_db()
        c = conn.cursor()

        c.execute("""
            SELECT setting_value, setting_type
            FROM app_settings
            WHERE setting_key = ?
        """, (setting_key,))

        row = c.fetchone()
        if row:
            value = row['setting_value']
            setting_type = row['setting_type']

            # Parse based on type
            if setting_type == 'json':
                try:
                    return json.loads(value)
                except:
                    return value
            elif setting_type == 'boolean':
                return value.lower() in ('true', '1', 'yes')
            else:
                return value

        # Not in database, try config file
        if fallback_to_config:
            config = get_config()
            if setting_key in config:
                return config[setting_key]

        # Return default value
        return default_value

    except Exception as e:
        logging.error(f"Error getting setting '{setting_key}' from database: {e}")

        # Fall back to config on error
        if fallback_to_config:
            try:
                config = get_config()
                if setting_key in config:
                    return config[setting_key]
            except:
                pass

        return default_value

def save_setting_to_db(setting_key, value, description=None):
    """
    Save a setting to the database.

    Args:
        setting_key: The key to save
        value: The value to save
        description: Optional description

    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_db()
        c = conn.cursor()

        # Determine value type
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
            value_type = 'json'
        elif isinstance(value, bool):
            value_str = str(value).lower()
            value_type = 'boolean'
        else:
            value_str = str(value)
            value_type = 'string'

        # Update or insert setting
        c.execute("""
            INSERT OR REPLACE INTO app_settings (setting_key, setting_value, setting_type, description, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (setting_key, value_str, value_type, description))

        conn.commit()
        logging.info(f"Saved setting '{setting_key}' to database")
        return True

    except Exception as e:
        logging.error(f"Error saving setting '{setting_key}' to database: {e}")
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
    all_configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
    
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
    """Count active projects for a user (legacy - last 7 days)"""
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

def count_active_projects_in_period(user, start_date, end_date):
    """Count projects that are currently active (not completed) within the date range"""
    try:
        cursor = get_db().cursor()
        # Projects that were opened but not yet completed in this period
        cursor.execute("""
            SELECT COUNT(DISTINCT l.project) 
            FROM logs l
            WHERE l.user = ? 
            AND DATE(l.timestamp) BETWEEN ? AND ?
            AND l.project NOT IN (
                SELECT DISTINCT project 
                FROM logs 
                WHERE user = ? 
                AND event = 'AFGEMELD'
                AND DATE(timestamp) <= ?
            )
            AND l.event IN ('OPEN', 'BEZIG', 'PROJECT_START')
        """, (user, start_date, end_date, user, end_date))
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logging.error(f"Error counting active projects in period for {user}: {e}")
        return 0

def user_has_work_assigned(user, start_date=None, end_date=None):
    """Check if user had any work assigned (OPEN events or sessions) in the period"""
    try:
        cursor = get_db().cursor()
        
        # Check for OPEN events in logs table
        if start_date and end_date:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM logs 
                WHERE user = ? 
                AND event = 'OPEN'
                AND DATE(timestamp) BETWEEN ? AND ?
            """, (user, start_date, end_date))
        else:
            # Check last 30 days by default
            cursor.execute("""
                SELECT COUNT(*) 
                FROM logs 
                WHERE user = ? 
                AND event = 'OPEN'
                AND timestamp > datetime('now', '-30 days')
            """, (user,))
        
        open_events = cursor.fetchone()[0]
        
        # Also check for sessions with items
        if start_date and end_date:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM sessions 
                WHERE user = ? 
                AND item_count > 0
                AND DATE(start_time) BETWEEN ? AND ?
            """, (user, start_date, end_date))
        else:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM sessions 
                WHERE user = ? 
                AND item_count > 0
                AND start_time > datetime('now', '-30 days')
            """, (user,))
        
        sessions_with_items = cursor.fetchone()[0]
        
        return open_events > 0 or sessions_with_items > 0
    except Exception as e:
        logging.error(f"Error checking work assigned for {user}: {e}")
        return False

def count_completed_today(user):
    """Count projects completed today by user"""
    try:
        cursor = get_db().cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        # Look at sessions table which has proper end_time for completed work
        cursor.execute("""
            SELECT COUNT(DISTINCT project) 
            FROM sessions 
            WHERE user = ? 
            AND status = 'completed'
            AND DATE(end_time) = ?
        """, (user, today))
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logging.error(f"Error counting completed today for {user}: {e}")
        return 0

def count_completed_in_period(user, start_date, end_date):
    """Count projects completed by user in specified period"""
    try:
        cursor = get_db().cursor()
        # Look at sessions table which has proper end_time for completed work
        cursor.execute("""
            SELECT COUNT(DISTINCT project) 
            FROM sessions 
            WHERE user = ? 
            AND status = 'completed'
            AND DATE(end_time) BETWEEN ? AND ?
        """, (user, start_date, end_date))
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logging.error(f"Error counting completed in period for {user}: {e}")
        return 0

def count_active_days_in_period(user, start_date, end_date):
    """Count unique days where user had any activity in specified period"""
    try:
        cursor = get_db().cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT DATE(timestamp)) as active_days
            FROM logs 
            WHERE user = ? 
            AND DATE(timestamp) BETWEEN ? AND ?
            AND event IN ('OPEN', 'BEZIG', 'AFGEMELD', 'PROJECT_START', 'SESSION_START', 'SESSION_END')
        """, (user, start_date, end_date))
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logging.error(f"Error counting active days for {user}: {e}")
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

def calculate_avg_items_per_hour(user, start_date=None, end_date=None):
    """Calculate historical average items per hour for user"""
    try:
        cursor = get_db().cursor()
        
        # If no date range specified, use last 90 days
        if start_date and end_date:
            date_filter = "AND s.start_time BETWEEN ? AND ?"
            params = (user, start_date, end_date + ' 23:59:59')
        else:
            date_filter = "AND s.start_time > datetime('now', '-90 days')"
            params = (user,)
        
        # Get all work sessions with item counts (including active sessions)
        cursor.execute(f"""
            SELECT 
                s.work_duration_minutes, 
                s.item_count,
                s.status,
                s.start_time,
                s.end_time
            FROM sessions s
            WHERE s.user = ?
            AND s.status IN ('completed', 'active')
            AND s.item_count > 0
            {date_filter}
        """, params)
        
        sessions = cursor.fetchall()
        
        if sessions:
            total_items = 0
            total_minutes = 0
            
            for session in sessions:
                total_items += session['item_count']
                
                # For completed sessions, use stored work_duration_minutes
                if session['status'] == 'completed' and session['work_duration_minutes']:
                    total_minutes += session['work_duration_minutes']
                # For active sessions, calculate duration from start to now
                elif session['status'] == 'active' and session['start_time']:
                    work_minutes = calculate_work_minutes(session['start_time'], datetime.now().isoformat())
                    total_minutes += work_minutes
            
            if total_minutes > 0:
                items_per_hour = (total_items / total_minutes) * 60
                return f"{items_per_hour:.1f}"
        
        return "--"
    except Exception as e:
        logging.error(f"Error calculating avg items/hr for {user}: {e}")
        return "--"

def calculate_performance_percentage(user, avg_items_per_hour):
    """Calculate performance percentage vs target from settings"""
    try:
        if avg_items_per_hour == "--":
            return 0, "bg-secondary"
        
        # Get user target from config.json (same as settings page)
        config_path = get_writable_path('config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                efficiency_targets = config.get('efficiency_targets', {})
                
                if user in efficiency_targets:
                    target = float(efficiency_targets[user])
                    actual = float(avg_items_per_hour)
                    
                    percentage = min(100, (actual / target) * 100)
                    
                    # Determine color class based on performance
                    if percentage >= 90:
                        color_class = "bg-success"
                    elif percentage >= 70:
                        color_class = "bg-warning"
                    else:
                        color_class = "bg-danger"
                        
                    return int(percentage), color_class
        
        return 0, "bg-secondary"  # No target set
    except Exception as e:
        logging.error(f"Error calculating performance for {user}: {e}")
        return 0, "bg-secondary"

def get_user_activity_last_30_days(user):
    """Get user activity data for the last 30 days"""
    try:
        cursor = get_db().cursor()
        cursor.execute("""
            SELECT DATE(start_time) as date, 
                   SUM(item_count) as items, 
                   SUM(work_duration_minutes) as minutes
            FROM sessions
            WHERE user = ?
            AND status = 'completed'
            AND start_time > datetime('now', '-30 days')
            GROUP BY DATE(start_time)
            ORDER BY date
        """, (user,))
        
        results = cursor.fetchall()
        activity_data = []
        
        for row in results:
            items_per_hour = (row['items'] / row['minutes']) * 60 if row['minutes'] > 0 else 0
            activity_data.append({
                'date': row['date'],
                'items': row['items'],
                'hours': round(row['minutes'] / 60, 1),
                'items_per_hour': round(items_per_hour, 1)
            })
        
        return activity_data
    except Exception as e:
        logging.error(f"Error getting 30-day activity for {user}: {e}")
        return []

def calculate_avg_session_duration(user, start_date, end_date):
    """Calculate average session duration for user in specified period"""
    try:
        cursor = get_db().cursor()
        cursor.execute("""
            SELECT 
                status,
                start_time,
                end_time,
                work_duration_minutes
            FROM sessions 
            WHERE user = ? 
            AND status IN ('completed', 'active')
            AND DATE(start_time) BETWEEN ? AND ?
        """, (user, start_date, end_date))
        
        sessions = cursor.fetchall()
        if not sessions:
            return "--"
            
        total_minutes = 0
        session_count = 0
        
        for session in sessions:
            if session['status'] == 'completed' and session['work_duration_minutes'] and session['work_duration_minutes'] > 0:
                total_minutes += session['work_duration_minutes']
                session_count += 1
            elif session['status'] == 'active' and session['start_time']:
                # For active sessions, calculate duration
                work_minutes = calculate_work_minutes(session['start_time'], datetime.now().isoformat())
                if work_minutes > 0:
                    total_minutes += work_minutes
                    session_count += 1
        
        if session_count > 0:
            avg_minutes = total_minutes / session_count
            hours = int(avg_minutes // 60)
            minutes = int(avg_minutes % 60)
            if hours > 0:
                return f"{hours}u {minutes}m"
            else:
                return f"{minutes}m"
        
        return "--"
    except Exception as e:
        logging.error(f"Error calculating avg session duration for {user}: {e}")
        return "--"

def get_user_activity_date_range(user, start_date, end_date):
    """Get user activity data for a specific date range - one row per project"""
    try:
        cursor = get_db().cursor()
        
        # Get all projects this user worked on in the date range
        cursor.execute("""
            SELECT DISTINCT 
                l.project,
                MIN(l.timestamp) as first_activity,
                MAX(l.timestamp) as last_activity
            FROM logs l
            WHERE l.user = ?
            AND l.project IS NOT NULL
            AND l.project != ''
            AND DATE(l.timestamp) BETWEEN ? AND ?
            GROUP BY l.project
            ORDER BY MIN(l.timestamp) DESC
        """, (user, start_date, end_date))
        
        projects = cursor.fetchall()
        activity_data = []
        
        for project_row in projects:
            project = project_row['project']

            # Get item count for this user/project from logs table
            # (matches productivity-metrics API - sessions can store total MO items, not per-subproject)
            cursor.execute("""
                SELECT MAX(COALESCE(item_count, 0)) as project_items
                FROM logs
                WHERE user = ?
                AND LOWER(project) = LOWER(?)
                AND item_count > 0
            """, (user, project))

            result = cursor.fetchone()
            project_items = result['project_items'] if result and result['project_items'] else 0
            
            # Get work time for this project from sessions
            total_minutes = 0
            
            # First check individual sessions (XLSX_UPDATED, MANUAL)
            # No date filter on sessions - the project was already found via logs in the date range,
            # and sessions may have start_time on a different date than the log entries.
            cursor.execute("""
                SELECT
                    status,
                    start_time,
                    end_time,
                    work_duration_minutes
                FROM sessions
                WHERE user = ? AND LOWER(project) = LOWER(?)
                AND session_type IN ('XLSX_UPDATED', 'MANUAL')
                AND status IN ('completed', 'active')
            """, (user, project))

            individual_sessions = cursor.fetchall()

            for session in individual_sessions:
                if session['status'] == 'completed' and session['work_duration_minutes']:
                    total_minutes += session['work_duration_minutes']
                elif session['status'] == 'active' and session['start_time']:
                    # For active sessions, calculate work time
                    work_minutes = calculate_work_minutes(session['start_time'], datetime.now().isoformat())
                    total_minutes += work_minutes

            # Check for batch sessions that included this project via session_projects
            cursor.execute("""
                SELECT
                    s.session_id,
                    s.start_time,
                    s.end_time,
                    s.work_duration_minutes,
                    s.status,
                    sp.item_count as project_items_in_batch
                FROM sessions s
                JOIN session_projects sp ON s.session_id = sp.session_id
                WHERE s.user = ?
                AND s.session_type = 'SCANNER'
                AND LOWER(sp.project) = LOWER(?)
                AND s.status IN ('completed', 'active')
            """, (user, project))
            
            batch_sessions = cursor.fetchall()
            
            for batch in batch_sessions:
                if batch['status'] == 'completed' and batch['work_duration_minutes'] and batch['work_duration_minutes'] > 0:
                    # Get total items in this batch session from session_projects
                    cursor.execute("""
                        SELECT SUM(COALESCE(item_count, 0)) as batch_total
                        FROM session_projects
                        WHERE session_id = ?
                    """, (batch['session_id'],))
                    
                    batch_result = cursor.fetchone()
                    batch_total_items = batch_result['batch_total'] if batch_result and batch_result['batch_total'] else 0
                    
                    # Calculate proportional time for this project
                    project_items_in_batch = batch['project_items_in_batch'] or project_items
                    if batch_total_items > 0 and project_items_in_batch > 0:
                        proportion = project_items_in_batch / batch_total_items
                        allocated_minutes = batch['work_duration_minutes'] * proportion
                        total_minutes += allocated_minutes
                elif batch['status'] == 'active':
                    # For active batch sessions, calculate current work time
                    work_minutes = calculate_work_minutes(batch['start_time'], datetime.now().isoformat())
                    
                    # Get total items for proportional allocation
                    cursor.execute("""
                        SELECT SUM(COALESCE(item_count, 0)) as batch_total
                        FROM session_projects
                        WHERE session_id = ?
                    """, (batch['session_id'],))
                    
                    batch_result = cursor.fetchone()
                    batch_total_items = batch_result['batch_total'] if batch_result and batch_result['batch_total'] else 0
                    
                    project_items_in_batch = batch['project_items_in_batch'] or 0
                    if batch_total_items > 0 and project_items_in_batch > 0:
                        proportion = project_items_in_batch / batch_total_items
                        total_minutes += work_minutes * proportion
                    else:
                        # Default allocation if no items tracked yet
                        total_minutes += work_minutes * 0.5
            
            # Calculate items per hour
            if total_minutes > 0:
                items_per_hour = (project_items / total_minutes) * 60
            else:
                items_per_hour = 0

            # Get the date of first activity for this project (date only, so chart can aggregate per day)
            raw_date = project_row['first_activity'] if project_row['first_activity'] else start_date
            activity_date = raw_date[:10] if raw_date else start_date

            # Determine project status: check for AFGEMELD event in logs, then session status
            project_status = 'active'
            cursor.execute("""
                SELECT 1 FROM logs
                WHERE user = ? AND project = ? AND event = 'AFGEMELD'
                LIMIT 1
            """, (user, project))
            if cursor.fetchone():
                project_status = 'completed'
            else:
                cursor.execute("""
                    SELECT 1 FROM sessions
                    WHERE user = ? AND LOWER(project) = LOWER(?)
                    AND status = 'completed'
                    LIMIT 1
                """, (user, project))
                if cursor.fetchone():
                    project_status = 'completed'

            activity_data.append({
                'date': activity_date,
                'project': project,
                'items': project_items,
                'hours': round(total_minutes / 60, 2),
                'items_per_hour': round(items_per_hour, 1),
                'status': project_status
            })
        
        return activity_data
    except Exception as e:
        logging.error(f"Error getting date range activity for {user}: {e}")
        return []

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

def calculate_items_hour_change_vs_last_week(user):
    """Calculate percentage change in items/hour vs last week"""
    try:
        cursor = get_db().cursor()
        
        # Get current week's data (last 7 days)
        cursor.execute("""
            SELECT 
                SUM(s.item_count) as total_items,
                SUM(s.work_duration_minutes) as total_work_minutes
            FROM sessions s
            WHERE s.user = ?
            AND s.status = 'completed'
            AND s.work_duration_minutes > 0
            AND s.item_count > 0
            AND s.start_time >= datetime('now', '-7 days')
        """, (user,))
        
        current_week = cursor.fetchone()
        
        # Get previous week's data (8-14 days ago)
        cursor.execute("""
            SELECT 
                SUM(s.item_count) as total_items,
                SUM(s.work_duration_minutes) as total_work_minutes
            FROM sessions s
            WHERE s.user = ?
            AND s.status = 'completed'
            AND s.work_duration_minutes > 0
            AND s.item_count > 0
            AND s.start_time >= datetime('now', '-14 days')
            AND s.start_time < datetime('now', '-7 days')
        """, (user,))
        
        last_week = cursor.fetchone()
        
        # Calculate items/hour for both weeks
        current_items_hour = 0
        last_items_hour = 0
        
        if current_week and current_week['total_work_minutes'] and current_week['total_items']:
            current_items_hour = (current_week['total_items'] * 60) / current_week['total_work_minutes']
        
        if last_week and last_week['total_work_minutes'] and last_week['total_items']:
            last_items_hour = (last_week['total_items'] * 60) / last_week['total_work_minutes']
        
        # Calculate percentage change
        if last_items_hour > 0:
            change_percent = round(((current_items_hour - last_items_hour) / last_items_hour) * 100, 1)
            return change_percent
        elif current_items_hour > 0:
            return 100  # If no data last week but data this week
        else:
            return 0  # No data for either week
            
    except Exception as e:
        logging.error(f"Error calculating items/hour change for {user}: {e}")
        return 0

def calculate_active_projects_change_vs_last_week(user):
    """Calculate change in active projects vs last week"""
    try:
        cursor = get_db().cursor()
        
        # Get current week's active projects count (average daily active projects)
        cursor.execute("""
            SELECT AVG(daily_active) as avg_active
            FROM (
                SELECT DATE(timestamp) as date, COUNT(DISTINCT project) as daily_active
                FROM logs
                WHERE user = ? 
                AND timestamp >= datetime('now', '-7 days')
                AND event IN ('OPEN', 'BEZIG')
                GROUP BY DATE(timestamp)
            )
        """, (user,))
        
        current_week = cursor.fetchone()
        
        # Get previous week's active projects count
        cursor.execute("""
            SELECT AVG(daily_active) as avg_active
            FROM (
                SELECT DATE(timestamp) as date, COUNT(DISTINCT project) as daily_active
                FROM logs
                WHERE user = ? 
                AND timestamp >= datetime('now', '-14 days')
                AND timestamp < datetime('now', '-7 days')
                AND event IN ('OPEN', 'BEZIG')
                GROUP BY DATE(timestamp)
            )
        """, (user,))
        
        last_week = cursor.fetchone()
        
        current_avg = current_week['avg_active'] if current_week and current_week['avg_active'] else 0
        last_avg = last_week['avg_active'] if last_week and last_week['avg_active'] else 0
        
        # Calculate absolute change (not percentage since it's project count)
        change = round(current_avg - last_avg, 1)
        return change
            
    except Exception as e:
        logging.error(f"Error calculating active projects change for {user}: {e}")
        return 0

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
    
    # Use unified work minutes calculation excluding weekends and holidays
    return calculate_work_minutes(start_time, end_time)

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
    
    # Get configured users from database (with config fallback)
    configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
    
    # Get all events for this project
    # Order by timestamp DESC, then prioritize AFGEMELD events when timestamps are equal
    c.execute("""
        SELECT timestamp, event, user, status
        FROM logs
        WHERE project = ?
        ORDER BY timestamp DESC, 
                CASE WHEN event = 'AFGEMELD' THEN 3 
                     WHEN event = 'OPEN' THEN 2
                     WHEN event = 'BEZIG' THEN 1
                     ELSE 0 END DESC
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
        # Prioritize AFGEMELD over other events at the same timestamp
        if event['event'] == 'AFGEMELD':
            if user not in user_afgemeld_events:
                user_afgemeld_events[user] = event
                # If there's a BEZIG event at the same timestamp, remove it
                if user in user_bezig_events and user_bezig_events[user]['timestamp'] == event['timestamp']:
                    del user_bezig_events[user]
        elif event['event'] == 'OPEN' and event['status'] == 'OPEN':
            if user not in user_open_events:
                user_open_events[user] = event
        elif event['status'] == 'BEZIG':
            # Only track BEZIG if we haven't seen AFGEMELD at the same or later timestamp
            if user not in user_bezig_events and user not in user_afgemeld_events:
                user_bezig_events[user] = event
    
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
        # Check if this is a new batch session (keeps previous session active)
        is_new_batch = data.get('is_new_batch', False)
        background_session = data.get('background_session', None)
        
        if not is_new_batch:
            # Normal behavior: Close any active sessions for this user
            c.execute("""
                SELECT session_id, start_time FROM sessions 
                WHERE user = ? AND status = 'active' AND session_type = 'SCANNER'
            """, (data['user'],))
            
            active_session = c.fetchone()
            if active_session:
                active_session = dict(active_session)
                work_minutes = calculate_work_minutes(active_session['start_time'], data['timestamp'])
                c.execute("""
                    UPDATE sessions 
                    SET status = 'completed', 
                        end_time = ?,
                        work_duration_minutes = ?
                    WHERE session_id = ? AND status = 'active'
                """, (data['timestamp'], work_minutes, active_session['session_id']))
        else:
            # New batch: Keep the background session active
            logging.info(f"New batch session - keeping {background_session} active in background")
        
        # Create new session with project linking
        session_type = data.get('session_type', 'SCANNER')  # Default to SCANNER for scanner panel
        project = data.get('project', '')  # Get project if provided
        project_id = normalize_project_id(project) if project else None
        
        # For SCANNER sessions, project_id might be None (batch work)
        c.execute("""
            INSERT INTO sessions (session_id, user, project, project_id, start_time, status, session_type)
            VALUES (?, ?, ?, ?, ?, 'active', ?)
        """, (data['session_id'], data['user'], project, project_id, data['timestamp'], session_type))
        
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
    
    # Check if we should keep projects active (for batch transitions)
    keep_projects_active = data.get('keep_projects_active', False)
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        # Get session details including pause duration
        c.execute("""
            SELECT start_time, pause_start, pause_duration_minutes 
            FROM sessions 
            WHERE session_id = ? AND status = 'active'
        """, (data['session_id'],))
        
        session = c.fetchone()
        if session:
            session = dict(session)
            # If session is currently paused, add final pause duration
            if session['pause_start']:
                final_pause = calculate_work_minutes(session['pause_start'], data['timestamp'])
                total_pause_minutes = (session['pause_duration_minutes'] or 0) + final_pause
            else:
                total_pause_minutes = session['pause_duration_minutes'] or 0
            
            # Calculate total work minutes
            total_minutes = calculate_work_minutes(session['start_time'], data['timestamp'])
            
            # Use the stored pause duration which is already calculated in work minutes
            # This is more reliable than recalculating from events
            work_pause_minutes = total_pause_minutes
            
            # Subtract pause time from total to get actual work time
            actual_work_minutes = max(0, total_minutes - work_pause_minutes)
            
            logging.info(f"Session {data['session_id']}: total_work_minutes={total_minutes}, pause_work_minutes={work_pause_minutes}, actual={actual_work_minutes}")
            
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
                    pause_duration_minutes = ?,
                    item_count = ?,
                    pause_start = NULL
                WHERE session_id = ? AND status = 'active'
            """, (data['timestamp'], actual_work_minutes, work_pause_minutes, total_items, data['session_id']))
            
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
            AND session_type = 'XLSX_UPDATED'
        """, (data['user'], data['project']))
        
        existing = c.fetchone()
        if not existing:
            # Create new ACTIVE session (work is starting now)
            session_id = f"{data['user']}_{data['project']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            project_id = normalize_project_id(data['project'])
            
            # Check for previous sessions in this project
            c.execute("""
                SELECT user, end_time, sequence_number
                FROM sessions 
                WHERE project_id = ? AND user != ?
                ORDER BY start_time DESC
                LIMIT 1
            """, (project_id, data['user']))
            
            prev_session = c.fetchone()
            if prev_session:
                prev_session = dict(prev_session)
                sequence_number = (prev_session['sequence_number'] or 0) + 1
                previous_user = prev_session['user']

                # Calculate handoff delay
                handoff_delay = None
                if previous_user and prev_session['end_time']:
                    handoff_delay = calculate_work_minutes(prev_session['end_time'], data['timestamp'])
            else:
                sequence_number = 1
                previous_user = None
                handoff_delay = None
            
            # Find the session start time for the current user's active session
            c.execute("""
                SELECT start_time FROM sessions 
                WHERE user = ? AND status = 'active' AND session_type = 'SCANNER'
                ORDER BY start_time DESC LIMIT 1
            """, (data['user'],))
            
            session_result = c.fetchone()
            project_start_time = session_result['start_time'] if session_result else data['timestamp']
            
            # Get the actual item count from the user's OPEN event
            c.execute("""
                SELECT item_count FROM logs 
                WHERE event = 'OPEN' AND project = ? AND user = ?
                ORDER BY id DESC LIMIT 1
            """, (data['project'], data['user']))
            
            open_event = c.fetchone()
            actual_item_count = open_event['item_count'] if open_event and open_event['item_count'] is not None else 0
            
            # Check if there's already an AFGEMELD event for this user/project
            # This prevents invalid PROJECT_START entries after AFGEMELD
            c.execute("""
                SELECT COUNT(*) as count FROM logs 
                WHERE event = 'AFGEMELD' 
                AND project = ? 
                AND user = ?
            """, (data['project'], data['user']))
            
            afgemeld_check = c.fetchone()
            if afgemeld_check and afgemeld_check['count'] > 0:
                logging.warning(f"Blocking PROJECT_START for {data['user']} on {data['project']} - already has AFGEMELD event")
                return jsonify({
                    'success': False, 
                    'error': 'Project already completed (AFGEMELD) for this user'
                }), 400
            
            # Use transaction for all related operations
            operations = [
                # 1. Insert new session
                ("""INSERT INTO sessions (session_id, user, project, project_id, start_time, status, 
                                        item_count, session_type, sequence_number, previous_user, handoff_delay_minutes)
                    VALUES (?, ?, ?, ?, ?, 'active', 0, 'XLSX_UPDATED', ?, ?, ?)""",
                 (session_id, data['user'], data['project'], project_id, data['timestamp'],
                  sequence_number, previous_user, handoff_delay)),
                
                # 2. Create project session entry
                ("""INSERT OR IGNORE INTO project_sessions (project, start_time, status)
                    VALUES (?, ?, 'active')""",
                 (data['project'], project_start_time)),
                
                # 3. Update project_log to BEZIG
                ("""UPDATE project_log 
                    SET event = 'BEZIG', timestamp = ?, user = ?
                    WHERE id = (
                        SELECT id FROM project_log 
                        WHERE project = ? AND event = 'OPEN'
                        ORDER BY id DESC LIMIT 1
                    )""",
                 (data['timestamp'], data['user'], data['project'])),
                
                # 4. Insert BEZIG event in project_log
                ("""INSERT INTO project_log (project, event, user, timestamp, item_count)
                    VALUES (?, 'BEZIG', ?, ?, ?)""",
                 (data['project'], data['user'], data['timestamp'], data.get('item_count', 0))),
                
                # 5. Update logs status to BEZIG
                ("""UPDATE logs 
                    SET status = 'BEZIG'
                    WHERE event = 'OPEN' AND status = 'OPEN' AND project = ? AND user = ?""",
                 (data['project'], data['user'])),
                
                # 6. Insert PROJECT_START event
                ("""INSERT INTO logs (timestamp, event, details, project, user, status, session_id)
                    VALUES (?, 'PROJECT_START', ?, ?, ?, 'BEZIG', ?)""",
                 (data['timestamp'], f"XLSX_UPDATED: {actual_item_count} items", 
                  data['project'], data['user'], session_id))
            ]
            
            # Execute all operations in a transaction
            execute_transaction(conn, operations)
            logging.info(f"XLSX_UPDATED session started for {data['user']} on project {data['project']} - Status changed to BEZIG")
            
        # Return the session_id so the client knows what was created
        return jsonify({'success': True, 'session_id': session_id if not existing else existing['session_id']})
        
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

@app.route('/api/user/<user>/active-sessions', methods=['GET'])
def get_user_active_sessions(user):
    """Get all active sessions for a specific user"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get all active sessions for this user
        c.execute("""
            SELECT session_id, user, session_type, project, start_time, pause_start, pause_duration_minutes
            FROM sessions
            WHERE user = ? AND status = 'active'
            ORDER BY start_time DESC
        """, (user,))

        sessions = []
        for row in c.fetchall():
            sessions.append({
                'session_id': row['session_id'],
                'user': row['user'],
                'session_type': row['session_type'],
                'project': row['project'] or '',
                'start_time': row['start_time'],
                'pause_start': row['pause_start'],
                'is_paused': row['pause_start'] is not None,
                'total_pause_duration': row['pause_duration_minutes'] or 0
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'user': user,
            'sessions': sessions,
            'count': len(sessions)
        })
        
    except Exception as e:
        logging.error(f"Error getting active sessions for user {user}: {e}")
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

        session = dict(session)

        # Calculate work duration excluding weekends and holidays
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

@app.route('/session/add_project', methods=['POST'])
def add_project_to_session():
    """Add a project to an active SCANNER session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        project = data.get('project')
        item_count = data.get('item_count', 0)
        timestamp = data.get('timestamp', datetime.now().isoformat())
        
        if not session_id or not project:
            return jsonify({'success': False, 'error': 'Missing session_id or project'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Verify session exists and is active
        c.execute("""
            SELECT session_id, session_type FROM sessions 
            WHERE session_id = ? AND status = 'active'
        """, (session_id,))
        
        session = c.fetchone()
        if not session:
            return jsonify({'success': False, 'error': 'Session not found or not active'}), 404
        
        # Add project to session_projects linking table
        try:
            c.execute("""
                INSERT INTO session_projects (session_id, project, added_time, item_count)
                VALUES (?, ?, ?, ?)
            """, (session_id, project, timestamp, item_count))
            
            # Create or update project_sessions entry
            # For batch sessions, we'll update the duration later when AFGEMELD is sent
            # Check if project already has a completed session
            c.execute("""
                SELECT total_duration_minutes, status
                FROM project_sessions
                WHERE project = ?
                ORDER BY start_time DESC
                LIMIT 1
            """, (project,))
            
            existing = c.fetchone()
            
            if not existing:
                # First time working on this project
                c.execute("""
                    INSERT INTO project_sessions (project, start_time, status, total_duration_minutes)
                    VALUES (?, ?, 'active', 0)
                """, (project, timestamp))
            elif existing['status'] == 'completed':
                # Project was worked on before and completed, keep the existing total
                # We'll add to it when this session completes
                pass
            else:
                # Project is already active, update start time if earlier
                c.execute("""
                    UPDATE project_sessions
                    SET start_time = MIN(start_time, ?)
                    WHERE project = ? AND status = 'active'
                """, (timestamp, project))
            
            # Don't update session's project field for SCANNER sessions - they use session_projects only
            # The project field stays NULL for SCANNER sessions
            
            conn.commit()
            logging.info(f"Added project {project} to session {session_id}")
            return jsonify({'success': True, 'message': f'Project {project} added to session'})
            
        except sqlite3.IntegrityError:
            # Project already linked to this session
            return jsonify({'success': True, 'message': 'Project already linked to session'})
        
    except Exception as e:
        logging.error(f"Error adding project to session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/session/update_project_items', methods=['POST'])
def update_project_items():
    """Update the item count for a project in session_projects table"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        project = data.get('project')
        item_count = data.get('item_count', 0)
        
        if not session_id or not project:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Update the item count for this project in session_projects
        c.execute("""
            UPDATE session_projects 
            SET item_count = ?
            WHERE session_id = ? AND project = ?
        """, (item_count, session_id, project))
        
        if c.rowcount == 0:
            # Entry doesn't exist, create it
            c.execute("""
                INSERT INTO session_projects (session_id, project, added_time, item_count)
                VALUES (?, ?, ?, ?)
            """, (session_id, project, datetime.now().isoformat(), item_count))
        
        conn.commit()
        logging.info(f"Updated item count for project {project} in session {session_id}: {item_count} items")
        
        return jsonify({
            'success': True,
            'message': f'Updated {project} with {item_count} items'
        })
    
    except Exception as e:
        logging.error(f"Error updating project items: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/session/close', methods=['POST'])
def close_session():
    """Close an active session for AFGEMELD - handles paused sessions properly"""
    try:
        data = request.get_json()
        user = data.get('user')
        project = data.get('project')
        timestamp = data.get('timestamp', datetime.now().isoformat())
        item_count = data.get('item_count', 0)
        
        if not user or not project:
            return jsonify({'success': False, 'error': 'Missing user or project'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Find active XLSX_UPDATED or MANUAL sessions for this user/project
        # Use normalized project_id for better matching
        project_id = normalize_project_id(project)
        
        c.execute("""
            SELECT session_id, start_time, session_type, pause_start, pause_duration_minutes 
            FROM sessions 
            WHERE user = ? 
            AND (project = ? OR project_id = ?)
            AND status = 'active'
            AND session_type IN ('XLSX_UPDATED', 'MANUAL')
        """, (user, project, project_id))
        
        sessions_closed = 0
        for session in c.fetchall():
            # Handle paused sessions properly
            total_pause_minutes = session['pause_duration_minutes'] or 0
            
            # If currently paused, add the final pause duration
            if session['pause_start']:
                final_pause = calculate_work_minutes(session['pause_start'], timestamp)
                total_pause_minutes += final_pause
            
            # Calculate total work time
            total_work_minutes = calculate_work_minutes(session['start_time'], timestamp)
            actual_work_minutes = max(0, total_work_minutes - total_pause_minutes)
            
            # Close the session
            c.execute("""
                UPDATE sessions 
                SET status = 'completed',
                    end_time = ?,
                    work_duration_minutes = ?,
                    pause_duration_minutes = ?,
                    item_count = ?,
                    pause_start = NULL
                WHERE session_id = ? AND status = 'active'
            """, (timestamp, actual_work_minutes, total_pause_minutes, 
                  item_count, session['session_id']))
            
            if c.rowcount > 0:
                sessions_closed += 1
                logging.info(f"Closed {session['session_type']} session {session['session_id']} for {user} on project {project}")
        
        conn.commit()
        
        if sessions_closed > 0:
            return jsonify({'success': True, 'sessions_closed': sessions_closed})
        else:
            return jsonify({'success': True, 'message': 'No active sessions to close', 'sessions_closed': 0})
            
    except Exception as e:
        logging.error(f"Error closing session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/session/check', methods=['GET'])
def check_session():
    """Check if there's an existing paused session for a user/project"""
    try:
        user = request.args.get('user')
        project = request.args.get('project')
        
        if not user or not project:
            return jsonify({'has_session': False, 'error': 'Missing user or project parameter'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Look for active sessions (including paused ones)
        c.execute("""
            SELECT session_id, start_time, item_count, pause_duration_minutes, pause_start
            FROM sessions 
            WHERE user = ? AND project = ? AND status = 'active'
            ORDER BY start_time DESC
            LIMIT 1
        """, (user, project))
        
        session = c.fetchone()

        if session:
            session = dict(session)
            # Check if it's paused (has pause_start)
            if session['pause_start']:
                return jsonify({
                    'has_session': True,
                    'session_id': session['session_id'],
                    'start_time': session['start_time'],
                    'item_count': session['item_count'],
                    'pause_duration_minutes': session['pause_duration_minutes'] or 0,
                    'is_paused': True
                })
            else:
                # Active but not paused - this shouldn't happen if we're on database panel
                # but return the info anyway
                return jsonify({
                    'has_session': True,
                    'session_id': session['session_id'],
                    'start_time': session['start_time'],
                    'item_count': session['item_count'],
                    'pause_duration_minutes': session['pause_duration_minutes'] or 0,
                    'is_paused': False
                })
        else:
            return jsonify({'has_session': False})
            
    except Exception as e:
        logging.error(f"Error checking session: {e}")
        return jsonify({'has_session': False, 'error': str(e)}), 500

@app.route('/session/pause', methods=['POST'])
def pause_session():
    """Pause an active session"""
    try:
        data = request.get_json()
        logging.info(f"[PAUSE_SESSION] Received pause request: {data}")
        required_fields = ['session_id', 'timestamp']
        
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Check if session exists and is active
        c.execute("""
            SELECT session_id, user, project, pause_start FROM sessions 
            WHERE session_id = ? AND status = 'active'
        """, (data['session_id'],))
        
        session = c.fetchone()
        if not session:
            return jsonify({'success': False, 'error': 'Session not found or already ended'}), 404

        # Convert Row to dict for easier access
        session_dict = dict(session)

        # Check if session is already paused
        if session_dict.get('pause_start'):
            logging.warning(f"Session {data['session_id']} is already paused since {session_dict['pause_start']}. Ignoring duplicate pause request.")
            return jsonify({'success': True, 'warning': 'Session was already paused', 'already_paused': True})
        
        # Store pause start time in session (add column if not exists)
        c.execute("PRAGMA table_info(sessions)")
        columns = [column[1] for column in c.fetchall()]
        if 'pause_start' not in columns:
            c.execute('ALTER TABLE sessions ADD COLUMN pause_start TEXT')
        if 'pause_duration_minutes' not in columns:
            c.execute('ALTER TABLE sessions ADD COLUMN pause_duration_minutes REAL DEFAULT 0')
        
        # Update session with pause start time
        c.execute("""
            UPDATE sessions 
            SET pause_start = ?
            WHERE session_id = ?
        """, (data['timestamp'], data['session_id']))
        
        # Log the pause event (already handled by scanner panels but kept for compatibility)
        # Get user and project from data if provided, otherwise use session values
        user = data.get('user', session_dict['user'])
        project = data.get('project', session_dict['project'])
        
        # Don't insert SESSION_PAUSE here - scanner_panel already sends it separately
        # This was causing duplicate events
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
        logging.info(f"[RESUME_SESSION] Received resume request: {data}")
        required_fields = ['session_id', 'timestamp']
        
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Check if session exists and is active
        c.execute("""
            SELECT session_id, user, project, pause_start, pause_duration_minutes 
            FROM sessions 
            WHERE session_id = ? AND status = 'active'
        """, (data['session_id'],))
        
        session = c.fetchone()
        if not session:
            return jsonify({'success': False, 'error': 'Session not found or already ended'}), 404

        # Convert Row to dict for easier access
        session_dict = dict(session)

        # Calculate pause duration and update session
        if session_dict['pause_start']:
            # Calculate pause duration in minutes
            pause_minutes = calculate_work_minutes(session_dict['pause_start'], data['timestamp'])

            # Add to total pause duration
            current_pause_duration = session_dict['pause_duration_minutes'] or 0
            total_pause_duration = current_pause_duration + pause_minutes

            # Update session with accumulated pause time and clear pause_start
            c.execute("""
                UPDATE sessions
                SET pause_duration_minutes = ?,
                    pause_start = NULL
                WHERE session_id = ?
            """, (total_pause_duration, data['session_id']))
        else:
            pause_minutes = 0
            total_pause_duration = session_dict['pause_duration_minutes'] or 0

        # Get user and project from data if provided, otherwise use session values
        user = data.get('user', session_dict['user'])
        project = data.get('project', session_dict['project'])
        
        # Don't insert SESSION_RESUME here - scanner_panel already sends it separately
        # This was causing duplicate events
        conn.commit()
        logging.info(f"Session resumed: {data['session_id']} (total pause: {total_pause_duration:.1f} minutes)")
        return jsonify({'success': True, 'pause_minutes': pause_minutes, 'total_pause_minutes': total_pause_duration})
        
    except Exception as e:
        logging.error(f"Error resuming session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/set_log_callback', methods=['POST'])
def set_log_callback():
    """Set the log callback for the background service"""
    try:
        # Set up the callback function on the background service
        global background_service
        if background_service:
            background_service.log_callback = background_work_callback
            logging.info("Background service log callback has been set successfully")
            return jsonify({'success': True, 'message': 'Log callback set successfully'})
        else:
            return jsonify({'success': False, 'error': 'Background service not available'}), 500
            
    except Exception as e:
        logging.error(f"Error setting log callback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/log', methods=['POST', 'GET'])
def log_event():
    data = request.get_json(force=True) if request.method == 'POST' else request.args
    logging.info(f"[db_log_api] /log called with data: {data}")

    event = data.get('event')
    if not event:
        return jsonify({'success': False, 'error': 'Missing event'}), 400

    # Debug SESSION events
    if event in ['SESSION_PAUSE', 'SESSION_RESUME']:
        logging.info(f"[SESSION_EVENT] Received {event} from {data.get('user')} for project {data.get('project')} session {data.get('session_id')}")

    user = data.get('user', 'unknown')
    if event == 'test_connect':
        logging.info(f"  [INFO] Received test_connect from user '{user}'. Connection successful.")
        return jsonify({'success': True})

    details = data.get('details')
    project = data.get('project', '')
    base_mo_code = data.get('base_mo_code', '')
    is_rep_variant = 1 if data.get('is_rep_variant', False) else 0
    file_path = data.get('file_path', '') # Default to empty string if not provided
    # Normalize file path if provided
    if file_path:
        file_path = os.path.normpath(file_path)
    item_count = data.get('item_count', None)  # New field
    session_id = data.get('session_id')
    timestamp = data.get('timestamp', datetime.now().isoformat())
    # Get status from request data if provided, otherwise default to empty
    status = data.get('status', '')

    try:
        conn = get_db()
        c = conn.cursor()

        if event == 'OPEN':
            status = 'OPEN'
            # Only trigger background import service for initial scanner events, not for auto-generated events
            # This prevents infinite loops where background service creates OPEN events that trigger more processing
            skip_trigger = False
            
            # Skip if auto-generated
            if details and ('Auto-detected' in details or 'XLSX_UPDATED' in details):
                skip_trigger = True
            
            # Skip if manual entry (already fully processed)
            if details and 'Manual entry' in details:
                skip_trigger = True
            
            # Skip if Excel unified processing already triggered from scanner panel
            if details and 'Excel-unified-triggered' in details:
                skip_trigger = True
            
            if not skip_trigger:
                # Trigger the background import service for processing
                logging.info(f"Event OPEN received for {user} on {project}. Triggering background import service.")
                background_service.trigger_import_for_event(
                    user_type=user,
                    project_code=project,
                    event_details=details,
                    timestamp=timestamp
                )
            else:
                logging.info(f"Skipping background import trigger: {user} on {project} ({details})")
        elif event == 'PROJECT_START':
            status = 'BEZIG'
            # Update the corresponding OPEN log to BEZIG status
            c.execute(
                'UPDATE logs SET status = ? WHERE event = ? AND status = ? AND lower(project) = ? AND user = ?',
                ('BEZIG', 'OPEN', 'OPEN', project.lower(), user)
            )
            if c.rowcount > 0:
                logging.info(f"Updated {c.rowcount} 'OPEN' log(s) to 'BEZIG' for user '{user}' on project '{project}'.")
        elif event == 'BEZIG':
            status = 'BEZIG'
            # Check if this is a visual-only BEZIG event
            visual_only = data.get('visual_only', False)
            if not visual_only:
                # Update the corresponding OPEN log to BEZIG status
                c.execute(
                    'UPDATE logs SET status = ? WHERE event = ? AND status = ? AND lower(project) = ? AND user = ?',
                    ('BEZIG', 'OPEN', 'OPEN', project.lower(), user)
                )
                if c.rowcount > 0:
                    logging.info(f"Updated {c.rowcount} 'OPEN' log(s) to 'BEZIG' for user '{user}' on project '{project}'.")
            else:
                logging.info(f"Visual-only BEZIG event for {user} on {project} - no session impact")
        elif event == 'AFGEMELD':
            status = 'AFGEMELD'
            # Find the corresponding 'OPEN' log and update its status to 'AFGEMELD'
            c.execute(
                'UPDATE logs SET status = ? WHERE event = ? AND status = ? AND lower(project) = ? AND user = ?',
                ('AFGEMELD', 'OPEN', 'OPEN', project.lower(), user)
            )
            if c.rowcount > 0:
                logging.info(f"Updated {c.rowcount} 'OPEN' log(s) to 'AFGEMELD' for user '{user}' on project '{project}'.")
            
            # Handle session completion for AFGEMELD events
            # SCANNER sessions (batch) should remain active until manually stopped
            # XLSX_UPDATED/MANUAL sessions should complete on AFGEMELD
            
            # Find active sessions for this user/project
            # Also check with normalized project_id for better matching
            project_id = normalize_project_id(project)
            c.execute("""
                SELECT session_id, start_time, session_type, pause_start, pause_duration_minutes 
                FROM sessions 
                WHERE user = ? 
                AND (project = ? OR project_id = ?)
                AND status = 'active'
            """, (user, project, project_id))
            
            active_sessions = c.fetchall()
            for session in active_sessions:
                session_type = session['session_type']
                
                if session_type in ['XLSX_UPDATED', 'MANUAL']:
                    # Complete individual work sessions on AFGEMELD
                    # Handle paused sessions properly
                    total_pause_minutes = session['pause_duration_minutes'] or 0
                    
                    # If currently paused, add the final pause duration
                    if session['pause_start']:
                        final_pause = calculate_work_minutes(session['pause_start'], timestamp)
                        total_pause_minutes += final_pause
                    
                    # Calculate total work time
                    total_work_minutes = calculate_work_minutes(session['start_time'], timestamp)
                    actual_work_minutes = max(0, total_work_minutes - total_pause_minutes)
                    
                    c.execute("""
                        UPDATE sessions 
                        SET status = 'completed',
                            end_time = ?,
                            work_duration_minutes = ?,
                            pause_duration_minutes = ?,
                            item_count = ?,
                            pause_start = NULL
                        WHERE session_id = ? AND status = 'active'
                    """, (timestamp, actual_work_minutes, total_pause_minutes, 
                          item_count or 0, session['session_id']))
                    
                    logging.info(f"Completed {session_type} session {session['session_id']} for {user} on project {project} (work: {actual_work_minutes:.1f} min, pause: {total_pause_minutes:.1f} min)")
                
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
                # For batch sessions, calculate proportional duration
                
                # Check if this project is part of a batch session
                c.execute("""
                    SELECT 
                        sp.session_id,
                        sp.item_count,
                        (SELECT SUM(sp2.item_count) FROM session_projects sp2 WHERE sp2.session_id = sp.session_id) as total_items,
                        s.work_duration_minutes,
                        s.pause_duration_minutes
                    FROM session_projects sp
                    JOIN sessions s ON sp.session_id = s.session_id
                    WHERE sp.project = ?
                    AND s.session_type = 'SCANNER'
                    ORDER BY s.start_time DESC
                    LIMIT 1
                """, (project,))
                
                batch_info = c.fetchone()
                
                if batch_info and batch_info['total_items'] > 1:
                    # This is part of a batch - use proportional time
                    proportion = batch_info['item_count'] / batch_info['total_items'] if batch_info['total_items'] > 0 else 1
                    
                    # If work_duration_minutes is None, the session is still active, calculate it
                    if batch_info['work_duration_minutes'] is None:
                        # Get session start time and calculate duration
                        c.execute("SELECT start_time FROM sessions WHERE session_id = ?", (batch_info['session_id'],))
                        session_start = c.fetchone()
                        if session_start:
                            work_minutes = calculate_work_minutes(session_start['start_time'], timestamp)
                        else:
                            work_minutes = 0
                    else:
                        work_minutes = batch_info['work_duration_minutes']
                    
                    total_session_time = work_minutes + (batch_info['pause_duration_minutes'] or 0)
                    proportional_duration = total_session_time * proportion
                    
                    # Check if project already has completed time from previous sessions
                    c.execute("""
                        SELECT total_duration_minutes 
                        FROM project_sessions 
                        WHERE project = ?
                    """, (project,))
                    
                    existing_duration = c.fetchone()
                    if existing_duration and existing_duration['total_duration_minutes']:
                        # Add to existing duration
                        new_total_duration = existing_duration['total_duration_minutes'] + proportional_duration
                    else:
                        new_total_duration = proportional_duration
                    
                    c.execute("""
                        UPDATE project_sessions 
                        SET status = 'completed',
                            end_time = ?,
                            total_duration_minutes = ?
                        WHERE project = ?
                    """, (timestamp, new_total_duration, project))
                else:
                    # Not a batch or single-project session - use full duration
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
        
        # Extract ACCURA-specific fields
        aantal_items = data.get('aantal_items', 0)
        aantal_sides = data.get('aantal_sides', 0)
        
        c.execute(
            '''INSERT INTO logs (timestamp, event, details, project, user, status, base_mo_code, is_rep_variant, 
               file_path, item_count, nesting_count, opdeelzaag_count, session_id, mo_number, so_number, 
               customer_name, color, aantal_items, aantal_sides) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (timestamp, event, details, project, user, status, base_mo_code, is_rep_variant, file_path, 
             item_count, nesting_count, opdeelzaag_count, session_id, mo_number, so_number, customer_name, color, aantal_items, aantal_sides)
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
    
    # Normalize the file path to use consistent separators
    file_path = os.path.normpath(file_path)

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

@app.route('/api/project/<path:project>/delete', methods=['DELETE'])
def delete_project(project):
    """Delete a project and ALL related data from the database."""
    logging.info(f"[DELETE_PROJECT] Request to delete project: {project}")
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # First check for active sessions working on this project
        # Check direct project sessions
        c.execute("""
            SELECT COUNT(*) FROM sessions 
            WHERE project = ? AND status = 'active'
        """, (project,))
        active_direct_sessions = c.fetchone()[0]
        
        # Check batch SCANNER sessions that might be working on this project
        c.execute("""
            SELECT COUNT(DISTINCT s.session_id) 
            FROM sessions s
            WHERE s.status = 'active' 
            AND s.session_type = 'SCANNER'
            AND EXISTS (
                SELECT 1 FROM logs l
                WHERE l.user = s.user
                AND l.project = ?
                AND l.timestamp >= s.start_time
                AND l.event IN ('OPEN', 'BEZIG')
                AND l.status IN ('OPEN', 'BEZIG')
            )
        """, (project,))
        active_batch_sessions = c.fetchone()[0]
        
        if active_direct_sessions > 0 or active_batch_sessions > 0:
            logging.warning(f"[DELETE_PROJECT] Cannot delete project '{project}' - has active sessions")
            return jsonify({
                'success': False,
                'error': f'Cannot delete project with active sessions. Found {active_direct_sessions} direct sessions and {active_batch_sessions} batch sessions working on this project.',
                'active_direct_sessions': active_direct_sessions,
                'active_batch_sessions': active_batch_sessions
            }), 400
        
        # Start transaction for atomic deletion
        conn.execute('BEGIN TRANSACTION')
        
        # Count affected records for logging
        counts = {}
        
        # Count and delete from logs table
        c.execute('SELECT COUNT(*) FROM logs WHERE project = ?', (project,))
        counts['logs'] = c.fetchone()[0]
        c.execute('DELETE FROM logs WHERE project = ?', (project,))
        
        # For sessions: only delete direct project sessions, NOT batch SCANNER sessions
        # Batch sessions may have worked on multiple projects
        c.execute("""
            SELECT COUNT(*) FROM sessions 
            WHERE project = ? 
            AND (session_type != 'SCANNER' OR session_type IS NULL)
        """, (project,))
        counts['direct_sessions'] = c.fetchone()[0]
        
        c.execute("""
            DELETE FROM sessions 
            WHERE project = ? 
            AND (session_type != 'SCANNER' OR session_type IS NULL)
        """, (project,))
        
        # For SCANNER batch sessions that ONLY worked on this project, we can delete them
        c.execute("""
            SELECT session_id FROM sessions s
            WHERE s.session_type = 'SCANNER'
            AND s.status = 'completed'
            AND NOT EXISTS (
                SELECT 1 FROM logs l
                WHERE l.user = s.user
                AND l.timestamp BETWEEN s.start_time AND COALESCE(s.end_time, datetime('now'))
                AND l.project != ?
            )
            AND EXISTS (
                SELECT 1 FROM logs l
                WHERE l.user = s.user
                AND l.timestamp BETWEEN s.start_time AND COALESCE(s.end_time, datetime('now'))
                AND l.project = ?
            )
        """, (project, project))
        
        single_project_batch_sessions = [row[0] for row in c.fetchall()]
        counts['single_project_batch_sessions'] = len(single_project_batch_sessions)
        
        if single_project_batch_sessions:
            placeholders = ','.join('?' * len(single_project_batch_sessions))
            c.execute(f"DELETE FROM sessions WHERE session_id IN ({placeholders})", single_project_batch_sessions)
        
        # Count and delete from project_metadata table (if exists)
        try:
            c.execute('SELECT COUNT(*) FROM project_metadata WHERE project_code = ?', (project,))
            counts['metadata'] = c.fetchone()[0]
            c.execute('DELETE FROM project_metadata WHERE project_code = ?', (project,))
        except sqlite3.OperationalError:
            counts['metadata'] = 0
            logging.info(f"[DELETE_PROJECT] project_metadata table does not exist")
        
        # Count and delete from workflow_events table (if exists)
        try:
            c.execute('SELECT COUNT(*) FROM workflow_events WHERE project_code = ?', (project,))
            counts['workflow_events'] = c.fetchone()[0]
            c.execute('DELETE FROM workflow_events WHERE project_code = ?', (project,))
        except sqlite3.OperationalError:
            counts['workflow_events'] = 0
            logging.info(f"[DELETE_PROJECT] workflow_events table does not exist")
        
        # Count and delete from efficiency_targets table (if exists and project-specific)
        try:
            c.execute('SELECT COUNT(*) FROM efficiency_targets WHERE project_code = ?', (project,))
            counts['efficiency_targets'] = c.fetchone()[0]
            c.execute('DELETE FROM efficiency_targets WHERE project_code = ?', (project,))
        except sqlite3.OperationalError:
            counts['efficiency_targets'] = 0
            logging.info(f"[DELETE_PROJECT] efficiency_targets table does not exist or no project column")
        
        # Count and delete from user_stats table entries related to this project
        try:
            c.execute('SELECT COUNT(*) FROM user_stats WHERE project = ?', (project,))
            counts['user_stats'] = c.fetchone()[0]
            c.execute('DELETE FROM user_stats WHERE project = ?', (project,))
        except sqlite3.OperationalError:
            counts['user_stats'] = 0
            logging.info(f"[DELETE_PROJECT] user_stats table does not exist or no project column")
        
        # Commit the transaction
        conn.commit()
        
        # Log the deletion
        total_deleted = sum(counts.values())
        logging.info(f"[DELETE_PROJECT] Successfully deleted project '{project}':")
        logging.info(f"  - Logs: {counts['logs']} records")
        logging.info(f"  - Direct sessions: {counts['direct_sessions']} records")
        logging.info(f"  - Single-project batch sessions: {counts['single_project_batch_sessions']} records")
        logging.info(f"  - Metadata: {counts['metadata']} records")
        logging.info(f"  - Workflow events: {counts['workflow_events']} records")
        logging.info(f"  - Efficiency targets: {counts['efficiency_targets']} records")
        logging.info(f"  - User stats: {counts['user_stats']} records")
        logging.info(f"  - Total: {total_deleted} records deleted")
        
        return jsonify({
            'success': True,
            'message': f'Project {project} and all related data deleted successfully',
            'deleted_counts': counts,
            'total_deleted': total_deleted
        }), 200
        
    except Exception as e:
        # Rollback on error
        conn.rollback()
        logging.error(f"[DELETE_PROJECT] Error deleting project '{project}': {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Failed to delete project: {str(e)}'
        }), 500

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

@app.route('/update_metadata', methods=['POST'])
def update_metadata():
    """Update metadata (mo_number, so_number, color, customer_name) for existing log entries."""
    data = request.get_json(force=True)
    project = data.get('project')
    user = data.get('user')
    
    if not project or not user:
        return jsonify({'success': False, 'error': 'Missing project or user'}), 400
        
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Build update query dynamically based on provided fields
        update_fields = []
        update_values = []
        
        if 'mo_number' in data:
            update_fields.append('mo_number = ?')
            update_values.append(data['mo_number'])
        if 'so_number' in data:
            update_fields.append('so_number = ?')
            update_values.append(data['so_number'])
        if 'color' in data:
            update_fields.append('color = ?')
            update_values.append(data['color'])
        if 'customer_name' in data:
            update_fields.append('customer_name = ?')
            update_values.append(data['customer_name'])
            
        if update_fields:
            # Add project and user to the values for WHERE clause
            update_values.extend([project, user])
            
            query = f"""
                UPDATE logs 
                SET {', '.join(update_fields)}
                WHERE project = ? AND user = ? AND event IN ('OPEN', 'XLSX_UPDATED')
            """
            
            c.execute(query, update_values)
            rows_updated = c.rowcount
            conn.commit()
            
            logging.info(f"Updated metadata for {rows_updated} rows - project: {project}, user: {user}")
            return jsonify({'success': True, 'rows_updated': rows_updated}), 200
        else:
            return jsonify({'success': True, 'message': 'No metadata fields to update'}), 200
            
    except Exception as e:
        logging.error(f"Error updating metadata: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

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
                AND status IN ('OPEN', 'AFGEMELD', 'CLOSED')
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

@app.route('/api/sessions/active', methods=['GET'])
def get_active_sessions():
    """Get all active sessions"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get active sessions with project information
        c.execute("""
            SELECT 
                s.session_id,
                s.session_type,
                s.user,
                s.project,
                s.start_time,
                s.pause_start,
                s.pause_duration_minutes,
                s.item_count,
                CASE 
                    WHEN s.pause_start IS NOT NULL THEN
                        (julianday('now') - julianday(s.start_time)) * 24 * 60 - COALESCE(s.pause_duration_minutes, 0)
                    ELSE
                        (julianday('now') - julianday(s.start_time)) * 24 * 60
                END as duration_minutes,
                GROUP_CONCAT(sp.project, ', ') as projects
            FROM sessions s
            LEFT JOIN session_projects sp ON s.session_id = sp.session_id
            WHERE s.status = 'active'
            GROUP BY s.session_id
            ORDER BY s.start_time DESC
        """)
        
        sessions = []
        for row in c.fetchall():
            session = dict(row)
            # Use projects from session_projects if available (for SCANNER sessions)
            if session['projects']:
                session['project'] = None  # Clear single project field
            sessions.append(session)
        
        return jsonify({'success': True, 'sessions': sessions})
        
    except Exception as e:
        logging.error(f"Error getting active sessions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sessions/recent', methods=['GET'])
def get_recent_sessions():
    """Get recent completed sessions"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get recent sessions (last 24 hours)
        c.execute("""
            SELECT 
                s.session_id,
                s.session_type,
                s.user,
                s.project,
                s.start_time,
                s.end_time,
                s.work_duration_minutes,
                s.pause_duration_minutes,
                s.item_count,
                GROUP_CONCAT(sp.project, ', ') as projects
            FROM sessions s
            LEFT JOIN session_projects sp ON s.session_id = sp.session_id
            WHERE s.status = 'completed'
            AND s.end_time >= datetime('now', '-24 hours')
            GROUP BY s.session_id
            ORDER BY s.end_time DESC
            LIMIT 50
        """)
        
        sessions = []
        for row in c.fetchall():
            session = dict(row)
            # Use projects from session_projects if available (for SCANNER sessions)
            if session['projects']:
                session['project'] = None  # Clear single project field
            sessions.append(session)
        
        return jsonify({'success': True, 'sessions': sessions})
        
    except Exception as e:
        logging.error(f"Error getting recent sessions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/session/update_id', methods=['POST'])
def update_session_id():
    """Update a session's ID when moving to background (Session 1 -> Session 2)"""
    try:
        data = request.get_json()
        old_session_id = data.get('old_session_id')
        new_session_id = data.get('new_session_id')
        session_number = data.get('session_number', 2)
        
        if not old_session_id or not new_session_id:
            return jsonify({'success': False, 'error': 'Missing session IDs'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Update session ID in sessions table
        c.execute("""
            UPDATE sessions 
            SET session_id = ?
            WHERE session_id = ? AND status = 'active'
        """, (new_session_id, old_session_id))
        
        # Update session ID in session_projects table
        c.execute("""
            UPDATE session_projects 
            SET session_id = ?
            WHERE session_id = ?
        """, (new_session_id, old_session_id))
        
        # Update session ID in logs table
        c.execute("""
            UPDATE logs 
            SET session_id = ?
            WHERE session_id = ?
        """, (new_session_id, old_session_id))
        
        conn.commit()
        
        logging.info(f"Updated session ID from {old_session_id} to {new_session_id} (Session {session_number})")
        return jsonify({'success': True, 'message': 'Session ID updated successfully'})
        
    except Exception as e:
        logging.error(f"Error updating session ID: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# --- Manual AFGEMELD Endpoints ---
@app.route('/api/users/active-projects/<user>', methods=['GET'])
def get_user_active_projects(user):
    """Get all active (OPEN or BEZIG) projects for a specific user"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get projects where the user has OPEN, BEZIG, or PAUZE status but not AFGEMELD
        # Need to check both status field AND event type (SESSION_PAUSE has NULL status)
        c.execute("""
            WITH user_project_latest AS (
                SELECT
                    project,
                    MAX(timestamp) as last_activity,
                    MAX(item_count) as item_count,
                    -- Get the most recent event type
                    (SELECT event FROM logs l2
                     WHERE l2.user = ? AND l2.project = logs.project
                     ORDER BY l2.timestamp DESC LIMIT 1) as latest_event,
                    -- Get the actual status from the most recent log entry with status
                    (SELECT status FROM logs l2
                     WHERE l2.user = ? AND l2.project = logs.project
                     AND l2.status IS NOT NULL
                     ORDER BY l2.timestamp DESC LIMIT 1) as current_status,
                    -- Check if project has been AFGEMELD
                    MAX(CASE WHEN event = 'AFGEMELD' THEN 1 ELSE 0 END) as is_afgemeld
                FROM logs
                WHERE user = ?
                GROUP BY project
            )
            SELECT
                project,
                last_activity,
                -- If latest event is SESSION_PAUSE, show PAUZE status
                CASE
                    WHEN latest_event = 'SESSION_PAUSE' THEN 'PAUZE'
                    ELSE COALESCE(current_status, 'OPEN')
                END as status,
                item_count
            FROM user_project_latest
            WHERE is_afgemeld = 0
            AND (
                latest_event = 'SESSION_PAUSE'
                OR current_status IN ('OPEN', 'BEZIG', 'PAUZE')
            )
            ORDER BY last_activity DESC
        """, (user, user, user,))
        
        projects = []
        for row in c.fetchall():
            projects.append({
                'project': row['project'],
                'status': row['status'],
                'last_activity': row['last_activity'],
                'item_count': row['item_count'] or 0
            })
        
        return jsonify({
            'success': True,
            'user': user,
            'active_projects': projects,
            'count': len(projects)
        })
        
    except Exception as e:
        logging.error(f"Error getting active projects for {user}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/project/status', methods=['GET'])
def check_project_status():
    """Check if a project has been marked as AFGEMELD for a user"""
    try:
        project = request.args.get('project')
        user = request.args.get('user')
        
        if not project or not user:
            return jsonify({'success': False, 'error': 'Project and user are required'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Check if there's an AFGEMELD event for this user/project
        c.execute("""
            SELECT COUNT(*) as count 
            FROM logs 
            WHERE event = 'AFGEMELD' 
            AND project = ? 
            AND user = ?
        """, (project, user))
        
        result = c.fetchone()
        has_afgemeld = result['count'] > 0 if result else False
        
        return jsonify({
            'success': True,
            'has_afgemeld': has_afgemeld,
            'project': project,
            'user': user
        })
        
    except Exception as e:
        logging.error(f"Error checking project status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/manual-afgemeld', methods=['POST'])
def send_manual_afgemeld():
    """Send a manual AFGEMELD event for a user and project"""
    try:
        data = request.get_json()
        user = data.get('user')
        project = data.get('project')
        
        if not user or not project:
            return jsonify({'success': False, 'error': 'User and project are required'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Check if project exists and is active for the user
        c.execute("""
            SELECT 
                MAX(timestamp) as last_activity,
                MAX(CASE WHEN event = 'AFGEMELD' THEN 1 ELSE 0 END) as already_afgemeld,
                MAX(item_count) as item_count
            FROM logs
            WHERE user = ? AND project = ?
        """, (user, project))
        
        result = c.fetchone()
        if not result or not result['last_activity']:
            return jsonify({'success': False, 'error': 'Project not found for user'}), 404
        
        if result['already_afgemeld']:
            return jsonify({'success': False, 'error': 'Project already marked as AFGEMELD'}), 400
        
        # Create AFGEMELD event
        timestamp = datetime.now().isoformat()
        
        # Insert AFGEMELD log entry
        c.execute("""
            INSERT INTO logs (timestamp, event, status, details, project, user, item_count)
            VALUES (?, 'AFGEMELD', 'AFGEMELD', 'Manueel afgemeld via Database Management', ?, ?, ?)
        """, (timestamp, project, user, result['item_count'] or 0))
        
        # Note: We do NOT update the OPEN event's status field
        # The OPEN event should keep status='OPEN' for the project completion logic to work
        # The AFGEMELD event itself indicates completion
        
        updated_rows = 0  # No rows updated since we're not changing OPEN status
        
        # Close any active individual sessions for this user/project
        c.execute("""
            UPDATE sessions
            SET status = 'completed',
                end_time = ?,
                work_duration_minutes = ROUND((julianday(?) - julianday(start_time) - COALESCE(pause_duration_minutes/60.0, 0)) * 24 * 60)
            WHERE user = ? 
            AND status = 'active'
            AND session_type IN ('XLSX_UPDATED', 'MANUAL')
            AND session_id IN (
                SELECT session_id FROM session_projects 
                WHERE project = ?
            )
        """, (timestamp, timestamp, user, project))
        
        closed_sessions = c.rowcount
        
        conn.commit()
        
        logging.info(f"Manueel AFGEMELD verzonden voor {user} op project {project}. Closed {closed_sessions} sessions.")
        
        return jsonify({
            'success': True,
            'message': f'AFGEMELD event succesvol verzonden',
            'closed_sessions': closed_sessions
        })
        
    except Exception as e:
        logging.error(f"Error sending manueel AFGEMELD: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/users/with-active-projects', methods=['GET'])
def get_users_with_active_projects():
    """Get list of all users that have active projects"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get all users with active projects
        c.execute("""
            WITH user_active_projects AS (
                SELECT 
                    user,
                    project,
                    MAX(CASE WHEN event = 'AFGEMELD' THEN 1 ELSE 0 END) as is_afgemeld
                FROM logs
                WHERE event IN ('OPEN', 'BEZIG', 'AFGEMELD')
                GROUP BY user, project
                HAVING is_afgemeld = 0
            )
            SELECT 
                user,
                COUNT(DISTINCT project) as active_project_count
            FROM user_active_projects
            GROUP BY user
            ORDER BY user
        """)
        
        users = []
        for row in c.fetchall():
            users.append({
                'user': row['user'],
                'active_projects': row['active_project_count']
            })
        
        return jsonify({
            'success': True,
            'users': users
        })
        
    except Exception as e:
        logging.error(f"Error getting users with active projects: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/sessions/end', methods=['POST'])
def end_session_manually():
    """Manually end an active session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Missing session_id'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Get session details
        c.execute("""
            SELECT session_type, user, project, start_time, pause_start, pause_duration_minutes
            FROM sessions 
            WHERE session_id = ? AND status = 'active'
        """, (session_id,))
        
        session = c.fetchone()
        if not session:
            return jsonify({'success': False, 'error': 'Session not found or already completed'}), 404

        session = dict(session)

        # Calculate final work duration
        end_time = datetime.now().isoformat()
        total_minutes = calculate_work_minutes(session['start_time'], end_time)
        
        # Handle paused sessions
        pause_minutes = session['pause_duration_minutes'] or 0
        if session['pause_start']:
            # Add current pause duration
            pause_minutes += calculate_work_minutes(session['pause_start'], end_time)
        
        work_minutes = max(0, total_minutes - pause_minutes)
        
        # Update session to completed
        c.execute("""
            UPDATE sessions 
            SET status = 'completed',
                end_time = ?,
                work_duration_minutes = ?,
                pause_duration_minutes = ?,
                pause_start = NULL
            WHERE session_id = ?
        """, (end_time, work_minutes, pause_minutes, session_id))
        
        # For SCANNER sessions, update project_sessions for all linked projects
        if session['session_type'] == 'SCANNER':
            c.execute("""
                SELECT project, item_count 
                FROM session_projects 
                WHERE session_id = ?
            """, (session_id,))
            
            projects = c.fetchall()
            total_items = sum(p['item_count'] or 0 for p in projects)
            
            for project in projects:
                if total_items > 0 and project['item_count']:
                    # Calculate proportional time
                    proportion = project['item_count'] / total_items
                    project_work_minutes = work_minutes * proportion
                    
                    # Check if project_sessions entry exists
                    c.execute("""
                        SELECT id, start_time, total_duration_minutes 
                        FROM project_sessions 
                        WHERE project = ?
                    """, (project['project'],))
                    
                    existing_project_session = c.fetchone()
                    
                    if existing_project_session:
                        # Update existing entry
                        c.execute("""
                            UPDATE project_sessions 
                            SET total_duration_minutes = COALESCE(total_duration_minutes, 0) + ?,
                                end_time = ?,
                                status = 'AFGEMELD'
                            WHERE project = ?
                        """, (project_work_minutes, end_time, project['project']))
                    else:
                        # Create new entry with all required fields including start_time
                        c.execute("""
                            INSERT INTO project_sessions (project, start_time, end_time, status, total_duration_minutes)
                            VALUES (?, ?, ?, 'AFGEMELD', ?)
                        """, (project['project'], session['start_time'], end_time, project_work_minutes))
        
        conn.commit()
        
        logging.info(f"Manually ended session {session_id} for user {session['user']}")
        return jsonify({'success': True, 'message': 'Session ended successfully'})
        
    except Exception as e:
        logging.error(f"Error ending session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/clear_logs', methods=['POST'])
def clear_all_logs():
    logging.info("[db_log_api] /clear_logs POST request received.")
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Clear all project and session data for complete reset
        tables_to_clear = ['logs', 'sessions', 'project_sessions', 'session_projects']
        
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

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get all application settings from database"""
    try:
        conn = get_db()
        c = conn.cursor()

        c.execute("""
            SELECT setting_key, setting_value, setting_type, description
            FROM app_settings
            WHERE setting_key != 'migration_completed'
            ORDER BY setting_key
        """)

        settings = {}
        for row in c.fetchall():
            key = row['setting_key']
            value = row['setting_value']
            setting_type = row['setting_type']

            # Parse JSON values back to objects
            if setting_type == 'json':
                import json
                try:
                    settings[key] = json.loads(value)
                except:
                    settings[key] = value
            elif setting_type == 'boolean':
                settings[key] = value.lower() in ('true', '1', 'yes')
            else:
                settings[key] = value

        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        logging.error(f"Error getting settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update application settings in database"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        conn = get_db()
        c = conn.cursor()

        updated_keys = []
        for key, value in data.items():
            # Determine value type
            if isinstance(value, (dict, list)):
                import json
                value_str = json.dumps(value)
                value_type = 'json'
            elif isinstance(value, bool):
                value_str = str(value).lower()
                value_type = 'boolean'
            else:
                value_str = str(value)
                value_type = 'string'

            # Update or insert setting
            c.execute("""
                INSERT OR REPLACE INTO app_settings (setting_key, setting_value, setting_type, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (key, value_str, value_type))

            updated_keys.append(key)

        conn.commit()
        logging.info(f"Updated settings: {', '.join(updated_keys)}")

        return jsonify({'success': True, 'updated_keys': updated_keys})
    except Exception as e:
        logging.error(f"Error updating settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

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
@login_required
def index():
    """Redirect root to production flow dashboard"""
    return redirect(url_for('dashboard_production_flow'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get configured users for display from database (with config fallback)
        dashboard_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
        
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
        
        # First, identify which user-project combinations should be hidden
        # Only hide if the LATEST STATUS (not just any event) for this user-project is AFGEMELD from more than a day ago
        c.execute("""
            WITH latest_status_per_user AS (
                SELECT user, project, MAX(timestamp) as max_ts
                FROM logs
                WHERE user IS NOT NULL 
                AND project IS NOT NULL
                AND status IS NOT NULL
                GROUP BY user, project
            )
            SELECT l.user, l.project
            FROM logs l
            INNER JOIN latest_status_per_user lspu
                ON l.user = lspu.user 
                AND l.project = lspu.project 
                AND l.timestamp = lspu.max_ts
            WHERE l.event = 'AFGEMELD'
              AND DATE(l.timestamp) < ?
        """, (today.isoformat(),))
        
        completed_projects = set()
        for row in c.fetchall():
            completed_projects.add((row['user'], row['project']))
        
        # Query to get the latest meaningful status for each user-project combination
        # We need the latest event that has a status (OPEN, BEZIG, AFGEMELD)
        # When multiple events have the same timestamp, prioritize AFGEMELD
        c.execute("""
            WITH latest_status_events AS (
                SELECT user, project, MAX(timestamp) as max_timestamp
                FROM logs
                WHERE user IS NOT NULL 
                AND project IS NOT NULL 
                AND status IS NOT NULL
                GROUP BY user, project
            )
            SELECT l.*
            FROM logs l
            INNER JOIN latest_status_events lse 
                ON l.user = lse.user 
                AND l.project = lse.project 
                AND l.timestamp = lse.max_timestamp
            WHERE l.id = (
                -- When multiple events at same timestamp, pick the right one
                SELECT id FROM logs l2
                WHERE l2.user = l.user 
                AND l2.project = l.project 
                AND l2.timestamp = l.timestamp
                AND l2.status IS NOT NULL
                ORDER BY 
                    CASE WHEN l2.event = 'AFGEMELD' THEN 3 
                         WHEN l2.event = 'OPEN' THEN 2
                         WHEN l2.status = 'BEZIG' THEN 1
                         ELSE 0 END DESC
                LIMIT 1
            )
            ORDER BY l.timestamp DESC
        """)
        
        logs_for_display = c.fetchall()
        
        # Group by user, keeping track of all projects
        users_projects = {}
        
        for log in logs_for_display:
            log_dict = dict(log)
            user = log_dict.get('user')
            project = log_dict.get('project')
            
            # Skip if this user-project combination was completed more than a day ago
            # AND has no newer activity
            if (user, project) in completed_projects:
                continue
            
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
                
                # Use the latest status for each user-project combination
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
        # Count both open/in-progress and completed repair projects
        c.execute("""
            SELECT COUNT(DISTINCT project) as repair_count
            FROM logs
            WHERE is_rep_variant = 1 
            AND event IN ('OPEN', 'BEZIG', 'AFGEMELD')
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


@app.route('/dashboard/enterprise')
@login_required
def dashboard_enterprise():
    """Enterprise dashboard with simplified Odoo-style interface"""
    try:
        return render_template('dashboard_enterprise_simple.html', active_page='dashboard')
    except Exception as e:
        logging.error(f"Enterprise dashboard error: {str(e)}", exc_info=True)
        return render_template('error.html', message=str(e)), 500


@app.route('/dashboard/production-flow')
@login_required
def dashboard_production_flow():
    """Production flow dashboard with pipeline visualization and bottleneck detection"""
    try:
        # Get configured users for display from database (with config fallback)
        dashboard_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])

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

        logging.info(f"Production flow dashboard users: {dashboard_users}")

        # Get today's date
        today = datetime.now().date()

        conn = get_db()
        c = conn.cursor()

        # Initialize dept_stats for each user
        dept_stats = {}
        for user in dashboard_users:
            dept_stats[user] = {
                'active_projects': 0,
                'queue': 0
            }

        # Get user projects similar to main dashboard
        c.execute("""
            WITH latest_status_events AS (
                SELECT user, project, MAX(timestamp) as max_timestamp
                FROM logs
                WHERE user IS NOT NULL
                AND project IS NOT NULL
                AND status IS NOT NULL
                GROUP BY user, project
            )
            SELECT l.*
            FROM logs l
            INNER JOIN latest_status_events lse
                ON l.user = lse.user
                AND l.project = lse.project
                AND l.timestamp = lse.max_timestamp
            WHERE l.id = (
                SELECT id FROM logs l2
                WHERE l2.user = l.user
                AND l2.project = l.project
                AND l2.timestamp = l.timestamp
                AND l2.status IS NOT NULL
                ORDER BY
                    CASE WHEN l2.event = 'AFGEMELD' THEN 3
                         WHEN l2.event = 'OPEN' THEN 2
                         WHEN l2.status = 'BEZIG' THEN 1
                         ELSE 0 END DESC
                LIMIT 1
            )
            ORDER BY l.timestamp DESC
        """)

        logs_for_display = c.fetchall()

        # Group by user
        users_projects = {}
        completed_projects = set()

        # Find ANY project that has been AFGEMELD before today (not just latest status)
        # Once a project is AFGEMELD, it cannot be re-opened
        # Check both event='AFGEMELD' and status='AFGEMELD' (some records have status set differently)
        c.execute("""
            SELECT DISTINCT user, project
            FROM logs
            WHERE (event = 'AFGEMELD' OR status = 'AFGEMELD')
              AND DATE(timestamp) < ?
              AND user IS NOT NULL
              AND project IS NOT NULL
        """, (today.isoformat(),))

        for row in c.fetchall():
            completed_projects.add((row['user'], row['project']))

        for log in logs_for_display:
            log_dict = dict(log)
            user = log_dict.get('user')
            project = log_dict.get('project')

            if (user, project) in completed_projects:
                continue

            if user not in users_projects:
                users_projects[user] = []

            # Calculate duration
            start_time = datetime.fromisoformat(log_dict.get('timestamp'))
            duration = datetime.now() - start_time
            hours = duration.total_seconds() / 3600

            if hours < 1:
                duration_str = f"{int(duration.total_seconds() / 60)} min"
            else:
                duration_str = f"{hours:.1f} hours"

            # Get metadata for this project
            c.execute("""
                SELECT DISTINCT mo_number, so_number, customer_name, color
                FROM logs
                WHERE project = ?
                AND (mo_number IS NOT NULL OR so_number IS NOT NULL OR customer_name IS NOT NULL OR color IS NOT NULL)
                ORDER BY
                    CASE WHEN mo_number IS NOT NULL THEN 1 ELSE 0 END +
                    CASE WHEN so_number IS NOT NULL THEN 1 ELSE 0 END +
                    CASE WHEN customer_name IS NOT NULL THEN 1 ELSE 0 END +
                    CASE WHEN color IS NOT NULL THEN 1 ELSE 0 END DESC
                LIMIT 1
            """, (project,))

            metadata_row = c.fetchone()
            mo_number = None
            so_number = None
            customer_name = None
            color = None

            if metadata_row:
                mo_number = metadata_row['mo_number']
                so_number = metadata_row['so_number']
                customer_name = metadata_row['customer_name']
                color = metadata_row['color']

            # Extract MO from project name if not in database
            if not mo_number:
                mo_match = re.match(r'(MO\d+)', project)
                if mo_match:
                    mo_number = mo_match.group(1)

            users_projects[user].append({
                'project': project,
                'status': log_dict.get('status', 'UNKNOWN'),
                'timestamp': log_dict.get('timestamp'),
                'duration': duration_str,
                'item_count': log_dict.get('item_count', 0),
                'mo_number': mo_number,
                'so_number': so_number,
                'customer_name': customer_name,
                'color': color
            })

        # Count active projects for each user for the pipeline
        for user, projects in users_projects.items():
            if user in dept_stats:
                dept_stats[user]['active_projects'] = len(projects)

        # Get recent activity for feed
        c.execute("""
            SELECT
                timestamp,
                user,
                project,
                event,
                details,
                item_count
            FROM logs
            WHERE timestamp > datetime('now', '-2 hours')
            ORDER BY timestamp DESC
            LIMIT 20
        """)

        recent_activity = []
        for row in c.fetchall():
            recent_activity.append({
                'timestamp': row['timestamp'],
                'user': row['user'],
                'project': row['project'],
                'event': row['event'],
                'item_count': row['item_count']
            })

        # Calculate metrics - get overall totals and today's completed
        c.execute("""
            SELECT
                (SELECT COUNT(DISTINCT project) FROM logs) as total_projects,
                (SELECT COUNT(DISTINCT project) FROM logs WHERE status = 'BEZIG') as active_projects,
                (SELECT COUNT(DISTINCT project) FROM logs WHERE event = 'AFGEMELD' AND DATE(timestamp) = DATE('now')) as completed_today
        """)

        metrics = c.fetchone()

        return render_template('dashboard_production_flow.html',
                             dept_stats=dept_stats,
                             users_projects=users_projects,
                             dashboard_users=dashboard_users,
                             recent_activity=recent_activity,
                             total_projects=metrics['total_projects'],
                             active_projects=metrics['active_projects'],
                             completed_today=metrics['completed_today'],
                             active_page='dashboard')

    except Exception as e:
        logging.error(f"Production flow dashboard error: {str(e)}", exc_info=True)
        return render_template('error.html', message=str(e)), 500


# --- API Endpoints ---
@app.route('/api/configured_users')
def get_configured_users():
    users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
    return jsonify({
        'success': True,
        'users': users
    })

@app.route('/api/workflow-completion')
def get_workflow_completion():
    """Get which projects have been AFGEMELD by which users for workflow filtering"""
    try:
        conn = get_db()
        c = conn.cursor()

        # Get all AFGEMELD events grouped by project and user
        # Check both event='AFGEMELD' and status='AFGEMELD' (some records have status set differently)
        c.execute("""
            SELECT DISTINCT project, user
            FROM logs
            WHERE (event = 'AFGEMELD' OR status = 'AFGEMELD')
              AND project IS NOT NULL
              AND user IS NOT NULL
        """)

        # Build a dict: project -> list of users who have AFGEMELD it
        workflow_completion = {}
        for row in c.fetchall():
            project = row['project']
            user = row['user']
            if project not in workflow_completion:
                workflow_completion[project] = []
            if user not in workflow_completion[project]:
                workflow_completion[project].append(user)

        # Get the workflow order
        workflow_order = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])

        return jsonify({
            'success': True,
            'workflow_completion': workflow_completion,
            'workflow_order': workflow_order
        })

    except Exception as e:
        logging.error(f"Workflow completion API error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config')
def get_config_api():
    """Get relevant configuration for frontend use"""
    # Get settings from database with config fallback
    return jsonify({
        'scanner_user_to_processing_type_map': get_setting_from_db('scanner_user_to_processing_type_map', fallback_to_config=True, default_value={}),
        'scanner_panel_open_event_users': get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
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

# API endpoint for login history
@app.route('/api/database/login-history', methods=['GET'])
@login_required
def get_login_history():
    try:
        conn = get_db()
        c = conn.cursor()

        # Get limit from query params (default 100)
        limit = request.args.get('limit', 100, type=int)

        # Fetch login history, newest first
        c.execute('''
            SELECT id, username, ip_address, user_agent, login_time,
                   login_success, login_type, session_duration_minutes, logout_time
            FROM login_history
            ORDER BY login_time DESC
            LIMIT ?
        ''', (limit,))

        logins = []
        for row in c.fetchall():
            logins.append({
                'id': row[0],
                'username': row[1],
                'ip_address': row[2] or 'Unknown',
                'user_agent': row[3] or 'Unknown',
                'login_time': row[4],
                'login_success': bool(row[5]),
                'login_type': row[6],
                'session_duration_minutes': row[7],
                'logout_time': row[8]
            })

        return jsonify({
            'success': True,
            'logins': logins
        })
    except Exception as e:
        logging.error(f"Error fetching login history: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoint for production time estimates
@app.route('/api/production-time-estimates', methods=['GET'])
def get_production_time_estimates():
    """Calculate production time estimates based on open/bezig projects"""
    try:
        conn = get_db()
        c = conn.cursor()

        # Get all users with their current average items/hour from recent performance
        # Fixed: Use weighted average (total items / total time) instead of simple average
        # This prevents short sessions with high items/hour from skewing the results
        c.execute("""
            WITH user_performance AS (
                SELECT
                    user,
                    CASE
                        WHEN SUM(work_duration_minutes) > 0
                        THEN (SUM(item_count) * 60.0) / SUM(work_duration_minutes)
                        ELSE NULL
                    END as avg_items_per_hour
                FROM sessions
                WHERE end_time IS NOT NULL
                    AND work_duration_minutes > 0
                    AND item_count > 0
                    AND start_time > date('now', '-30 days')
                GROUP BY user
            )
            SELECT * FROM user_performance
        """)

        user_performance = {row['user']: row['avg_items_per_hour'] or 0 for row in c.fetchall()}

        # Get efficiency targets from config.json
        user_targets = {}
        try:
            config_path = get_writable_path('config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    efficiency_targets = config.get('efficiency_targets', {})
                    # Convert to user: target_value mapping
                    for user, target_value in efficiency_targets.items():
                        if isinstance(target_value, (int, float)):
                            user_targets[user] = float(target_value)
                    logging.info(f"Loaded efficiency targets from config: {user_targets}")
        except Exception as e:
            logging.error(f"Error loading efficiency targets from config: {e}")
            # Fallback to database if config fails
            c.execute("""
                SELECT user, target_items_per_hour
                FROM work_hours_config
                WHERE target_items_per_hour IS NOT NULL
            """)
            user_targets = {row['user']: row['target_items_per_hour'] for row in c.fetchall()}
            logging.info(f"Loaded efficiency targets from database: {user_targets}")

        # Get all OPEN and BEZIG projects with their item counts
        # Fixed: Get the true latest status for each project, not just latest OPEN/BEZIG
        # Also get the MAX item_count for each project, not just from the latest status log
        c.execute("""
            WITH latest_status_per_project AS (
                SELECT
                    user,
                    project,
                    MAX(timestamp) as latest_timestamp
                FROM logs
                WHERE user IS NOT NULL
                    AND project IS NOT NULL
                    AND status IS NOT NULL
                GROUP BY user, project
            ),
            max_item_count_per_project AS (
                SELECT
                    user,
                    project,
                    MAX(COALESCE(item_count, 0)) as max_item_count
                FROM logs
                WHERE user IS NOT NULL
                    AND project IS NOT NULL
                    AND item_count > 0
                GROUP BY user, project
            ),
            active_projects AS (
                SELECT
                    l.user,
                    l.project,
                    l.status,
                    l.event,
                    COALESCE(mic.max_item_count, 0) as item_count,
                    l.timestamp
                FROM logs l
                INNER JOIN latest_status_per_project ls
                    ON l.user = ls.user
                    AND l.project = ls.project
                    AND l.timestamp = ls.latest_timestamp
                LEFT JOIN max_item_count_per_project mic
                    ON l.user = mic.user
                    AND l.project = mic.project
                WHERE l.status IN ('OPEN', 'BEZIG')
                    AND l.event != 'AFGEMELD'
            )
            SELECT
                user,
                COUNT(DISTINCT project) as project_count,
                SUM(COALESCE(item_count, 0)) as total_items
            FROM active_projects
            GROUP BY user
        """)

        estimates = []
        for row in c.fetchall():
            user = row['user']
            total_items = row['total_items'] or 0
            project_count = row['project_count'] or 0

            # Get user's average performance (items per hour)
            avg_performance = user_performance.get(user, None)

            # Get user's target performance
            target_performance = user_targets.get(user, None)

            # Format time strings
            def format_hours(hours):
                if hours is None:
                    return "Geen data"
                if hours == 0:
                    return "0m"
                # Round up to at least 1 minute if there's any time
                if hours > 0 and hours < 0.0167:  # Less than 1 minute
                    return "<1m"
                h = int(hours)
                m = int(round((hours - h) * 60))  # Round minutes instead of truncating
                if h > 0 and m > 0:
                    return f"{h}u {m}m"
                elif h > 0:
                    return f"{h}u"
                else:
                    return f"{m}m" if m > 0 else "<1m"

            # Calculate estimated hours only if we have performance data
            if avg_performance and avg_performance > 0:
                estimated_hours = total_items / avg_performance
            else:
                estimated_hours = None

            # Calculate goal hours only if we have target data
            if target_performance and target_performance > 0:
                goal_hours = total_items / target_performance
            else:
                goal_hours = None

            # Calculate efficiency ratio only if both values exist
            if estimated_hours and goal_hours and estimated_hours > 0:
                efficiency_ratio = round((goal_hours / estimated_hours * 100), 1)
            else:
                efficiency_ratio = None

            estimates.append({
                'user': user,
                'project_count': project_count,
                'total_items': total_items,
                'avg_items_per_hour': round(avg_performance, 1) if avg_performance else None,
                'target_items_per_hour': round(target_performance, 1) if target_performance else None,
                'estimated_hours': round(estimated_hours, 2) if estimated_hours else None,
                'goal_hours': round(goal_hours, 2) if goal_hours else None,
                'estimated_time_str': format_hours(estimated_hours),
                'goal_time_str': format_hours(goal_hours),
                'efficiency_ratio': efficiency_ratio,
                'has_performance_data': avg_performance is not None,
                'has_target_data': target_performance is not None
            })

        return jsonify({
            'success': True,
            'estimates': estimates
        })

    except Exception as e:
        logging.error(f"Error calculating production time estimates: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# --- API Endpoint to Manage Dashboard Users ---
@app.route('/api/dashboard/users', methods=['GET', 'POST'])
def manage_dashboard_users():
    """Manage which users should always be displayed on the dashboard"""
    if request.method == 'GET':
        users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
        return jsonify({
            'success': True,
            'users': users
        })

    elif request.method == 'POST':
        try:
            data = request.get_json()
            users = data.get('users', [])

            # Validate users list
            if not isinstance(users, list):
                return jsonify({'success': False, 'error': 'Users must be a list'}), 400

            # Save to database (with config fallback)
            success = save_setting_to_db('scanner_panel_open_event_users', users, 'List of configured users')
            if not success:
                # Fallback to config file if database save failed
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
        # Get users from database (with config fallback)
        scanner_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])

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
        configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
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
    # initialize_efficiency_tracking()  # Initialize efficiency tracking system - moved to after function definition
    
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

@app.route('/api/project/<project>/linked_sessions')
def get_linked_sessions(project):
    """Get all sessions linked to a project (normalized)"""
    try:
        project_id = normalize_project_id(project)
        
        conn = get_db()
        c = conn.cursor()
        
        # Get all sessions for this project_id (including batch sessions via session_projects)
        c.execute("""
            SELECT DISTINCT
                s.session_id,
                s.user,
                COALESCE(sp.project, s.project) as project,
                s.project_id,
                s.start_time,
                s.end_time,
                s.status,
                s.session_type,
                s.work_duration_minutes,
                s.pause_duration_minutes,
                COALESCE(sp.item_count, s.item_count) as item_count,
                s.sequence_number,
                s.previous_user,
                s.handoff_delay_minutes,
                sp.item_count as batch_items,
                (SELECT SUM(sp2.item_count) FROM session_projects sp2 WHERE sp2.session_id = s.session_id) as batch_total_items
            FROM sessions s
            LEFT JOIN session_projects sp ON s.session_id = sp.session_id AND sp.project = ?
            WHERE s.project_id = ? 
               OR s.project = ?
               OR sp.project = ?
            ORDER BY s.sequence_number, s.start_time
        """, (project, project_id, project, project))
        
        sessions = []
        for row in c.fetchall():
            session = dict(row)
            
            # For SCANNER batch sessions, calculate proportional work time
            if session['session_type'] == 'SCANNER' and session['batch_items'] and session['batch_total_items']:
                # Calculate proportional time for this project in the batch
                proportion = session['batch_items'] / session['batch_total_items']
                session['allocated_work_minutes'] = session['work_duration_minutes'] * proportion
                session['allocated_pause_minutes'] = (session['pause_duration_minutes'] or 0) * proportion
            else:
                # For non-batch sessions, use full time
                session['allocated_work_minutes'] = session['work_duration_minutes']
                session['allocated_pause_minutes'] = session['pause_duration_minutes'] or 0
            
            sessions.append(session)
        
        # Calculate aggregated metrics using allocated time for batch sessions
        total_work = sum(s['allocated_work_minutes'] or 0 for s in sessions)
        total_pause = sum(s['allocated_pause_minutes'] or 0 for s in sessions)
        total_handoff = sum(s['handoff_delay_minutes'] or 0 for s in sessions if s['handoff_delay_minutes'])
        unique_users = list(set(s['user'] for s in sessions))
        
        # Build workflow chain
        workflow = []
        for session in sessions:
            workflow.append({
                'user': session['user'],
                'sequence': session['sequence_number'],
                'start': session['start_time'],
                'end': session['end_time'],
                'work_minutes': session['allocated_work_minutes'],
                'handoff_from': session['previous_user'],
                'handoff_delay': session['handoff_delay_minutes']
            })
        
        return jsonify({
            'project_id': project_id,
            'sessions': sessions,
            'metrics': {
                'total_work_minutes': total_work,
                'total_pause_minutes': total_pause,
                'total_handoff_minutes': total_handoff,
                'unique_users': unique_users,
                'session_count': len(sessions)
            },
            'workflow': workflow
        })
        
    except Exception as e:
        logging.error(f"Error getting linked sessions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/logs_project')
@login_required
def logs_project():
    # Get configured users from database (with config fallback)
    configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
    
    project = request.args.get('project', '')
    if not project:
        return render_template('error.html', message='Project parameter is missing.'), 400

    logging.info(f"logs_project endpoint called for project: '{project}'")
    try:
        conn = get_db()
        c = conn.cursor()

        c.execute('SELECT * FROM logs WHERE lower(project) = ? AND event NOT IN (?, ?) ORDER BY id DESC', (project.lower(), 'AUTO_IMPORT', 'BACKGROUND_WORK_FOUND'))
        log_entries = []
        for row in c.fetchall():
            entry = dict(row)
            # Ensure all values are JSON serializable
            for key, value in entry.items():
                if value is None:
                    entry[key] = ''
                elif isinstance(value, bytes):
                    entry[key] = value.decode('utf-8', errors='replace')
            log_entries.append(entry)

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
        
        # Get sessions data for this project
        # Note: We match on exact project name, not normalized project_id
        # This ensures REP variants are tracked separately for time calculations

        # Still calculate project_id for template display purposes
        project_id = normalize_project_id(project)

        # Get all linked sessions for this project (including via session_projects)
        c.execute('''
            SELECT DISTINCT
                s.session_id,
                s.user,
                s.project as original_project,
                COALESCE(sp.project, s.project, ?) as project,
                s.project_id,
                s.start_time,
                s.end_time,
                s.status,
                COALESCE(sp.item_count, s.item_count) as item_count,
                s.work_duration_minutes,
                s.pause_duration_minutes,
                s.session_type,
                s.sequence_number,
                s.previous_user,
                s.handoff_delay_minutes,
                (SELECT COUNT(*) FROM session_projects WHERE session_id = s.session_id) as total_projects_in_session,
                (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) as total_items_in_session
            FROM sessions s
            LEFT JOIN session_projects sp ON s.session_id = sp.session_id AND sp.project = ?
            WHERE s.project = ?
               OR sp.project = ?
            ORDER BY s.sequence_number, s.start_time ASC
        ''', (project, project, project, project))
        linked_sessions = []
        for row in c.fetchall():
            session = dict(row)
            # Ensure pause_duration_minutes has a valid value
            if session.get('pause_duration_minutes') is None:
                session['pause_duration_minutes'] = 0
            linked_sessions.append(session)
        
        # Sessions are now properly linked via session_projects table
        # No need for separate batch session query
        sessions_data = linked_sessions
        
        # Clean up data for JSON serialization
        import math
        def clean_for_json(obj):
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(v) for v in obj]
            elif isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return 0
                return obj
            elif obj is None:
                return ''  # Return None instead of empty string for proper JSON null
            return obj
        
        # Clean all data before sending to template
        log_entries = clean_for_json(log_entries)
        sessions_data = clean_for_json(sessions_data)
        linked_sessions = clean_for_json(linked_sessions)
        
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
                               project_id=project_id,
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
                               linked_sessions=linked_sessions,
                               active_page='projects')

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return render_template('error.html', message='An error occurred while loading the project.'), 500

# Update the projects route in db_log_api.py

@app.route('/sales_orders', methods=['GET'])
@login_required
def sales_orders():
    """View all Sales Orders with aggregated metrics from their MOs"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get all unique SO numbers with their MO counts and metrics
        c.execute("""
            SELECT 
                so_number,
                COUNT(DISTINCT mo_number) as unique_mo_count,
                COUNT(DISTINCT project) as project_count,
                COUNT(DISTINCT user) as user_count,
                MIN(CASE WHEN event NOT IN ('AUTO_IMPORT', 'BACKGROUND_WORK_FOUND') THEN timestamp END) as first_activity,
                MAX(timestamp) as last_activity,
                GROUP_CONCAT(DISTINCT project) as projects,
                GROUP_CONCAT(DISTINCT mo_number) as mo_numbers,
                GROUP_CONCAT(DISTINCT customer_name) as customer_names
            FROM logs 
            WHERE so_number IS NOT NULL AND so_number != ''
            GROUP BY so_number
            ORDER BY so_number DESC
        """)
        
        sales_orders = []
        for row in c.fetchall():
            # Calculate completion status
            c.execute("""
                SELECT 
                    COUNT(DISTINCT project) as total_mos,
                    COUNT(DISTINCT CASE WHEN event = 'AFGEMELD' THEN project END) as completed_mos
                FROM logs
                WHERE so_number = ?
            """, (row['so_number'],))
            status_row = c.fetchone()
            
            completion_percentage = 0
            if status_row['total_mos'] > 0:
                completion_percentage = (status_row['completed_mos'] / status_row['total_mos']) * 100
            
            # Get customer name (first non-null)
            customer_name = None
            if row['customer_names']:
                names = [n for n in row['customer_names'].split(',') if n and n != 'None']
                customer_name = names[0] if names else None
            
            # Calculate total items correctly - use processing chain logic like logs_project
            total_items = 0
            total_work_minutes = 0
            total_project_minutes = 0
            
            if row['projects']:
                projects_list = row['projects'].split(',')
                configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True,
                                             default_value=['NESTING', 'ACCURA', 'OPUS', 'KL GANNOMAT', 'BOERE'])
                
                for project in projects_list:
                    project = project.strip()
                    
                    # Check users in reverse order to find the last one in the chain with items
                    final_items = 0
                    for user in reversed(configured_users):
                        c.execute("""
                            SELECT item_count 
                            FROM logs 
                            WHERE project = ? 
                            AND user = ?
                            AND item_count IS NOT NULL 
                            AND item_count > 0
                            ORDER BY timestamp DESC 
                            LIMIT 1
                        """, (project, user))
                        item_row = c.fetchone()
                        if item_row and item_row['item_count']:
                            final_items = item_row['item_count']
                            break  # Found the last user in chain with items
                    
                    total_items += final_items
                    
                    # Calculate work time using same method as sales_order_detail
                    project_id = normalize_project_id(project)
                    c.execute('''
                        SELECT DISTINCT
                            s.session_id,
                            s.work_duration_minutes,
                            s.status,
                            COALESCE(sp.item_count, s.item_count) as item_count,
                            (SELECT COUNT(*) FROM session_projects WHERE session_id = s.session_id) as total_projects_in_session,
                            (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) as total_items_in_session
                        FROM sessions s
                        LEFT JOIN session_projects sp ON s.session_id = sp.session_id AND sp.project = ?
                        WHERE s.project_id = ? 
                           OR s.project = ?
                           OR sp.project = ?
                    ''', (project, project_id, project, project))
                    
                    for session in c.fetchall():
                        work_minutes = session['work_duration_minutes'] or 0
                        
                        # For batch sessions with multiple projects, allocate proportionally
                        if session['total_projects_in_session'] and session['total_projects_in_session'] > 1:
                            project_items = session['item_count'] or 0
                            total_items_session = session['total_items_in_session'] or 0
                            
                            if total_items_session > 0 and project_items > 0:
                                proportion = project_items / total_items_session
                                total_work_minutes += work_minutes * proportion
                        else:
                            # Single project session - use full time
                            total_work_minutes += work_minutes
                    
                    # Calculate project time using v2 method
                    try:
                        v2_result = get_project_time_metrics_v2_internal(project, conn)
                        
                        if v2_result and v2_result.get('success'):
                            project_minutes = v2_result.get('total_project_minutes', 0)
                            if project_minutes > 0:
                                total_project_minutes += project_minutes
                    except Exception as e:
                        logging.warning(f"Could not get project time for {project}: {e}")
                        # Fallback calculation
                        c.execute("""
                            SELECT MIN(timestamp) as first_time, MAX(timestamp) as last_time
                            FROM logs
                            WHERE project = ?
                        """, (project,))
                        time_row = c.fetchone()
                        if time_row and time_row['first_time'] and time_row['last_time']:
                            project_minutes = calculate_work_minutes(time_row['first_time'], time_row['last_time'])
                            if project_minutes > 0:
                                total_project_minutes += project_minutes
            
            sales_orders.append({
                'so_number': row['so_number'],
                'mo_count': row['unique_mo_count'] if row['unique_mo_count'] else 0,
                'user_count': row['user_count'],
                'total_items': total_items,
                'total_work_minutes': total_work_minutes,
                'total_project_minutes': total_project_minutes,
                'first_activity': row['first_activity'],
                'last_activity': row['last_activity'],
                'projects': row['projects'].split(',') if row['projects'] else [],
                'customer_name': customer_name,
                'completion_percentage': round(completion_percentage, 1),
                'completed_mos': status_row['completed_mos'],
                'total_mos': status_row['total_mos']
            })
        
        conn.close()
        
        return render_template('sales_orders.html',
                             sales_orders=sales_orders,
                             total_count=len(sales_orders),
                             active_page='sales_orders')
        
    except Exception as e:
        logging.error(f"Error loading sales orders: {e}", exc_info=True)
        return render_template('error.html', message='Could not load sales orders.'), 500

@app.route('/sales_order/<so_number>')
@login_required  
def sales_order_detail(so_number):
    """Detailed view of a single Sales Order with all its MOs"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # First get all projects associated with this SO
        c.execute("""
            SELECT DISTINCT project
            FROM logs
            WHERE so_number = ?
        """, (so_number,))
        so_projects = [row['project'] for row in c.fetchall()]

        # Get all MO projects for this SO with their activity data
        mo_data = []
        for project in so_projects:
            c.execute("""
                SELECT
                    ? as project,
                    MAX(mo_number) as mo_number,
                    MIN(CASE WHEN event NOT IN ('AUTO_IMPORT', 'BACKGROUND_WORK_FOUND') THEN timestamp END) as first_activity,
                    MAX(timestamp) as last_activity,
                    COUNT(DISTINCT user) as user_count,
                    SUM(item_count) as total_items,
                    GROUP_CONCAT(DISTINCT user) as users,
                    MAX(CASE WHEN event = 'AFGEMELD' THEN 1 ELSE 0 END) as is_completed
                FROM logs
                WHERE project = ?
            """, (project, project))
            result = c.fetchone()
            if result:
                mo_data.append(result)
        
        mo_projects = []
        rep_projects = []
        total_completed = 0
        for row in mo_data:
            # Get detailed status for each MO
            status, _ = determine_project_status(row['project'], conn)
            
            if row['is_completed']:
                total_completed += 1
            
            # Check if this is a REP variant or SPOED project
            project_upper = row['project'].upper()
            is_rep = '_REP' in project_upper or 'SPOED' in project_upper
                
            # Use the EXACT same calculations as logs_project by calling the internal functions
            # Get work duration from sessions
            work_duration = 0
            project_time = 0
            
            try:
                # Call the v2 time metrics function directly (same as logs_project does)
                v2_result = get_project_time_metrics_v2_internal(row['project'], conn)
                
                # Extract the project time from the v2 result
                if v2_result and v2_result.get('success'):
                    project_time = v2_result.get('total_project_minutes', 0)
                
                # Get work time from sessions (same calculation as logs_project)
                project_id = normalize_project_id(row['project'])
                c.execute('''
                    SELECT DISTINCT
                        s.session_id,
                        s.work_duration_minutes,
                        s.status,
                        COALESCE(sp.item_count, s.item_count) as item_count,
                        (SELECT COUNT(*) FROM session_projects WHERE session_id = s.session_id) as total_projects_in_session,
                        (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) as total_items_in_session
                    FROM sessions s
                    LEFT JOIN session_projects sp ON s.session_id = sp.session_id AND sp.project = ?
                    WHERE s.project_id = ? 
                       OR s.project = ?
                       OR sp.project = ?
                ''', (row['project'], project_id, row['project'], row['project']))
                
                for session in c.fetchall():
                    work_minutes = session['work_duration_minutes'] or 0
                    
                    # For batch sessions with multiple projects, allocate proportionally
                    if session['total_projects_in_session'] and session['total_projects_in_session'] > 1:
                        project_items = session['item_count'] or 0
                        total_items = session['total_items_in_session'] or 0
                        
                        if total_items > 0 and project_items > 0:
                            proportion = project_items / total_items
                            work_duration += work_minutes * proportion
                    else:
                        # Single project session - use full time
                        work_duration += work_minutes
                        
            except Exception as e:
                logging.warning(f"Could not get time metrics for {row['project']}: {e}")
                # Fallback to basic calculation if import fails
                if row['first_activity'] and row['last_activity']:
                    project_time = calculate_work_minutes(row['first_activity'], row['last_activity'])
            
            # Get the final item count from the last user in the processing chain
            # Processing chain order (reverse for finding last user with items)
            configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True,
                                         default_value=['NESTING', 'ACCURA', 'OPUS', 'KL GANNOMAT', 'BOERE'])
            
            final_items = 0
            # Check each user in reverse order (BOERE → KL GANNOMAT → OPUS → ACCURA → NESTING)
            for user in reversed(configured_users):
                c.execute("""
                    SELECT item_count 
                    FROM logs 
                    WHERE project = ? 
                    AND user = ?
                    AND item_count IS NOT NULL 
                    AND item_count > 0
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, (row['project'], user))
                item_row = c.fetchone()
                if item_row and item_row['item_count']:
                    final_items = item_row['item_count']
                    break  # Found the last user in chain with items
            
            # If no items found from any user, use the total
            if final_items == 0:
                final_items = row['total_items'] or 0
            
            # Get individual user statuses for this project (same as logs_project)
            c.execute('''
                SELECT user, status
                FROM logs l1
                WHERE lower(project) = ? AND user != ''
                AND timestamp = (
                    SELECT MAX(timestamp) 
                    FROM logs l2 
                    WHERE l2.user = l1.user AND lower(l2.project) = lower(l1.project)
                )
                GROUP BY user
            ''', (row['project'].lower(),))
            
            user_statuses = {}
            for user_row in c.fetchall():
                user_statuses[user_row['user']] = user_row['status']
            
            # Sort users according to processing chain order
            raw_users = row['users'].split(',') if row['users'] else []
            configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True,
                                         default_value=['NESTING', 'ACCURA', 'OPUS', 'KL GANNOMAT', 'BOERE'])
            
            # Create a dict for ordering
            user_order = {user: i for i, user in enumerate(configured_users)}
            
            # Sort users by their position in the configured order
            sorted_users = sorted(raw_users, 
                                key=lambda u: user_order.get(u, len(configured_users)))
            
            project_data = {
                'project': row['project'],
                'mo_number': row['mo_number'],
                'first_activity': row['first_activity'],
                'last_activity': row['last_activity'],
                'user_count': row['user_count'],
                'total_items': row['total_items'] or 0,
                'final_items': final_items or 0,
                'users': sorted_users,
                'user_statuses': user_statuses,
                'status': status,
                'is_completed': bool(row['is_completed']),
                'work_duration_minutes': work_duration,
                'project_duration_minutes': project_time
            }
            
            # Add to appropriate list based on REP status
            if is_rep:
                rep_projects.append(project_data)
            else:
                mo_projects.append(project_data)
        
        # Get all projects associated with this SO
        c.execute("""
            SELECT DISTINCT project
            FROM logs
            WHERE so_number = ?
        """, (so_number,))
        so_projects = [row['project'] for row in c.fetchall()]

        # Get aggregate metrics for the SO
        if so_projects:
            placeholders = ','.join(['?'] * len(so_projects))
            c.execute(f"""
                SELECT
                    MIN(CASE WHEN event NOT IN ('AUTO_IMPORT', 'BACKGROUND_WORK_FOUND') THEN timestamp END) as first_activity,
                    MAX(timestamp) as last_activity,
                    COUNT(DISTINCT user) as total_users,
                    COUNT(DISTINCT CASE WHEN mo_number IS NOT NULL AND mo_number != '' THEN mo_number END) as unique_mo_count,
                    MAX(customer_name) as customer_name
                FROM logs
                WHERE project IN ({placeholders})
            """, so_projects)
        else:
            # Fallback to original query if no projects found
            c.execute("""
                SELECT
                    MIN(CASE WHEN event NOT IN ('AUTO_IMPORT', 'BACKGROUND_WORK_FOUND') THEN timestamp END) as first_activity,
                    MAX(timestamp) as last_activity,
                    COUNT(DISTINCT user) as total_users,
                    COUNT(DISTINCT CASE WHEN mo_number IS NOT NULL AND mo_number != '' THEN mo_number END) as unique_mo_count,
                    MAX(customer_name) as customer_name
                FROM logs
                WHERE so_number = ?
            """, (so_number,))
        
        so_info = c.fetchone()
        
        # Calculate totals for regular MOs
        mo_work_duration = sum(project['work_duration_minutes'] for project in mo_projects)
        mo_project_duration = sum(project['project_duration_minutes'] for project in mo_projects)
        mo_items = sum(project['final_items'] for project in mo_projects)

        # Calculate totals for reparaties
        rep_work_duration = sum(project['work_duration_minutes'] for project in rep_projects)
        rep_project_duration = sum(project['project_duration_minutes'] for project in rep_projects)
        rep_items = sum(project['final_items'] for project in rep_projects)

        # Count unique MO numbers from regular MOs
        unique_mo_numbers = set()
        for project in mo_projects:
            if project.get('mo_number'):
                unique_mo_numbers.add(project['mo_number'])
        total_unique_mos = len(unique_mo_numbers)

        # Count reparaties
        total_reparaties = len(rep_projects)

        # Calculate overall totals (for compatibility if needed)
        all_projects = mo_projects + rep_projects
        total_work_duration = mo_work_duration + rep_work_duration
        total_project_duration = mo_project_duration + rep_project_duration
        total_items = mo_items + rep_items

        completion_percentage = (total_completed / len(all_projects) * 100) if all_projects else 0
        
        conn.close()
        
        return render_template('sales_order_detail.html',
                             so_number=so_number,
                             customer_name=so_info['customer_name'],
                             mo_projects=mo_projects,
                             rep_projects=rep_projects,
                             total_mos=total_unique_mos,
                             total_reparaties=total_reparaties,
                             total_users=so_info['total_users'],
                             total_items=total_items,
                             first_activity=so_info['first_activity'],
                             last_activity=so_info['last_activity'],
                             total_work_duration=total_work_duration,
                             total_project_duration=total_project_duration,
                             # Regular MO metrics
                             mo_items=mo_items,
                             mo_work_duration=mo_work_duration,
                             mo_project_duration=mo_project_duration,
                             # Reparaties metrics
                             rep_items=rep_items,
                             rep_work_duration=rep_work_duration,
                             rep_project_duration=rep_project_duration,
                             completion_percentage=round(completion_percentage, 1),
                             total_completed=total_completed,
                             active_page='sales_orders')
        
    except Exception as e:
        logging.error(f"Error loading SO detail for {so_number}: {e}", exc_info=True)
        return render_template('error.html', message=f'Could not load details for SO {so_number}.'), 500

@app.route('/api/projects/all', methods=['GET'])
@login_required
def get_all_projects():
    """Get all projects without pagination for client-side sorting"""
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

        for project_code in all_projects:
            # Determine the project status
            try:
                result = determine_project_status(project_code, conn)
                if len(result) != 2:
                    continue
                project_status, current_user = result
            except ValueError:
                continue

            # Get the latest timestamp
            c.execute("""
                SELECT MAX(timestamp) as latest_timestamp, COUNT(*) as event_count
                FROM logs
                WHERE project = ?
            """, (project_code,))

            result = c.fetchone()
            latest_timestamp = result['latest_timestamp'] if result else None
            event_count = result['event_count'] if result else 0

            # Get metadata
            c.execute("""
                SELECT is_rep_variant, mo_number, so_number, customer_name, color
                FROM logs
                WHERE project = ?
                ORDER BY
                    CASE WHEN mo_number IS NOT NULL THEN 1 ELSE 0 END +
                    CASE WHEN so_number IS NOT NULL THEN 1 ELSE 0 END +
                    CASE WHEN customer_name IS NOT NULL THEN 1 ELSE 0 END +
                    CASE WHEN color IS NOT NULL THEN 1 ELSE 0 END DESC,
                    timestamp DESC
                LIMIT 1
            """, (project_code,))

            rep_result = c.fetchone()

            projects.append({
                'code': project_code,
                'user': current_user or 'Onbekend',
                'status': project_status,
                'timestamp': latest_timestamp,
                'event_count': event_count,
                'is_rep_variant': rep_result and rep_result['is_rep_variant'] == 1,
                'mo_number': rep_result['mo_number'] if rep_result else None,
                'so_number': rep_result['so_number'] if rep_result else None,
                'customer_name': rep_result['customer_name'] if rep_result else None,
                'color': rep_result['color'] if rep_result else None
            })

        return jsonify({
            'success': True,
            'projects': projects,
            'total': len(projects)
        })

    except Exception as e:
        logging.error(f"Error getting all projects: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/projects', methods=['GET'])
@login_required
def projects():
    configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get search and sort parameters
    search_query = request.args.get('search', '', type=str).strip()
    sort_by = request.args.get('sort', 'recent', type=str)
    
    # Ensure per_page is within reasonable bounds
    per_page = max(5, min(100, per_page))
    
    logging.info(f'projects endpoint called - page: {page}, per_page: {per_page}, search: {search_query}, sort: {sort_by}')
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
        total_projects_count = len(all_projects)
        completed_projects = 0
        in_progress = 0
        rep_variant_projects = 0
        
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
            
            # Check if project is a rep variant and get metadata
            # Prioritize records with metadata over just is_rep_variant condition
            c.execute("""
                SELECT is_rep_variant, mo_number, so_number, customer_name, color
                FROM logs
                WHERE project = ?
                ORDER BY 
                    CASE WHEN mo_number IS NOT NULL THEN 1 ELSE 0 END +
                    CASE WHEN so_number IS NOT NULL THEN 1 ELSE 0 END +
                    CASE WHEN customer_name IS NOT NULL THEN 1 ELSE 0 END +
                    CASE WHEN color IS NOT NULL THEN 1 ELSE 0 END DESC,
                    CASE WHEN is_rep_variant IS NOT NULL THEN 1 ELSE 0 END DESC,
                    timestamp DESC
                LIMIT 1
            """, (project_code,))
            
            rep_result = c.fetchone()
            is_rep_variant = rep_result and rep_result['is_rep_variant'] == 1
            mo_number = rep_result['mo_number'] if rep_result else None
            so_number = rep_result['so_number'] if rep_result else None
            customer_name = rep_result['customer_name'] if rep_result else None
            color = rep_result['color'] if rep_result else None
            
            # Create project entry
            project_dict = {
                'code': project_code,
                'user': current_user or 'Onbekend',
                'status': project_status,
                'timestamp': formatted_timestamp,
                'raw_timestamp': latest_timestamp,  # Add raw timestamp for sorting
                'event_count': event_count,
                'is_rep_variant': is_rep_variant,
                'mo_number': mo_number,
                'so_number': so_number,
                'customer_name': customer_name,
                'color': color
            }
            
            # Count statuses
            if project_status in ['AFGEMELD', 'AFGEROND']:
                completed_projects += 1
            elif project_status in ['OPEN', 'BEZIG']:
                in_progress += 1
            
            # Count rep variant projects
            if is_rep_variant:
                rep_variant_projects += 1
            
            projects.append(project_dict)
        
        # Apply search filter if provided
        if search_query:
            search_lower = search_query.lower()
            filtered_projects = []
            for proj in projects:
                # Search in multiple fields
                searchable_text = (
                    (proj['code'] or '').lower() + ' ' +
                    (proj['user'] or '').lower() + ' ' +
                    (proj['status'] or '').lower() + ' ' +
                    (proj['mo_number'] or '').lower() + ' ' +
                    (proj['so_number'] or '').lower() + ' ' +
                    (proj['customer_name'] or '').lower() + ' ' +
                    (proj['color'] or '').lower()
                )
                if search_lower in searchable_text:
                    filtered_projects.append(proj)
            projects = filtered_projects
        
        # Apply sorting based on sort parameter
        if sort_by == 'recent':
            # Sort by timestamp (most recent first)
            projects.sort(key=lambda x: x['timestamp'], reverse=True)
        elif sort_by == 'oldest':
            # Sort by timestamp (oldest first)
            projects.sort(key=lambda x: x['timestamp'])
        elif sort_by == 'code':
            # Sort by project code
            projects.sort(key=lambda x: x['code'])
        elif sort_by == 'customer':
            # Sort by customer name, then by code for those without customer
            projects.sort(key=lambda x: (x['customer_name'] or 'zzz', x['code']))
        elif sort_by == 'status':
            # Sort by status
            projects.sort(key=lambda x: x['status'])
        else:
            # Default to recent
            projects.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # No pagination - return all projects (filtering/sorting handled client-side)
        total_projects = len(projects)

        return render_template('projects.html',
                             projects=projects,
                             configured_users=configured_users,
                             total_projects=total_projects_count,
                             rep_variant_projects=rep_variant_projects,
                             completed_projects=completed_projects,
                             in_progress=in_progress,
                             active_page='projects',
                             search_query=search_query,
                             sort_by=sort_by)
    
    except Exception as e:
        logging.error(f"Failed to render projects page: {e}", exc_info=True)
        return render_template('error.html', message='Could not retrieve projects from the database.'), 500
        

@app.route('/users', methods=['GET'])
@login_required
def users():
    # Get configured users from database (with config fallback)
    configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
    
    logging.info('users endpoint was called')
    try:
        # Get real user data from database
        user_stats = []
        
        for user in configured_users:
            # Check if user had any work assigned
            has_work = user_has_work_assigned(user)
            
            active = count_active_projects(user)
            completed = count_completed_today(user)
            avg_items_per_hour = calculate_avg_items_per_hour(user)
            items_hour_change = calculate_items_hour_change_vs_last_week(user)
            active_projects_change = calculate_active_projects_change_vs_last_week(user)
            activity_data = get_user_activity_last_7_days(user)
            
            stats = {
                'name': user,
                'role': 'Operator',
                'initials': ''.join([part[0] for part in user.split()]),
                'active_projects': active,
                'completed_today': completed,
                'avg_items_per_hour': avg_items_per_hour,
                'items_hour_change': items_hour_change,
                'active_projects_change': active_projects_change,
                'activity_data': activity_data,
                'has_work_assigned': has_work  # Add flag to indicate if user had work
            }
            user_stats.append(stats)
        
        return render_template('users.html',
                             users=user_stats,
                             active_page='users')
    
    except Exception as e:
        logging.error(f"Failed to render users page: {e}", exc_info=True)
        return render_template('error.html', message='Could not retrieve users from the database.'), 500

@app.route('/user/<username>')
@login_required
def user_performance(username):
    """Individual user performance page with detailed analytics"""
    # Get configured users from database (with config fallback)
    configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
    
    if username not in configured_users:
        return render_template('error.html', message='User not found'), 404
    
    try:
        # Get date range parameters (consistent with statistics page)
        from datetime import datetime, timedelta
        
        # Handle different period types like statistics endpoints
        period_type = request.args.get('period_type', 'days')
        period = request.args.get('period', '30')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Calculate date range based on period_type
        if period_type == 'custom' and start_date and end_date:
            # Use provided custom dates
            pass
        elif period_type == 'all':
            # Use a very wide range for all data
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        else:
            # Use period-based calculation (default behavior)
            period_days = int(period)
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=period_days)).strftime('%Y-%m-%d')
        
        # Check if user had work assigned in this period
        has_work = user_has_work_assigned(username, start_date, end_date)
        
        # Get activity data first - single data source for all KPIs
        activity_data = get_user_activity_date_range(username, start_date, end_date)

        # Derive all KPIs from activity_data
        total_items = sum(a['items'] for a in activity_data)
        total_hours = sum(a['hours'] for a in activity_data)
        active_projects = sum(1 for a in activity_data if a['status'] == 'active')
        completed_in_period = sum(1 for a in activity_data if a['status'] == 'completed')
        # Simple average of per-project items/hour (matches trendline midpoint)
        projects_with_rate = [a for a in activity_data if a['items_per_hour'] > 0]
        if projects_with_rate:
            avg_items_per_hour = f"{sum(a['items_per_hour'] for a in projects_with_rate) / len(projects_with_rate):.1f}"
        else:
            avg_items_per_hour = "--"

        user_data = {
            'name': username,
            'role': 'Operator',
            'initials': ''.join([part[0] for part in username.split()]),
            'avg_items_per_hour': avg_items_per_hour,
            'active_projects': active_projects,
            'completed_today': count_completed_today(username),
            'completed_in_period': completed_in_period,
            'has_work_assigned': has_work,
            'activity_data': activity_data,
            'total_items_in_period': total_items
        }

        # Get performance percentage
        performance_percentage, performance_class = calculate_performance_percentage(username, user_data['avg_items_per_hour'])
        user_data['performance_percentage'] = performance_percentage
        user_data['performance_class'] = performance_class

        # Keep database_avg for discrepancy logging
        user_data['database_avg_items_per_hour'] = calculate_avg_items_per_hour(username, start_date, end_date)

        # Calculate actual number of active days (unique days with activity)
        user_data['active_days_count'] = count_active_days_in_period(username, start_date, end_date)

        # Calculate period label for display
        period_label = 'Vandaag'
        if period_type == 'custom':
            period_label = f'{start_date} - {end_date}'
        elif period_type == 'all':
            period_label = 'Totaal'
        else:
            period_labels = {
                '1': 'Vandaag',
                '7': 'Deze Week',
                '30': 'Deze Maand',
                '90': 'Dit Kwartaal',
                '365': 'Dit Jaar'
            }
            period_label = period_labels.get(period, f'Laatste {period} Dagen')

        user_data['period_label'] = period_label
        
        return render_template('user_performance.html',
                             user=user_data,
                             start_date=start_date,
                             end_date=end_date,
                             period_type=period_type,
                             period=period,
                             active_page='users')
    
    except Exception as e:
        logging.error(f"Failed to render user performance page: {e}", exc_info=True)
        return render_template('error.html', message='Could not load user performance data.'), 500

@app.route('/time-estimation')
@login_required
def time_estimation_calculator():
    """Project time estimation calculator page"""
    try:
        return render_template('time_estimation_calculator.html', active_page='time_estimation')
    except Exception as e:
        logging.error(f"Failed to render time estimation calculator: {e}", exc_info=True)
        return render_template('error.html', message='Could not load time estimation calculator.'), 500

@app.route('/statistics')
@login_required
def statistics():
    """Statistics page view with comprehensive analytics"""
    configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
    
    try:
        return render_template('statistics.html',
                             configured_users=configured_users,
                             work_hours=WORK_HOURS,
                             active_page='statistics')
    except Exception as e:
        logging.error(f"Failed to render statistics page: {e}", exc_info=True)
        return render_template('error.html', message='Could not load statistics page.'), 500

@app.route('/settings')
@login_required
def settings():
    """Settings page for work hours configuration"""
    configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
    
    try:
        return render_template('settings.html',
                             configured_users=configured_users,
                             active_page='settings')
    except Exception as e:
        logging.error(f"Failed to render settings page: {e}", exc_info=True)
        return render_template('error.html', message='Could not load settings page.'), 500

@app.route('/database', methods=['GET'])
@login_required
def database():
    configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
    
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
            WITH BatchProjects AS (
                -- Get all projects linked to SCANNER sessions via session_projects
                SELECT 
                    s.user,
                    s.session_id,
                    sp.project,
                    s.session_type,
                    sp.item_count,
                    s.work_duration_minutes,
                    s.start_time,
                    s.end_time
                FROM sessions s
                JOIN session_projects sp ON s.session_id = sp.session_id
                WHERE s.session_type = 'SCANNER' 
                AND s.status = 'completed'
                {date_filter.replace('timestamp', 's.start_time')}
            ),
            OtherSessions AS (
                -- Get non-SCANNER sessions (XLSX_UPDATED, MANUAL)
                SELECT 
                    s.user,
                    s.session_id,
                    s.project,
                    s.session_type,
                    s.item_count,
                    s.work_duration_minutes,
                    s.start_time,
                    s.end_time
                FROM sessions s
                WHERE s.session_type != 'SCANNER'
                AND s.status = 'completed'
                {date_filter.replace('timestamp', 's.start_time')}
            ),
            BatchAllocation AS (
                -- For SCANNER sessions, allocate time proportionally based on items
                SELECT 
                    bp.user,
                    bp.project,
                    bp.session_type,
                    bp.item_count,
                    -- Calculate proportional time allocation
                    CASE 
                        WHEN (SELECT SUM(item_count) FROM BatchProjects bp2 WHERE bp2.session_id = bp.session_id) > 0 THEN
                            bp.item_count * 1.0 / (SELECT SUM(item_count) FROM BatchProjects bp2 WHERE bp2.session_id = bp.session_id) * bp.work_duration_minutes
                        ELSE 
                            bp.work_duration_minutes / NULLIF((SELECT COUNT(*) FROM BatchProjects bp2 WHERE bp2.session_id = bp.session_id), 0)
                    END as allocated_duration_minutes
                FROM BatchProjects bp
                
                UNION ALL
                
                -- For other sessions, use actual session time
                SELECT 
                    user,
                    project,
                    session_type,
                    item_count,
                    work_duration_minutes as allocated_duration_minutes
                FROM OtherSessions
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
            WITH BatchProjects AS (
                -- Get all projects linked to SCANNER sessions via session_projects
                SELECT 
                    s.user,
                    s.session_id,
                    sp.project,
                    s.session_type,
                    sp.item_count,
                    s.work_duration_minutes,
                    s.start_time
                FROM sessions s
                JOIN session_projects sp ON s.session_id = sp.session_id
                WHERE s.session_type = 'SCANNER' 
                AND s.status = 'completed'
                {date_filter.replace('timestamp', 's.start_time')}
            ),
            OtherSessions AS (
                -- Get non-SCANNER sessions
                SELECT 
                    s.user,
                    s.session_id,
                    s.project,
                    s.session_type,
                    s.item_count,
                    s.work_duration_minutes,
                    s.start_time
                FROM sessions s
                WHERE s.session_type != 'SCANNER'
                AND s.status = 'completed'
                {date_filter.replace('timestamp', 's.start_time')}
            ),
            BatchAllocation AS (
                -- For SCANNER sessions, allocate time proportionally based on items
                SELECT 
                    bp.user,
                    bp.session_type,
                    bp.item_count,
                    -- Calculate proportional time allocation
                    CASE 
                        WHEN (SELECT SUM(item_count) FROM BatchProjects bp2 WHERE bp2.session_id = bp.session_id) > 0 THEN
                            bp.item_count * 1.0 / (SELECT SUM(item_count) FROM BatchProjects bp2 WHERE bp2.session_id = bp.session_id) * bp.work_duration_minutes
                        ELSE 
                            bp.work_duration_minutes / NULLIF((SELECT COUNT(*) FROM BatchProjects bp2 WHERE bp2.session_id = bp.session_id), 0)
                    END as allocated_duration_minutes
                FROM BatchProjects bp
                
                UNION ALL
                
                -- For other sessions, use actual session time
                SELECT 
                    user,
                    session_type,
                    item_count,
                    work_duration_minutes as allocated_duration_minutes
                FROM OtherSessions
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
            
            # Calculate actual work minutes between handoff excluding weekends and holidays
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

@app.route('/api/project/estimate-time', methods=['POST'])
def estimate_project_time():
    """
    Estimate project completion time based on historical data and current capacity

    Request JSON:
    {
        "project": "P240912-002", (optional - for analyzing similar past projects)
        "items": 150, (required - number of items to process)
        "project_type": "NESTING_PROCESSING", (optional - filter historical data by type)
        "assigned_users": ["NESTING", "OPUS"], (optional - estimate based on specific users)
        "use_optimal_capacity": true/false (default: false - use current vs optimal capacity)
        "include_idle_time": true/false (default: true - factor in historical idle time)
        "what_if": {
            "improved_handoff_percent": 20,  (reduce idle time by %)
            "user_improvements": {"NESTING": 30}  (improve user items/h by %)
        }
    }

    Response includes:
    - Estimated hours based on historical averages
    - Best/worst case scenarios
    - Per-user estimates
    - Optimal capacity vs current capacity comparison
    - Similar historical projects analysis
    - Idle time analysis and impact
    - What-if scenario results
    - Maximum capacity calculations
    """
    try:
        data = request.get_json()
        items = data.get('items')
        project_type = data.get('project_type')
        assigned_users = data.get('assigned_users', [])
        use_optimal_capacity = data.get('use_optimal_capacity', False)
        include_idle_time = data.get('include_idle_time', True)
        what_if = data.get('what_if', {})
        project_reference = data.get('project')

        if not items or items <= 0:
            return jsonify({'success': False, 'error': 'Valid items count is required'}), 400

        conn = get_db()
        c = conn.cursor()

        # 1. Get historical averages from completed projects
        type_filter = ""
        if project_type:
            type_filter = f"AND s.session_type = '{project_type}'"

        # Calculate historical performance from sessions
        c.execute(f"""
            WITH SessionPerformance AS (
                SELECT
                    s.user,
                    s.session_type,
                    s.item_count,
                    s.work_duration_minutes,
                    CASE
                        WHEN s.session_type = 'SCANNER' THEN
                            -- For SCANNER sessions, allocate time proportionally
                            s.item_count * 1.0 / NULLIF(
                                (SELECT SUM(s2.item_count)
                                 FROM sessions s2
                                 WHERE s2.user = s.user
                                 AND s2.session_type = 'SCANNER'
                                 AND s2.status = 'completed'
                                 AND DATE(s2.start_time) = DATE(s.start_time)), 0
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
                    END as allocated_minutes
                FROM sessions s
                WHERE s.status = 'completed'
                AND s.item_count > 0
                AND s.work_duration_minutes > 0
                {type_filter}
                AND s.start_time >= date('now', '-90 days')
            )
            SELECT
                ROUND(AVG(item_count * 60.0 / NULLIF(allocated_minutes, 0)), 2) as avg_items_per_hour,
                ROUND(AVG(allocated_minutes / NULLIF(item_count, 0)), 2) as avg_minutes_per_item,
                COUNT(*) as sample_size,
                SUM(item_count) as total_items_analyzed,
                MIN(item_count * 60.0 / NULLIF(allocated_minutes, 0)) as min_items_per_hour,
                MAX(item_count * 60.0 / NULLIF(allocated_minutes, 0)) as max_items_per_hour
            FROM SessionPerformance
            WHERE allocated_minutes > 0
        """)

        historical_result = c.fetchone()

        if not historical_result or not historical_result[0]:
            # No historical data - use defaults
            avg_items_per_hour = 20.0
            avg_minutes_per_item = 3.0
            sample_size = 0
            total_items_analyzed = 0
            min_items_per_hour = 10.0
            max_items_per_hour = 40.0
        else:
            avg_items_per_hour = historical_result[0]
            avg_minutes_per_item = historical_result[1]
            sample_size = historical_result[2]
            total_items_analyzed = historical_result[3]
            min_items_per_hour = historical_result[4] or avg_items_per_hour * 0.5
            max_items_per_hour = historical_result[5] or avg_items_per_hour * 1.5

        # 2. Calculate per-user performance and capacity
        user_estimates = []

        # Get efficiency targets from config
        efficiency_targets = {}
        try:
            config_path = get_writable_path('config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    efficiency_targets = config.get('efficiency_targets', {})
        except Exception as e:
            logging.warning(f"Could not load efficiency targets: {e}")

        # Get actual performance for each user
        user_filter = ""
        if assigned_users:
            placeholders = ','.join(['?' for _ in assigned_users])
            user_filter = f"AND user IN ({placeholders})"

        query = f"""
            WITH SessionPerformance AS (
                SELECT
                    s.user,
                    s.item_count,
                    CASE
                        WHEN s.session_type = 'SCANNER' THEN
                            s.item_count * 1.0 / NULLIF(
                                (SELECT SUM(s2.item_count)
                                 FROM sessions s2
                                 WHERE s2.user = s.user
                                 AND s2.session_type = 'SCANNER'
                                 AND s2.status = 'completed'
                                 AND DATE(s2.start_time) = DATE(s.start_time)), 0
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
                    END as allocated_minutes
                FROM sessions s
                WHERE s.status = 'completed'
                AND s.item_count > 0
                AND s.work_duration_minutes > 0
                {type_filter}
                {user_filter}
                AND s.start_time >= date('now', '-90 days')
            )
            SELECT
                user,
                ROUND(AVG(item_count * 60.0 / NULLIF(allocated_minutes, 0)), 2) as actual_items_per_hour,
                ROUND(AVG(allocated_minutes / NULLIF(item_count, 0)), 2) as minutes_per_item,
                COUNT(*) as sessions_count
            FROM SessionPerformance
            WHERE allocated_minutes > 0
            GROUP BY user
            HAVING COUNT(*) >= 3
        """

        if assigned_users:
            c.execute(query, assigned_users)
        else:
            c.execute(query)

        for row in c.fetchall():
            user = row[0]
            actual_items_per_hour = row[1] or avg_items_per_hour
            minutes_per_item = row[2] or avg_minutes_per_item
            sessions_count = row[3]

            # Get target/optimal capacity from config
            optimal_items_per_hour = efficiency_targets.get(user, actual_items_per_hour * 1.2)

            # Calculate estimates
            if use_optimal_capacity:
                # Estimate based on optimal capacity
                estimated_hours = items / optimal_items_per_hour
                capacity_utilization = (actual_items_per_hour / optimal_items_per_hour) * 100
            else:
                # Estimate based on current/actual capacity
                estimated_hours = items / actual_items_per_hour
                capacity_utilization = 100  # Using current capacity

            user_estimates.append({
                'user': user,
                'actual_items_per_hour': round(actual_items_per_hour, 2),
                'optimal_items_per_hour': round(optimal_items_per_hour, 2),
                'estimated_hours': round(estimated_hours, 2),
                'estimated_minutes': round(estimated_hours * 60, 0),
                'capacity_utilization_percentage': round(capacity_utilization, 1),
                'sessions_analyzed': sessions_count,
                'minutes_per_item': round(minutes_per_item, 2)
            })

        # Sort by fastest completion time
        user_estimates.sort(key=lambda x: x['estimated_hours'])

        # 3. Global estimates
        if use_optimal_capacity:
            # Calculate average optimal capacity
            if user_estimates:
                avg_optimal_capacity = sum(u['optimal_items_per_hour'] for u in user_estimates) / len(user_estimates)
            else:
                avg_optimal_capacity = avg_items_per_hour * 1.2
            global_estimated_hours = items / avg_optimal_capacity
        else:
            global_estimated_hours = items / avg_items_per_hour

        # 4. Best/worst case scenarios
        best_case_hours = items / max_items_per_hour
        worst_case_hours = items / min_items_per_hour

        # 5. Find similar historical projects
        similar_projects = []
        if project_reference:
            # Try to find similar projects by pattern (e.g., same customer or project prefix)
            project_prefix = project_reference.split('-')[0] if '-' in project_reference else project_reference[:8]

            c.execute("""
                SELECT
                    ps.project,
                    ps.total_items,
                    ps.total_duration_minutes,
                    ps.status,
                    ROUND(ps.total_items * 60.0 / NULLIF(ps.total_duration_minutes, 0), 2) as items_per_hour,
                    ps.start_time,
                    ps.end_time
                FROM project_sessions ps
                WHERE ps.project LIKE ? || '%'
                AND ps.total_items > 0
                AND ps.status = 'completed'
                ORDER BY ps.start_time DESC
                LIMIT 5
            """, (project_prefix,))

            for row in c.fetchall():
                similar_projects.append({
                    'project': row[0],
                    'items': row[1],
                    'duration_hours': round(row[2] / 60.0, 2),
                    'status': row[3],
                    'items_per_hour': row[4] or 0,
                    'start_time': row[5],
                    'end_time': row[6]
                })

        # 6. Calculate multi-user parallel processing estimate
        parallel_estimate_hours = None
        if len(user_estimates) > 1:
            # If multiple users work in parallel, estimate is based on combined throughput
            combined_items_per_hour = sum(u['actual_items_per_hour'] if not use_optimal_capacity else u['optimal_items_per_hour']
                                         for u in user_estimates)
            parallel_estimate_hours = items / combined_items_per_hour if combined_items_per_hour > 0 else None

        # 7. Calculate idle time impact (project time vs session time)
        idle_time_analysis = {}
        if include_idle_time:
            # Get historical idle time percentage from project_sessions vs sessions
            c.execute(f"""
                WITH ProjectTime AS (
                    SELECT
                        SUM(ps.total_duration_minutes) as total_project_minutes,
                        COUNT(*) as project_count
                    FROM project_sessions ps
                    WHERE ps.status = 'completed'
                    AND ps.start_time >= date('now', '-90 days')
                    {f"AND ps.project LIKE '{project_type}%'" if project_type else ''}
                ),
                SessionTime AS (
                    SELECT
                        SUM(s.work_duration_minutes) as total_session_minutes
                    FROM sessions s
                    WHERE s.status = 'completed'
                    AND s.start_time >= date('now', '-90 days')
                    {type_filter.replace('s.session_type', 'session_type') if type_filter else ''}
                )
                SELECT
                    pt.total_project_minutes,
                    st.total_session_minutes,
                    CASE
                        WHEN pt.total_project_minutes > 0 THEN
                            ROUND(((pt.total_project_minutes - st.total_session_minutes) / pt.total_project_minutes) * 100, 1)
                        ELSE 0
                    END as idle_percentage,
                    pt.total_project_minutes - st.total_session_minutes as idle_minutes,
                    pt.project_count
                FROM ProjectTime pt, SessionTime st
            """)

            idle_result = c.fetchone()
            if idle_result and idle_result[0]:
                total_project_minutes = idle_result[0]
                total_session_minutes = idle_result[1]
                idle_percentage = idle_result[2] or 0
                idle_minutes = idle_result[3] or 0
                project_count = idle_result[4] or 0

                # Apply idle time to estimate
                if idle_percentage > 0:
                    idle_multiplier = 1 + (idle_percentage / 100)
                    estimated_with_idle = global_estimated_hours * idle_multiplier

                    idle_time_analysis = {
                        'historical_idle_percentage': idle_percentage,
                        'avg_idle_hours_per_project': round(idle_minutes / project_count / 60, 2) if project_count > 0 else 0,
                        'estimated_idle_hours': round((estimated_with_idle - global_estimated_hours), 2),
                        'total_time_with_idle': round(estimated_with_idle, 2),
                        'projects_analyzed': project_count,
                        'idle_impact': 'high' if idle_percentage > 30 else 'medium' if idle_percentage > 15 else 'low'
                    }

                    # Update global estimate to include idle time
                    if include_idle_time:
                        global_estimated_hours = estimated_with_idle

        # 8. What-if scenario calculations
        what_if_results = {}
        if what_if:
            improved_handoff_percent = what_if.get('improved_handoff_percent', 0)
            user_improvements = what_if.get('user_improvements', {})

            # Scenario: Improved handoff/idle time
            if improved_handoff_percent > 0 and idle_time_analysis:
                reduced_idle = idle_time_analysis.get('historical_idle_percentage', 0) * (1 - improved_handoff_percent / 100)
                new_multiplier = 1 + (reduced_idle / 100)
                improved_hours = (items / avg_items_per_hour) * new_multiplier
                time_saved = global_estimated_hours - improved_hours

                what_if_results['improved_handoff'] = {
                    'reduced_idle_percentage': round(reduced_idle, 1),
                    'estimated_hours': round(improved_hours, 2),
                    'time_saved_hours': round(time_saved, 2),
                    'improvement_percent': improved_handoff_percent
                }

            # Scenario: Improved user performance
            if user_improvements:
                improved_estimates = []
                for user_est in user_estimates:
                    user = user_est['user']
                    if user in user_improvements:
                        improvement_pct = user_improvements[user]
                        current_rate = user_est['actual_items_per_hour']
                        improved_rate = current_rate * (1 + improvement_pct / 100)
                        improved_hours = items / improved_rate
                        time_saved = user_est['estimated_hours'] - improved_hours

                        improved_estimates.append({
                            'user': user,
                            'current_items_per_hour': round(current_rate, 2),
                            'improved_items_per_hour': round(improved_rate, 2),
                            'current_estimated_hours': user_est['estimated_hours'],
                            'improved_estimated_hours': round(improved_hours, 2),
                            'time_saved_hours': round(time_saved, 2),
                            'improvement_percent': improvement_pct
                        })

                if improved_estimates:
                    what_if_results['user_improvements'] = improved_estimates

        # 9. Maximum production capacity calculations
        max_capacity_analysis = {}
        if user_estimates or avg_items_per_hour > 0:
            # Calculate theoretical maximum based on all users at optimal capacity
            if user_estimates:
                max_combined_rate = sum(u['optimal_items_per_hour'] for u in user_estimates)
            else:
                # Use historical max if no user estimates
                max_combined_rate = max_items_per_hour

            # Maximum items per day (8 hour workday)
            max_items_per_day = max_combined_rate * 8

            # Maximum items per week (5 days)
            max_items_per_week = max_items_per_day * 5

            # Time to reach target if working at maximum
            max_capacity_hours = items / max_combined_rate if max_combined_rate > 0 else 0

            max_capacity_analysis = {
                'max_items_per_hour': round(max_combined_rate, 2),
                'max_items_per_day': round(max_items_per_day, 0),
                'max_items_per_week': round(max_items_per_week, 0),
                'hours_at_max_capacity': round(max_capacity_hours, 2),
                'potential_improvement': round(((global_estimated_hours - max_capacity_hours) / global_estimated_hours * 100), 1) if global_estimated_hours > 0 else 0,
                'users_at_optimal': len([u for u in user_estimates if u['capacity_utilization_percentage'] >= 100])
            }

        # 10. Reverse calculator - items needed to reach target hours
        reverse_calculations = {}
        if user_estimates or avg_items_per_hour > 0:
            target_hours_options = [4, 8, 16, 40]  # 4h, 1 day, 2 days, 1 week

            for target_hours in target_hours_options:
                if use_optimal_capacity and user_estimates:
                    avg_rate = sum(u['optimal_items_per_hour'] for u in user_estimates) / len(user_estimates)
                else:
                    avg_rate = avg_items_per_hour

                items_for_target = target_hours * avg_rate

                reverse_calculations[f'{target_hours}h'] = {
                    'target_hours': target_hours,
                    'items_achievable': round(items_for_target, 0),
                    'rate_used': round(avg_rate, 2)
                }

        # 7. Build response
        response = {
            'success': True,
            'input': {
                'items': items,
                'project_type': project_type,
                'assigned_users': assigned_users,
                'use_optimal_capacity': use_optimal_capacity
            },
            'global_estimate': {
                'estimated_hours': round(global_estimated_hours, 2),
                'estimated_minutes': round(global_estimated_hours * 60, 0),
                'best_case_hours': round(best_case_hours, 2),
                'worst_case_hours': round(worst_case_hours, 2),
                'avg_items_per_hour': round(avg_items_per_hour, 2),
                'avg_minutes_per_item': round(avg_minutes_per_item, 2),
                'confidence_level': 'high' if sample_size >= 20 else 'medium' if sample_size >= 10 else 'low'
            },
            'user_estimates': user_estimates,
            'parallel_processing': {
                'enabled': len(user_estimates) > 1,
                'estimated_hours': round(parallel_estimate_hours, 2) if parallel_estimate_hours else None,
                'users_count': len(user_estimates)
            },
            'historical_analysis': {
                'sample_size': sample_size,
                'total_items_analyzed': total_items_analyzed,
                'data_period': 'last 90 days',
                'similar_projects': similar_projects
            },
            'capacity_analysis': {
                'using_optimal': use_optimal_capacity,
                'avg_capacity_utilization': round(sum(u['capacity_utilization_percentage'] for u in user_estimates) / len(user_estimates), 1) if user_estimates else 0
            },
            'idle_time_analysis': idle_time_analysis if idle_time_analysis else None,
            'what_if_scenarios': what_if_results if what_if_results else None,
            'maximum_capacity': max_capacity_analysis if max_capacity_analysis else None,
            'reverse_calculator': reverse_calculations if reverse_calculations else None
        }

        return jsonify(response)

    except Exception as e:
        logging.error(f"Error estimating project time: {e}", exc_info=True)
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

def get_holidays_for_period(start_date=None, end_date=None):
    """Helper function to get holidays for a specific period"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        if start_date and end_date:
            c.execute("""
                SELECT date, name, type FROM holidays 
                WHERE date BETWEEN ? AND ?
                ORDER BY date
            """, (start_date, end_date))
        else:
            # Default to current year
            from datetime import datetime
            current_year = datetime.now().year
            c.execute("""
                SELECT date, name, type FROM holidays 
                WHERE date LIKE ?
                ORDER BY date
            """, (f"{current_year}%",))
        
        holidays = {}
        for row in c.fetchall():
            holidays[row[0]] = {
                'name': row[1],
                'type': row[2]
            }
        
        return holidays
        
    except Exception as e:
        logging.error(f"Error getting holidays for period: {e}")
        return {}

# Unified Work Hours and Holiday Management API
@app.route('/api/work-hours/unified', methods=['GET'])
def get_unified_work_hours():
    """Get unified work hours configuration with holiday support for entire company"""
    try:
        # Get base work hours configuration
        work_hours = WORK_HOURS.copy()
        
        # Add holiday information for current month (can be extended for date ranges)
        holidays = get_holidays_for_period()
        
        # Add calculated work days and formatted times
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        formatted_times = {}
        
        for day in days:
            if day in work_hours and 'start' in work_hours[day] and 'end' in work_hours[day]:
                start_hour = work_hours[day]['start']
                end_hour = work_hours[day]['end']
                
                start_time = f"{int(start_hour):02d}:{int((start_hour % 1) * 60):02d}"
                end_time = f"{int(end_hour):02d}:{int((end_hour % 1) * 60):02d}"
                
                formatted_times[f'{day}_start_time'] = start_time
                formatted_times[f'{day}_end_time'] = end_time
                formatted_times[f'{day}_hours'] = round((end_hour - start_hour) - 
                    ((work_hours.get('break_end', 12.5) - work_hours.get('break_start', 12)) if 
                     start_hour <= work_hours.get('break_start', 12) and end_hour >= work_hours.get('break_end', 12.5) 
                     else 0), 1)
        
        # Add break times
        break_start_hour = work_hours.get('break_start', 12)
        break_end_hour = work_hours.get('break_end', 12.5)
        
        formatted_times['break_start_time'] = f"{int(break_start_hour):02d}:{int((break_start_hour % 1) * 60):02d}"
        formatted_times['break_end_time'] = f"{int(break_end_hour):02d}:{int((break_end_hour % 1) * 60):02d}"
        
        return jsonify({
            'success': True,
            'work_hours': work_hours,
            'formatted_times': formatted_times,
            'holidays': holidays,
            'company_wide': True
        })
        
    except Exception as e:
        logging.error(f"Error getting unified work hours: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/work-hours/calculate', methods=['POST'])
def calculate_unified_work_minutes():
    """Calculate work minutes using unified system with holiday support"""
    try:
        data = request.get_json()
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if not start_time or not end_time:
            return jsonify({'success': False, 'error': 'start_time and end_time required'}), 400
        
        # Calculate work minutes excluding weekends and holidays
        work_minutes = calculate_work_minutes(start_time, end_time)
        
        return jsonify({
            'success': True,
            'work_minutes': work_minutes,
            'work_hours': round(work_minutes / 60, 2)
        })
        
    except Exception as e:
        logging.error(f"Error calculating unified work minutes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Holiday Management API
@app.route('/api/holidays', methods=['GET'])
def get_holidays():
    """Get all holidays or holidays for a specific period"""
    try:
        year = request.args.get('year')
        month = request.args.get('month')
        
        conn = get_db()
        c = conn.cursor()
        
        query = "SELECT * FROM holidays"
        params = []
        
        if year:
            if month:
                query += " WHERE date LIKE ? ORDER BY date"
                params.append(f"{year}-{month:02d}%")
            else:
                query += " WHERE date LIKE ? ORDER BY date"
                params.append(f"{year}%")
        else:
            query += " ORDER BY date"
        
        c.execute(query, params)
        holidays = []
        for row in c.fetchall():
            holidays.append({
                'id': row[0],
                'date': row[1],
                'name': row[2],
                'type': row[3],
                'is_recurring': bool(row[4]),
                'created_at': row[5]
            })
        
        return jsonify({
            'success': True,
            'holidays': holidays
        })
        
    except Exception as e:
        logging.error(f"Error getting holidays: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/holidays', methods=['POST'])
def add_holiday():
    """Add a new holiday"""
    try:
        data = request.get_json()
        date = data.get('date')
        name = data.get('name')
        holiday_type = data.get('type', 'holiday')
        is_recurring = data.get('is_recurring', False)
        
        if not date or not name:
            return jsonify({'success': False, 'error': 'date and name required'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO holidays (date, name, type, is_recurring)
            VALUES (?, ?, ?, ?)
        """, (date, name, holiday_type, is_recurring))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Holiday added successfully',
            'id': c.lastrowid
        })
        
    except Exception as e:
        logging.error(f"Error adding holiday: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/holidays/<int:holiday_id>', methods=['DELETE'])
def delete_holiday(holiday_id):
    """Delete a holiday"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("DELETE FROM holidays WHERE id = ?", (holiday_id,))
        conn.commit()
        
        if c.rowcount == 0:
            return jsonify({'success': False, 'error': 'Holiday not found'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Holiday deleted successfully'
        })
        
    except Exception as e:
        logging.error(f"Error deleting holiday: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def calculate_work_minutes(start_time, end_time, work_hours=WORK_HOURS):
    """Calculate work minutes EXCLUDING weekends and holidays"""
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time)
    
    # Get holidays for the period
    start_date = start_time.strftime('%Y-%m-%d')
    end_date = end_time.strftime('%Y-%m-%d')
    holidays = get_holidays_for_period(start_date, end_date)
    
    total_minutes = 0
    current = start_time
    
    # Day name mapping
    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    while current < end_time:
        current_date = current.strftime('%Y-%m-%d')
        
        # Check if current date is a holiday
        if current_date in holidays:
            # Skip holidays - no work time
            current = current.replace(hour=0, minute=0, second=0) + timedelta(days=1)
            continue
        
        # Skip weekends if not in work_days
        if current.weekday() not in WORK_HOURS.get('work_days', [0, 1, 2, 3, 4]):
            current = current.replace(hour=0, minute=0, second=0) + timedelta(days=1)
            continue
        
        # Get day-specific work hours
        day_name = day_names[current.weekday()]
        day_config = WORK_HOURS.get(day_name, {'start': 7.5, 'end': 16})
        
        # Calculate work time for current day (same logic as original)
        day_start = current.replace(hour=int(day_config['start']), 
                                   minute=int((day_config['start'] % 1) * 60), second=0)
        day_end = current.replace(hour=int(day_config['end']), 
                                 minute=int((day_config['end'] % 1) * 60), second=0)
        break_start = current.replace(hour=int(WORK_HOURS.get('break_start', 12)), 
                                     minute=int((WORK_HOURS.get('break_start', 12) % 1) * 60), second=0)
        break_end = current.replace(hour=int(WORK_HOURS.get('break_end', 12.5)), 
                                   minute=int((WORK_HOURS.get('break_end', 12.5) % 1) * 60), second=0)
        
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

# User and Team Utilization Metrics API
@app.route('/api/utilization/user/<user>', methods=['GET'])
def get_user_utilization(user):
    """Calculate user utilization rate using unified work hours and holiday system"""
    try:
        # Get date filter parameters
        days = request.args.get('days', 30, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Calculate date range
        if start_date and end_date:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        else:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=days)
        
        conn = get_db()
        c = conn.cursor()
        
        # Get user's session time for the period
        c.execute("""
            SELECT 
                SUM(COALESCE(work_duration_minutes, 0)) as total_session_minutes,
                COUNT(*) as session_count,
                COUNT(DISTINCT DATE(start_time)) as active_days
            FROM sessions 
            WHERE user = ? 
            AND start_time >= ? 
            AND start_time <= ?
            AND status = 'completed'
        """, (user, start_dt.isoformat(), end_dt.isoformat()))
        
        session_data = c.fetchone()
        session_minutes = session_data[0] or 0
        session_count = session_data[1] or 0
        active_days = session_data[2] or 0
        
        # Calculate total scheduled work hours for this user during the period
        # Excluding weekends and holidays
        scheduled_work_minutes = calculate_work_minutes(start_dt, end_dt)
        
        # Calculate utilization rate
        utilization_rate = 0
        if scheduled_work_minutes > 0:
            utilization_rate = (session_minutes / scheduled_work_minutes) * 100
        
        # Get additional metrics
        avg_session_minutes = session_minutes / session_count if session_count > 0 else 0
        avg_daily_minutes = session_minutes / active_days if active_days > 0 else 0
        
        return jsonify({
            'success': True,
            'user': user,
            'period': {
                'start_date': start_dt.strftime('%Y-%m-%d'),
                'end_date': end_dt.strftime('%Y-%m-%d'),
                'days': (end_dt - start_dt).days
            },
            'utilization': {
                'rate_percentage': round(utilization_rate, 2),
                'session_hours': round(session_minutes / 60, 2),
                'scheduled_hours': round(scheduled_work_minutes / 60, 2),
                'session_count': session_count,
                'active_days': active_days,
                'avg_session_hours': round(avg_session_minutes / 60, 2),
                'avg_daily_hours': round(avg_daily_minutes / 60, 2)
            }
        })
        
    except Exception as e:
        logging.error(f"Error calculating user utilization: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/utilization/team', methods=['GET'])
def get_team_utilization():
    """Calculate team utilization rates using unified work hours and holiday system"""
    try:
        # Get date filter parameters (consistent with other statistics endpoints)
        period_type = request.args.get('period_type', 'days')
        period = request.args.get('period', '30')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        days = request.args.get('days', type=int)  # Legacy support
        
        # Calculate date range
        if period_type == 'custom' and start_date and end_date:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        elif period_type == 'all':
            # For "all" period, use a very wide range (e.g., last 365 days)
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=365)
        else:
            # Use period parameter (sent by frontend) or legacy days parameter
            period_days = days if days is not None else int(period)
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=period_days)
        
        conn = get_db()
        c = conn.cursor()
        
        # Get configured users
        configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])

        if not configured_users:
            return jsonify({'success': False, 'error': 'No configured users found'}), 400

        # Get team session data
        user_placeholders = ','.join(['?' for _ in configured_users])
        c.execute(f"""
            SELECT 
                user,
                SUM(COALESCE(work_duration_minutes, 0)) as total_session_minutes,
                COUNT(*) as session_count,
                COUNT(DISTINCT DATE(start_time)) as active_days
            FROM sessions 
            WHERE user IN ({user_placeholders})
            AND start_time >= ? 
            AND start_time <= ?
            AND status = 'completed'
            GROUP BY user
        """, configured_users + [start_dt.isoformat(), end_dt.isoformat()])
        
        user_data = {}
        total_session_minutes = 0
        total_sessions = 0
        total_active_days = 0
        
        for row in c.fetchall():
            user = row[0]
            session_minutes = row[1] or 0
            session_count = row[2] or 0
            active_days = row[3] or 0
            
            total_session_minutes += session_minutes
            total_sessions += session_count
            total_active_days += active_days
            
            user_data[user] = {
                'session_minutes': session_minutes,
                'session_count': session_count,
                'active_days': active_days
            }
        
        # Calculate total scheduled work time for the team
        scheduled_work_minutes_per_user = calculate_work_minutes(start_dt, end_dt)
        total_scheduled_minutes = scheduled_work_minutes_per_user * len(configured_users)
        
        # Calculate team utilization
        team_utilization_rate = 0
        if total_scheduled_minutes > 0:
            team_utilization_rate = (total_session_minutes / total_scheduled_minutes) * 100
        
        # Calculate individual user utilizations
        user_utilizations = []
        for user in configured_users:
            if user in user_data:
                data = user_data[user]
                user_utilization = 0
                if scheduled_work_minutes_per_user > 0:
                    user_utilization = (data['session_minutes'] / scheduled_work_minutes_per_user) * 100
                
                user_utilizations.append({
                    'user': user,
                    'utilization_rate': round(user_utilization, 2),
                    'session_hours': round(data['session_minutes'] / 60, 2),
                    'scheduled_hours': round(scheduled_work_minutes_per_user / 60, 2),
                    'session_count': data['session_count'],
                    'active_days': data['active_days']
                })
            else:
                # User had no sessions
                user_utilizations.append({
                    'user': user,
                    'utilization_rate': 0,
                    'session_hours': 0,
                    'scheduled_hours': round(scheduled_work_minutes_per_user / 60, 2),
                    'session_count': 0,
                    'active_days': 0
                })
        
        # Sort by utilization rate
        user_utilizations.sort(key=lambda x: x['utilization_rate'], reverse=True)
        
        # Calculate additional team metrics
        avg_user_utilization = sum(u['utilization_rate'] for u in user_utilizations) / len(user_utilizations)
        active_users = len([u for u in user_utilizations if u['session_count'] > 0])
        
        return jsonify({
            'success': True,
            'period': {
                'start_date': start_dt.strftime('%Y-%m-%d'),
                'end_date': end_dt.strftime('%Y-%m-%d'),
                'days': (end_dt - start_dt).days
            },
            'team_metrics': {
                'team_utilization_rate': round(team_utilization_rate, 2),
                'total_session_hours': round(total_session_minutes / 60, 2),
                'total_scheduled_hours': round(total_scheduled_minutes / 60, 2),
                'total_sessions': total_sessions,
                'active_users': active_users,
                'total_users': len(configured_users),
                'avg_user_utilization': round(avg_user_utilization, 2)
            },
            'user_utilizations': user_utilizations
        })
        
    except Exception as e:
        logging.error(f"Error calculating team utilization: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/utilization/trends', methods=['GET'])
def get_utilization_trends():
    """Get utilization trends over time for team analysis"""
    try:
        # Get date filter parameters
        days = request.args.get('days', 30, type=int)
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
        
        conn = get_db()
        c = conn.cursor()
        
        # Get configured users
        configured_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])

        if not configured_users:
            return jsonify({'success': False, 'error': 'No configured users found'}), 400

        # Get daily utilization data
        user_placeholders = ','.join(['?' for _ in configured_users])
        c.execute(f"""
            SELECT 
                DATE(start_time) as date,
                user,
                SUM(COALESCE(work_duration_minutes, 0)) as daily_session_minutes
            FROM sessions 
            WHERE user IN ({user_placeholders})
            AND start_time >= ? 
            AND start_time <= ?
            AND status = 'completed'
            GROUP BY DATE(start_time), user
            ORDER BY date, user
        """, configured_users + [start_dt.isoformat(), end_dt.isoformat()])
        
        daily_data = {}
        for row in c.fetchall():
            date = row[0]
            user = row[1]
            session_minutes = row[2] or 0
            
            if date not in daily_data:
                daily_data[date] = {}
            daily_data[date][user] = session_minutes
        
        # Calculate daily utilization rates
        utilization_trends = []
        current_date = start_dt.date()
        end_date = end_dt.date()
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Calculate scheduled work minutes for this specific day
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())
            daily_scheduled_minutes = calculate_work_minutes(day_start, day_end)
            
            if daily_scheduled_minutes > 0:  # Only include work days
                daily_session_minutes = 0
                user_count = 0
                
                for user in configured_users:
                    if date_str in daily_data and user in daily_data[date_str]:
                        daily_session_minutes += daily_data[date_str][user]
                        user_count += 1
                
                total_scheduled_minutes = daily_scheduled_minutes * len(configured_users)
                daily_utilization = (daily_session_minutes / total_scheduled_minutes * 100) if total_scheduled_minutes > 0 else 0
                
                utilization_trends.append({
                    'date': date_str,
                    'utilization_rate': round(daily_utilization, 2),
                    'session_hours': round(daily_session_minutes / 60, 2),
                    'scheduled_hours': round(total_scheduled_minutes / 60, 2),
                    'active_users': user_count
                })
            
            current_date += timedelta(days=1)
        
        return jsonify({
            'success': True,
            'period': {
                'start_date': start_dt.strftime('%Y-%m-%d'),
                'end_date': end_dt.strftime('%Y-%m-%d'),
                'days': days
            },
            'trends': utilization_trends
        })
        
    except Exception as e:
        logging.error(f"Error calculating utilization trends: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        date_filter_with_alias = ""  # For queries using 'l' alias
        params = []
        
        if period_type == 'custom' and start_date and end_date:
            date_filter = " AND timestamp BETWEEN ? AND ?"
            date_filter_with_alias = " AND l.timestamp BETWEEN ? AND ?"
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
            date_filter = " AND timestamp >= datetime('now', '-{} days')".format(period_int)
            date_filter_with_alias = " AND l.timestamp >= datetime('now', '-{} days')".format(period_int)
        
        conn = get_db()
        c = conn.cursor()
        
        # Overall quality metrics
        quality_query = f"""
            SELECT 
                COUNT(*) as total_items,
                COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) as rework_items,
                COUNT(CASE WHEN l.is_rep_variant = 0 THEN 1 END) as normal_items,
                ROUND((COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)), 2) as defect_rate
            FROM logs l
            WHERE l.event = 'AFGEMELD' {date_filter_with_alias}
        """
        
        c.execute(quality_query, params)
        overall_metrics = c.fetchone()
        
        # Quality metrics by user
        user_quality_query = f"""
            SELECT 
                l.user,
                COUNT(*) as total_items,
                COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) as rework_items,
                ROUND((COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)), 2) as defect_rate,
                ROUND(AVG(CASE WHEN l.is_rep_variant = 0 THEN 
                    (julianday(l.timestamp) - julianday(
                        (SELECT MIN(l2.timestamp) FROM logs l2 WHERE l2.project = l.project AND l2.user = l.user AND l2.event = 'OPEN')
                    )) * 24 * 60 END), 2) as avg_normal_minutes,
                ROUND(AVG(CASE WHEN l.is_rep_variant = 1 THEN 
                    (julianday(l.timestamp) - julianday(
                        (SELECT MIN(l2.timestamp) FROM logs l2 WHERE l2.project = l.project AND l2.user = l.user AND l2.event = 'OPEN')
                    )) * 24 * 60 END), 2) as avg_rework_minutes
            FROM logs l
            WHERE l.event = 'AFGEMELD' {date_filter_with_alias}
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
                ROUND((COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)), 2) as defect_rate
            FROM logs l
            WHERE l.event = 'AFGEMELD' {date_filter_with_alias}
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
                ROUND((COUNT(CASE WHEN l.is_rep_variant = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)), 2) as defect_rate
            FROM logs l
            WHERE l.event = 'AFGEMELD' {date_filter_with_alias}
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
                'quality_rate': round(100 - ((overall_metrics['defect_rate'] or 0) if overall_metrics else 0), 2)
            },
            'user_metrics': [
                {
                    'user': row['user'],
                    'total_items': row['total_items'],
                    'rework_items': row['rework_items'],
                    'defect_rate': row['defect_rate'],
                    'quality_rate': round(100 - (row['defect_rate'] or 0), 2),
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
                    'quality_rate': round(100 - (row['defect_rate'] or 0), 2)
                } for row in quality_trends
            ],
            'product_metrics': [
                {
                    'product_type': row['product_type'],
                    'total_items': row['total_items'],
                    'rework_items': row['rework_items'],
                    'defect_rate': row['defect_rate'],
                    'quality_rate': round(100 - (row['defect_rate'] or 0), 2)
                } for row in product_metrics
            ]
        }
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"Error getting quality metrics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/statistics/project-time-analysis', methods=['GET'])
def get_project_time_analysis():
    """
    Get project-level time analysis using v2 calculation method (work hours only).
    This uses get_project_time_metrics_v2_internal() for accurate project time calculation
    that respects work hours, excludes weekends/holidays, and handles batch sessions properly.
    """
    try:
        # Get date filtering parameters
        period_type = request.args.get('period_type', 'days')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period = request.args.get('period', '30')

        # Build date filter for logs table
        logs_date_filter = ""
        params = []

        if period_type == 'custom' and start_date and end_date:
            logs_date_filter = " AND timestamp BETWEEN ? AND ?"
            params.extend([start_date + ' 00:00:00', end_date + ' 23:59:59'])
        elif period_type == 'all':
            pass  # No date filter
        else:
            period_int = int(period)
            logs_date_filter = f" AND timestamp >= datetime('now', '-{period_int} days')"

        conn = get_db()
        c = conn.cursor()

        # Get all projects that STARTED in the filtered period (based on first log entry)
        # This gives a clear view: "Projects that started in this date range"
        if period_type == 'custom' and start_date and end_date:
            c.execute("""
                SELECT project, MIN(timestamp) as start_time
                FROM logs
                WHERE project IS NOT NULL AND project != ''
                GROUP BY project
                HAVING DATE(MIN(timestamp)) BETWEEN ? AND ?
                ORDER BY start_time DESC
            """, [start_date, end_date])
        elif period_type == 'all':
            c.execute("""
                SELECT project, MIN(timestamp) as start_time
                FROM logs
                WHERE project IS NOT NULL AND project != ''
                GROUP BY project
                ORDER BY start_time DESC
            """)
        else:
            period_int = int(period)
            c.execute("""
                SELECT project, MIN(timestamp) as start_time
                FROM logs
                WHERE project IS NOT NULL AND project != ''
                GROUP BY project
                HAVING MIN(timestamp) >= datetime('now', '-? days')
                ORDER BY start_time DESC
            """, [period_int])

        projects = [row['project'] for row in c.fetchall()]

        logging.info(f"Found {len(projects)} projects that STARTED in period {period_type}")

        # Calculate metrics for each project using v2 method
        total_project_minutes = 0
        total_session_minutes = 0
        project_breakdown_data = []

        for project in projects:
            # Get v2 metrics for this project (work hours only)
            v2_result = get_project_time_metrics_v2_internal(project, conn)

            if not v2_result or not v2_result.get('success'):
                logging.warning(f"Failed to get v2 metrics for project {project}")
                continue

            project_minutes = v2_result.get('total_project_minutes', 0)
            if project_minutes <= 0:
                continue

            # Get session time for this project (already calculated correctly in sessions table)
            # Non-SCANNER sessions
            c.execute("""
                SELECT COALESCE(SUM(work_duration_minutes), 0) as non_scanner_minutes
                FROM sessions
                WHERE project = ?
                AND session_type != 'SCANNER'
            """, (project,))
            non_scanner_minutes = c.fetchone()['non_scanner_minutes'] or 0

            # SCANNER sessions (proportionally allocated)
            c.execute("""
                SELECT COALESCE(SUM(
                    CASE
                        WHEN (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) > 0 THEN
                            sp.item_count * 1.0 / (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) * s.work_duration_minutes
                        ELSE
                            s.work_duration_minutes / (SELECT COUNT(*) FROM session_projects WHERE session_id = s.session_id)
                    END
                ), 0) as scanner_minutes
                FROM session_projects sp
                JOIN sessions s ON s.session_id = sp.session_id
                WHERE sp.project = ?
                AND s.session_type = 'SCANNER'
            """, (project,))
            scanner_minutes = c.fetchone()['scanner_minutes'] or 0

            session_minutes = non_scanner_minutes + scanner_minutes
            idle_minutes = max(project_minutes - session_minutes, 0)
            efficiency = round((session_minutes * 100.0 / project_minutes), 1) if project_minutes > 0 else 0

            # Get additional project info
            c.execute("""
                SELECT
                    COALESCE(l.is_rep_variant, 0) as is_rep_variant,
                    DATE(l.timestamp) as start_date,
                    ps.status,
                    ps.total_items
                FROM logs l
                LEFT JOIN project_sessions ps ON ps.project = l.project
                WHERE l.project = ?
                AND l.event = 'OPEN'
                LIMIT 1
            """, (project,))

            project_info = c.fetchone()

            # Add to totals
            total_project_minutes += project_minutes
            total_session_minutes += session_minutes

            # Add to breakdown
            project_breakdown_data.append({
                'project': project,
                'project_hours': round(project_minutes / 60.0, 1),
                'session_hours': round(session_minutes / 60.0, 1),
                'idle_hours': round(idle_minutes / 60.0, 1),
                'efficiency_percentage': efficiency,
                'project_type': 'Rep' if project_info and project_info['is_rep_variant'] == 1 else 'Normal',
                'status': project_info['status'] if project_info else 'unknown',
                'total_items': project_info['total_items'] if project_info else 0,
                'start_date': project_info['start_date'] if project_info else None
            })

        # Calculate overall metrics
        total_idle_minutes = max(total_project_minutes - total_session_minutes, 0)
        overall_metrics = {
            'total_project_hours': round(total_project_minutes / 60.0, 1),
            'total_session_hours': round(total_session_minutes / 60.0, 1),
            'total_idle_hours': round(total_idle_minutes / 60.0, 1),
            'time_efficiency': round((total_session_minutes * 100.0 / total_project_minutes), 1) if total_project_minutes > 0 else 0
        }

        # Sort project breakdown by efficiency
        project_breakdown_data.sort(key=lambda x: x['efficiency_percentage'])

        # Efficiency trend - simplified for now (can be enhanced later)
        # For now, just return empty array as this would require recalculating for each date
        efficiency_trend = []

        conn.close()

        logging.info(f"Statistics calculated: {overall_metrics['total_project_hours']}h project time, {overall_metrics['total_session_hours']}h session time")

        return jsonify({
            'success': True,
            'calculation_method': 'v2 (work hours only)',
            'overall_metrics': overall_metrics,
            'project_breakdown': project_breakdown_data,
            'efficiency_trend': efficiency_trend
        })

    except Exception as e:
        logging.error(f"Error getting project time analysis: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/statistics/quality-control', methods=['GET'])
def get_quality_control():
    """
    Get rep/rework project metrics using v2 calculation (work hours only).
    Focuses exclusively on rep_variant projects: count, items, work time, and project time.
    """
    try:
        # Get date filtering parameters
        period_type = request.args.get('period_type', 'days')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period = request.args.get('period', '30')

        # Build date filter for logs table
        logs_date_filter = ""
        params = []

        if period_type == 'custom' and start_date and end_date:
            logs_date_filter = " AND timestamp BETWEEN ? AND ?"
            params.extend([start_date + ' 00:00:00', end_date + ' 23:59:59'])
        elif period_type == 'all':
            pass  # No date filter
        else:
            period_int = int(period)
            logs_date_filter = f" AND timestamp >= datetime('now', '-{period_int} days')"

        conn = get_db()
        c = conn.cursor()

        # Check if is_rep_variant column exists
        try:
            c.execute("PRAGMA table_info(logs)")
            columns = [column[1] for column in c.fetchall()]
            if 'is_rep_variant' not in columns:
                c.execute('ALTER TABLE logs ADD COLUMN is_rep_variant INTEGER DEFAULT 0')
                logging.info("Added 'is_rep_variant' column to logs table.")
                conn.commit()
        except Exception as e:
            logging.error(f"Error checking/adding is_rep_variant column: {e}")

        # Get all rep projects that had ANY activity in the filtered period
        if period_type == 'custom' and start_date and end_date:
            c.execute("""
                SELECT DISTINCT l.project, MIN(l.timestamp) as start_time
                FROM logs l
                WHERE l.is_rep_variant = 1
                AND l.project IS NOT NULL AND l.project != ''
                AND DATE(l.timestamp) BETWEEN ? AND ?
                GROUP BY l.project
                ORDER BY start_time DESC
            """, [start_date, end_date])
        elif period_type == 'all':
            c.execute("""
                SELECT DISTINCT l.project, MIN(l.timestamp) as start_time
                FROM logs l
                WHERE l.is_rep_variant = 1
                AND l.project IS NOT NULL AND l.project != ''
                GROUP BY l.project
                ORDER BY start_time DESC
            """)
        else:
            period_int = int(period)
            c.execute(f"""
                SELECT DISTINCT l.project, MIN(l.timestamp) as start_time
                FROM logs l
                WHERE l.is_rep_variant = 1
                AND l.project IS NOT NULL AND l.project != ''
                AND l.timestamp >= datetime('now', '-{period_int} days')
                GROUP BY l.project
                ORDER BY start_time DESC
            """)

        rep_projects_list = [row['project'] for row in c.fetchall()]

        logging.info(f"Found {len(rep_projects_list)} rep projects that STARTED in period {period_type}")

        # Calculate metrics for each rep project using v2 method
        total_rep_project_minutes = 0
        total_rep_session_minutes = 0
        total_rep_items = 0
        rep_project_details = []

        for project in rep_projects_list:
            # Get v2 metrics for this rep project (work hours only)
            v2_result = get_project_time_metrics_v2_internal(project, conn)

            if not v2_result or not v2_result.get('success'):
                logging.warning(f"Failed to get v2 metrics for rep project {project}")
                continue

            project_minutes = v2_result.get('total_project_minutes', 0)
            if project_minutes <= 0:
                continue

            # Get session time for this rep project
            # Non-SCANNER sessions
            c.execute("""
                SELECT COALESCE(SUM(work_duration_minutes), 0) as non_scanner_minutes
                FROM sessions
                WHERE project = ?
                AND session_type != 'SCANNER'
            """, (project,))
            non_scanner_minutes = c.fetchone()['non_scanner_minutes'] or 0

            # SCANNER sessions (proportionally allocated)
            c.execute("""
                SELECT COALESCE(SUM(
                    CASE
                        WHEN (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) > 0 THEN
                            sp.item_count * 1.0 / (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) * s.work_duration_minutes
                        ELSE
                            s.work_duration_minutes / (SELECT COUNT(*) FROM session_projects WHERE session_id = s.session_id)
                    END
                ), 0) as scanner_minutes
                FROM session_projects sp
                JOIN sessions s ON s.session_id = sp.session_id
                WHERE sp.project = ?
                AND s.session_type = 'SCANNER'
            """, (project,))
            scanner_minutes = c.fetchone()['scanner_minutes'] or 0

            session_minutes = non_scanner_minutes + scanner_minutes

            # Get item count and status
            c.execute("""
                SELECT
                    ps.status,
                    ps.total_items
                FROM project_sessions ps
                WHERE ps.project = ?
                LIMIT 1
            """, (project,))

            project_info = c.fetchone()
            items = project_info['total_items'] if project_info else 0
            status = project_info['status'] if project_info else 'unknown'

            # Add to totals
            total_rep_project_minutes += project_minutes
            total_rep_session_minutes += session_minutes
            total_rep_items += items or 0

            # Add to details list
            rep_project_details.append({
                'project': project,
                'project_hours': round(project_minutes / 60.0, 1),
                'work_hours': round(session_minutes / 60.0, 1),
                'items': items or 0,
                'status': status
            })

        # Sort by project time (most time first)
        rep_project_details.sort(key=lambda x: x['project_hours'], reverse=True)

        # Overall metrics for rep projects only
        overall_metrics = {
            'total_rep_projects': len(rep_projects_list),
            'total_rep_items': total_rep_items,
            'total_rep_project_hours': round(total_rep_project_minutes / 60.0, 1),
            'total_rep_work_hours': round(total_rep_session_minutes / 60.0, 1),
            'average_hours_per_rep_project': round((total_rep_project_minutes / 60.0) / len(rep_projects_list), 1) if len(rep_projects_list) > 0 else 0,
            'average_items_per_rep_project': round(total_rep_items / len(rep_projects_list), 1) if len(rep_projects_list) > 0 else 0
        }

        conn.close()

        logging.info(f"Rep projects calculated: {len(rep_projects_list)} projects, {total_rep_items} items, {overall_metrics['total_rep_project_hours']}h project time")

        return jsonify({
            'success': True,
            'calculation_method': 'v2 (work hours only)',
            'overall_metrics': overall_metrics,
            'rep_projects': rep_project_details
        })

    except Exception as e:
        logging.error(f"Error getting quality control metrics: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/statistics/project-completion-analysis', methods=['GET'])
def get_project_completion_analysis():
    """
    Get historical project completion data for estimation.
    Returns items vs time data for both total project time and active work time.
    Used to create scatter plots and calculate average time per item.
    """
    try:
        # Get period parameters
        period = request.args.get('period', '90')  # Default 90 days for better sample
        period_type = request.args.get('period_type', 'days')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        conn = get_db()
        c = conn.cursor()

        # Build date filter based on period type
        date_filter = ""
        if period_type == 'custom' and start_date and end_date:
            date_filter = f"AND DATE(ps.start_time) BETWEEN '{start_date}' AND '{end_date}'"
        elif period_type == 'all':
            date_filter = ""
        else:
            period_days = int(period) if period else 90
            date_filter = f"AND ps.start_time >= date('now', '-{period_days} days')"

        # Get completed projects with their items, total time, and work time
        c.execute(f"""
            WITH ProjectTotalTime AS (
                SELECT
                    ps.project,
                    ps.total_items as items,
                    ps.total_duration_minutes as total_minutes,
                    ROUND(ps.total_duration_minutes / 60.0, 2) as total_hours
                FROM project_sessions ps
                WHERE ps.status = 'completed'
                AND ps.total_items > 0
                AND ps.total_duration_minutes > 0
                {date_filter}
            ),
            ProjectWorkTime AS (
                SELECT
                    s.project,
                    SUM(s.work_duration_minutes) as work_minutes,
                    ROUND(SUM(s.work_duration_minutes) / 60.0, 2) as work_hours
                FROM sessions s
                WHERE s.status = 'completed'
                AND s.project IS NOT NULL
                AND s.work_duration_minutes > 0
                GROUP BY s.project
            )
            SELECT
                pt.project,
                pt.items,
                pt.total_minutes,
                pt.total_hours,
                COALESCE(pw.work_minutes, 0) as work_minutes,
                COALESCE(pw.work_hours, 0) as work_hours
            FROM ProjectTotalTime pt
            LEFT JOIN ProjectWorkTime pw ON pt.project = pw.project
            WHERE pt.items > 0
            ORDER BY pt.items ASC
        """)

        projects = []
        total_sum = 0
        work_sum = 0
        items_sum = 0

        for row in c.fetchall():
            project_data = {
                'project': row[0],
                'items': row[1],
                'total_minutes': row[2],
                'total_hours': row[3],
                'work_minutes': row[4],
                'work_hours': row[5]
            }
            projects.append(project_data)

            total_sum += row[2]
            work_sum += row[4]
            items_sum += row[1]

        # Calculate averages
        project_count = len(projects)

        if project_count > 0 and items_sum > 0:
            avg_total_min_per_item = total_sum / items_sum
            avg_work_min_per_item = work_sum / items_sum
            idle_percentage = ((total_sum - work_sum) / total_sum * 100) if total_sum > 0 else 0

            # Find best case (minimum time per item from all projects)
            best_time_per_item = min(p['total_minutes'] / p['items'] for p in projects) if projects else avg_total_min_per_item
        else:
            avg_total_min_per_item = 0
            avg_work_min_per_item = 0
            idle_percentage = 0
            best_time_per_item = 0

        averages = {
            'total_minutes_per_item': round(avg_total_min_per_item, 2),
            'work_minutes_per_item': round(avg_work_min_per_item, 2),
            'idle_percentage': round(idle_percentage, 1),
            'best_minutes_per_item': round(best_time_per_item, 2)
        }

        conn.close()

        return jsonify({
            'success': True,
            'projects': projects,
            'averages': averages,
            'project_count': project_count
        })

    except Exception as e:
        logging.error(f"Error getting project completion analysis: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

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

@app.route('/api/project/<project>/time-metrics', methods=['GET'])
def get_project_time_metrics(project):
    """Get accurate project time metrics using event logs and work hours constraints"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get all events for this project, sorted by timestamp
        c.execute("""
            SELECT timestamp, event, user FROM logs 
            WHERE LOWER(project) = LOWER(?) 
            AND event NOT IN ('AUTO_IMPORT', 'BACKGROUND_WORK_FOUND')
            ORDER BY timestamp ASC
        """, (project,))
        
        events = [dict(row) for row in c.fetchall()]
        
        if not events:
            return jsonify({
                'success': True,
                'project': project,
                'project_start_time': None,
                'project_end_time': None,
                'total_project_minutes': 0,
                'is_active': False
            })
        
        # Project start: first event from any user
        project_start_time = datetime.fromisoformat(events[0]['timestamp'])
        
        # Improved active project detection logic
        # Get the latest event for each user to determine their current status
        user_latest_events = {}
        for event in events:
            user = event['user']
            if user not in user_latest_events or event['timestamp'] > user_latest_events[user]['timestamp']:
                user_latest_events[user] = event
        
        # Check if any user is still active (has OPEN/BEZIG as their latest event)
        active_users = []
        completed_users = []
        
        for user, latest_event in user_latest_events.items():
            if latest_event['event'] in ['AFGEMELD', 'CLOSED']:
                completed_users.append(user)
            else:
                # User has OPEN, BEZIG, or other non-completion event as their latest
                active_users.append(user)
        
        # Project is active if there are any users still working
        is_active = len(active_users) > 0
        
        if is_active:
            # Project is still active - use current time as end
            project_end_time = datetime.now()
        else:
            # All users have completed - find the latest AFGEMELD event
            afgemeld_events = [e for e in events if e['event'] in ['AFGEMELD', 'CLOSED']]
            if afgemeld_events:
                last_afgemeld = max(afgemeld_events, key=lambda x: x['timestamp'])
                project_end_time = datetime.fromisoformat(last_afgemeld['timestamp'])
            else:
                # Fallback - shouldn't happen if logic is correct
                project_end_time = datetime.now()
        
        # Calculate total project time as:
        # 1. Proportional time from SCANNER batch sessions (if any)
        # 2. PLUS all individual XLSX_UPDATED session times
        
        total_project_minutes = 0
        
        # Get proportional time from SCANNER batch sessions
        c.execute("""
            SELECT SUM(total_duration_minutes) as scanner_minutes
            FROM project_sessions
            WHERE project = ?
        """, (project,))
        
        scanner_result = c.fetchone()
        if scanner_result and scanner_result['scanner_minutes']:
            total_project_minutes += scanner_result['scanner_minutes']
        
        # Add all XLSX_UPDATED individual session times (work + pause)
        c.execute("""
            SELECT SUM(work_duration_minutes + COALESCE(pause_duration_minutes, 0)) as xlsx_minutes
            FROM sessions
            WHERE project = ?
            AND session_type = 'XLSX_UPDATED'
        """, (project,))
        
        xlsx_result = c.fetchone()
        if xlsx_result and xlsx_result['xlsx_minutes']:
            total_project_minutes += xlsx_result['xlsx_minutes']
        
        return jsonify({
            'success': True,
            'project': project,
            'project_start_time': project_start_time.isoformat(),
            'project_end_time': project_end_time.isoformat(),
            'total_project_minutes': total_project_minutes,
            'is_active': is_active,
            'active_users': active_users,  # Debug info
            'completed_users': completed_users  # Debug info
        })
        
    except Exception as e:
        logging.error(f"Error getting project time metrics for {project}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

def get_project_time_metrics_v2_internal(project, conn=None):
    """
    Internal version of get_project_time_metrics_v2 that doesn't close the connection.
    Returns the metrics dict directly instead of a Flask response.
    """
    try:
        # Use provided connection or create a new one
        if conn is None:
            conn = get_db()
            should_close = True
        else:
            should_close = False
            
        c = conn.cursor()
        
        # Initialize response structure
        metrics = {
            'project': project,
            'calculation_version': 'v2',
            'success': True,
            'total_project_minutes': 0  # Initialize this
        }
        
        # Step 1: Calculate proportional batch time for SCANNER sessions
        c.execute("""
            SELECT 
                sp.session_id,
                sp.item_count as project_items,
                s.user,
                s.start_time,
                s.end_time,
                s.work_duration_minutes,
                s.pause_duration_minutes,
                (SELECT SUM(item_count) FROM session_projects WHERE session_id = sp.session_id) as total_batch_items
            FROM session_projects sp
            JOIN sessions s ON sp.session_id = s.session_id
            WHERE sp.project = ?
            AND s.session_type = 'SCANNER'
            AND s.status = 'completed'
            ORDER BY s.end_time DESC
            LIMIT 1
        """, (project,))
        
        batch_result = c.fetchone()
        batch_proportional_minutes = 0
        batch_end_time = None
        
        if batch_result and batch_result['total_batch_items'] and batch_result['project_items']:
            proportion = batch_result['project_items'] / batch_result['total_batch_items']
            work_minutes = batch_result['work_duration_minutes'] or 0
            pause_minutes = batch_result['pause_duration_minutes'] or 0
            batch_proportional_minutes = (work_minutes + pause_minutes) * proportion
            batch_end_time = batch_result['end_time']
            
            logging.info(f"Batch calculation for {project}: {batch_result['project_items']}/{batch_result['total_batch_items']} items = {proportion*100:.1f}% = {batch_proportional_minutes:.1f} min")
        else:
            logging.info(f"No batch sessions found for {project}")
        
        # Step 2: Get timeline from logs
        c.execute("""
            SELECT 
                MIN(timestamp) as first_event,
                MAX(timestamp) as last_event
            FROM logs
            WHERE project = ?
        """, (project,))
        
        timeline = c.fetchone()
        
        if not timeline or not timeline['first_event']:
            if should_close and conn:
                conn.close()
            return {
                'success': False,
                'error': 'No events found for project',
                'project': project,
                'total_project_minutes': 0
            }
        
        # Step 3: Calculate total project time (CRITICAL LOGIC)
        if batch_proportional_minutes > 0 and batch_end_time:
            # Project had batch processing
            # Add elapsed time from batch end to last event
            elapsed_minutes = calculate_work_minutes(batch_end_time, timeline['last_event'])
            total_project_minutes = batch_proportional_minutes + max(0, elapsed_minutes)
        else:
            # No batch processing, calculate from first to last event
            total_project_minutes = calculate_work_minutes(timeline['first_event'], timeline['last_event'])
        
        # Add detailed breakdown to metrics
        metrics.update({
            'total_project_minutes': round(total_project_minutes, 2),
            'batch_proportional_minutes': round(batch_proportional_minutes, 2),
            'batch_end_time': batch_end_time,
            'project_start_time': timeline['first_event'],
            'project_end_time': timeline['last_event']
        })
        
        if should_close and conn:
            conn.close()
            
        return metrics
        
    except Exception as e:
        logging.error(f"Error in internal time-metrics-v2 for project {project}: {e}", exc_info=True)
        if 'should_close' in locals() and should_close and conn:
            conn.close()
        return {
            'success': False,
            'error': str(e),
            'project': project,
            'total_project_minutes': 0
        }

@app.route('/api/project/<project>/time-metrics-v2', methods=['GET'])
def get_project_time_metrics_v2(project):
    """
    Correctly calculate project time metrics without relying on flawed project_sessions table.
    
    Calculation logic:
    1. For SCANNER batch sessions: Use proportional allocation based on item counts
    2. Add elapsed time from batch completion to last activity
    3. All calculations within work hours only
    """
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Initialize response structure
        metrics = {
            'project': project,
            'calculation_version': 'v2',
            'success': True
        }
        
        # Step 1: Calculate proportional batch time for SCANNER sessions
        c.execute("""
            SELECT 
                sp.session_id,
                sp.item_count as project_items,
                s.user,
                s.start_time,
                s.end_time,
                s.work_duration_minutes,
                s.pause_duration_minutes,
                (SELECT SUM(item_count) FROM session_projects WHERE session_id = sp.session_id) as total_batch_items
            FROM session_projects sp
            JOIN sessions s ON sp.session_id = s.session_id
            WHERE sp.project = ?
            AND s.session_type = 'SCANNER'
            AND s.status = 'completed'
            ORDER BY s.end_time DESC
            LIMIT 1
        """, (project,))
        
        batch_result = c.fetchone()
        batch_proportional_minutes = 0
        batch_end_time = None
        
        if batch_result and batch_result['total_batch_items'] and batch_result['project_items']:
            proportion = batch_result['project_items'] / batch_result['total_batch_items']
            work_minutes = batch_result['work_duration_minutes'] or 0
            pause_minutes = batch_result['pause_duration_minutes'] or 0
            batch_proportional_minutes = (work_minutes + pause_minutes) * proportion
            batch_end_time = batch_result['end_time']
            
            logging.info(f"Batch calculation for {project}: {batch_result['project_items']}/{batch_result['total_batch_items']} items = {proportion*100:.1f}% = {batch_proportional_minutes:.1f} min")
        
        # Step 2: Get timeline from logs
        c.execute("""
            SELECT 
                MIN(timestamp) as first_event,
                MAX(timestamp) as last_event
            FROM logs
            WHERE project = ?
        """, (project,))
        
        timeline = c.fetchone()
        
        if not timeline or not timeline['first_event']:
            return jsonify({
                'success': False,
                'error': 'No events found for project',
                'project': project
            }), 404
        
        # Step 3: Calculate total project time
        if batch_proportional_minutes > 0 and batch_end_time:
            # Project had batch processing
            # Add elapsed time from batch end to last event
            elapsed_minutes = calculate_work_minutes(batch_end_time, timeline['last_event'])
            total_project_minutes = batch_proportional_minutes + max(0, elapsed_minutes)
        else:
            # No batch processing, calculate from first to last event
            total_project_minutes = calculate_work_minutes(timeline['first_event'], timeline['last_event'])
        
        # Step 4: Get work time (already correct in your system)
        total_work_minutes = 0
        
        # Get proportional work from batch sessions
        if batch_result and batch_result['total_batch_items'] and batch_result['project_items']:
            proportion = batch_result['project_items'] / batch_result['total_batch_items']
            total_work_minutes += (batch_result['work_duration_minutes'] or 0) * proportion
        
        # Add XLSX_UPDATED sessions
        c.execute("""
            SELECT SUM(work_duration_minutes) as xlsx_work
            FROM sessions
            WHERE project = ?
            AND session_type = 'XLSX_UPDATED'
            AND status = 'completed'
        """, (project,))
        
        xlsx_result = c.fetchone()
        if xlsx_result and xlsx_result['xlsx_work']:
            total_work_minutes += xlsx_result['xlsx_work']
        
        # Step 5: Calculate idle time breakdown
        total_idle_minutes = max(0, total_project_minutes - total_work_minutes)
        
        # Calculate pause minutes (proportional for batch, full for XLSX_UPDATED)
        pause_minutes = 0
        pauses_by_user = {}
        
        # Get proportional pause from batch session
        if batch_result and batch_result['total_batch_items'] and batch_result['project_items']:
            proportion = batch_result['project_items'] / batch_result['total_batch_items']
            batch_pause = (batch_result['pause_duration_minutes'] or 0) * proportion
            pause_minutes += batch_pause
            if batch_pause > 0:
                pauses_by_user[batch_result['user']] = batch_pause
        
        # Add pauses from XLSX_UPDATED sessions
        c.execute("""
            SELECT user, SUM(pause_duration_minutes) as pause_mins
            FROM sessions
            WHERE project = ?
            AND session_type = 'XLSX_UPDATED'
            AND status = 'completed'
            AND pause_duration_minutes > 0
            GROUP BY user
        """, (project,))
        
        for row in c.fetchall():
            if row['pause_mins']:
                pause_minutes += row['pause_mins']
                if row['user'] in pauses_by_user:
                    pauses_by_user[row['user']] += row['pause_mins']
                else:
                    pauses_by_user[row['user']] = row['pause_mins']
        
        # Calculate handoff delays from logs
        handoff_minutes = 0
        handoff_details = {}
        
        c.execute("""
            SELECT user, timestamp, event
            FROM logs
            WHERE project = ?
            AND event IN ('AFGEMELD', 'OPEN', 'PROJECT_START')
            ORDER BY timestamp
        """, (project,))
        
        events = c.fetchall()
        last_afgemeld = None
        
        for event in events:
            if event['event'] == 'AFGEMELD':
                last_afgemeld = {'user': event['user'], 'time': event['timestamp']}
            elif event['event'] in ['OPEN', 'PROJECT_START'] and last_afgemeld and event['user'] != last_afgemeld['user']:
                # Calculate handoff delay
                delay_minutes = calculate_work_minutes(last_afgemeld['time'], event['timestamp'])
                if delay_minutes > 0:
                    handoff_key = f"{last_afgemeld['user']} → {event['user']}"
                    if handoff_key in handoff_details:
                        handoff_details[handoff_key] += delay_minutes
                    else:
                        handoff_details[handoff_key] = delay_minutes
                    handoff_minutes += delay_minutes
                    # Clear last_afgemeld after handoff is recorded to prevent double-counting
                    last_afgemeld = None
        
        # Step 6: Determine project status
        c.execute("""
            SELECT DISTINCT user, 
                   MAX(CASE WHEN event = 'AFGEMELD' THEN 1 ELSE 0 END) as has_afgemeld
            FROM logs
            WHERE project = ?
            GROUP BY user
        """, (project,))
        
        user_statuses = c.fetchall()
        active_users = []
        completed_users = []
        
        for status in user_statuses:
            if status['has_afgemeld']:
                completed_users.append(status['user'])
            else:
                active_users.append(status['user'])
        
        metrics.update({
            'total_project_minutes': round(total_project_minutes, 2),
            'total_work_minutes': round(total_work_minutes, 2),
            'total_idle_minutes': round(total_idle_minutes, 2),
            'project_start_time': timeline['first_event'],
            'project_end_time': timeline['last_event'],
            'is_active': len(active_users) > 0,
            'active_users': active_users,
            'completed_users': completed_users,
            'components': {
                'batch_proportional': {
                    'found_batch': batch_result is not None,
                    'proportional_total_minutes': round(batch_proportional_minutes, 2)
                },
                'elapsed_after_batch': round(total_project_minutes - batch_proportional_minutes, 2) if batch_proportional_minutes > 0 else 0,
                'timeline': {
                    'first_event_time': timeline['first_event'],
                    'last_event_time': timeline['last_event']
                },
                'idle_breakdown': {
                    'pause_minutes': round(pause_minutes, 2),
                    'pauses_by_user': {user: round(mins, 2) for user, mins in pauses_by_user.items()},
                    'handoff_minutes': round(handoff_minutes, 2),
                    'handoff_details': {key: round(mins, 2) for key, mins in handoff_details.items()},
                    'other_idle_minutes': round(max(0, total_idle_minutes - pause_minutes - handoff_minutes), 2),
                    'total_idle_for_verification': round(total_idle_minutes, 2)
                }
            }
        })
        
        return jsonify(metrics)
        
    except Exception as e:
        logging.error(f"Error in time-metrics-v2 for project {project}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'project': project
        }), 500
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
                    -- Check if this batch session processed this project via session_projects
                    SELECT 1 FROM session_projects sp
                    WHERE sp.session_id = s.session_id
                    AND sp.project = ?
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
                        # Check if this is a multi-project batch session
                        c.execute("""
                            SELECT COUNT(DISTINCT project) as project_count,
                                   SUM(item_count) as total_items
                            FROM session_projects
                            WHERE session_id = ?
                        """, (batch['session_id'],))
                        
                        batch_info = c.fetchone()
                        project_count = batch_info[0] if batch_info and batch_info[0] else 1
                        batch_total_items = batch_info[1] if batch_info and batch_info[1] else 0
                        
                        if project_count > 1 and batch_total_items > 0:
                            # Multi-project batch - use proportional allocation
                            # Get this project's items from session_projects
                            c.execute("""
                                SELECT item_count FROM session_projects
                                WHERE session_id = ? AND project = ?
                            """, (batch['session_id'], project))
                            
                            sp_result = c.fetchone()
                            if sp_result and sp_result[0]:
                                project_items_in_batch = sp_result[0]
                                proportion = project_items_in_batch / batch_total_items
                                allocated_minutes = batch['work_duration_minutes'] * proportion
                                total_duration_minutes += allocated_minutes
                            else:
                                # Project not found in session_projects - shouldn't happen for valid data
                                # Use full time as fallback (conservative approach)
                                total_duration_minutes += batch['work_duration_minutes']
                        else:
                            # Single project batch - use full time
                            total_duration_minutes += batch['work_duration_minutes']
            
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
            
            # Check for AFGEMELD status - this overrides other status checks
            c.execute("""
                SELECT event FROM logs 
                WHERE user = ? AND LOWER(project) = LOWER(?) 
                AND event IN ('AFGEMELD', 'CLOSED')
                ORDER BY timestamp DESC
                LIMIT 1
            """, (user, project))
            
            afgemeld_check = c.fetchone()
            
            # Check for active XLSX_UPDATED sessions specifically
            has_active_xlsx_session = False
            for session in individual_sessions:
                if session['status'] == 'active' and session['session_type'] == 'XLSX_UPDATED':
                    has_active_xlsx_session = True
                    break
            
            # Determine status: show user if they have OPEN event, but only show data if they have work sessions
            if afgemeld_check:
                # User has manually set status to AFGEMELD
                # But check if they have an active SCANNER session for THIS project
                if active_batch and user in ['NESTING']:  # SCANNER batch users
                    # Check if this batch is actually processing THIS project
                    c.execute("""
                        SELECT COUNT(*) FROM logs 
                        WHERE user = ? AND LOWER(project) = LOWER(?) 
                        AND timestamp >= ?
                        AND event IN ('OPEN', 'BEZIG')
                    """, (user, project, active_batch[1]))  # active_batch[1] is start_time
                    
                    has_recent_activity = c.fetchone()[0] > 0
                    
                    if has_recent_activity:
                        # NESTING with active SCANNER session for THIS project continues after AFGEMELD
                        status = 'IN_PROGRESS'
                    else:
                        # Active batch but not for this project - show as COMPLETED
                        status = 'COMPLETED'
                else:
                    # Other users or no active batch - show as COMPLETED
                    status = 'COMPLETED'
            elif has_active_xlsx_session:
                # User has active XLSX_UPDATED session for this project - show as IN_PROGRESS
                status = 'IN_PROGRESS'
            elif individual_sessions:
                # User has individual work (XLSX_UPDATED/MANUAL) for this project - always COMPLETED
                status = 'COMPLETED'
            elif completed_batches:
                # User has completed batch work for this project (SCANNER user only)
                status = 'COMPLETED'  
            elif active_batch:
                # User has active batch session (SCANNER type like NESTING)
                # Check if this batch is actually processing THIS project
                # by looking for recent logs during the current batch session
                c.execute("""
                    SELECT COUNT(*) FROM logs 
                    WHERE user = ? AND LOWER(project) = LOWER(?) 
                    AND timestamp >= ?
                    AND event IN ('OPEN', 'BEZIG')
                """, (user, project, active_batch[1]))  # active_batch[1] is start_time
                
                has_recent_activity = c.fetchone()[0] > 0
                
                if has_recent_activity:
                    # This batch is actively processing THIS project
                    status = 'IN_PROGRESS'
                else:
                    # This batch is not processing this project - check if project is completed
                    c.execute("""
                        SELECT COUNT(*) FROM logs 
                        WHERE user = ? AND LOWER(project) = LOWER(?) 
                        AND event = 'OPEN'
                    """, (user, project))
                    
                    has_open_event = c.fetchone()[0] > 0
                    if has_open_event:
                        # User has worked on this project before, but not in current batch
                        status = 'COMPLETED'
                    else:
                        status = 'WAITING'
            else:
                # User has OPEN event but no work sessions yet - show as WAITING but keep item count
                status = 'WAITING'
                # Keep total_items from project_items (don't reset to 0)
                total_duration_minutes = 0
                manual_items = 0
                auto_items = 0
            
            # Calculate productivity
            if status == 'WAITING':
                # User has OPEN event but no work sessions - show blank
                items_per_hour = '--'
                session_hours = '--'
            elif status == 'IN_PROGRESS' and active_batch:
                # For active batch sessions (SCANNER type), calculate elapsed time with proportional allocation
                from datetime import datetime
                start_time = datetime.fromisoformat(active_batch[1])  # active_batch[1] is start_time
                current_time = datetime.now()
                elapsed_minutes = int((current_time - start_time).total_seconds() / 60)
                
                # Check if this is a multi-project batch session
                c.execute("""
                    SELECT COUNT(DISTINCT project) as project_count,
                           SUM(item_count) as total_items
                    FROM session_projects
                    WHERE session_id = ?
                """, (active_batch[0],))  # active_batch[0] is session_id
                
                batch_info = c.fetchone()
                project_count = batch_info[0] if batch_info and batch_info[0] else 1
                batch_total_items = batch_info[1] if batch_info and batch_info[1] else 0
                
                if project_count > 1 and batch_total_items > 0:
                    # Multi-project batch - use proportional allocation for elapsed time
                    c.execute("""
                        SELECT item_count FROM session_projects
                        WHERE session_id = ? AND project = ?
                    """, (active_batch[0], project))
                    
                    sp_result = c.fetchone()
                    if sp_result and sp_result[0]:
                        project_items_in_batch = sp_result[0]
                        proportion = project_items_in_batch / batch_total_items
                        allocated_elapsed_minutes = elapsed_minutes * proportion
                        total_work_minutes = total_duration_minutes + allocated_elapsed_minutes
                    else:
                        # Project not found in session_projects - use full time as fallback
                        total_work_minutes = total_duration_minutes + elapsed_minutes
                else:
                    # Single project batch - use full elapsed time
                    total_work_minutes = total_duration_minutes + elapsed_minutes
                
                if total_work_minutes > 0:
                    if total_items > 0:
                        items_per_hour = round((total_items * 60.0) / total_work_minutes, 2)
                    else:
                        items_per_hour = 'IN_PROGRESS'
                    session_hours = round(total_work_minutes / 60.0, 2)  # Return actual elapsed time
                else:
                    items_per_hour = 'IN_PROGRESS'
                    session_hours = 0
            elif status == 'IN_PROGRESS' and has_active_xlsx_session:
                # For active XLSX_UPDATED sessions, calculate elapsed time including active sessions
                from datetime import datetime
                active_work_minutes = 0
                
                # Calculate time for all active XLSX_UPDATED sessions
                c.execute("""
                    SELECT start_time, item_count
                    FROM sessions 
                    WHERE user = ? AND LOWER(project) = LOWER(?)
                    AND session_type = 'XLSX_UPDATED'
                    AND status = 'active'
                """, (user, project))
                
                active_sessions = c.fetchall()
                for active_session in active_sessions:
                    start_time = datetime.fromisoformat(active_session['start_time'])
                    current_time = datetime.now()
                    work_minutes = calculate_work_minutes(active_session['start_time'], current_time.isoformat())
                    active_work_minutes += work_minutes
                
                # Add completed session time
                total_work_minutes = total_duration_minutes + active_work_minutes
                
                if total_work_minutes > 0 and total_items > 0:
                    items_per_hour = round((total_items * 60.0) / total_work_minutes, 2)
                    session_hours = round(total_work_minutes / 60.0, 2)
                else:
                    items_per_hour = 'IN_PROGRESS'
                    session_hours = 'IN_PROGRESS'
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
                scanner_users = get_setting_from_db('scanner_panel_open_event_users', fallback_to_config=True, default_value=[])
                dashboard_users = get_setting_from_db('dashboard_display_users', fallback_to_config=True, default_value=[])
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
        valid_processing_types = [
            'GEEN_PROCESSING',
            'HOPS_PROCESSING',
            'MDB_PROCESSING',
            'NESTING_PROCESSING',
            'ACCURA_PROCESSING',
            'BOERE_PROCESSING',
            'MASSIEF_PROCESSING',
            'HANDWERK_PROCESSING',
            'AFWERKING_PROCESSING'
        ]
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


@app.route("/api/holidays/<int:holiday_id>", methods=["PUT"])
def update_holiday(holiday_id):
    """Update an existing holiday"""
    try:
        data = request.get_json()
        date = data.get("date")
        name = data.get("name")
        holiday_type = data.get("type", "holiday")
        is_recurring = data.get("is_recurring", False)
        
        if not date or not name:
            return jsonify({"success": False, "error": "date and name required"}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Check if holiday exists
        c.execute("SELECT id FROM holidays WHERE id = ?", (holiday_id,))
        if not c.fetchone():
            return jsonify({"success": False, "error": "Holiday not found"}), 404
        
        # Update the holiday
        c.execute("""
            UPDATE holidays 
            SET date = ?, name = ?, type = ?, is_recurring = ?
            WHERE id = ?
        """, (date, name, holiday_type, is_recurring, holiday_id))
        
        conn.commit()
        
        return jsonify({
            "success": True,
            "message": "Holiday updated successfully"
        })
        
    except Exception as e:
        logging.error(f"Error updating holiday: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/project/<project>/items-by-user', methods=['GET'])
def get_project_items_by_user(project):
    """
    Get total item counts by user for a specific project.
    Returns the sum of all item_count entries for each user.
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Normalize project name
        project_normalized = normalize_project_id(project)
        
        # Query to sum item counts per user for this project
        cursor.execute('''
            SELECT user, SUM(COALESCE(item_count, 0)) as total_items
            FROM logs
            WHERE project = ? OR project = ?
            GROUP BY user
            HAVING total_items > 0
            ORDER BY user
        ''', (project, project_normalized))
        
        rows = cursor.fetchall()
        
        # Build user_items dictionary
        user_items = {}
        for row in rows:
            user = row[0]
            total = row[1]
            if user and total > 0:
                user_items[user] = int(total)
        
        return jsonify({
            'success': True,
            'project': project,
            'user_items': user_items,
            'total_users': len(user_items),
            'total_items': sum(user_items.values())
        })
        
    except Exception as e:
        logging.error(f"Error getting project items by user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

