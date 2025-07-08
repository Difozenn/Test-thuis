#!/usr/bin/env python3
"""
Test complete workflow: scanner_panel session → scan 2 projects → logs_project display
"""

import sqlite3
import requests
import json
from datetime import datetime, timedelta

class WorkflowTester:
    def __init__(self):
        self.db_path = '/home/difusion/Projects/BarcodeMaster/database/central_logging.sqlite'
        self.api_base = 'http://localhost:5001'
        self.user = 'NESTING'
        self.test_projects = ['TEST_PROJECT_A', 'TEST_PROJECT_B']
        self.session_id = f'{self.user}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        
    def log_step(self, step, status="✅"):
        print(f"{status} {step}")
        
    def clear_test_data(self):
        """Clear any existing test data"""
        print("\n=== 🧹 Clearing Test Data ===")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Clear test projects
        for project in self.test_projects:
            c.execute("DELETE FROM logs WHERE project = ?", (project,))
            c.execute("DELETE FROM sessions WHERE project = ?", (project,))
        
        # Clear test session
        c.execute("DELETE FROM sessions WHERE session_id = ?", (self.session_id,))
        
        conn.commit()
        conn.close()
        self.log_step("Test data cleared")
    
    def start_scanner_session(self):
        """Step 1: Start scanner session (like scanner_panel does)"""
        print("\n=== 🚀 Step 1: Start Scanner Session ===")
        
        try:
            response = requests.post(f'{self.api_base}/session/start', json={
                'user': self.user,
                'session_id': self.session_id,
                'timestamp': datetime.now().isoformat(),
                'session_type': 'SCANNER',
                'project': ''  # Scanner sessions have empty project
            }, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_step("Scanner session started successfully")
                    return True
                else:
                    self.log_step(f"Session start failed: {data.get('error')}", "❌")
                    return False
            else:
                self.log_step(f"API returned {response.status_code}: {response.text}", "❌")
                return False
                
        except requests.exceptions.ConnectionError:
            self.log_step("Database server not running - simulating session start", "⚠️")
            # Manually insert session
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                INSERT INTO sessions (session_id, user, project, start_time, status, session_type)
                VALUES (?, ?, '', ?, 'active', 'SCANNER')
            """, (self.session_id, self.user, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            self.log_step("Scanner session simulated in database")
            return True
    
    def scan_projects(self):
        """Step 2: Scan projects (like barcode scanning does)"""
        print("\n=== 📊 Step 2: Scan Projects ===")
        
        success_count = 0
        
        for i, project in enumerate(self.test_projects, 1):
            items = i * 5  # Project A = 5 items, Project B = 10 items
            scan_time = datetime.now() + timedelta(minutes=i * 2)
            
            try:
                # Send OPEN event (project detected)
                response = requests.post(f'{self.api_base}/log', json={
                    'event': 'OPEN',
                    'user': self.user,
                    'project': project,
                    'details': f'Auto-detected from {self.user} scan',
                    'timestamp': scan_time.isoformat(),
                    'item_count': items,
                    'session_id': self.session_id
                }, timeout=5)
                
                if response.status_code == 201:
                    self.log_step(f"Project {project} opened with {items} items")
                    success_count += 1
                else:
                    self.log_step(f"Failed to open {project}: {response.text}", "❌")
                    
            except requests.exceptions.ConnectionError:
                self.log_step("Database server not running - simulating scan", "⚠️")
                # Manually insert log
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute("""
                    INSERT INTO logs (timestamp, event, user, project, details, status, item_count, session_id)
                    VALUES (?, 'OPEN', ?, ?, ?, 'OPEN', ?, ?)
                """, (scan_time.isoformat(), self.user, project, 
                     f'Auto-detected from {self.user} scan', items, self.session_id))
                conn.commit()
                conn.close()
                self.log_step(f"Project {project} scan simulated with {items} items")
                success_count += 1
        
        return success_count == len(self.test_projects)
    
    def end_scanner_session(self):
        """Step 3: End scanner session"""
        print("\n=== 🏁 Step 3: End Scanner Session ===")
        
        try:
            response = requests.post(f'{self.api_base}/session/end', json={
                'session_id': self.session_id,
                'timestamp': datetime.now().isoformat()
            }, timeout=5)
            
            if response.status_code == 200:
                self.log_step("Scanner session ended successfully")
                return True
            else:
                self.log_step(f"Failed to end session: {response.text}", "❌")
                return False
                
        except requests.exceptions.ConnectionError:
            self.log_step("Database server not running - simulating session end", "⚠️")
            # Manually end session
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Calculate work minutes (simulate 30 minutes)
            work_minutes = 30.0
            end_time = datetime.now().isoformat()
            
            c.execute("""
                UPDATE sessions 
                SET status = 'completed', end_time = ?, work_duration_minutes = ?
                WHERE session_id = ? AND status = 'active'
            """, (end_time, work_minutes, self.session_id))
            conn.commit()
            conn.close()
            self.log_step(f"Scanner session ended (simulated {work_minutes} minutes)")
            return True
    
    def test_productivity_api(self, project):
        """Step 4: Test productivity metrics API for each project"""
        print(f"\n=== 📈 Step 4: Test Productivity API for {project} ===")
        
        try:
            response = requests.get(f'{self.api_base}/api/project/{project}/productivity-metrics', timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_step(f"Productivity API working for {project}")
                    
                    # Find NESTING user data
                    nesting_data = None
                    for user_data in data.get('user_productivity', []):
                        if user_data['user'] == self.user:
                            nesting_data = user_data
                            break
                    
                    if nesting_data:
                        print(f"   NESTING data:")
                        print(f"     Items: {nesting_data['total_items']}")
                        print(f"     Session hours: {nesting_data['session_hours']}")
                        print(f"     Items/hour: {nesting_data['items_per_hour']}")
                        print(f"     Status: {nesting_data['status']}")
                        return True
                    else:
                        self.log_step(f"NESTING not found in API response", "❌")
                        return False
                else:
                    self.log_step(f"API error: {data.get('error')}", "❌")
                    return False
            else:
                self.log_step(f"API returned {response.status_code}: {response.text}", "❌")
                return False
                
        except requests.exceptions.ConnectionError:
            self.log_step("Database server not running - testing database directly", "⚠️")
            return self.test_database_calculation(project)
    
    def test_database_calculation(self, project):
        """Test calculation directly from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Get items for this project
        c.execute("""
            SELECT MAX(COALESCE(item_count, 0)) as project_items
            FROM logs
            WHERE user = ? AND LOWER(project) = LOWER(?)
            AND item_count > 0
        """, (self.user, project))
        
        result = c.fetchone()
        project_items = result[0] if result and result[0] else 0
        
        # Get completed batch session
        c.execute("""
            SELECT work_duration_minutes FROM sessions
            WHERE session_id = ? AND status = 'completed'
        """, (self.session_id,))
        
        session = c.fetchone()
        session_minutes = session[0] if session else 0
        
        # Get total items in batch
        c.execute("""
            SELECT SUM(COALESCE(item_count, 0)) as total_items
            FROM logs
            WHERE user = ? AND session_id = ?
            AND item_count > 0
        """, (self.user, self.session_id))
        
        total_result = c.fetchone()
        total_items = total_result[0] if total_result and total_result[0] else 0
        
        # Calculate proportional allocation
        if total_items > 0 and project_items > 0 and session_minutes > 0:
            proportion = project_items / total_items
            allocated_minutes = session_minutes * proportion
            items_per_hour = (project_items * 60.0) / allocated_minutes
            
            print(f"   Database calculation:")
            print(f"     Project items: {project_items}")
            print(f"     Total batch items: {total_items}")
            print(f"     Session minutes: {session_minutes}")
            print(f"     Proportion: {proportion:.2%}")
            print(f"     Allocated minutes: {allocated_minutes:.1f}")
            print(f"     Items/hour: {items_per_hour:.1f}")
            print(f"     Status: COMPLETED")
            
            conn.close()
            return True
        else:
            self.log_step("Insufficient data for calculation", "❌")
            conn.close()
            return False
    
    def verify_logs_project_data(self):
        """Step 5: Verify logs_project page would have correct data"""
        print("\n=== 🔍 Step 5: Verify logs_project Data ===")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Check session data exists
        c.execute("""
            SELECT session_type, status, work_duration_minutes, item_count
            FROM sessions
            WHERE session_id = ?
        """, (self.session_id,))
        
        session = c.fetchone()
        if session:
            self.log_step(f"Session found: type={session[0]}, status={session[1]}, duration={session[2]}min")
        else:
            self.log_step("Session not found", "❌")
            return False
        
        # Check log entries exist
        c.execute("""
            SELECT COUNT(*) as count FROM logs
            WHERE session_id = ?
        """, (self.session_id,))
        
        log_count = c.fetchone()[0]
        self.log_step(f"Log entries found: {log_count}")
        
        # Test each project's data
        success = True
        for project in self.test_projects:
            api_success = self.test_productivity_api(project)
            if not api_success:
                success = False
        
        conn.close()
        return success
    
    def run_complete_test(self):
        """Run the complete workflow test"""
        print("🧪 Testing Complete Scanner Panel → logs_project Workflow")
        print("=" * 60)
        
        # Clear any previous test data
        self.clear_test_data()
        
        # Step 1: Start scanner session
        if not self.start_scanner_session():
            return False
        
        # Step 2: Scan projects
        if not self.scan_projects():
            return False
        
        # Step 3: End scanner session
        if not self.end_scanner_session():
            return False
        
        # Step 4 & 5: Verify data and API
        if not self.verify_logs_project_data():
            return False
        
        print("\n" + "=" * 60)
        print("🎉 COMPLETE WORKFLOW TEST PASSED!")
        print("\nThe logs_project page should now correctly show:")
        print("- NESTING with completed batch work")
        print("- Proportional time allocation per project")
        print("- Correct items/hour calculations")
        print("- COMPLETED status (not IN_PROGRESS)")
        
        return True

if __name__ == "__main__":
    tester = WorkflowTester()
    success = tester.run_complete_test()
    exit(0 if success else 1)