# app.py - Main Flask Application with Automatic Database Migration
import os
import json
import threading
import socket
import sqlite3
import shutil
import zipfile
import csv
import tempfile
from io import StringIO, BytesIO
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_file, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
import plotly.graph_objs as go
import plotly.utils
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
import re
from functools import wraps
from sqlalchemy import func, and_, or_, text
from sqlalchemy.exc import OperationalError

# Import our translation module
from translations import get_translation, setup_translations, get_available_languages

# Initialize Flask extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()

def check_and_migrate_database():
    """Check if database needs migration and perform it automatically"""
    db_path = 'file_monitor.db'
    
    if not os.path.exists(db_path):
        return True  # New database, will be created by SQLAlchemy
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if efficiency columns exist
        cursor.execute("PRAGMA table_info(weekly_work_hours)")
        columns = [column[1] for column in cursor.fetchall()]
        
        efficiency_high_exists = 'efficiency_high_threshold' in columns
        efficiency_medium_exists = 'efficiency_medium_threshold' in columns
        
        if not efficiency_high_exists or not efficiency_medium_exists:
            print("🔄 Database migration needed. Adding efficiency threshold columns...")
            
            if not efficiency_high_exists:
                cursor.execute("""
                    ALTER TABLE weekly_work_hours 
                    ADD COLUMN efficiency_high_threshold REAL DEFAULT 5.0
                """)
                print("✅ Added efficiency_high_threshold column")
            
            if not efficiency_medium_exists:
                cursor.execute("""
                    ALTER TABLE weekly_work_hours 
                    ADD COLUMN efficiency_medium_threshold REAL DEFAULT 2.0
                """)
                print("✅ Added efficiency_medium_threshold column")
            
            # Update existing records
            cursor.execute("""
                UPDATE weekly_work_hours 
                SET efficiency_high_threshold = COALESCE(efficiency_high_threshold, 5.0),
                    efficiency_medium_threshold = COALESCE(efficiency_medium_threshold, 2.0)
            """)
            
            conn.commit()
            print("✅ Database migration completed successfully!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        if 'conn' in locals():
            conn.close()
        return False

# Create Flask app with application factory pattern
def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///file_monitor.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'reports'
    app.config['LANGUAGES'] = get_available_languages()
    
    # Static files configuration
    app.static_folder = 'static'
    app.static_url_path = '/static'
    
    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Setup translations
    setup_translations(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    return app

# Create app instance
app = create_app()

# Add custom Jinja2 filters
@app.template_filter('basename')
def basename_filter(path):
    """Extract basename from file path"""
    return os.path.basename(path)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='operator')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)
    language = db.Column(db.String(2), default='en')
    
    events = db.relationship('Event', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    keywords = db.Column(db.Text)
    file_patterns = db.Column(db.Text)
    color = db.Column(db.String(7), default='#007bff')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    events = db.relationship('Event', backref='category', lazy='dynamic')
    
    def get_keywords(self):
        return json.loads(self.keywords) if self.keywords else []
    
    def get_patterns(self):
        return json.loads(self.file_patterns) if self.file_patterns else []

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    file_path = db.Column(db.String(500), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    matched_keyword = db.Column(db.String(100))
    computer_name = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    event_type = db.Column(db.String(20))
    file_size = db.Column(db.Integer)

class MonitoredPath(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_directory = db.Column(db.Boolean, default=False)
    recursive = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_modified = db.Column(db.DateTime)
    file_size = db.Column(db.Integer)
    change_count = db.Column(db.Integer, default=0)
    last_change_detected = db.Column(db.DateTime)
    
    user = db.relationship('User', backref='monitored_paths')
    __table_args__ = (db.UniqueConstraint('path', 'user_id', name='_path_user_uc'),)
    
    def increment_change_count(self):
        self.change_count = (self.change_count or 0) + 1
        self.last_change_detected = datetime.now(timezone.utc)

class FileChangeHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monitored_path_id = db.Column(db.Integer, db.ForeignKey('monitored_path.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    change_type = db.Column(db.String(20))
    old_size = db.Column(db.Integer)
    new_size = db.Column(db.Integer)
    old_modified = db.Column(db.DateTime)
    new_modified = db.Column(db.DateTime)
    
    monitored_path = db.relationship('MonitoredPath', backref='change_history')

class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    
    @staticmethod
    def get_setting(key, default=None):
        setting = SystemSettings.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def set_setting(key, value):
        setting = SystemSettings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = SystemSettings(key=key, value=value)
            db.session.add(setting)
        db.session.commit()

class WeeklyWorkHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    monday_hours = db.Column(db.Float, default=8.0)
    tuesday_hours = db.Column(db.Float, default=8.0)
    wednesday_hours = db.Column(db.Float, default=8.0)
    thursday_hours = db.Column(db.Float, default=8.0)
    friday_hours = db.Column(db.Float, default=8.0)
    saturday_hours = db.Column(db.Float, default=0.0)
    sunday_hours = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Efficiency configuration - configurable thresholds for efficiency calculation per user
    efficiency_high_threshold = db.Column(db.Float, default=5.0)  # events per hour for "high" efficiency
    efficiency_medium_threshold = db.Column(db.Float, default=2.0)  # events per hour for "medium" efficiency
    
    user = db.relationship('User', backref=db.backref('work_hours', uselist=False))
    
    def get_hours_for_day(self, day_number):
        """Get hours for a specific day (0=Monday, 6=Sunday)"""
        days = [
            self.monday_hours, self.tuesday_hours, self.wednesday_hours,
            self.thursday_hours, self.friday_hours, self.saturday_hours, self.sunday_hours
        ]
        return days[day_number] if 0 <= day_number <= 6 else 0.0
    
    def get_total_weekly_hours(self):
        """Get total hours for the week"""
        return (self.monday_hours + self.tuesday_hours + self.wednesday_hours + 
                self.thursday_hours + self.friday_hours + self.saturday_hours + self.sunday_hours)
    
    def get_working_days(self):
        """Get number of working days (days with > 0 hours)"""
        hours = [self.monday_hours, self.tuesday_hours, self.wednesday_hours,
                self.thursday_hours, self.friday_hours, self.saturday_hours, self.sunday_hours]
        return sum(1 for h in hours if h > 0)
    
    def get_average_daily_hours(self):
        """Get average hours per working day"""
        working_days = self.get_working_days()
        return self.get_total_weekly_hours() / working_days if working_days > 0 else 0.0
    
    def calculate_efficiency(self, events_per_hour):
        """Calculate efficiency level based on events per hour and configurable thresholds"""
        # Use default values if attributes don't exist (backward compatibility)
        high_threshold = getattr(self, 'efficiency_high_threshold', 5.0) or 5.0
        medium_threshold = getattr(self, 'efficiency_medium_threshold', 2.0) or 2.0
        
        if events_per_hour >= high_threshold:
            return 'high'
        elif events_per_hour >= medium_threshold:
            return 'medium'
        else:
            return 'low'

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    format = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    file_path = db.Column(db.String(500))
    
    user = db.relationship('User', backref='reports')

class DatabaseBackup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # full, data_only, structure_only
    size_mb = db.Column(db.Float)
    note = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    created_by = db.relationship('User', backref='database_backups')

class ScheduledBackupSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, default=False)
    frequency = db.Column(db.String(20), default='daily')  # daily, weekly, monthly
    time = db.Column(db.String(5), default='02:00')  # HH:MM format
    retention_days = db.Column(db.Integer, default=30)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)

# Helper function to get user's work hours with error handling
def get_user_work_hours(user_id=None):
    """Get work hours for a user or create default if not exists"""
    if user_id is None:
        user_id = current_user.id if current_user.is_authenticated else None
    
    if user_id:
        try:
            work_hours = WeeklyWorkHours.query.filter_by(user_id=user_id).first()
            if not work_hours:
                # Create default work hours (Monday-Friday 8h, Weekend 0h)
                work_hours = WeeklyWorkHours(
                    user_id=user_id,
                    monday_hours=8.0,
                    tuesday_hours=8.0,
                    wednesday_hours=8.0,
                    thursday_hours=8.0,
                    friday_hours=8.0,
                    saturday_hours=0.0,
                    sunday_hours=0.0,
                    efficiency_high_threshold=5.0,
                    efficiency_medium_threshold=2.0
                )
                db.session.add(work_hours)
                db.session.commit()
            else:
                # Ensure efficiency thresholds exist (backward compatibility)
                if not hasattr(work_hours, 'efficiency_high_threshold') or work_hours.efficiency_high_threshold is None:
                    work_hours.efficiency_high_threshold = 5.0
                if not hasattr(work_hours, 'efficiency_medium_threshold') or work_hours.efficiency_medium_threshold is None:
                    work_hours.efficiency_medium_threshold = 2.0
                db.session.commit()
            
            return work_hours
        except OperationalError as e:
            if "no such column" in str(e):
                print("⚠️ Database schema outdated. Please run the migration script or restart the application.")
                # Return a basic work hours object with default efficiency calculation
                class BasicWorkHours:
                    def __init__(self):
                        self.monday_hours = 8.0
                        self.tuesday_hours = 8.0
                        self.wednesday_hours = 8.0
                        self.thursday_hours = 8.0
                        self.friday_hours = 8.0
                        self.saturday_hours = 0.0
                        self.sunday_hours = 0.0
                        self.efficiency_high_threshold = 5.0
                        self.efficiency_medium_threshold = 2.0
                    
                    def get_hours_for_day(self, day_number):
                        days = [self.monday_hours, self.tuesday_hours, self.wednesday_hours,
                               self.thursday_hours, self.friday_hours, self.saturday_hours, self.sunday_hours]
                        return days[day_number] if 0 <= day_number <= 6 else 0.0
                    
                    def get_total_weekly_hours(self):
                        return 40.0
                    
                    def get_working_days(self):
                        return 5
                    
                    def get_average_daily_hours(self):
                        return 8.0
                    
                    def calculate_efficiency(self, events_per_hour):
                        if events_per_hour >= 5.0:
                            return 'high'
                        elif events_per_hour >= 2.0:
                            return 'medium'
                        else:
                            return 'low'
                
                return BasicWorkHours()
            else:
                raise e
    return None

# Login Manager
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Role-based access decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash(get_translation('admin_required'), 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Enhanced File Monitor Handler with change tracking
class EnhancedFileMonitorHandler(FileSystemEventHandler):
    def __init__(self, app, user_id):
        self.app = app
        self.user_id = user_id
        self.seen_events = set()
        self.monitored_files = {}
        self.load_monitored_files()
        
    def load_monitored_files(self):
        with self.app.app_context():
            file_paths = MonitoredPath.query.filter_by(
                user_id=self.user_id, 
                is_active=True, 
                is_directory=False
            ).all()
            self.monitored_files = {fp.path: fp for fp in file_paths}
    
    def on_created(self, event):
        if not event.is_directory:
            self.process_event(event.src_path, 'created')
    
    def on_modified(self, event):
        if not event.is_directory:
            self.process_event(event.src_path, 'modified')
    
    def process_event(self, file_path, event_type):
        if self.monitored_files and file_path not in self.monitored_files:
            return
            
        try:
            event_key = f"{file_path}_{os.path.getmtime(file_path)}_{self.user_id}"
        except:
            return
            
        if event_key in self.seen_events:
            return
        self.seen_events.add(event_key)
        
        with self.app.app_context():
            try:
                if file_path in self.monitored_files:
                    self.update_file_tracking(file_path, event_type)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except:
                    content = ""
                
                categories = Category.query.all()
                for category in categories:
                    keywords = category.get_keywords()
                    patterns = category.get_patterns()
                    
                    file_name = os.path.basename(file_path)
                    pattern_match = any(re.match(pattern, file_name) for pattern in patterns)
                    
                    keyword_match = None
                    for keyword in keywords:
                        if keyword.lower() in content.lower():
                            keyword_match = keyword
                            break
                    
                    if pattern_match or keyword_match:
                        file_description = None
                        if file_path in self.monitored_files:
                            file_description = self.monitored_files[file_path].description
                        
                        event_path = file_path
                        if file_description:
                            event_path = f"{file_description} ({os.path.basename(file_path)})"
                        
                        event = Event(
                            file_path=event_path,
                            category_id=category.id,
                            matched_keyword=keyword_match,
                            computer_name=socket.gethostname(),
                            user_id=self.user_id,
                            event_type=event_type,
                            file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0
                        )
                        db.session.add(event)
                        db.session.commit()
                        break
                        
            except Exception as e:
                print(f"Error processing file {file_path}: {str(e)}")
    
    def update_file_tracking(self, file_path, event_type):
        try:
            monitored_file = self.monitored_files.get(file_path)
            if not monitored_file or not os.path.exists(file_path):
                return
                
            stat = os.stat(file_path)
            new_modified = datetime.fromtimestamp(stat.st_mtime)
            new_size = stat.st_size
            
            old_modified = monitored_file.last_modified
            old_size = monitored_file.file_size
            
            change_type = event_type
            if old_size is not None and old_size != new_size:
                change_type = 'size_change'
            
            monitored_file.last_modified = new_modified
            monitored_file.file_size = new_size
            monitored_file.increment_change_count()
            
            change_history = FileChangeHistory(
                monitored_path_id=monitored_file.id,
                change_type=change_type,
                old_size=old_size,
                new_size=new_size,
                old_modified=old_modified,
                new_modified=new_modified
            )
            db.session.add(change_history)
            db.session.commit()
            
        except Exception as e:
            print(f"Error updating file tracking for {file_path}: {str(e)}")

# Global file monitors
file_observers = {}

def start_file_monitor():
    global file_observers
    
    with app.app_context():
        paths = MonitoredPath.query.filter_by(is_active=True).all()
        
        user_paths = {}
        for path in paths:
            if path.user_id not in user_paths:
                user_paths[path.user_id] = {'directories': [], 'files': []}
            
            if path.is_directory:
                user_paths[path.user_id]['directories'].append(path)
            else:
                user_paths[path.user_id]['files'].append(path)
        
        for user_id, user_paths_dict in user_paths.items():
            if user_id in file_observers and file_observers[user_id].is_alive():
                continue
                
            observer = Observer()
            handler = EnhancedFileMonitorHandler(app, user_id)
            
            for directory in user_paths_dict['directories']:
                if os.path.exists(directory.path) and os.path.isdir(directory.path):
                    observer.schedule(handler, directory.path, recursive=directory.recursive)
            
            file_dirs = set()
            for file_path in user_paths_dict['files']:
                if os.path.exists(file_path.path) and os.path.isfile(file_path.path):
                    parent_dir = os.path.dirname(file_path.path)
                    file_dirs.add(parent_dir)
            
            for file_dir in file_dirs:
                if os.path.exists(file_dir):
                    observer.schedule(handler, file_dir, recursive=False)
            
            if len(user_paths_dict['directories']) > 0 or len(user_paths_dict['files']) > 0:
                observer.start()
                file_observers[user_id] = observer

def stop_file_monitor():
    global file_observers
    for user_id, observer in file_observers.items():
        if observer and observer.is_alive():
            observer.stop()
            observer.join()
    file_observers.clear()

# Create Blueprints
auth_bp = Blueprint('auth', __name__)
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Routes - Authentication Blueprint
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash(get_translation('invalid_credentials'), 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash(get_translation('logout_success'), 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        if current_user.check_password(current_password):
            current_user.set_password(new_password)
            db.session.commit()
            flash(get_translation('password_changed'), 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash(get_translation('incorrect_password'), 'danger')
    
    return render_template('change_password.html')

@auth_bp.route('/language', methods=['POST'])
@login_required
def change_language():
    language = request.form.get('language')
    if language in app.config['LANGUAGES']:
        current_user.language = language
        db.session.commit()
        flash(get_translation('language_updated', language), 'success')
    
    return redirect(request.referrer or url_for('main.dashboard'))

# Routes - Main Blueprint
@main_bp.route('/')
@login_required
def dashboard():
    user_filter = request.args.get('user_id', type=int)
    date_range = request.args.get('range', 'today')
    
    # Get work hours for calculations
    work_hours = get_user_work_hours(current_user.id)
    
    # Get operators list (exclude admin users)
    operators = User.query.filter_by(is_active=True, role='operator').order_by(User.username).all()
    
    # Date range setup
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if date_range == 'week':
        start_date = today_start - timedelta(days=today_start.weekday())
        end_date = now
    elif date_range == 'month':
        start_date = today_start.replace(day=1)
        end_date = now
    else:  # today
        start_date = today_start
        end_date = now
    
    # Initialize query objects based on user role
    if current_user.role == 'admin':
        if user_filter:
            events_query = Event.query.filter_by(user_id=user_filter)
            paths_query = MonitoredPath.query.filter_by(user_id=user_filter, is_active=True)
            filtered_user = User.query.get(user_filter)
            # Get the filtered user's work hours for efficiency calculations
            work_hours_for_stats = get_user_work_hours(user_filter)
        else:
            events_query = Event.query
            paths_query = MonitoredPath.query.filter_by(is_active=True)
            filtered_user = None
            work_hours_for_stats = work_hours
    else:
        events_query = Event.query.filter_by(user_id=current_user.id)
        paths_query = MonitoredPath.query.filter_by(user_id=current_user.id, is_active=True)
        filtered_user = current_user
        user_filter = current_user.id
        work_hours_for_stats = work_hours
    
    # Apply date range filter
    date_filtered_events = events_query.filter(
        Event.timestamp >= start_date,
        Event.timestamp <= end_date
    )
    
    # KPI Metrics with weekly work hours
    today_events = events_query.filter(Event.timestamp >= today_start).count()
    
    yesterday_start = today_start - timedelta(days=1)
    yesterday_end = today_start
    yesterday_events = events_query.filter(
        Event.timestamp >= yesterday_start,
        Event.timestamp < yesterday_end
    ).count()
    
    # Calculate hourly average using today's configured work hours
    today_weekday = now.weekday()  # 0=Monday, 6=Sunday
    today_work_hours = work_hours_for_stats.get_hours_for_day(today_weekday) if work_hours_for_stats else 8.0
    
    if today_work_hours > 0:
        # Calculate how many work hours have passed today
        hours_passed = min(now.hour + now.minute/60, today_work_hours)
        work_hour_events = today_events  # All events today (could be filtered by work time)
        hourly_average = work_hour_events / max(hours_passed, 0.1)
    else:
        hourly_average = 0  # Non-working day
    
    # Active paths and categories
    active_paths = paths_query.count()
    total_files = paths_query.filter_by(is_directory=False).count()
    total_dirs = paths_query.filter_by(is_directory=True).count()
    
    active_categories = db.session.query(Category.id).join(Event).filter(
        Event.timestamp >= start_date
    ).distinct().count()
    total_categories = Category.query.count()
    
    # Recent activity (last 50 events)
    recent_events = date_filtered_events.order_by(Event.timestamp.desc()).limit(50).all()
    
    # Category distribution for pie chart
    category_stats = db.session.query(
        Category.name,
        Category.color,
        func.count(Event.id).label('count')
    ).join(Event).filter(
        Event.timestamp >= start_date,
        Event.timestamp <= end_date
    )
    
    if user_filter:
        category_stats = category_stats.filter(Event.user_id == user_filter)
    
    category_stats = category_stats.group_by(Category.id).order_by(func.count(Event.id).desc()).all()
    
    category_chart_data = {
        'labels': [stat.name for stat in category_stats],
        'values': [stat.count for stat in category_stats],
        'colors': [stat.color for stat in category_stats]
    } if category_stats else None
    
    # Daily activity for the date range
    daily_stats = db.session.query(
        func.date(Event.timestamp).label('date'),
        func.count(Event.id).label('count')
    ).filter(
        Event.timestamp >= start_date,
        Event.timestamp <= end_date
    )
    
    if user_filter:
        daily_stats = daily_stats.filter(Event.user_id == user_filter)
    
    daily_stats = daily_stats.group_by(func.date(Event.timestamp)).order_by('date').all()
    
    # Fill in missing dates
    daily_data = {}
    current_date = start_date.date()
    while current_date <= end_date.date():
        daily_data[current_date.strftime('%Y-%m-%d')] = 0
        current_date += timedelta(days=1)
    
    # Handle both string and date objects from the database
    for stat in daily_stats:
        if isinstance(stat.date, str):
            date_key = stat.date
        else:
            date_key = stat.date.strftime('%Y-%m-%d')
        daily_data[date_key] = stat.count
    
    daily_activity_data = {
        'labels': list(daily_data.keys())[-7:],  # Last 7 days
        'values': list(daily_data.values())[-7:]
    }
    
    # Weekly activity pattern using work hours with configurable efficiency
    weekly_activity = []
    week_start = start_date - timedelta(days=start_date.weekday())
    for i in range(7):  # 0=Monday, 6=Sunday
        day_start = week_start + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_events = events_query.filter(
            Event.timestamp >= day_start,
            Event.timestamp < day_end
        ).count()
        
        day_work_hours = work_hours_for_stats.get_hours_for_day(i) if work_hours_for_stats else 8.0
        events_per_hour = day_events / max(day_work_hours, 0.1) if day_work_hours > 0 else 0
        
        # Calculate efficiency using configurable thresholds for the viewed user
        if work_hours_for_stats:
            efficiency = work_hours_for_stats.calculate_efficiency(events_per_hour)
        else:
            # Default efficiency calculation if no work hours configured
            if events_per_hour >= 5.0:
                efficiency = 'high'
            elif events_per_hour >= 2.0:
                efficiency = 'medium'
            else:
                efficiency = 'low'
        
        weekly_activity.append({
            'day': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][i],
            'events': day_events,
            'work_hours': day_work_hours,
            'normalized': round(events_per_hour, 2),
            'efficiency': efficiency
        })
    
    # Path distribution
    path_stats = db.session.query(
        MonitoredPath.id,
        MonitoredPath.path,
        MonitoredPath.description,
        func.count(Event.id).label('count')
    ).join(
        Event,
        Event.user_id == MonitoredPath.user_id  # Match by user instead
    ).filter(
        Event.timestamp >= start_date,
        Event.timestamp <= end_date,
        MonitoredPath.is_active == True
    )
    
    if user_filter:
        path_stats = path_stats.filter(Event.user_id == user_filter)
    
    path_stats = path_stats.group_by(MonitoredPath.id).order_by(func.count(Event.id).desc()).limit(10).all()
    
    path_distribution_data = {
        'labels': [stat.description or os.path.basename(stat.path) for stat in path_stats],
        'values': [stat.count for stat in path_stats]
    } if path_stats else None
    
    # Hourly timeline for today
    hourly_stats = db.session.query(
        func.extract('hour', Event.timestamp).label('hour'),
        func.count(Event.id).label('count')
    ).filter(
        Event.timestamp >= today_start
    )
    
    if user_filter:
        hourly_stats = hourly_stats.filter(Event.user_id == user_filter)
    
    hourly_stats = hourly_stats.group_by('hour').all()
    
    hourly_data = {h: 0 for h in range(24)}
    for stat in hourly_stats:
        hourly_data[stat.hour] = stat.count
    
    hourly_timeline_data = {
        'labels': [f"{h}:00" for h in range(24)],
        'values': [hourly_data[h] for h in range(24)]
    }
    
    # Top categories today
    top_categories = db.session.query(
        Category.name,
        Category.color,
        func.count(Event.id).label('count')
    ).join(Event).filter(
        Event.timestamp >= today_start
    )
    
    if user_filter:
        top_categories = top_categories.filter(Event.user_id == user_filter)
    
    top_categories = top_categories.group_by(Category.id).order_by(
        func.count(Event.id).desc()
    ).limit(5).all()
    
    # Top changed files
    top_changed_files = paths_query.filter_by(is_directory=False).filter(
        MonitoredPath.change_count > 0
    ).order_by(MonitoredPath.change_count.desc()).limit(5).all()
    
    # User activity today (for admin view)
    user_activity = []
    if current_user.role == 'admin' and not user_filter:
        user_activity = db.session.query(
            User.username,
            func.count(Event.id).label('event_count')
        ).join(Event).filter(
            Event.timestamp >= today_start,
            User.role == 'operator'
        ).group_by(User.id).order_by(
            func.count(Event.id).desc()
        ).limit(5).all()
    
    return render_template('dashboard.html',
                         # Filters
                         operators=operators,
                         user_filter=user_filter,
                         filtered_user=filtered_user,
                         date_range=date_range,
                         # Work hours
                         work_hours=work_hours,
                         work_hours_for_stats=work_hours_for_stats,
                         # KPIs
                         today_events=today_events,
                         yesterday_events=yesterday_events,
                         hourly_average=hourly_average,
                         active_paths=active_paths,
                         total_files=total_files,
                         total_dirs=total_dirs,
                         active_categories=active_categories,
                         total_categories=total_categories,
                         # Recent activity
                         recent_events=recent_events,
                         # Chart data
                         category_chart_data=json.dumps(category_chart_data),
                         daily_activity_data=json.dumps(daily_activity_data),
                         path_distribution_data=json.dumps(path_distribution_data),
                         hourly_timeline_data=json.dumps(hourly_timeline_data),
                         weekly_activity=weekly_activity,
                         # Top lists
                         top_categories=top_categories,
                         top_changed_files=top_changed_files,
                         user_activity=user_activity,
                         # Helper
                         datetime=datetime)

@main_bp.route('/events')
@login_required
def events():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = Event.query
    
    # Apply filters
    if current_user.role == 'admin':
        user_id = request.args.get('user_id', type=int)
        if user_id:
            query = query.filter_by(user_id=user_id)
    else:
        query = query.filter_by(user_id=current_user.id)
    
    category_id = request.args.get('category', type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    date_from = request.args.get('date_from')
    if date_from:
        query = query.filter(Event.timestamp >= datetime.fromisoformat(date_from))
    
    date_to = request.args.get('date_to')
    if date_to:
        query = query.filter(Event.timestamp <= datetime.fromisoformat(date_to))
    
    events = query.order_by(Event.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    categories = Category.query.all()
    users = User.query.all() if current_user.role == 'admin' else None
    
    return render_template('events.html', 
                         events=events, 
                         categories=categories,
                         users=users)

@main_bp.route('/manual_entry', methods=['GET', 'POST'])
@login_required
def manual_entry():
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category_id', type=int)
        matched_keyword = request.form.get('matched_keyword', '').strip()
        amount = request.form.get('amount', type=int)
        
        if description and category_id and amount and 1 <= amount <= 100:
            # Create multiple events based on amount
            events_created = 0
            for i in range(amount):
                # Create a unique identifier for each entry if amount > 1
                if amount > 1:
                    entry_description = f"{description} (Entry {i+1}/{amount})"
                else:
                    entry_description = description
                
                event = Event(
                    file_path=f"Manual Entry: {entry_description}",
                    category_id=category_id,
                    matched_keyword=matched_keyword if matched_keyword else None,
                    computer_name=socket.gethostname(),
                    user_id=current_user.id,
                    event_type='manual'
                )
                db.session.add(event)
                events_created += 1
            
            db.session.commit()
            
            if events_created == 1:
                flash(get_translation('event_added'), 'success')
            else:
                flash(f"{events_created} {get_translation('events_added')}", 'success')
            
            return redirect(url_for('main.events'))
        else:
            flash('Please provide valid description, category, and amount (1-100)', 'danger')
    
    categories = Category.query.all()
    return render_template('manual_entry.html', categories=categories)

@main_bp.route('/reports')
@login_required
def reports():
    users = User.query.all() if current_user.role == 'admin' else None
    
    # Get recent reports
    if current_user.role == 'admin':
        recent_reports = Report.query.order_by(Report.created_at.desc()).limit(10).all()
    else:
        recent_reports = Report.query.filter_by(user_id=current_user.id)\
                                   .order_by(Report.created_at.desc()).limit(10).all()
    
    return render_template('reports.html', users=users, recent_reports=recent_reports)

@main_bp.route('/reports/generate', methods=['POST'])
@login_required
def generate_report():
    report_type = request.form.get('report_type', 'detailed')
    export_format = request.form.get('export_format', 'excel')
    date_range = request.form.get('date_range', 'today')
    
    # Calculate date range
    today = datetime.now(timezone.utc).date()
    if date_range == 'custom':
        date_from = datetime.strptime(request.form.get('date_from'), '%Y-%m-%d').date()
        date_to = datetime.strptime(request.form.get('date_to'), '%Y-%m-%d').date()
    else:
        date_from, date_to = calculate_date_range(date_range)
    
    # User filter
    user_filter = request.form.get('user_filter')
    
    # Generate report based on type
    if report_type == 'dashboard':
        wb = generate_dashboard_report(date_from, date_to, user_filter, request.form)
    elif report_type == 'audit':
        wb = generate_audit_report(date_from, date_to, user_filter, request.form)
    elif report_type == 'summary':
        wb = generate_summary_report(date_from, date_to, user_filter)
    else:  # detailed
        wb = generate_detailed_report(date_from, date_to, user_filter, request.form)
    
    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{report_type}_report_{timestamp}.xlsx"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    wb.save(filepath)
    
    # Save report record
    report = Report(
        filename=filename,
        type=report_type,
        format=export_format,
        user_id=current_user.id,
        file_path=filepath
    )
    db.session.add(report)
    db.session.commit()
    
    return send_file(filepath, as_attachment=True, download_name=filename)

@main_bp.route('/report/download/<int:id>')
@login_required
def download_report(id):
    report = Report.query.get_or_404(id)
    
    if current_user.role != 'admin' and report.user_id != current_user.id:
        flash(get_translation('no_permission'), 'danger')
        return redirect(url_for('main.reports'))
    
    if os.path.exists(report.file_path):
        return send_file(report.file_path, as_attachment=True, download_name=report.filename)
    else:
        flash(get_translation('report_not_found'), 'danger')
        return redirect(url_for('main.reports'))

@main_bp.route('/categories')
@login_required
@admin_required
def categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

@main_bp.route('/category/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_category():
    if request.method == 'POST':
        name = request.form.get('name')
        color = request.form.get('color', '#007bff')
        keywords = request.form.getlist('keywords[]')
        patterns = request.form.getlist('patterns[]')
        
        # Filter out empty values
        keywords = [k.strip() for k in keywords if k.strip()]
        patterns = [p.strip() for p in patterns if p.strip()]
        
        category = Category(
            name=name,
            color=color,
            keywords=json.dumps(keywords),
            file_patterns=json.dumps(patterns)
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash(get_translation('category_added'), 'success')
        return redirect(url_for('main.categories'))
    
    return render_template('category_form.html', category=None)

@main_bp.route('/category/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.color = request.form.get('color', '#007bff')
        
        keywords = request.form.getlist('keywords[]')
        patterns = request.form.getlist('patterns[]')
        
        keywords = [k.strip() for k in keywords if k.strip()]
        patterns = [p.strip() for p in patterns if p.strip()]
        
        category.keywords = json.dumps(keywords)
        category.file_patterns = json.dumps(patterns)
        
        db.session.commit()
        flash(get_translation('category_updated'), 'success')
        return redirect(url_for('main.categories'))
    
    return render_template('category_form.html', category=category)

@main_bp.route('/category/delete/<int:id>')
@login_required
@admin_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    flash(get_translation('category_deleted'), 'success')
    return redirect(url_for('main.categories'))

@main_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('users.html', users=users)

@main_bp.route('/user/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'operator')
        
        user = User(
            username=username,
            email=email,
            role=role
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash(get_translation('user_added'), 'success')
        return redirect(url_for('main.users'))
    
    return render_template('user_form.html')

@main_bp.route('/user/toggle/<int:id>')
@login_required
@admin_required
def toggle_user(id):
    user = User.query.get_or_404(id)
    if user.id != current_user.id:  # Can't disable yourself
        user.is_active = not user.is_active
        db.session.commit()
    return redirect(url_for('main.users'))

@main_bp.route('/user/reset_password/<int:id>', methods=['POST'])
@login_required
@admin_required
def reset_user_password(id):
    user = User.query.get_or_404(id)
    new_password = request.form.get('new_password')
    
    if new_password:
        user.set_password(new_password)
        db.session.commit()
        flash(f"{get_translation('password_reset')} {user.username}", 'success')
    
    return redirect(url_for('main.users'))

@main_bp.route('/settings')
@login_required
def settings():
    if current_user.role == 'admin':
        paths = MonitoredPath.query.all()
        users = User.query.filter_by(is_active=True).all()
        # Get all operators with their work hours for efficiency configuration
        operators = User.query.filter_by(role='operator', is_active=True).all()
        # Ensure each operator has work hours
        for operator in operators:
            operator.work_hours = get_user_work_hours(operator.id)
    else:
        paths = MonitoredPath.query.filter_by(user_id=current_user.id).all()
        users = None
        operators = None
    
    # Get weekly work hours for the current user
    work_hours = get_user_work_hours(current_user.id)
    
    return render_template('settings.html', 
                         paths=paths, 
                         users=users,
                         operators=operators,
                         work_hours=work_hours)

@main_bp.route('/settings/work_hours', methods=['POST'])
@login_required
def update_work_hours():
    try:
        # Get or create work hours for the current user
        work_hours = get_user_work_hours(current_user.id)
        
        # Update hours for each day
        work_hours.monday_hours = float(request.form.get('monday_hours', 8.0))
        work_hours.tuesday_hours = float(request.form.get('tuesday_hours', 8.0))
        work_hours.wednesday_hours = float(request.form.get('wednesday_hours', 8.0))
        work_hours.thursday_hours = float(request.form.get('thursday_hours', 8.0))
        work_hours.friday_hours = float(request.form.get('friday_hours', 8.0))
        work_hours.saturday_hours = float(request.form.get('saturday_hours', 0.0))
        work_hours.sunday_hours = float(request.form.get('sunday_hours', 0.0))
        
        work_hours.updated_at = datetime.now(timezone.utc)
        
        # Validate hours (0-24 for each day)
        hours = [work_hours.monday_hours, work_hours.tuesday_hours, work_hours.wednesday_hours,
                work_hours.thursday_hours, work_hours.friday_hours, work_hours.saturday_hours, work_hours.sunday_hours]
        
        if any(h < 0 or h > 24 for h in hours):
            flash(get_translation('invalid_work_hours'), 'danger')
            return redirect(url_for('main.settings'))
        
        db.session.commit()
        flash(get_translation('work_hours_updated'), 'success')
        
    except ValueError:
        flash(get_translation('invalid_work_hours'), 'danger')
    
    return redirect(url_for('main.settings'))

@main_bp.route('/settings/operator_efficiency', methods=['POST'])
@login_required
@admin_required
def update_operator_efficiency():
    try:
        operator_id = request.form.get('operator_id', type=int)
        efficiency_high = request.form.get('efficiency_high_threshold', type=float)
        efficiency_medium = request.form.get('efficiency_medium_threshold', type=float)
        
        if not operator_id:
            flash('Invalid operator ID', 'danger')
            return redirect(url_for('main.settings'))
        
        # Verify the user is an operator
        operator = User.query.get(operator_id)
        if not operator or operator.role != 'operator':
            flash('User not found or not an operator', 'danger')
            return redirect(url_for('main.settings'))
        
        # Get or create work hours for the operator
        work_hours = get_user_work_hours(operator_id)
        
        # Update efficiency thresholds
        if efficiency_high:
            work_hours.efficiency_high_threshold = efficiency_high
        if efficiency_medium:
            work_hours.efficiency_medium_threshold = efficiency_medium
        
        # Validate efficiency thresholds
        if work_hours.efficiency_high_threshold <= work_hours.efficiency_medium_threshold:
            flash('High efficiency threshold must be greater than medium threshold', 'danger')
            return redirect(url_for('main.settings'))
        
        work_hours.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        flash(f'Efficiency thresholds updated for {operator.username}', 'success')
        
    except ValueError:
        flash('Invalid efficiency values', 'danger')
    except Exception as e:
        flash(f'Error updating efficiency thresholds: {str(e)}', 'danger')
    
    return redirect(url_for('main.settings'))

@main_bp.route('/path/add', methods=['POST'])
@login_required
def add_monitored_path():
    path = request.form.get('path')
    path_type = request.form.get('path_type', 'file')
    description = request.form.get('description', '').strip()
    recursive = request.form.get('recursive') == 'on'
    
    if current_user.role == 'admin':
        user_id = request.form.get('user_id', type=int) or current_user.id
    else:
        user_id = current_user.id
    
    if os.path.exists(path):
        existing = MonitoredPath.query.filter_by(path=path, user_id=user_id).first()
        if existing:
            flash('This path is already being monitored by this user', 'warning')
        else:
            is_directory = path_type == 'directory'
            
            # Verify path type matches actual filesystem
            actual_is_dir = os.path.isdir(path)
            if is_directory != actual_is_dir:
                flash(f'Path type mismatch: {path} is {"a directory" if actual_is_dir else "a file"}', 'danger')
                return redirect(url_for('main.settings'))
            
            last_modified = None
            file_size = None
            if not is_directory:
                try:
                    stat = os.stat(path)
                    last_modified = datetime.fromtimestamp(stat.st_mtime)
                    file_size = stat.st_size
                except:
                    pass
            
            if not description and not is_directory:
                description = os.path.splitext(os.path.basename(path))[0].replace('_', ' ').replace('-', ' ').title()
            
            monitored_path = MonitoredPath(
                path=path, 
                user_id=user_id, 
                is_directory=is_directory,
                recursive=recursive if is_directory else False,
                description=description if description else None,
                last_modified=last_modified,
                file_size=file_size,
                change_count=0
            )
            db.session.add(monitored_path)
            db.session.commit()
            
            stop_file_monitor()
            start_file_monitor()
            
            path_type = "directory" if is_directory else "file"
            flash(f'{path_type.capitalize()} added successfully', 'success')
    else:
        flash('Path does not exist', 'danger')
    
    return redirect(url_for('main.settings'))

@main_bp.route('/path/toggle/<int:id>')
@login_required
def toggle_monitored_path(id):
    path = MonitoredPath.query.get_or_404(id)
    
    if current_user.role == 'admin' or path.user_id == current_user.id:
        path.is_active = not path.is_active
        db.session.commit()
        
        stop_file_monitor()
        start_file_monitor()
    
    return redirect(url_for('main.settings'))

@main_bp.route('/path/delete/<int:id>')
@login_required
def delete_monitored_path(id):
    path = MonitoredPath.query.get_or_404(id)
    
    if current_user.role == 'admin' or path.user_id == current_user.id:
        db.session.delete(path)
        db.session.commit()
        
        # Restart file monitor
        stop_file_monitor()
        start_file_monitor()
    
    return redirect(url_for('main.settings'))

@main_bp.route('/database_control')
@login_required
@admin_required
def database_control():
    # Calculate database statistics
    db_path = 'file_monitor.db'
    db_size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    db_size_mb = round(db_size_bytes / (1024 * 1024), 2)
    
    # Get oldest event
    oldest_event = Event.query.order_by(Event.timestamp.asc()).first()
    oldest_event_days = 0
    if oldest_event:
        # Ensure both datetimes are timezone-aware
        if oldest_event.timestamp.tzinfo is None:
            # If timestamp is naive, assume it's UTC
            oldest_timestamp_aware = oldest_event.timestamp.replace(tzinfo=timezone.utc)
        else:
            oldest_timestamp_aware = oldest_event.timestamp
        oldest_event_days = (datetime.now(timezone.utc) - oldest_timestamp_aware).days
    
    stats = {
        'total_events': Event.query.count(),
        'total_users': User.query.count(),
        'total_categories': Category.query.count(),
        'total_paths': MonitoredPath.query.count(),
        'db_size': f"{db_size_mb} MB",
        'oldest_event_days': oldest_event_days
    }
    
    # Get recent backups
    recent_backups = DatabaseBackup.query.order_by(DatabaseBackup.created_at.desc()).limit(10).all()
    
    # Get scheduled backup settings
    scheduled_backup = ScheduledBackupSettings.query.first()
    if not scheduled_backup:
        scheduled_backup = ScheduledBackupSettings()
        db.session.add(scheduled_backup)
        db.session.commit()
    
    return render_template('database_control.html',
                         stats=stats,
                         recent_backups=recent_backups,
                         scheduled_backup=scheduled_backup)

@main_bp.route('/database/backup', methods=['POST'])
@login_required
@admin_required
def backup_database():
    backup_type = request.form.get('backup_type', 'full')
    compress = request.form.get('compress') == 'on'
    note = request.form.get('backup_note', '').strip()
    
    # Create backup directory
    backup_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if backup_type == 'full':
        # Full database backup
        db_path = 'file_monitor.db'
        backup_filename = f"backup_full_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Stop file monitor during backup
        stop_file_monitor()
        
        try:
            # Copy database file
            shutil.copy2(db_path, backup_path)
            
            if compress:
                # Compress the backup
                zip_filename = f"backup_full_{timestamp}.zip"
                zip_path = os.path.join(backup_dir, zip_filename)
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(backup_path, backup_filename)
                
                # Remove uncompressed file
                os.remove(backup_path)
                backup_filename = zip_filename
                backup_path = zip_path
            
            # Get file size
            size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            
            # Save backup record
            backup_record = DatabaseBackup(
                filename=backup_filename,
                type=backup_type,
                size_mb=round(size_mb, 2),
                note=note,
                created_by_id=current_user.id
            )
            db.session.add(backup_record)
            db.session.commit()
            
            flash(get_translation('backup_created_successfully'), 'success')
            
            # Send file for download
            return send_file(backup_path, as_attachment=True, download_name=backup_filename)
            
        finally:
            # Restart file monitor
            start_file_monitor()
    
    elif backup_type == 'data_only':
        # Export data to SQL format
        backup_filename = f"backup_data_{timestamp}.sql"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Generate SQL export
        with open(backup_path, 'w', encoding='utf-8') as f:
            # Export events
            f.write("-- Events Table\n")
            events = Event.query.all()
            for event in events:
                f.write(f"INSERT INTO event (timestamp, file_path, category_id, matched_keyword, computer_name, user_id, event_type, file_size) VALUES ('{event.timestamp}', '{event.file_path}', {event.category_id or 'NULL'}, '{event.matched_keyword or ''}', '{event.computer_name}', {event.user_id or 'NULL'}, '{event.event_type}', {event.file_size or 'NULL'});\n")
            
            # Export categories
            f.write("\n-- Categories Table\n")
            categories = Category.query.all()
            for cat in categories:
                f.write(f"INSERT INTO category (name, keywords, file_patterns, color) VALUES ('{cat.name}', '{cat.keywords}', '{cat.file_patterns}', '{cat.color}');\n")
        
        if compress:
            zip_filename = f"backup_data_{timestamp}.zip"
            zip_path = os.path.join(backup_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(backup_path, backup_filename)
            
            os.remove(backup_path)
            backup_filename = zip_filename
            backup_path = zip_path
        
        size_mb = os.path.getsize(backup_path) / (1024 * 1024)
        
        backup_record = DatabaseBackup(
            filename=backup_filename,
            type=backup_type,
            size_mb=round(size_mb, 2),
            note=note,
            created_by_id=current_user.id
        )
        db.session.add(backup_record)
        db.session.commit()
        
        return send_file(backup_path, as_attachment=True, download_name=backup_filename)
    
    return redirect(url_for('main.database_control'))

@main_bp.route('/database/restore', methods=['POST'])
@login_required
@admin_required
def restore_database():
    if 'backup_file' not in request.files:
        flash(get_translation('no_file_uploaded'), 'danger')
        return redirect(url_for('main.database_control'))
    
    file = request.files['backup_file']
    if file.filename == '':
        flash(get_translation('no_file_selected'), 'danger')
        return redirect(url_for('main.database_control'))
    
    # Save uploaded file
    backup_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'backups', 'temp')
    os.makedirs(backup_dir, exist_ok=True)
    
    temp_path = os.path.join(backup_dir, file.filename)
    file.save(temp_path)
    
    try:
        # Stop file monitor
        stop_file_monitor()
        
        # Determine file type and restore
        if file.filename.endswith('.zip'):
            # Extract zip file
            with zipfile.ZipFile(temp_path, 'r') as zipf:
                # Find .db file in zip
                db_files = [f for f in zipf.namelist() if f.endswith('.db')]
                if db_files:
                    # Extract and restore database
                    zipf.extract(db_files[0], backup_dir)
                    extracted_path = os.path.join(backup_dir, db_files[0])
                    
                    # Backup current database
                    shutil.copy2('file_monitor.db', 'file_monitor.db.before_restore')
                    
                    # Replace with restored database
                    shutil.copy2(extracted_path, 'file_monitor.db')
                    os.remove(extracted_path)
                    
                    flash(get_translation('database_restored_successfully'), 'success')
                else:
                    flash(get_translation('no_database_in_zip'), 'danger')
        
        elif file.filename.endswith('.db'):
            # Direct database file
            shutil.copy2('file_monitor.db', 'file_monitor.db.before_restore')
            shutil.copy2(temp_path, 'file_monitor.db')
            flash(get_translation('database_restored_successfully'), 'success')
        
        elif file.filename.endswith('.sql'):
            # SQL file - would need to parse and execute
            flash(get_translation('sql_restore_not_implemented'), 'warning')
        
        else:
            flash(get_translation('unsupported_file_format'), 'danger')
    
    except Exception as e:
        flash(f"{get_translation('restore_failed')}: {str(e)}", 'danger')
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Restart file monitor
        start_file_monitor()
    
    return redirect(url_for('main.database_control'))

@main_bp.route('/database/export', methods=['POST'])
@login_required
@admin_required
def export_database():
    export_format = request.form.get('export_format', 'csv')
    
    # Determine what to export
    export_events = request.form.get('export_events') == 'on'
    export_users = request.form.get('export_users') == 'on'
    export_categories = request.form.get('export_categories') == 'on'
    export_paths = request.form.get('export_paths') == 'on'
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if export_format == 'csv':
        # Create a zip file with multiple CSVs
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Export events
            if export_events:
                csv_buffer = StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(['Timestamp', 'Category', 'File Path', 'Computer', 'User', 'Type', 'Keyword'])
                
                events = Event.query.all()
                for event in events:
                    writer.writerow([
                        event.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        event.category.name if event.category else 'Uncategorized',
                        event.file_path,
                        event.computer_name,
                        event.user.username if event.user else 'System',
                        event.event_type,
                        event.matched_keyword or ''
                    ])
                
                zipf.writestr('events.csv', csv_buffer.getvalue())
            
            # Export users
            if export_users:
                csv_buffer = StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(['Username', 'Email', 'Role', 'Active', 'Created'])
                
                users = User.query.all()
                for user in users:
                    writer.writerow([
                        user.username,
                        user.email,
                        user.role,
                        'Yes' if user.is_active else 'No',
                        user.created_at.strftime('%Y-%m-%d')
                    ])
                
                zipf.writestr('users.csv', csv_buffer.getvalue())
            
            # Export categories
            if export_categories:
                csv_buffer = StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(['Name', 'Keywords', 'Patterns', 'Color'])
                
                categories = Category.query.all()
                for cat in categories:
                    writer.writerow([
                        cat.name,
                        ', '.join(cat.get_keywords()),
                        ', '.join(cat.get_patterns()),
                        cat.color
                    ])
                
                zipf.writestr('categories.csv', csv_buffer.getvalue())
            
            # Export paths
            if export_paths:
                csv_buffer = StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(['Path', 'User', 'Type', 'Active', 'Description'])
                
                paths = MonitoredPath.query.all()
                for path in paths:
                    writer.writerow([
                        path.path,
                        path.user.username,
                        'Directory' if path.is_directory else 'File',
                        'Yes' if path.is_active else 'No',
                        path.description or ''
                    ])
                
                zipf.writestr('monitored_paths.csv', csv_buffer.getvalue())
        
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'export_{timestamp}.zip'
        )
    
    elif export_format == 'json':
        # Export as JSON
        data = {}
        
        if export_events:
            data['events'] = [{
                'timestamp': event.timestamp.isoformat(),
                'category': event.category.name if event.category else None,
                'file_path': event.file_path,
                'computer_name': event.computer_name,
                'user': event.user.username if event.user else None,
                'event_type': event.event_type,
                'keyword': event.matched_keyword
            } for event in Event.query.all()]
        
        if export_users:
            data['users'] = [{
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'active': user.is_active,
                'created': user.created_at.isoformat()
            } for user in User.query.all()]
        
        if export_categories:
            data['categories'] = [{
                'name': cat.name,
                'keywords': cat.get_keywords(),
                'patterns': cat.get_patterns(),
                'color': cat.color
            } for cat in Category.query.all()]
        
        if export_paths:
            data['monitored_paths'] = [{
                'path': path.path,
                'user': path.user.username,
                'is_directory': path.is_directory,
                'active': path.is_active,
                'description': path.description
            } for path in MonitoredPath.query.all()]
        
        json_buffer = BytesIO()
        json_buffer.write(json.dumps(data, indent=2).encode('utf-8'))
        json_buffer.seek(0)
        
        return send_file(
            json_buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'export_{timestamp}.json'
        )
    
    return redirect(url_for('main.database_control'))

@main_bp.route('/database/cleanup', methods=['POST'])
@login_required
@admin_required
def cleanup_events():
    cleanup_period = int(request.form.get('cleanup_period', 30))
    
    # Calculate cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=cleanup_period)
    
    # Delete old events
    deleted_count = Event.query.filter(Event.timestamp < cutoff_date).delete()
    db.session.commit()
    
    flash(f"{get_translation('deleted')} {deleted_count} {get_translation('old_events')}", 'success')
    
    return redirect(url_for('main.database_control'))

@main_bp.route('/database/optimize', methods=['POST'])
@login_required
@admin_required
def optimize_database():
    try:
        # For SQLite, we can VACUUM the database
        db.session.execute(text('VACUUM'))
        db.session.commit()
        
        flash(get_translation('database_optimized'), 'success')
    except Exception as e:
        flash(f"{get_translation('optimization_failed')}: {str(e)}", 'danger')
    
    return redirect(url_for('main.database_control'))

@main_bp.route('/database/backup_schedule', methods=['POST'])
@login_required
@admin_required
def update_backup_schedule():
    settings = ScheduledBackupSettings.query.first()
    if not settings:
        settings = ScheduledBackupSettings()
        db.session.add(settings)
    
    settings.enabled = request.form.get('enable_scheduled') == 'on'
    settings.frequency = request.form.get('backup_frequency', 'daily')
    settings.time = request.form.get('backup_time', '02:00')
    settings.retention_days = int(request.form.get('retention_days', 30))
    
    # Calculate next run time
    if settings.enabled:
        now = datetime.now()
        backup_hour, backup_minute = map(int, settings.time.split(':'))
        next_run = now.replace(hour=backup_hour, minute=backup_minute, second=0, microsecond=0)
        
        if next_run <= now:
            next_run += timedelta(days=1)
        
        if settings.frequency == 'weekly':
            # Run on Sundays
            days_until_sunday = (6 - next_run.weekday()) % 7
            if days_until_sunday == 0 and next_run <= now:
                days_until_sunday = 7
            next_run += timedelta(days=days_until_sunday)
        elif settings.frequency == 'monthly':
            # Run on 1st of each month
            if next_run.day != 1:
                next_month = next_run.replace(day=1)
                if next_run.month == 12:
                    next_month = next_month.replace(year=next_run.year + 1, month=1)
                else:
                    next_month = next_month.replace(month=next_run.month + 1)
                next_run = next_month
        
        settings.next_run = next_run
    
    db.session.commit()
    flash(get_translation('backup_schedule_updated'), 'success')
    
    return redirect(url_for('main.database_control'))

# API Blueprint Routes
@api_bp.route('/monitor/status')
@login_required
def monitor_status():
    global file_observers
    
    if current_user.role == 'admin':
        running_monitors = sum(1 for obs in file_observers.values() if obs and obs.is_alive())
        total_paths = MonitoredPath.query.filter_by(is_active=True).count()
        total_files = MonitoredPath.query.filter_by(is_active=True, is_directory=False).count()
        total_dirs = MonitoredPath.query.filter_by(is_active=True, is_directory=True).count()
        
        return jsonify({
            'running': running_monitors > 0,
            'monitors_count': running_monitors,
            'paths': total_paths,
            'files': total_files,
            'directories': total_dirs
        })
    else:
        user_observer = file_observers.get(current_user.id)
        user_paths = MonitoredPath.query.filter_by(user_id=current_user.id, is_active=True).count()
        user_files = MonitoredPath.query.filter_by(user_id=current_user.id, is_active=True, is_directory=False).count()
        user_dirs = MonitoredPath.query.filter_by(user_id=current_user.id, is_active=True, is_directory=True).count()
        
        return jsonify({
            'running': user_observer is not None and user_observer.is_alive(),
            'paths': user_paths,
            'files': user_files,
            'directories': user_dirs
        })

@api_bp.route('/monitor/start', methods=['POST'])
@login_required
@admin_required
def start_monitor():
    start_file_monitor()
    return jsonify({'status': 'started'})

@api_bp.route('/categories')
@login_required
def api_categories():
    categories = Category.query.all()
    return jsonify([{
        'id': cat.id,
        'name': cat.name,
        'color': cat.color
    } for cat in categories])

@api_bp.route('/validate_path', methods=['POST'])
@login_required
def validate_path():
    data = request.get_json()
    path = data.get('path', '')
    
    exists = os.path.exists(path)
    is_directory = os.path.isdir(path) if exists else False
    is_file = os.path.isfile(path) if exists else False
    
    return jsonify({
        'exists': exists,
        'is_directory': is_directory,
        'is_file': is_file,
        'readable': os.access(path, os.R_OK) if exists else False
    })

@api_bp.route('/manual_entry', methods=['POST'])
@login_required
def api_manual_entry():
    data = request.get_json()
    
    description = data.get('description', '').strip()
    category_name = data.get('category')
    amount = data.get('amount', 1)
    
    # Remove the description required check - only category is required
    if not category_name:
        return jsonify({'error': 'Category is required'}), 400
    
    if not isinstance(amount, int) or amount < 1 or amount > 100:
        return jsonify({'error': 'Amount must be between 1 and 100'}), 400
    
    category = Category.query.filter_by(name=category_name).first()
    if not category:
        return jsonify({'error': 'Category not found'}), 400
    
    try:
        # Use bulk_insert_mappings for better performance
        events_to_insert = []
        timestamp = datetime.now().strftime('%H:%M:%S')
        base_timestamp = datetime.now(timezone.utc)
        
        for i in range(amount):
            # Generate entry description
            if description:
                if amount > 1:
                    entry_description = f"{description} (Entry {i+1}/{amount})"
                else:
                    entry_description = description
            else:
                # No description provided - use category name with timestamp
                if amount > 1:
                    entry_description = f"{category_name} at {timestamp} (Entry {i+1}/{amount})"
                else:
                    entry_description = f"{category_name} at {timestamp}"
            
            events_to_insert.append({
                'file_path': f"Manual Entry: {entry_description}",
                'category_id': category.id,
                'matched_keyword': None,
                'computer_name': socket.gethostname(),
                'user_id': current_user.id,
                'event_type': 'manual',
                'timestamp': base_timestamp
            })
        
        # Bulk insert for better performance
        db.session.bulk_insert_mappings(Event, events_to_insert)
        db.session.commit()
        
        return jsonify({
            'status': 'success', 
            'count': len(events_to_insert)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@api_bp.route('/file_changes/stats')
@login_required
def file_changes_stats():
    if current_user.role == 'admin':
        query = MonitoredPath.query.filter_by(is_directory=False)
    else:
        query = MonitoredPath.query.filter_by(user_id=current_user.id, is_directory=False)
    
    file_changes = query.filter(MonitoredPath.change_count > 0)\
                       .order_by(MonitoredPath.change_count.desc())\
                       .limit(10).all()
    
    total_changes = db.session.query(func.sum(MonitoredPath.change_count))\
                             .filter_by(is_directory=False).scalar() or 0
    
    return jsonify({
        'files': [{
            'label': f.description or os.path.basename(f.path),
            'changes': f.change_count
        } for f in file_changes],
        'total_changes': total_changes
    })

@api_bp.route('/file_changes/history/<int:path_id>')
@login_required
def file_change_history(path_id):
    path = MonitoredPath.query.get_or_404(path_id)
    
    if current_user.role != 'admin' and path.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    history = FileChangeHistory.query.filter_by(monitored_path_id=path_id)\
                                   .order_by(FileChangeHistory.timestamp.desc())\
                                   .limit(50).all()
    
    return jsonify({
        'file_info': {
            'path': path.path,
            'description': path.description,
            'total_changes': path.change_count,
            'last_change': path.last_change_detected.isoformat() if path.last_change_detected else None
        },
        'history': [{
            'timestamp': h.timestamp.isoformat(),
            'change_type': h.change_type,
            'size_change': (h.new_size - h.old_size) if h.new_size and h.old_size else None
        } for h in history]
    })

@api_bp.route('/report/<int:report_id>', methods=['DELETE'])
@login_required
def delete_report(report_id):
    report = Report.query.get_or_404(report_id)
    
    if current_user.role != 'admin' and report.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        # Delete file
        if os.path.exists(report.file_path):
            os.remove(report.file_path)
        
        # Delete record
        db.session.delete(report)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/report/preview', methods=['POST'])
@login_required
def preview_report():
    report_type = request.form.get('report_type')
    date_range = request.form.get('date_range', 'today')
    
    # Generate preview HTML based on report type
    preview_html = generate_report_preview(report_type, date_range)
    
    return jsonify({'html': preview_html})

@api_bp.route('/database/cleanup_count')
@login_required
@admin_required
def cleanup_count():
    days = int(request.args.get('days', 30))
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    count = Event.query.filter(Event.timestamp < cutoff_date).count()
    return jsonify({'count': count})

@api_bp.route('/database/restore/<filename>', methods=['POST'])
@login_required
@admin_required
def api_restore_database(filename):
    try:
        backup_path = os.path.join(app.config['UPLOAD_FOLDER'], 'backups', filename)
        
        if not os.path.exists(backup_path):
            return jsonify({'success': False, 'error': 'Backup file not found'})
        
        # Stop file monitor
        stop_file_monitor()
        
        # Backup current database
        shutil.copy2('file_monitor.db', 'file_monitor.db.before_restore')
        
        if filename.endswith('.zip'):
            # Extract and restore
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                db_files = [f for f in zipf.namelist() if f.endswith('.db')]
                if db_files:
                    temp_dir = tempfile.mkdtemp()
                    zipf.extract(db_files[0], temp_dir)
                    shutil.copy2(os.path.join(temp_dir, db_files[0]), 'file_monitor.db')
                    shutil.rmtree(temp_dir)
        else:
            # Direct copy
            shutil.copy2(backup_path, 'file_monitor.db')
        
        # Restart file monitor
        start_file_monitor()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@api_bp.route('/database/backup/<int:backup_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_backup(backup_id):
    backup = DatabaseBackup.query.get_or_404(backup_id)
    
    # Delete file
    backup_path = os.path.join(app.config['UPLOAD_FOLDER'], 'backups', backup.filename)
    if os.path.exists(backup_path):
        os.remove(backup_path)
    
    # Delete record
    db.session.delete(backup)
    db.session.commit()
    
    return jsonify({'success': True})

@api_bp.route('/database/reset', methods=['POST'])
@login_required
@admin_required
def reset_database():
    try:
        # Delete all events but keep system data
        Event.query.delete()
        FileChangeHistory.query.delete()
        
        # Reset change counts
        MonitoredPath.query.update({
            'change_count': 0,
            'last_change_detected': None
        })
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@api_bp.route('/database/delete_all', methods=['POST'])
@login_required
@admin_required
def delete_all_data():
    try:
        # Delete all data from all tables except the admin user
        Event.query.delete()
        FileChangeHistory.query.delete()
        MonitoredPath.query.delete()
        Category.query.delete()
        Report.query.delete()
        DatabaseBackup.query.delete()
        WeeklyWorkHours.query.delete()
        
        # Keep only admin users
        User.query.filter(User.role != 'admin').delete()
        
        db.session.commit()
        
        # Recreate default categories
        create_default_categories()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Helper functions for report generation
def calculate_date_range(range_type):
    """Calculate date range based on range type"""
    today = datetime.now(timezone.utc).date()
    
    if range_type == 'today':
        return today, today
    elif range_type == 'yesterday':
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif range_type == 'week':
        start = today - timedelta(days=7)
        return start, today
    elif range_type == 'last_week':
        end = today - timedelta(days=today.weekday() + 1)
        start = end - timedelta(days=6)
        return start, end
    elif range_type == 'month':
        start = today.replace(day=1)
        return start, today
    elif range_type == 'last_month':
        last_month = today.replace(day=1) - timedelta(days=1)
        start = last_month.replace(day=1)
        return start, last_month
    elif range_type == 'quarter':
        quarter = (today.month - 1) // 3
        start = today.replace(month=quarter * 3 + 1, day=1)
        return start, today
    elif range_type == 'year':
        start = today.replace(month=1, day=1)
        return start, today
    
    return today, today

def generate_report_preview(report_type, date_range):
    """Generate HTML preview of report with actual content"""
    if date_range == 'custom':
        date_info = "Custom date range selected"
    else:
        date_from, date_to = calculate_date_range(date_range)
        date_info = f"Date range: {date_from} to {date_to}"
    
    # Get sample data for preview
    today = datetime.now(timezone.utc).date()
    if date_range == 'today':
        start_date = today
    else:
        start_date = today - timedelta(days=7)
    
    # Query sample data
    total_events = Event.query.filter(
        Event.timestamp >= datetime.combine(start_date, datetime.min.time())
    ).count()
    
    categories = db.session.query(
        Category.name,
        func.count(Event.id).label('count')
    ).join(Event).filter(
        Event.timestamp >= datetime.combine(start_date, datetime.min.time())
    ).group_by(Category.id).limit(5).all()
    
    preview_html = f"""
    <div class="row">
        <div class="col-12">
            <h6>Report Type: <strong>{report_type.title()} Report</strong></h6>
            <p>{date_info}</p>
            <hr>
        </div>
    </div>
    
    <div class="row">
        <div class="col-md-6">
            <h6>Preview Content:</h6>
            <ul>
    """
    
    if report_type == 'dashboard':
        preview_html += f"""
                <li>KPI Summary with {total_events} total events</li>
                <li>Category Distribution Chart</li>
                <li>Daily Activity Chart</li>
                <li>Hourly Timeline</li>
                <li>Work Hours Analysis</li>
            </ul>
        </div>
        <div class="col-md-6">
            <h6>Top Categories:</h6>
            <ul>
        """
        for cat in categories[:5]:
            preview_html += f"<li>{cat.name}: {cat.count} events</li>"
            
    elif report_type == 'detailed':
        preview_html += f"""
                <li>Complete event listing ({total_events} events)</li>
                <li>Statistical summary by category</li>
                <li>File change history</li>
                <li>User activity breakdown</li>
            </ul>
        </div>
        <div class="col-md-6">
            <h6>Data Sheets:</h6>
            <ul>
                <li>Events (all columns)</li>
                <li>Statistics Summary</li>
                <li>File Changes</li>
        """
        
    elif report_type == 'summary':
        preview_html += f"""
                <li>Executive summary</li>
                <li>Key performance indicators</li>
                <li>Trend analysis</li>
                <li>Category breakdown</li>
            </ul>
        </div>
        <div class="col-md-6">
            <h6>Summary Metrics:</h6>
            <ul>
                <li>Total Events: {total_events}</li>
                <li>Active Categories: {len(categories)}</li>
                <li>Date Range: {(date_to - date_from).days + 1} days</li>
        """
        
    elif report_type == 'audit':
        preview_html += f"""
                <li>User activity log</li>
                <li>Access patterns analysis</li>
                <li>Anomaly detection results</li>
                <li>Security events</li>
            </ul>
        </div>
        <div class="col-md-6">
            <h6>Audit Sections:</h6>
            <ul>
                <li>User Activities</li>
                <li>File Access Patterns</li>
                <li>Time-based Analysis</li>
        """
    
    preview_html += """
            </ul>
        </div>
    </div>
    """
    
    return preview_html

def generate_dashboard_report(date_from, date_to, user_filter, options):
    """Generate Excel report with actual dashboard charts and data"""
    wb = openpyxl.Workbook()
    
    # Query base data
    query = Event.query
    if user_filter and user_filter != 'operators':
        query = query.filter_by(user_id=int(user_filter))
    elif user_filter == 'operators':
        operator_ids = [u.id for u in User.query.filter_by(role='operator').all()]
        query = query.filter(Event.user_id.in_(operator_ids))
    
    date_query = query.filter(
        Event.timestamp >= datetime.combine(date_from, datetime.min.time()),
        Event.timestamp <= datetime.combine(date_to, datetime.max.time())
    )
    
    # KPI Summary Sheet
    if options.get('include_kpis'):
        ws = wb.active
        ws.title = "KPI Summary"
        
        # Title and formatting
        ws['A1'] = "Dashboard Report - KPI Summary"
        ws['A1'].font = Font(size=16, bold=True)
        ws['A2'] = f"Date Range: {date_from} to {date_to}"
        ws['A3'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Calculate KPIs
        total_events = date_query.count()
        days_in_range = max((date_to - date_from).days + 1, 1)
        
        work_hours = get_user_work_hours(current_user.id)
        
        # Category breakdown
        category_stats = db.session.query(
            Category.name,
            Category.color,
            func.count(Event.id).label('count')
        ).join(Event).filter(
            Event.timestamp >= datetime.combine(date_from, datetime.min.time()),
            Event.timestamp <= datetime.combine(date_to, datetime.max.time())
        ).group_by(Category.id).all()
        
        # Add KPIs with formatting
        kpi_data = [
            ("Total Events", total_events),
            ("Average Events per Day", round(total_events / days_in_range, 1)),
            ("Total Categories Used", len(category_stats)),
            ("Date Range (Days)", days_in_range),
            ("Weekly Work Hours", f"{work_hours.get_total_weekly_hours()}h" if work_hours else "40h"),
            ("Working Days per Week", work_hours.get_working_days() if work_hours else 5),
            ("Report Generated", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            ("Generated By", current_user.username)
        ]
        
        # Write KPIs
        row = 5
        ws[f'A{row}'] = "KEY METRICS"
        ws[f'A{row}'].font = Font(bold=True, size=12)
        row += 1
        
        for label, value in kpi_data:
            ws[f'A{row}'] = label
            ws[f'B{row}'] = value
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'B{row}'].alignment = Alignment(horizontal='left')
            row += 1
        
        # Add Category Summary
        row += 2
        ws[f'A{row}'] = "CATEGORY BREAKDOWN"
        ws[f'A{row}'].font = Font(bold=True, size=12)
        row += 1
        
        ws[f'A{row}'] = "Category"
        ws[f'B{row}'] = "Event Count"
        ws[f'C{row}'] = "Percentage"
        for col in ['A', 'B', 'C']:
            ws[f'{col}{row}'].font = Font(bold=True)
            ws[f'{col}{row}'].fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            ws[f'{col}{row}'].font = Font(color="FFFFFF", bold=True)
        
        row += 1
        for cat in category_stats:
            ws[f'A{row}'] = cat.name
            ws[f'B{row}'] = cat.count
            ws[f'C{row}'] = f"{(cat.count / total_events * 100):.1f}%" if total_events > 0 else "0%"
            row += 1
    
    # Category Distribution Sheet with Chart
    if options.get('include_category_dist'):
        ws = wb.create_sheet("Category Distribution")
        
        # Data for chart
        ws['A1'] = "Category Distribution"
        ws['A1'].font = Font(size=14, bold=True)
        
        ws['A3'] = "Category"
        ws['B3'] = "Count"
        ws['A3'].font = Font(bold=True)
        ws['B3'].font = Font(bold=True)
        
        row = 4
        for cat in category_stats:
            ws[f'A{row}'] = cat.name
            ws[f'B{row}'] = cat.count
            row += 1
        
        # Create chart using openpyxl
        from openpyxl.chart import PieChart, Reference
        
        pie = PieChart()
        pie.title = "Events by Category"
        data = Reference(ws, min_col=2, min_row=3, max_row=row-1)
        labels = Reference(ws, min_col=1, min_row=4, max_row=row-1)
        pie.add_data(data, titles_from_data=True)
        pie.set_categories(labels)
        pie.height = 10
        pie.width = 15
        ws.add_chart(pie, "D3")
    
    # Daily Activity Sheet with Chart
    if options.get('include_daily_activity'):
        ws = wb.create_sheet("Daily Activity")
        
        # Get daily data
        daily_stats = db.session.query(
            func.date(Event.timestamp).label('date'),
            func.count(Event.id).label('count')
        ).filter(
            Event.timestamp >= datetime.combine(date_from, datetime.min.time()),
            Event.timestamp <= datetime.combine(date_to, datetime.max.time())
        ).group_by(func.date(Event.timestamp)).all()
        
        ws['A1'] = "Daily Activity"
        ws['A1'].font = Font(size=14, bold=True)
        
        ws['A3'] = "Date"
        ws['B3'] = "Events"
        ws['A3'].font = Font(bold=True)
        ws['B3'].font = Font(bold=True)
        
        row = 4
        for stat in daily_stats:
            ws[f'A{row}'] = stat.date if isinstance(stat.date, str) else stat.date.strftime('%Y-%m-%d')
            ws[f'B{row}'] = stat.count
            row += 1
        
        # Create bar chart
        from openpyxl.chart import BarChart, Reference
        
        chart = BarChart()
        chart.title = "Events per Day"
        chart.y_axis.title = 'Event Count'
        chart.x_axis.title = 'Date'
        
        data = Reference(ws, min_col=2, min_row=3, max_row=row-1)
        dates = Reference(ws, min_col=1, min_row=4, max_row=row-1)
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(dates)
        chart.height = 10
        chart.width = 20
        ws.add_chart(chart, "D3")
    
    # Hourly Timeline Sheet
    if options.get('include_hourly_timeline'):
        ws = wb.create_sheet("Hourly Timeline")
        
        # Get hourly data for the period
        hourly_stats = db.session.query(
            func.extract('hour', Event.timestamp).label('hour'),
            func.count(Event.id).label('count')
        ).filter(
            Event.timestamp >= datetime.combine(date_from, datetime.min.time()),
            Event.timestamp <= datetime.combine(date_to, datetime.max.time())
        ).group_by('hour').all()
        
        ws['A1'] = "Hourly Activity Pattern"
        ws['A1'].font = Font(size=14, bold=True)
        
        ws['A3'] = "Hour"
        ws['B3'] = "Events"
        ws['A3'].font = Font(bold=True)
        ws['B3'].font = Font(bold=True)
        
        # Fill all 24 hours
        hourly_data = {h: 0 for h in range(24)}
        for stat in hourly_stats:
            hourly_data[int(stat.hour)] = stat.count
        
        row = 4
        for hour in range(24):
            ws[f'A{row}'] = f"{hour:02d}:00"
            ws[f'B{row}'] = hourly_data[hour]
            row += 1
        
        # Create line chart
        from openpyxl.chart import LineChart, Reference
        
        chart = LineChart()
        chart.title = "Hourly Event Distribution"
        chart.y_axis.title = 'Event Count'
        chart.x_axis.title = 'Hour of Day'
        
        data = Reference(ws, min_col=2, min_row=3, max_row=row-1)
        hours = Reference(ws, min_col=1, min_row=4, max_row=row-1)
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(hours)
        chart.height = 10
        chart.width = 20
        ws.add_chart(chart, "D3")
    
    # Auto-adjust column widths for all sheets
    for sheet in wb.worksheets:
        for column in sheet.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            sheet.column_dimensions[column_letter].width = adjusted_width
    
    return wb

def generate_detailed_report(date_from, date_to, user_filter, options):
    """Generate comprehensive detailed report"""
    wb = openpyxl.Workbook()
    
    # Events Sheet
    ws = wb.active
    ws.title = "Events"
    
    # Headers
    headers = ['Timestamp', 'Category', 'File Path', 'Computer', 'User', 'Type', 'Keyword']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.font = Font(color="FFFFFF", bold=True)
    
    # Query events
    query = Event.query.filter(
        Event.timestamp >= datetime.combine(date_from, datetime.min.time()),
        Event.timestamp <= datetime.combine(date_to, datetime.max.time())
    )
    
    if user_filter and user_filter != 'operators':
        query = query.filter_by(user_id=int(user_filter))
    elif user_filter == 'operators':
        operator_ids = [u.id for u in User.query.filter_by(role='operator').all()]
        query = query.filter(Event.user_id.in_(operator_ids))
    
    events = query.order_by(Event.timestamp.desc()).all()
    
    # Data
    for row, event in enumerate(events, 2):
        ws.cell(row=row, column=1, value=event.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
        ws.cell(row=row, column=2, value=event.category.name if event.category else 'Uncategorized')
        ws.cell(row=row, column=3, value=event.file_path)
        ws.cell(row=row, column=4, value=event.computer_name)
        ws.cell(row=row, column=5, value=event.user.username if event.user else 'System')
        ws.cell(row=row, column=6, value=event.event_type)
        ws.cell(row=row, column=7, value=event.matched_keyword or '-')
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    return wb

def generate_summary_report(date_from, date_to, user_filter):
    """Generate a high-level summary report"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Executive Summary"
    
    # Title
    ws['A1'] = "Executive Summary Report"
    ws['A1'].font = Font(size=18, bold=True)
    ws['A2'] = f"Period: {date_from} to {date_to}"
    ws['A3'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    return wb

def generate_audit_report(date_from, date_to, user_filter, options):
    """Generate a detailed audit report"""
    wb = openpyxl.Workbook()
    
    # User Activity Log
    if options.get('include_user_activity'):
        ws = wb.active
        ws.title = "User Activity Log"
        
        # Headers
        headers = ['Username', 'Role', 'Total Events', 'First Activity', 'Last Activity']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    
    return wb

def create_default_categories():
    """Create some default categories for demo purposes"""
    with app.app_context():
        if Category.query.count() == 0:
            default_categories = [
                {
                    'name': 'Documents',
                    'keywords': ['document', 'doc', 'report', 'text'],
                    'file_patterns': ['.*\\.doc.*', '.*\\.pdf', '.*\\.txt'],
                    'color': '#007bff'
                },
                {
                    'name': 'Images',
                    'keywords': ['image', 'photo', 'picture'],
                    'file_patterns': ['.*\\.jpg', '.*\\.png', '.*\\.gif', '.*\\.bmp'],
                    'color': '#28a745'
                },
                {
                    'name': 'Data Files',
                    'keywords': ['data', 'csv', 'excel', 'spreadsheet'],
                    'file_patterns': ['.*\\.csv', '.*\\.xlsx?', '.*\\.json'],
                    'color': '#ffc107'
                },
                {
                    'name': 'Log Files',
                    'keywords': ['log', 'error', 'debug', 'trace'],
                    'file_patterns': ['.*\\.log', '.*\\.trace'],
                    'color': '#dc3545'
                }
            ]
            
            for cat_data in default_categories:
                category = Category(
                    name=cat_data['name'],
                    keywords=json.dumps(cat_data['keywords']),
                    file_patterns=json.dumps(cat_data['file_patterns']),
                    color=cat_data['color']
                )
                db.session.add(category)
            
            db.session.commit()
            print("Default categories created.")

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)

# Cleanup on exit
import atexit
atexit.register(stop_file_monitor)

# Initialize database function
def initialize_database():
    """Initialize the database and start file monitoring"""
    with app.app_context():
        try:
            # Check and migrate database first
            if not check_and_migrate_database():
                print("❌ Database migration failed. Please check the error messages.")
                return False
            
            # Create all database tables
            db.create_all()
            print("Database tables created successfully.")
            
            # Create backup directories
            os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'backups'), exist_ok=True)
            os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'backups', 'temp'), exist_ok=True)
            
            # Create default admin user if it doesn't exist
            if not User.query.filter_by(role='admin').first():
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    role='admin'
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("Default admin user created: admin/admin123")
            else:
                print("Admin user already exists.")
            
            print("Starting file monitoring service...")
            start_file_monitor()
            print("File monitoring service started.")
            
            return True
            
        except Exception as e:
            print(f"Error during database initialization: {e}")
            return False

# Main execution
if __name__ == '__main__':
    try:
        print("Enterprise File Monitor starting...")
        if not initialize_database():
            print("❌ Failed to initialize database. Exiting.")
            exit(1)
        
        create_default_categories()
        
        if not os.environ.get('WERKZEUG_RUN_MAIN'):
            print("="*50)
            print("Enterprise File Monitor is running!")
            print("URL: http://localhost:5002")
            print("Default login: admin / admin123")
            print("="*50)
        
        app.run(debug=False, host='0.0.0.0', port=5002, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        stop_file_monitor()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")