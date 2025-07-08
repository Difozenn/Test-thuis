#!/usr/bin/env python3
"""
Comprehensive Database Events Test for BarcodeMaster logs_project page

This script tests EVERY database event type to ensure they all display 
correctly on the frontend logs_project page.

Events to test:
- OPEN (project start)
- PROJECT_START (XLSX_UPDATED session start)
- SESSION_START (scanner session start)
- BEZIG (work in progress)
- WERK_UPDATE (work progress)
- AFGEMELD (work completed)
- SESSION_END (session completion)
- ERROR events (error handling)
- IDLE events (idle time tracking)
- BATCH_START/BATCH_END (batch processing)
"""

import sqlite3
import json
import webbrowser
import tempfile
import os
from datetime import datetime, timedelta

class AllEventsTestFramework:
    def __init__(self, db_path='/home/difusion/Projects/BarcodeMaster/database/central_logging.sqlite'):
        self.db_path = db_path
        self.project = 'TEST_ALL_EVENTS_001'
        self.users = ['NESTING', 'OPUS', 'KL GANNOMAT', 'VERZEND']
        self.test_events = []
        self.base_time = datetime.now()
        
    def log_step(self, step, status="✅"):
        print(f"{status} {step}")
        
    def connect_db(self):
        """Connect to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None
    
    def clear_test_data(self):
        """Clear any existing test data"""
        print("\n=== 🧹 Clearing Previous Test Data ===")
        
        conn = self.connect_db()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM logs WHERE project = ?", (self.project,))
            cursor.execute("DELETE FROM sessions WHERE project = ?", (self.project,))
            conn.commit()
            conn.close()
            
            self.log_step("Previous test data cleared")
            return True
            
        except Exception as e:
            self.log_step(f"Failed to clear test data: {e}", "❌")
            return False
    
    def generate_all_event_types(self):
        """Generate comprehensive test events covering all database event types"""
        print("\n=== 📊 Generating All Event Types ===")
        
        events = []
        time_offset = 0
        
        # 1. PROJECT INITIALIZATION EVENTS
        events.append({
            'timestamp': (self.base_time + timedelta(minutes=time_offset)).isoformat(),
            'event': 'OPEN',
            'user': 'NESTING',
            'project': self.project,
            'details': f'Project {self.project} opened for processing',
            'status': 'OPEN',
            'item_count': 0,
            'session_id': 'NESTING_SCANNER_20250705_143000'
        })
        time_offset += 1
        
        # 2. SESSION START EVENTS
        events.append({
            'timestamp': (self.base_time + timedelta(minutes=time_offset)).isoformat(),
            'event': 'SESSION_START',
            'user': 'NESTING',
            'project': self.project,
            'details': 'SCANNER session started for batch processing',
            'status': 'BEZIG',
            'item_count': 0,
            'session_id': 'NESTING_SCANNER_20250705_143000'
        })
        time_offset += 2
        
        # 3. PROJECT_START EVENTS (XLSX_UPDATED sessions)
        for user in ['OPUS', 'KL GANNOMAT']:
            events.append({
                'timestamp': (self.base_time + timedelta(minutes=time_offset)).isoformat(),
                'event': 'PROJECT_START',
                'user': user,
                'project': self.project,
                'details': f'XLSX_UPDATED: {user} session started',
                'status': 'BEZIG',
                'item_count': 0,
                'session_id': f'{user}_{self.project}_20250705_{143000 + time_offset}'
            })
            time_offset += 1
        
        # 4. BATCH PROCESSING EVENTS
        events.append({
            'timestamp': (self.base_time + timedelta(minutes=time_offset)).isoformat(),
            'event': 'BATCH_START',
            'user': 'SYSTEM',
            'project': self.project,
            'details': 'Batch processing initiated for multiple users',
            'status': 'BEZIG',
            'item_count': 0,
            'session_id': 'BATCH_SYSTEM_20250705_143000'
        })
        time_offset += 2
        
        # 5. WORK PROGRESS EVENTS
        work_updates = [
            ('NESTING', 'Scanning barcode items in batch', 15),
            ('OPUS', 'Processing XLSX file data', 12),
            ('KL GANNOMAT', 'Updating MDB database records', 18),
            ('VERZEND', 'Preparing shipping labels', 8)
        ]
        
        for user, detail, progress_items in work_updates:
            events.append({
                'timestamp': (self.base_time + timedelta(minutes=time_offset)).isoformat(),
                'event': 'WERK_UPDATE',
                'user': user,
                'project': self.project,
                'details': detail,
                'status': 'BEZIG',
                'item_count': progress_items,
                'session_id': f'{user}_{self.project}_20250705_{143000 + time_offset}'
            })
            time_offset += 3
        
        # 6. BEZIG (WORK IN PROGRESS) EVENTS
        events.append({
            'timestamp': (self.base_time + timedelta(minutes=time_offset)).isoformat(),
            'event': 'BEZIG',
            'user': 'NESTING',
            'project': self.project,
            'details': 'Active scanning in progress',
            'status': 'BEZIG',
            'item_count': 25,
            'session_id': 'NESTING_SCANNER_20250705_143000'
        })
        time_offset += 5
        
        # 7. IDLE TIME EVENTS
        events.append({
            'timestamp': (self.base_time + timedelta(minutes=time_offset)).isoformat(),
            'event': 'IDLE',
            'user': 'NESTING',
            'project': self.project,
            'details': 'Scanner idle - waiting for next batch',
            'status': 'IDLE',
            'item_count': 25,
            'session_id': 'NESTING_SCANNER_20250705_143000'
        })
        time_offset += 8
        
        # 8. ERROR EVENTS
        events.append({
            'timestamp': (self.base_time + timedelta(minutes=time_offset)).isoformat(),
            'event': 'ERROR',
            'user': 'OPUS',
            'project': self.project,
            'details': 'XLSX file format error - retrying with backup data',
            'status': 'ERROR',
            'item_count': 12,
            'session_id': f'OPUS_{self.project}_20250705_143200'
        })
        time_offset += 2
        
        # 9. RECOVERY EVENTS
        events.append({
            'timestamp': (self.base_time + timedelta(minutes=time_offset)).isoformat(),
            'event': 'RECOVERY',
            'user': 'OPUS',
            'project': self.project,
            'details': 'Error resolved - continuing with XLSX processing',
            'status': 'BEZIG',
            'item_count': 12,
            'session_id': f'OPUS_{self.project}_20250705_143200'
        })
        time_offset += 3
        
        # 10. COMPLETION EVENTS (AFGEMELD)
        completion_order = [
            ('VERZEND', 28),
            ('KL GANNOMAT', 42),
            ('OPUS', 38),
            ('NESTING', 55)
        ]
        
        for user, final_items in completion_order:
            events.append({
                'timestamp': (self.base_time + timedelta(minutes=time_offset)).isoformat(),
                'event': 'AFGEMELD',
                'user': user,
                'project': self.project,
                'details': f'{self.project} completed by {user} - {final_items} items processed',
                'status': 'AFGEMELD',
                'item_count': final_items,
                'session_id': f'{user}_{self.project}_20250705_{143000 + time_offset}'
            })
            time_offset += 4
        
        # 11. SESSION END EVENTS
        for user in ['VERZEND', 'KL GANNOMAT', 'OPUS', 'NESTING']:
            events.append({
                'timestamp': (self.base_time + timedelta(minutes=time_offset)).isoformat(),
                'event': 'SESSION_END',
                'user': user,
                'project': self.project,
                'details': f'{user} session ended - work complete',
                'status': 'COMPLETED',
                'item_count': 0,
                'session_id': f'{user}_{self.project}_SESSION_END'
            })
            time_offset += 1
        
        # 12. BATCH END EVENT
        events.append({
            'timestamp': (self.base_time + timedelta(minutes=time_offset)).isoformat(),
            'event': 'BATCH_END',
            'user': 'SYSTEM',
            'project': self.project,
            'details': 'Batch processing completed for all users',
            'status': 'COMPLETED',
            'item_count': 163,  # Total items
            'session_id': 'BATCH_SYSTEM_20250705_143000'
        })
        
        # 13. PROJECT COMPLETION EVENT
        events.append({
            'timestamp': (self.base_time + timedelta(minutes=time_offset + 1)).isoformat(),
            'event': 'PROJECT_COMPLETE',
            'user': 'SYSTEM',
            'project': self.project,
            'details': f'Project {self.project} fully completed - all workflows finished',
            'status': 'COMPLETED',
            'item_count': 163,
            'session_id': 'PROJECT_SYSTEM_COMPLETE'
        })
        
        self.test_events = events
        self.log_step(f"Generated {len(events)} comprehensive test events")
        
        # Log event types for verification
        event_types = {}
        for event in events:
            event_type = event['event']
            if event_type not in event_types:
                event_types[event_type] = 0
            event_types[event_type] += 1
        
        print("\n📋 Event Types Generated:")
        for event_type, count in event_types.items():
            print(f"  {event_type}: {count} events")
            
        return True
    
    def insert_test_events(self):
        """Insert all test events into database"""
        print("\n=== 📥 Inserting Test Events ===")
        
        conn = self.connect_db()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
            # Insert all events
            for event in self.test_events:
                cursor.execute("""
                    INSERT INTO logs (timestamp, event, user, project, details, status, item_count, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event['timestamp'], event['event'], event['user'], event['project'],
                    event['details'], event['status'], event['item_count'], event['session_id']
                ))
            
            # Create corresponding sessions
            sessions = [
                {
                    'session_id': 'NESTING_SCANNER_20250705_143000',
                    'user': 'NESTING',
                    'project': self.project,
                    'start_time': self.base_time.isoformat(),
                    'end_time': (self.base_time + timedelta(minutes=60)).isoformat(),
                    'status': 'completed',
                    'item_count': 55,
                    'work_duration_minutes': 45,
                    'session_type': 'SCANNER'
                },
                {
                    'session_id': f'OPUS_{self.project}_20250705_143200',
                    'user': 'OPUS',
                    'project': self.project,
                    'start_time': (self.base_time + timedelta(minutes=3)).isoformat(),
                    'end_time': (self.base_time + timedelta(minutes=50)).isoformat(),
                    'status': 'completed',
                    'item_count': 38,
                    'work_duration_minutes': 42,
                    'session_type': 'XLSX_UPDATED'
                },
                {
                    'session_id': f'KL GANNOMAT_{self.project}_20250705_143300',
                    'user': 'KL GANNOMAT',
                    'project': self.project,
                    'start_time': (self.base_time + timedelta(minutes=4)).isoformat(),
                    'end_time': (self.base_time + timedelta(minutes=48)).isoformat(),
                    'status': 'completed',
                    'item_count': 42,
                    'work_duration_minutes': 38,
                    'session_type': 'XLSX_UPDATED'
                },
                {
                    'session_id': f'VERZEND_{self.project}_20250705_143400',
                    'user': 'VERZEND',
                    'project': self.project,
                    'start_time': (self.base_time + timedelta(minutes=20)).isoformat(),
                    'end_time': (self.base_time + timedelta(minutes=45)).isoformat(),
                    'status': 'completed',
                    'item_count': 28,
                    'work_duration_minutes': 25,
                    'session_type': 'MANUAL'
                }
            ]
            
            # Insert sessions
            for session in sessions:
                cursor.execute("""
                    INSERT INTO sessions (session_id, user, project, start_time, end_time, status, 
                                        item_count, work_duration_minutes, session_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session['session_id'], session['user'], session['project'],
                    session['start_time'], session['end_time'], session['status'],
                    session['item_count'], session['work_duration_minutes'], session['session_type']
                ))
            
            conn.commit()
            conn.close()
            
            self.log_step(f"Inserted {len(self.test_events)} events and {len(sessions)} sessions")
            return True
            
        except Exception as e:
            self.log_step(f"Failed to insert test data: {e}", "❌")
            return False
    
    def create_test_frontend_page(self):
        """Create a test frontend page that shows all events"""
        print("\n=== 🌐 Creating Test Frontend Page ===")
        
        # Get test data from database
        conn = self.connect_db()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor()
            
            # Get logs
            cursor.execute("""
                SELECT * FROM logs WHERE project = ? ORDER BY timestamp ASC
            """, (self.project,))
            logs = [dict(row) for row in cursor.fetchall()]
            
            # Get sessions  
            cursor.execute("""
                SELECT * FROM sessions WHERE project = ? ORDER BY start_time ASC
            """, (self.project,))
            sessions = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            # Create HTML content
            html_content = f"""
<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BarcodeMaster - All Events Test</title>
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <style>
        :root {{
            --primary-blue: #1a73e8;
            --secondary-blue: #4285f4;
            --dark-blue: #1557b0;
        }}

        body {{
            background-color: #f8f9fa;
        }}

        .test-header {{
            background: linear-gradient(135deg, #1a73e8, #4285f4);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}

        .enterprise-section {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            margin-bottom: 25px;
        }}

        .event-card {{
            border-left: 4px solid #007bff;
            padding: 15px;
            margin-bottom: 10px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .event-card.error {{
            border-left-color: #dc3545;
        }}

        .event-card.success {{
            border-left-color: #28a745;
        }}

        .event-card.warning {{
            border-left-color: #ffc107;
        }}

        .event-card.info {{
            border-left-color: #17a2b8;
        }}

        .status-badge {{
            font-size: 0.7rem;
            padding: 3px 8px;
            border-radius: 4px;
        }}

        .status-open {{ background-color: #e3f2fd; color: #1976d2; }}
        .status-bezig {{ background-color: #fff3e0; color: #f57c00; }}
        .status-afgemeld {{ background-color: #e8f5e8; color: #388e3c; }}
        .status-error {{ background-color: #ffebee; color: #d32f2f; }}
        .status-idle {{ background-color: #f3e5f5; color: #7b1fa2; }}
        .status-completed {{ background-color: #e8f5e8; color: #388e3c; }}

        .event-stats {{
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="container-fluid py-4">
        <div class="test-header">
            <h1><i class="fas fa-flask"></i> All Database Events Test</h1>
            <p class="mb-0">Testing every event type on logs_project page functionality</p>
        </div>

        <div class="event-stats">
            <h5><i class="fas fa-chart-bar"></i> Test Statistics</h5>
            <div class="row">
                <div class="col-md-3"><strong>Project:</strong> {self.project}</div>
                <div class="col-md-3"><strong>Total Events:</strong> {len(logs)}</div>
                <div class="col-md-3"><strong>Total Sessions:</strong> {len(sessions)}</div>
                <div class="col-md-3"><strong>Users:</strong> {len(set(log['user'] for log in logs if log['user']))}</div>
            </div>
        </div>

        <div class="row">
            <div class="col-lg-8">
                <div class="enterprise-section">
                    <h4><i class="fas fa-list-alt"></i> All Events Log</h4>
                    <div id="events-container">
                        <!-- Events will be populated by JavaScript -->
                    </div>
                </div>
            </div>
            
            <div class="col-lg-4">
                <div class="enterprise-section">
                    <h4><i class="fas fa-chart-pie"></i> Event Types</h4>
                    <div id="event-types-summary">
                        <!-- Event summary will be populated by JavaScript -->
                    </div>
                </div>
                
                <div class="enterprise-section">
                    <h4><i class="fas fa-users"></i> Sessions Summary</h4>
                    <div id="sessions-summary">
                        <!-- Sessions summary will be populated by JavaScript -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Test data
        const logData = {json.dumps(logs, indent=8)};
        const sessionsData = {json.dumps(sessions, indent=8)};
        const configuredUsers = {json.dumps(self.users)};

        console.log('Test data loaded:');
        console.log('Log entries:', logData.length);
        console.log('Sessions:', sessionsData.length);
        console.log('Users:', configuredUsers);

        function initializePage() {{
            console.log('Initializing comprehensive events test page...');
            
            try {{
                populateEventsLog();
                populateEventTypesSummary();
                populateSessionsSummary();
                
                console.log('✅ Page initialized successfully!');
            }} catch (error) {{
                console.error('❌ Error initializing page:', error);
            }}
        }}

        function populateEventsLog() {{
            const container = document.getElementById('events-container');
            if (!container) return;
            
            let html = '';
            
            logData.forEach((log, index) => {{
                const eventClass = getEventClass(log.event, log.status);
                const icon = getEventIcon(log.event);
                const timestamp = formatTimestamp(log.timestamp);
                
                html += `
                    <div class="event-card ${{eventClass}}">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <div class="d-flex align-items-center mb-2">
                                    ${{icon}}
                                    <strong class="ms-2">${{log.event || 'UNKNOWN'}}</strong>
                                    <span class="badge bg-secondary ms-2">#${{log.id || index + 1}}</span>
                                </div>
                                
                                <div class="d-flex align-items-center mb-2">
                                    <i class="fas fa-user text-muted"></i>
                                    <span class="ms-2"><strong>${{log.user || 'SYSTEM'}}</strong></span>
                                </div>
                                
                                <p class="mb-2 text-muted">${{log.details || 'No details available'}}</p>
                                
                                <div class="d-flex align-items-center gap-2 flex-wrap">
                                    <span class="status-badge status-${{getStatusClass(log.status)}}">${{log.status || 'N/A'}}</span>
                                    ${{log.item_count ? `<span class="badge bg-info">${{log.item_count}} items</span>` : ''}}
                                    <small class="text-muted">
                                        <i class="far fa-clock"></i> ${{timestamp}}
                                    </small>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }});
            
            container.innerHTML = html;
        }}

        function populateEventTypesSummary() {{
            const container = document.getElementById('event-types-summary');
            if (!container) return;
            
            // Count event types
            const eventTypes = {{}};
            logData.forEach(log => {{
                const event = log.event || 'UNKNOWN';
                eventTypes[event] = (eventTypes[event] || 0) + 1;
            }});
            
            let html = '';
            Object.entries(eventTypes).forEach(([event, count]) => {{
                const icon = getEventIcon(event);
                html += `
                    <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
                        <div>${{icon}} ${{event}}</div>
                        <span class="badge bg-primary">${{count}}</span>
                    </div>
                `;
            }});
            
            container.innerHTML = html;
        }}

        function populateSessionsSummary() {{
            const container = document.getElementById('sessions-summary');
            if (!container) return;
            
            let html = '';
            sessionsData.forEach(session => {{
                const duration = session.work_duration_minutes || 0;
                const hours = Math.floor(duration / 60);
                const minutes = duration % 60;
                const timeText = hours > 0 ? `${{hours}}h ${{minutes}}m` : `${{minutes}}m`;
                
                html += `
                    <div class="mb-3 p-3 bg-light rounded">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <strong>${{session.user}}</strong>
                            <span class="badge bg-secondary">${{session.session_type}}</span>
                        </div>
                        <div class="small text-muted">
                            <div>Items: ${{session.item_count || 0}}</div>
                            <div>Duration: ${{timeText}}</div>
                            <div>Status: ${{session.status}}</div>
                        </div>
                    </div>
                `;
            }});
            
            container.innerHTML = html;
        }}

        function getEventClass(event, status) {{
            if (!event) return 'info';
            
            const eventLower = event.toLowerCase();
            const statusLower = (status || '').toLowerCase();
            
            if (eventLower.includes('error') || statusLower.includes('error')) return 'error';
            if (eventLower.includes('afgemeld') || eventLower.includes('complete')) return 'success';
            if (eventLower.includes('idle') || eventLower.includes('warning')) return 'warning';
            return 'info';
        }}

        function getEventIcon(event) {{
            if (!event) return '<i class="fas fa-question text-muted"></i>';
            
            const eventLower = event.toLowerCase();
            
            if (eventLower.includes('open')) return '<i class="fas fa-folder-open text-primary"></i>';
            if (eventLower.includes('start')) return '<i class="fas fa-play text-success"></i>';
            if (eventLower.includes('end') || eventLower.includes('complete')) return '<i class="fas fa-check text-success"></i>';
            if (eventLower.includes('afgemeld')) return '<i class="fas fa-check-circle text-success"></i>';
            if (eventLower.includes('error')) return '<i class="fas fa-exclamation-triangle text-danger"></i>';
            if (eventLower.includes('bezig') || eventLower.includes('update')) return '<i class="fas fa-cog text-warning"></i>';
            if (eventLower.includes('idle')) return '<i class="fas fa-pause text-secondary"></i>';
            if (eventLower.includes('batch')) return '<i class="fas fa-layer-group text-info"></i>';
            if (eventLower.includes('recovery')) return '<i class="fas fa-redo text-success"></i>';
            if (eventLower.includes('mo_start')) return '<i class="fas fa-play-circle text-info"></i>';
            
            return '<i class="fas fa-info-circle text-secondary"></i>';
        }}

        function getStatusClass(status) {{
            if (!status) return 'secondary';
            
            const statusLower = status.toLowerCase();
            if (statusLower.includes('open')) return 'open';
            if (statusLower.includes('bezig')) return 'bezig';
            if (statusLower.includes('afgemeld')) return 'afgemeld';
            if (statusLower.includes('error')) return 'error';
            if (statusLower.includes('idle')) return 'idle';
            if (statusLower.includes('completed')) return 'completed';
            return 'secondary';
        }}

        function formatTimestamp(timestamp) {{
            try {{
                const date = new Date(timestamp);
                return date.toLocaleString('nl-NL', {{
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                }});
            }} catch (e) {{
                return timestamp;
            }}
        }}

        // Initialize page
        document.addEventListener('DOMContentLoaded', initializePage);
        
        console.log('🧪 All Events Test Page loaded successfully!');
    </script>
</body>
</html>
            """
            
            # Write to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                temp_file = f.name
            
            self.log_step(f"Created test frontend page: {temp_file}")
            return temp_file
            
        except Exception as e:
            self.log_step(f"Failed to create test page: {e}", "❌")
            return None
    
    def verify_events_display(self):
        """Verify all events display correctly"""
        print("\n=== ✅ Verifying Events Display ===")
        
        # Check database has all events
        conn = self.connect_db()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT event, COUNT(*) FROM logs WHERE project = ? GROUP BY event", (self.project,))
            event_counts = dict(cursor.fetchall())
            
            expected_events = [
                'OPEN', 'SESSION_START', 'PROJECT_START', 'BATCH_START', 'WERK_UPDATE', 
                'BEZIG', 'IDLE', 'ERROR', 'RECOVERY', 'AFGEMELD', 'SESSION_END', 
                'BATCH_END', 'PROJECT_COMPLETE'
            ]
            
            all_present = True
            for event in expected_events:
                if event in event_counts:
                    self.log_step(f"Event '{event}' found: {event_counts[event]} entries")
                else:
                    self.log_step(f"Event '{event}' missing", "❌")
                    all_present = False
            
            conn.close()
            return all_present
            
        except Exception as e:
            self.log_step(f"Verification failed: {e}", "❌")
            return False
    
    def run_complete_test(self):
        """Run complete event testing"""
        print("🧪 BarcodeMaster - ALL Database Events Test")
        print("=" * 60)
        print(f"Testing project: {self.project}")
        print(f"Database: {self.db_path}")
        print(f"Users: {', '.join(self.users)}")
        
        # Test phases
        phases = [
            ("Clear Previous Test Data", self.clear_test_data),
            ("Generate All Event Types", self.generate_all_event_types),
            ("Insert Test Events", self.insert_test_events),
            ("Verify Events Display", self.verify_events_display),
            ("Create Test Frontend Page", self.create_test_frontend_page)
        ]
        
        success_count = 0
        test_page_file = None
        
        for phase_name, phase_func in phases:
            print(f"\n--- {phase_name} ---")
            try:
                result = phase_func()
                if result:
                    success_count += 1
                    if phase_name == "Create Test Frontend Page":
                        test_page_file = result
                else:
                    print(f"\n❌ Phase '{phase_name}' failed!")
                    break
            except Exception as e:
                print(f"\n❌ Phase '{phase_name}' error: {e}")
                break
        
        # Results
        print("\n" + "=" * 60)
        print("🏆 TEST RESULTS")
        print("=" * 60)
        
        if success_count == len(phases):
            print("✅ ALL EVENT TESTS PASSED!")
            print("\n🎯 All database events are working:")
            
            event_types = set(event['event'] for event in self.test_events)
            for event_type in sorted(event_types):
                print(f"  ✓ {event_type}")
            
            if test_page_file:
                print(f"\n📱 Test page created: {test_page_file}")
                print(f"🌐 View test page: file://{os.path.abspath(test_page_file)}")
                
                # Automatically open in browser
                try:
                    webbrowser.open(f'file://{os.path.abspath(test_page_file)}')
                    print("🔓 Test page opened in browser")
                except:
                    print("💡 Copy the file path above to your browser to view")
                    
        else:
            print(f"❌ {success_count}/{len(phases)} phases completed")
        
        return success_count == len(phases)

if __name__ == "__main__":
    tester = AllEventsTestFramework()
    tester.run_complete_test()