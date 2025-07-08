#!/usr/bin/env python3
"""
Complete BarcodeMaster Workflow Frontend Test

This script simulates the entire BarcodeMaster workflow by sending database events
and then tests if the frontend displays them correctly.

Workflow Steps:
1. NESTING scans OPEN → triggers chain
2. Background service creates XLSX_UPDATED sessions for OPUS/GANNOMAT
3. Users work simultaneously in batch
4. AFGEMELD events complete projects
5. Verify frontend displays all stages correctly
"""

import requests
import json
import time
from datetime import datetime, timedelta
import uuid

class WorkflowTester:
    def __init__(self, api_base='http://localhost:5001', project='TEST_WORKFLOW_001'):
        self.api_base = api_base
        self.project = project
        self.session_data = {}
        self.users = ['NESTING', 'OPUS', 'KL GANNOMAT']
        
    def log_step(self, step, status="✓"):
        print(f"{status} {step}")
        
    def send_request(self, endpoint, data=None, method='POST'):
        """Send request to API and handle errors"""
        try:
            url = f"{self.api_base}{endpoint}"
            if method == 'POST':
                response = requests.post(url, json=data, timeout=10)
            else:
                response = requests.get(url, timeout=10)
                
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Request failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Request error: {e}")
            return None
    
    def test_api_availability(self):
        """Test if API is available"""
        print("\n=== 🔍 Testing API Availability ===")
        
        result = self.send_request('/api/statistics/productivity-metrics', method='GET')
        if result:
            self.log_step("API is running and responsive")
            return True
        else:
            self.log_step("API not available", "❌")
            return False
    
    def phase_1_scanner_open_event(self):
        """Phase 1: NESTING scans OPEN event (triggers workflow chain)"""
        print("\n=== 📁 Phase 1: Scanner OPEN Event ===")
        
        # Start main scanner session
        session_id = f"NESTING_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.session_data['main_session'] = session_id
        
        session_data = {
            'session_id': session_id,
            'user': 'NESTING',
            'timestamp': datetime.now().isoformat(),
            'session_type': 'SCANNER'
        }
        
        result = self.send_request('/session/start', session_data)
        if result and result.get('success'):
            self.log_step(f"Main scanner session started: {session_id}")
        else:
            self.log_step("Failed to start main session", "❌")
            return False
        
        # Send OPEN event (this triggers the workflow chain)
        open_data = {
            'event': 'OPEN',
            'user': 'NESTING',
            'project': self.project,
            'details': f'Project {self.project} opened for processing',
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id
        }
        
        result = self.send_request('/log', open_data)
        if result and result.get('success'):
            self.log_step(f"OPEN event logged for {self.project}")
            time.sleep(2)  # Allow cascade processing
            return True
        else:
            self.log_step("Failed to log OPEN event", "❌")
            return False
    
    def phase_2_background_xlsx_sessions(self):
        """Phase 2: Background service creates XLSX_UPDATED sessions"""
        print("\n=== 🔄 Phase 2: Background XLSX_UPDATED Sessions ===")
        
        # Simulate background service creating XLSX_UPDATED sessions
        for user in ['OPUS', 'KL GANNOMAT']:
            xlsx_data = {
                'user': user,
                'project': self.project,
                'timestamp': (datetime.now() + timedelta(seconds=5)).isoformat(),
                'item_count': 0  # Starts at 0, will be updated on AFGEMELD
            }
            
            result = self.send_request('/session/xlsx_updated', xlsx_data)
            if result and result.get('success'):
                self.log_step(f"XLSX_UPDATED session created for {user}")
            else:
                self.log_step(f"Failed to create XLSX_UPDATED session for {user}", "❌")
                return False
        
        time.sleep(3)  # Allow processing
        return True
    
    def phase_3_concurrent_work(self):
        """Phase 3: Simulate concurrent work (all users working simultaneously)"""
        print("\n=== ⚡ Phase 3: Concurrent Batch Processing ===")
        
        # Simulate work progression over time
        work_duration = 30  # seconds of simulated work
        print(f"Simulating {work_duration} seconds of concurrent work...")
        
        # Add some intermediate events to show activity
        intermediate_events = [
            ('NESTING', 'Processing batch items', 10),
            ('OPUS', 'XLSX file processing started', 15),
            ('KL GANNOMAT', 'MDB processing initiated', 20),
        ]
        
        for user, detail, delay in intermediate_events:
            time.sleep(delay)
            
            # Log work progress event
            progress_data = {
                'event': 'WERK_UPDATE',
                'user': user,
                'project': self.project,
                'details': detail,
                'timestamp': datetime.now().isoformat()
            }
            
            result = self.send_request('/log', progress_data)
            if result:
                self.log_step(f"{user}: {detail}")
        
        return True
    
    def phase_4_afgemeld_completion(self):
        """Phase 4: AFGEMELD events (project completion)"""
        print("\n=== ✅ Phase 4: Project Completion (AFGEMELD) ===")
        
        # Define completion order and item counts
        completions = [
            ('NESTING', 45, 5),    # 45 items, 5 second delay
            ('OPUS', 32, 3),       # 32 items, 3 second delay  
            ('KL GANNOMAT', 28, 2) # 28 items, 2 second delay
        ]
        
        for user, item_count, delay in completions:
            time.sleep(delay)
            
            afgemeld_data = {
                'event': 'AFGEMELD',
                'user': user,
                'project': self.project,
                'details': f'{self.project} completed by {user}',
                'item_count': item_count,
                'timestamp': datetime.now().isoformat()
            }
            
            result = self.send_request('/log', afgemeld_data)
            if result and result.get('success'):
                self.log_step(f"{user} completed with {item_count} items")
            else:
                self.log_step(f"Failed to complete {user}", "❌")
                return False
        
        return True
    
    def phase_5_end_main_session(self):
        """Phase 5: End main scanner session"""
        print("\n=== 🏁 Phase 5: End Main Session ===")
        
        if 'main_session' not in self.session_data:
            self.log_step("No main session to end", "❌")
            return False
        
        end_data = {
            'session_id': self.session_data['main_session'],
            'user': 'NESTING',
            'timestamp': datetime.now().isoformat()
        }
        
        result = self.send_request('/session/end', end_data)
        if result and result.get('success'):
            self.log_step("Main session ended successfully")
            return True
        else:
            self.log_step("Failed to end main session", "❌")
            return False
    
    def verify_frontend_data(self):
        """Phase 6: Verify frontend receives correct data"""
        print("\n=== 📺 Phase 6: Frontend Data Verification ===")
        
        # Test logs_project endpoint
        try:
            url = f"{self.api_base}/logs_project?project={self.project}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                self.log_step("logs_project page accessible")
                
                # Check if page contains our test data
                page_content = response.text
                
                checks = [
                    (self.project in page_content, f"Project {self.project} found in page"),
                    ('NESTING' in page_content, "NESTING user found"),
                    ('OPUS' in page_content, "OPUS user found"),
                    ('KL GANNOMAT' in page_content, "KL GANNOMAT user found"),
                    ('AFGEMELD' in page_content, "AFGEMELD events found"),
                    ('logData' in page_content, "JavaScript log data present"),
                    ('sessionsData' in page_content, "JavaScript sessions data present")
                ]
                
                for check_passed, description in checks:
                    status = "✓" if check_passed else "❌"
                    self.log_step(description, status)
                    
            else:
                self.log_step(f"logs_project page failed: {response.status_code}", "❌")
                
        except Exception as e:
            self.log_step(f"Frontend verification error: {e}", "❌")
        
        # Test API endpoints
        endpoints_to_test = [
            f'/api/project/{self.project}/productivity-metrics',
            '/api/statistics/productivity-metrics',
            f'/api/project/{self.project}/sessions'
        ]
        
        for endpoint in endpoints_to_test:
            result = self.send_request(endpoint, method='GET')
            if result and result.get('success'):
                self.log_step(f"API endpoint working: {endpoint}")
            else:
                self.log_step(f"API endpoint failed: {endpoint}", "❌")
    
    def cleanup_test_data(self):
        """Clean up test data (optional)"""
        print("\n=== 🧹 Cleanup (Optional) ===")
        print(f"Test data created for project: {self.project}")
        print("You can view the results at:")
        print(f"  - Project page: {self.api_base}/logs_project?project={self.project}")
        print(f"  - API data: {self.api_base}/api/project/{self.project}/productivity-metrics")
    
    def run_complete_test(self):
        """Run the complete workflow test"""
        print("🧪 BarcodeMaster Complete Workflow Frontend Test")
        print("=" * 60)
        print(f"Testing project: {self.project}")
        print(f"API endpoint: {self.api_base}")
        print(f"Users: {', '.join(self.users)}")
        
        # Run all phases
        phases = [
            ("API Availability", self.test_api_availability),
            ("Scanner OPEN Event", self.phase_1_scanner_open_event),
            ("Background XLSX Sessions", self.phase_2_background_xlsx_sessions),
            ("Concurrent Work", self.phase_3_concurrent_work),
            ("AFGEMELD Completion", self.phase_4_afgemeld_completion),
            ("End Main Session", self.phase_5_end_main_session),
            ("Frontend Verification", self.verify_frontend_data)
        ]
        
        success_count = 0
        for phase_name, phase_func in phases:
            try:
                if phase_func():
                    success_count += 1
                else:
                    print(f"\n❌ Phase '{phase_name}' failed!")
                    break
            except Exception as e:
                print(f"\n❌ Phase '{phase_name}' error: {e}")
                break
        
        # Final results
        print("\n" + "=" * 60)
        print("🏆 TEST RESULTS")
        print("=" * 60)
        
        if success_count == len(phases):
            print("✅ ALL PHASES COMPLETED SUCCESSFULLY!")
            print("\n🎯 Frontend should now display:")
            print("  - Complete workflow chain with all user statuses")
            print("  - Live activity timeline with all events")
            print("  - Project activity log with full workflow")
            print("  - Proper proportional time allocation in metrics")
        else:
            print(f"❌ {success_count}/{len(phases)} phases completed")
            print("Some issues need to be resolved.")
        
        self.cleanup_test_data()
        
        return success_count == len(phases)

if __name__ == "__main__":
    tester = WorkflowTester()
    tester.run_complete_test()