#!/usr/bin/env python3
"""
Static Frontend Test for BarcodeMaster Workflow

This script creates a static HTML file with test data to verify
that the frontend JavaScript works correctly with the workflow fixes.
"""

import json
from datetime import datetime, timedelta

def generate_test_data():
    """Generate comprehensive test data for frontend testing"""
    
    base_time = datetime.now()
    project = "TEST_WORKFLOW_001"
    
    # Generate log entries for complete workflow
    log_entries = [
        {
            "id": 1,
            "timestamp": (base_time).isoformat(),
            "event": "OPEN",
            "user": "NESTING",
            "project": project,
            "details": f"Project {project} opened for processing",
            "status": "OPEN",
            "item_count": 0,
            "session_id": "NESTING_20250705_143000"
        },
        {
            "id": 2,
            "timestamp": (base_time + timedelta(minutes=2)).isoformat(),
            "event": "PROJECT_START",
            "user": "OPUS",
            "project": project,
            "details": "XLSX_UPDATED: 0 items",
            "status": "BEZIG",
            "item_count": 0,
            "session_id": "OPUS_TEST_WORKFLOW_001_20250705_143200"
        },
        {
            "id": 3,
            "timestamp": (base_time + timedelta(minutes=3)).isoformat(),
            "event": "PROJECT_START",
            "user": "KL GANNOMAT",
            "project": project,
            "details": "XLSX_UPDATED: 0 items",
            "status": "BEZIG",
            "item_count": 0,
            "session_id": "GANNOMAT_TEST_WORKFLOW_001_20250705_143300"
        },
        {
            "id": 4,
            "timestamp": (base_time + timedelta(minutes=15)).isoformat(),
            "event": "WERK_UPDATE",
            "user": "NESTING",
            "project": project,
            "details": "Processing batch items",
            "status": "BEZIG",
            "item_count": 0,
            "session_id": "NESTING_20250705_143000"
        },
        {
            "id": 5,
            "timestamp": (base_time + timedelta(minutes=20)).isoformat(),
            "event": "WERK_UPDATE",
            "user": "OPUS",
            "project": project,
            "details": "XLSX file processing started",
            "status": "BEZIG",
            "item_count": 0,
            "session_id": "OPUS_TEST_WORKFLOW_001_20250705_143200"
        },
        {
            "id": 6,
            "timestamp": (base_time + timedelta(minutes=25)).isoformat(),
            "event": "WERK_UPDATE",
            "user": "KL GANNOMAT",
            "project": project,
            "details": "MDB processing initiated",
            "status": "BEZIG",
            "item_count": 0,
            "session_id": "GANNOMAT_TEST_WORKFLOW_001_20250705_143300"
        },
        {
            "id": 7,
            "timestamp": (base_time + timedelta(minutes=35)).isoformat(),
            "event": "AFGEMELD",
            "user": "NESTING",
            "project": project,
            "details": f"{project} completed by NESTING",
            "status": "AFGEMELD",
            "item_count": 45,
            "session_id": "NESTING_20250705_143000"
        },
        {
            "id": 8,
            "timestamp": (base_time + timedelta(minutes=40)).isoformat(),
            "event": "AFGEMELD",
            "user": "OPUS",
            "project": project,
            "details": f"{project} completed by OPUS",
            "status": "AFGEMELD",
            "item_count": 32,
            "session_id": "OPUS_TEST_WORKFLOW_001_20250705_143200"
        },
        {
            "id": 9,
            "timestamp": (base_time + timedelta(minutes=45)).isoformat(),
            "event": "AFGEMELD",
            "user": "KL GANNOMAT",
            "project": project,
            "details": f"{project} completed by KL GANNOMAT",
            "status": "AFGEMELD",
            "item_count": 28,
            "session_id": "GANNOMAT_TEST_WORKFLOW_001_20250705_143300"
        }
    ]
    
    # Generate sessions data
    sessions_data = [
        {
            "session_id": "NESTING_20250705_143000",
            "user": "NESTING",
            "project": project,
            "start_time": base_time.isoformat(),
            "end_time": (base_time + timedelta(minutes=45)).isoformat(),
            "status": "completed",
            "item_count": 45,
            "work_duration_minutes": 45,
            "session_type": "SCANNER"
        },
        {
            "session_id": "OPUS_TEST_WORKFLOW_001_20250705_143200",
            "user": "OPUS",
            "project": project,
            "start_time": (base_time + timedelta(minutes=2)).isoformat(),
            "end_time": (base_time + timedelta(minutes=40)).isoformat(),
            "status": "completed",
            "item_count": 32,
            "work_duration_minutes": 38,
            "session_type": "XLSX_UPDATED"
        },
        {
            "session_id": "GANNOMAT_TEST_WORKFLOW_001_20250705_143300",
            "user": "KL GANNOMAT",
            "project": project,
            "start_time": (base_time + timedelta(minutes=3)).isoformat(),
            "end_time": (base_time + timedelta(minutes=45)).isoformat(),
            "status": "completed",
            "item_count": 28,
            "work_duration_minutes": 42,
            "session_type": "XLSX_UPDATED"
        }
    ]
    
    # Configured users
    configured_users = ["NESTING", "OPUS", "KL GANNOMAT"]
    
    # Work hours
    work_hours = {
        'monday': {'start': 7.5, 'end': 16},
        'tuesday': {'start': 7.5, 'end': 16},
        'wednesday': {'start': 7.5, 'end': 16},
        'thursday': {'start': 7.5, 'end': 16},
        'friday': {'start': 7.5, 'end': 15},
        'break_start': 12,
        'break_end': 12.5,
        'work_days': [0, 1, 2, 3, 4]
    }
    
    return {
        'log_entries': log_entries,
        'sessions_data': sessions_data,
        'configured_users': configured_users,
        'work_hours': work_hours,
        'project': project
    }

def create_test_html():
    """Create a standalone HTML file for testing frontend functionality"""
    
    test_data = generate_test_data()
    
    html_content = f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BarcodeMaster - Frontend Workflow Test</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
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

        .enterprise-section {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            margin-bottom: 25px;
        }}

        .section-header {{
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e9ecef;
        }}

        .section-header h4 {{
            color: var(--dark-blue);
            font-weight: 600;
            margin: 0;
        }}

        /* Workflow Chain Styles */
        .workflow-chain {{
            position: relative;
            display: flex;
            align-items: center;
            gap: 30px;
            padding: 20px 0;
            overflow-x: auto;
            min-height: 120px;
        }}

        .chain-connection {{
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(
                to right, 
                var(--primary-blue) 0%, 
                var(--primary-blue) var(--progress, 0%), 
                #e9ecef var(--progress, 0%), 
                #e9ecef 100%
            );
            z-index: 1;
            border-radius: 2px;
            transition: all 0.5s ease;
        }}

        .chain-step {{
            position: relative;
            z-index: 2;
            text-align: center;
            min-width: 100px;
            flex-shrink: 0;
            transition: all 0.3s ease;
        }}

        .chain-step-indicator {{
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: #e9ecef;
            border: 3px solid #e9ecef;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 10px;
            transition: all 0.3s ease;
            color: #6c757d;
        }}

        .chain-step.completed .chain-step-indicator {{
            background: var(--primary-blue);
            border-color: var(--primary-blue);
            color: white;
        }}

        .chain-step.active .chain-step-indicator {{
            background: #ffc107;
            border-color: #ffc107;
            color: #000;
            animation: pulse 2s infinite;
        }}

        .chain-step-content {{
            font-size: 0.85rem;
        }}

        .chain-step-title {{
            font-weight: 600;
            color: #495057;
            margin-bottom: 4px;
        }}

        .chain-step-user {{
            color: #6c757d;
            font-size: 0.75rem;
            margin-bottom: 2px;
        }}

        .chain-step-time {{
            color: #adb5bd;
            font-size: 0.7rem;
        }}

        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.1); opacity: 0.8; }}
        }}

        /* Activity Timeline */
        .activity-timeline {{
            max-height: 500px;
            overflow-y: auto;
        }}

        .timeline-item {{
            padding: 15px;
            border-bottom: 1px solid #e9ecef;
            transition: all 0.3s ease;
        }}

        .timeline-item:hover {{
            background-color: #f8f9fa;
        }}

        .status-badge {{
            font-size: 0.7rem;
            padding: 3px 8px;
            border-radius: 4px;
        }}

        .status-open {{ background-color: #e3f2fd; color: #1976d2; }}
        .status-bezig {{ background-color: #fff3e0; color: #f57c00; }}
        .status-afgemeld {{ background-color: #e8f5e8; color: #388e3c; }}

        /* Test specific */
        .test-header {{
            background: linear-gradient(135deg, #1a73e8, #4285f4);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}

        .test-status {{
            background: #f1f3f4;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="container-fluid py-4">
        <div class="test-header">
            <h1><i class="fas fa-flask"></i> BarcodeMaster Frontend Workflow Test</h1>
            <p class="mb-0">Testing complete workflow visualization with all fixes applied</p>
        </div>

        <div class="test-status">
            <h5><i class="fas fa-info-circle"></i> Test Information</h5>
            <div class="row">
                <div class="col-md-3"><strong>Project:</strong> {test_data['project']}</div>
                <div class="col-md-3"><strong>Users:</strong> {', '.join(test_data['configured_users'])}</div>
                <div class="col-md-3"><strong>Log Entries:</strong> {len(test_data['log_entries'])}</div>
                <div class="col-md-3"><strong>Sessions:</strong> {len(test_data['sessions_data'])}</div>
            </div>
        </div>

        <div class="row">
            <div class="col-lg-8">
                <!-- Workflow Status & Progress -->
                <div class="enterprise-section">
                    <div class="section-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <h4><i class="fas fa-sitemap"></i> Workflow Status & Progress</h4>
                            <div id="overall-status" class="badge bg-secondary">Analyseren...</div>
                        </div>
                    </div>
                    <div class="workflow-chain" id="workflowChain">
                        <div class="chain-connection" style="--progress: 0%;"></div>
                    </div>
                </div>

                <!-- Project Activities Log -->
                <div class="enterprise-section">
                    <div class="section-header">
                        <h4><i class="fas fa-list-alt"></i> Project Activiteiten Log</h4>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Tijdstip</th>
                                    <th>Event</th>
                                    <th>Gebruiker</th>
                                    <th>Details</th>
                                    <th>Status</th>
                                    <th>Items</th>
                                </tr>
                            </thead>
                            <tbody id="log-table-body">
                                <!-- Will be populated by JavaScript -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="col-lg-4">
                <!-- Live Activity -->
                <div class="enterprise-section">
                    <div class="section-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <h4><i class="fas fa-rss"></i> Live Activiteit</h4>
                            <span class="badge bg-success d-flex align-items-center gap-1">
                                <i class="fas fa-circle" style="font-size: 0.6rem;"></i> TEST
                            </span>
                        </div>
                    </div>
                    <div class="activity-timeline" id="activityTimeline">
                        <!-- Will be populated by JavaScript -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Test data injection
        let logData = {json.dumps(test_data['log_entries'], indent=8)};
        let configuredUsers = {json.dumps(test_data['configured_users'])};
        let workHours = {json.dumps(test_data['work_hours'])};
        let sessionsData = {json.dumps(test_data['sessions_data'], indent=8)};
        
        console.log('Test data loaded:');
        console.log('Log entries:', logData);
        console.log('Sessions data:', sessionsData);
        console.log('Configured users:', configuredUsers);

        // Initialize page on load
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('🧪 Starting frontend workflow test...');
            initializePage();
        }});

        function initializePage() {{
            console.log('Initializing page with data:');
            console.log('Log entries:', logData);
            console.log('Sessions data:', sessionsData);
            console.log('Configured users:', configuredUsers);
            
            try {{
                // Initialize workflow chain
                initializeWorkflowChain();
                
                // Update workflow status
                updateWorkflowStatus();
                
                // Update live activity timeline
                updateActivityTimeline();
                
                // Populate log table
                populateLogTable();
                
                console.log('✅ Page initialized successfully!');
            }} catch (error) {{
                console.error('❌ Error initializing page:', error);
                document.getElementById('overall-status').textContent = 'Fout bij laden';
                document.getElementById('overall-status').className = 'badge bg-danger';
            }}
        }}

        function initializeWorkflowChain() {{
            const workflowContainer = document.getElementById('workflowChain');
            if (!workflowContainer) {{
                console.error('Workflow container not found');
                return;
            }}
            
            // Check if already initialized
            if (workflowContainer.children.length > 1) {{
                return;
            }}
            
            let workflowHTML = `
                <!-- Project Start Step -->
                <div class="chain-step" id="step-started">
                    <div class="chain-step-indicator">
                        <i class="fas fa-play"></i>
                    </div>
                    <div class="chain-step-content">
                        <div class="chain-step-title">Project Start</div>
                        <div class="chain-step-user">-</div>
                        <div class="chain-step-time">-</div>
                    </div>
                </div>
            `;
            
            // Add user steps
            configuredUsers.forEach(user => {{
                const stepId = 'step-' + user.toLowerCase().replace(/ /g, '-');
                workflowHTML += `
                    <div class="chain-step" id="${{stepId}}">
                        <div class="chain-step-indicator">
                            <i class="fas fa-user"></i>
                        </div>
                        <div class="chain-step-content">
                            <div class="chain-step-title">${{user}}</div>
                            <div class="chain-step-user">In afwachting</div>
                            <div class="chain-step-time">-</div>
                        </div>
                    </div>
                `;
            }});
            
            // Add completion step
            workflowHTML += `
                <div class="chain-step" id="step-completed">
                    <div class="chain-step-indicator">
                        <i class="fas fa-check"></i>
                    </div>
                    <div class="chain-step-content">
                        <div class="chain-step-title">Voltooid</div>
                        <div class="chain-step-user">-</div>
                        <div class="chain-step-time">-</div>
                    </div>
                </div>
            `;
            
            // Keep the connection line and add the content
            const connectionEl = workflowContainer.querySelector('.chain-connection');
            workflowContainer.innerHTML = workflowHTML;
            workflowContainer.insertBefore(connectionEl, workflowContainer.firstChild);
            
            console.log('Workflow chain initialized');
        }}

        function updateWorkflowStatus() {{
            try {{
                console.log('Starting updateWorkflowStatus');
                
                if (!logData || !Array.isArray(logData)) {{
                    console.warn('No log data available');
                    return;
                }}
                
                const workflowOrder = configuredUsers;
                
                // Process logs to determine workflow status
                const openEvents = {{}};
                const afgemeldEvents = {{}};
                const moStartEvents = {{}};
            
                logData.forEach(log => {{
                    if (!log.user) return;
                    
                    const key = `${{log.user}}_${{log.project}}`;
                    
                    if (log.event === 'OPEN' && log.status === 'OPEN') {{
                        openEvents[key] = log;
                    }} else if (log.event === 'AFGEMELD') {{
                        afgemeldEvents[key] = log;
                    }} else if (log.event === 'PROJECT_START') {{
                        moStartEvents[key] = log;
                    }}
                }});
                
                // Determine which users are involved in this project
                const involvedUsers = new Set();
                Object.keys(openEvents).forEach(key => {{
                    const user = key.split('_')[0];
                    involvedUsers.add(user);
                }});
                Object.keys(afgemeldEvents).forEach(key => {{
                    const user = key.split('_')[0];
                    involvedUsers.add(user);
                }});
                Object.keys(moStartEvents).forEach(key => {{
                    const user = key.split('_')[0];
                    involvedUsers.add(user);
                }});
                
                console.log('Involved users:', Array.from(involvedUsers));
                console.log('Open events:', openEvents);
                console.log('PROJECT_START events:', moStartEvents);
                console.log('AFGEMELD events:', afgemeldEvents);
                
                // Check if project has started
                const hasStarted = Object.keys(openEvents).length > 0 || Object.keys(moStartEvents).length > 0;
                if (hasStarted) {{
                    document.getElementById('step-started').classList.add('completed');
                    const allStartEvents = [...Object.values(openEvents), ...Object.values(moStartEvents)];
                    allStartEvents.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
                    const firstStart = allStartEvents[0];
                    document.querySelector('#step-started .chain-step-time').textContent = 
                        formatTimestamp(firstStart.timestamp).split(' ')[1];
                }}
                
                // Update each user step
                let lastCompletedIndex = -1;
                let currentActiveUser = null;
                let isProjectCompleted = false;
                
                workflowOrder.forEach((user, index) => {{
                    const stepId = 'step-' + user.toLowerCase().replace(/ /g, '-');
                    const stepElement = document.getElementById(stepId);
                    if (!stepElement) {{
                        console.warn(`Step element not found: ${{stepId}}`);
                        return;
                    }}
                    
                    const userKey = `${{user}}_${{"{test_data['project']}"}}`;
                    const hasOpen = openEvents[userKey];
                    const hasAfgemeld = afgemeldEvents[userKey];
                    const hasMoStart = moStartEvents[userKey];
                    
                    // Clear previous classes
                    stepElement.classList.remove('completed', 'active', 'processing', 'pending');
                    
                    // Always show configured users
                    stepElement.style.display = '';
                    
                    if (hasAfgemeld) {{
                        stepElement.classList.add('completed');
                        stepElement.querySelector('.chain-step-user').textContent = 'Voltooid';
                        stepElement.querySelector('.chain-step-time').textContent = 
                            formatTimestamp(hasAfgemeld.timestamp).split(' ')[1];
                        lastCompletedIndex = index;
                    }} else if (hasOpen || hasMoStart) {{
                        stepElement.classList.add('active');
                        stepElement.querySelector('.chain-step-user').textContent = 'Werk ontvangen';
                        const startEvent = hasOpen || hasMoStart;
                        stepElement.querySelector('.chain-step-time').textContent = 
                            formatTimestamp(startEvent.timestamp).split(' ')[1];
                        if (!currentActiveUser) {{
                            currentActiveUser = user;
                        }}
                    }} else {{
                        stepElement.querySelector('.chain-step-user').textContent = 'In afwachting';
                        stepElement.querySelector('.chain-step-time').textContent = '-';
                    }}
                }});
                
                // Check if all involved users have completed
                const activeUsers = involvedUsers.size > 0 ? workflowOrder.filter(user => involvedUsers.has(user)) : [];
                const allCompleted = activeUsers.length > 0 && activeUsers.every(user => {{
                    const userKey = `${{user}}_${{"{test_data['project']}"}}`;
                    return afgemeldEvents[userKey] !== undefined;
                }});
                
                if (allCompleted && activeUsers.length > 0) {{
                    document.getElementById('step-completed').classList.add('completed');
                    isProjectCompleted = true;
                }}
                
                // Update progress bar
                const totalConfiguredUsers = workflowOrder.length;
                const completedUsers = workflowOrder.filter(user => {{
                    const userKey = `${{user}}_${{"{test_data['project']}"}}`;
                    return afgemeldEvents[userKey] !== undefined;
                }}).length;
                
                const totalSteps = totalConfiguredUsers + 2; // Start + All Users + Complete
                const completedSteps = (hasStarted ? 1 : 0) + completedUsers + (isProjectCompleted ? 1 : 0);
                const progress = Math.min(100, (completedSteps / totalSteps) * 100);
                document.querySelector('.chain-connection').style.setProperty('--progress', progress + '%');
                
                // Update project status
                const statusElement = document.getElementById('overall-status');
                if (isProjectCompleted) {{
                    statusElement.className = 'badge bg-success';
                    statusElement.textContent = '✅ Project Afgerond';
                }} else if (currentActiveUser) {{
                    statusElement.className = 'badge bg-warning';
                    statusElement.textContent = `⚡ Bezig - ${{currentActiveUser}}`;
                }} else if (hasStarted) {{
                    statusElement.className = 'badge bg-info';
                    statusElement.textContent = '🚀 Project Gestart';
                }} else {{
                    statusElement.className = 'badge bg-secondary';
                    statusElement.textContent = '⏳ Wacht op Start';
                }}
                
                console.log('Workflow status updated successfully');
                
            }} catch (error) {{
                console.error('Error in updateWorkflowStatus:', error);
                document.getElementById('overall-status').textContent = 'Fout bij verwerken';
                document.getElementById('overall-status').className = 'badge bg-danger';
            }}
        }}

        function updateActivityTimeline() {{
            try {{
                console.log('Starting updateActivityTimeline');
                
                const timeline = document.getElementById('activityTimeline');
                if (!timeline) {{
                    console.warn('Activity timeline element not found');
                    return;
                }}
                
                if (!logData || !Array.isArray(logData)) {{
                    console.warn('No log data available for timeline');
                    timeline.innerHTML = `
                        <div class="text-center text-muted py-4">
                            <i class="fas fa-inbox fa-2x mb-3" style="opacity: 0.3;"></i>
                            <p class="mb-0">Geen data beschikbaar</p>
                        </div>
                    `;
                    return;
                }}
                
                const sortedLogs = [...logData].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                const recentLogs = sortedLogs.slice(0, 15);
                
                let timelineHTML = '';
                if (recentLogs.length === 0) {{
                    timelineHTML = `
                        <div class="text-center text-muted py-4">
                            <i class="fas fa-inbox fa-2x mb-3" style="opacity: 0.3;"></i>
                            <p class="mb-0">Geen recente activiteit</p>
                        </div>
                    `;
                }} else {{
                    recentLogs.forEach((log, index) => {{
                        const timeAgo = getTimeAgo(log.timestamp);
                        const icon = getEventIcon(log.event);
                        const statusClass = getStatusClass(log.status);
                        const isRecent = index < 3;
                        
                        timelineHTML += `
                            <div class="timeline-item ${{isRecent ? 'border-start border-3 border-primary' : ''}}" style="${{isRecent ? 'background-color: rgba(26, 115, 232, 0.02);' : ''}}">
                                <div class="d-flex justify-content-between align-items-start">
                                    <div class="flex-grow-1">
                                        <div class="d-flex align-items-center mb-2">
                                            ${{icon}}
                                            <strong class="ms-2 text-dark">${{log.event || 'Systeem Event'}}</strong>
                                            ${{isRecent ? '<span class="badge bg-primary ms-2" style="font-size: 0.6rem;">NIEUW</span>' : ''}}
                                        </div>
                                        
                                        ${{log.user ? `
                                            <div class="d-flex align-items-center mb-2">
                                                <i class="fas fa-user text-muted" style="font-size: 0.8rem;"></i>
                                                <span class="ms-2 fw-medium text-secondary">${{log.user}}</span>
                                            </div>
                                        ` : ''}}
                                        
                                        ${{log.details ? `<p class="mb-2 text-muted small" style="line-height: 1.4;">${{log.details}}</p>` : ''}}
                                        
                                        <div class="d-flex align-items-center gap-2 flex-wrap">
                                            ${{log.status ? `<span class="status-badge status-${{statusClass}}">${{log.status}}</span>` : ''}}
                                            ${{log.item_count ? `<span class="badge bg-info" style="font-size: 0.7rem;">${{log.item_count}} items</span>` : ''}}
                                            <small class="text-muted">
                                                <i class="far fa-clock"></i> ${{timeAgo}}
                                            </small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                    }});
                }}
                
                timeline.innerHTML = timelineHTML;
                console.log('Activity timeline updated successfully');
                
            }} catch (error) {{
                console.error('Error in updateActivityTimeline:', error);
                const timeline = document.getElementById('activityTimeline');
                if (timeline) {{
                    timeline.innerHTML = `
                        <div class="text-center text-muted py-4">
                            <i class="fas fa-exclamation-triangle fa-2x mb-3" style="opacity: 0.3; color: #dc3545;"></i>
                            <p class="mb-0">Fout bij laden van activiteiten</p>
                        </div>
                    `;
                }}
            }}
        }}

        function populateLogTable() {{
            try {{
                const tableBody = document.getElementById('log-table-body');
                if (!tableBody) return;
                
                const sortedLogs = [...logData].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                
                let tableHTML = '';
                sortedLogs.forEach(log => {{
                    const statusClass = getStatusClass(log.status);
                    tableHTML += `
                        <tr>
                            <td>${{formatTimestamp(log.timestamp)}}</td>
                            <td><i class="${{getEventIconClass(log.event)}}"></i> ${{log.event}}</td>
                            <td><strong>${{log.user || '-'}}</strong></td>
                            <td>${{log.details || '-'}}</td>
                            <td><span class="status-badge status-${{statusClass}}">${{log.status || '-'}}</span></td>
                            <td>${{log.item_count || '-'}}</td>
                        </tr>
                    `;
                }});
                
                tableBody.innerHTML = tableHTML;
                
            }} catch (error) {{
                console.error('Error populating log table:', error);
            }}
        }}

        // Helper functions
        function formatTimestamp(timestamp) {{
            try {{
                const date = new Date(timestamp);
                return date.toLocaleString('nl-NL', {{
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                }});
            }} catch (e) {{
                return timestamp;
            }}
        }}

        function getTimeAgo(timestamp) {{
            try {{
                const now = new Date();
                const then = new Date(timestamp);
                const diffMinutes = Math.round((now - then) / 60000);
                
                if (diffMinutes < 1) return 'Zojuist';
                if (diffMinutes < 60) return `${{diffMinutes}}m geleden`;
                if (diffMinutes < 1440) {{
                    const hours = Math.round(diffMinutes / 60);
                    return `${{hours}}u geleden`;
                }}
                const days = Math.round(diffMinutes / 1440);
                return `${{days}}d geleden`;
            }} catch (e) {{
                return 'Onbekend';
            }}
        }}

        function getEventIcon(event) {{
            if (!event) return '<i class="fas fa-circle text-muted" style="font-size: 0.8rem;"></i>';
            
            const eventLower = event.toLowerCase();
            
            if (eventLower.includes('open')) {{
                return '<i class="fas fa-folder-open text-primary" style="font-size: 0.9rem;"></i>';
            }} else if (eventLower.includes('afgemeld')) {{
                return '<i class="fas fa-check-circle text-success" style="font-size: 0.9rem;"></i>';
            }} else if (eventLower.includes('project_start')) {{
                return '<i class="fas fa-play-circle text-info" style="font-size: 0.9rem;"></i>';
            }} else if (eventLower.includes('werk')) {{
                return '<i class="fas fa-cog text-warning" style="font-size: 0.9rem;"></i>';
            }} else {{
                return '<i class="fas fa-info-circle text-secondary" style="font-size: 0.9rem;"></i>';
            }}
        }}

        function getEventIconClass(event) {{
            if (!event) return 'fas fa-circle text-muted';
            
            const eventLower = event.toLowerCase();
            if (eventLower.includes('open')) return 'fas fa-folder-open text-primary';
            if (eventLower.includes('afgemeld')) return 'fas fa-check-circle text-success';
            if (eventLower.includes('mo_start')) return 'fas fa-play-circle text-info';
            if (eventLower.includes('werk')) return 'fas fa-cog text-warning';
            return 'fas fa-info-circle text-secondary';
        }}

        function getStatusClass(status) {{
            if (!status) return 'secondary';
            
            const statusLower = status.toLowerCase();
            if (statusLower.includes('open')) return 'open';
            if (statusLower.includes('bezig')) return 'bezig';
            if (statusLower.includes('afgemeld')) return 'afgemeld';
            return 'secondary';
        }}

        console.log('🧪 Frontend test script loaded successfully!');
    </script>
</body>
</html>"""

    return html_content

def main():
    """Create the test HTML file"""
    print("🧪 Creating BarcodeMaster Frontend Workflow Test...")
    
    html_content = create_test_html()
    
    test_file = '/home/difusion/Projects/BarcodeMaster/test_frontend_workflow.html'
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Test file created: {test_file}")
    print("\n🎯 To test the frontend:")
    print(f"   1. Open {test_file} in a web browser")
    print("   2. Check browser console (F12) for any JavaScript errors")
    print("   3. Verify that the workflow shows:")
    print("      - ✅ Project Start (completed)")
    print("      - ⚡ NESTING (active/completed)")
    print("      - ⚡ OPUS (active/completed)")  
    print("      - ⚡ KL GANNOMAT (active/completed)")
    print("      - ✅ Project Completed")
    print("   4. Verify Live Activity shows all workflow events")
    print("   5. Verify Project Activities Log shows complete timeline")
    
    print(f"\n📂 Test data includes:")
    test_data = generate_test_data()
    print(f"   - {len(test_data['log_entries'])} log entries")
    print(f"   - {len(test_data['sessions_data'])} sessions")
    print(f"   - {len(test_data['configured_users'])} users")
    print(f"   - Complete workflow from OPEN to AFGEMELD")

if __name__ == "__main__":
    main()