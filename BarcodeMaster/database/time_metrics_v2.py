# Add this code to your db_log_api.py file
# This is the new v2 endpoint for correct time calculations

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
        
        # Step 5: Calculate idle time
        total_idle_minutes = max(0, total_project_minutes - total_work_minutes)
        
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