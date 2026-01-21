# Project Time Estimation API Documentation

## Overview

The Project Time Estimation API provides intelligent time predictions for manufacturing projects based on historical performance data, user capacity analysis, and optimal throughput calculations.

## Features

- **Historical Performance Analysis**: Analyzes past 90 days of session data
- **Per-User Capacity**: Individual performance tracking and predictions
- **Optimal vs. Current Capacity**: Compare actual performance against target goals
- **Parallel Processing**: Calculate time savings when multiple users work together
- **Similar Projects Analysis**: Find and analyze historically similar projects
- **Best/Worst Case Scenarios**: Confidence intervals based on performance variance
- **Intelligent Time Allocation**: Properly handles SCANNER session time distribution

---

## API Endpoint

### POST `/api/project/estimate-time`

Estimate project completion time based on various parameters.

#### Request Headers
```
Content-Type: application/json
```

#### Request Body

```json
{
  "items": 150,                           // Required: Number of items to process
  "project_type": "NESTING_PROCESSING",   // Optional: Filter by processing type
  "assigned_users": ["NESTING", "OPUS"],  // Optional: Specific users
  "use_optimal_capacity": false,          // Optional: Use target vs actual performance
  "project": "P240912-002"                // Optional: Reference project for similarity search
}
```

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `items` | integer | Yes | Number of items to process (must be > 0) |
| `project_type` | string | No | Processing type (NESTING_PROCESSING, HOPS_PROCESSING, etc.) |
| `assigned_users` | array[string] | No | List of user names to include in estimation |
| `use_optimal_capacity` | boolean | No | If true, uses target efficiency goals instead of current performance |
| `project` | string | No | Project reference to find similar historical projects |

#### Response

```json
{
  "success": true,
  "input": {
    "items": 150,
    "project_type": "NESTING_PROCESSING",
    "assigned_users": ["NESTING", "OPUS"],
    "use_optimal_capacity": false
  },
  "global_estimate": {
    "estimated_hours": 6.8,
    "estimated_minutes": 408,
    "best_case_hours": 4.2,
    "worst_case_hours": 9.5,
    "avg_items_per_hour": 22.06,
    "avg_minutes_per_item": 2.72,
    "confidence_level": "high"
  },
  "user_estimates": [
    {
      "user": "NESTING",
      "actual_items_per_hour": 25.5,
      "optimal_items_per_hour": 25.0,
      "estimated_hours": 5.88,
      "estimated_minutes": 353,
      "capacity_utilization_percentage": 102.0,
      "sessions_analyzed": 45,
      "minutes_per_item": 2.35
    },
    {
      "user": "OPUS",
      "actual_items_per_hour": 18.7,
      "optimal_items_per_hour": 15.0,
      "estimated_hours": 8.02,
      "estimated_minutes": 481,
      "capacity_utilization_percentage": 124.7,
      "sessions_analyzed": 32,
      "minutes_per_item": 3.21
    }
  ],
  "parallel_processing": {
    "enabled": true,
    "estimated_hours": 3.4,
    "users_count": 2
  },
  "historical_analysis": {
    "sample_size": 77,
    "total_items_analyzed": 3245,
    "data_period": "last 90 days",
    "similar_projects": [
      {
        "project": "P240912-001",
        "items": 145,
        "duration_hours": 6.2,
        "status": "completed",
        "items_per_hour": 23.4,
        "start_time": "2025-09-12 08:00:00",
        "end_time": "2025-09-12 14:15:00"
      }
    ]
  },
  "capacity_analysis": {
    "using_optimal": false,
    "avg_capacity_utilization": 113.4
  }
}
```

#### Response Fields

##### Global Estimate
- `estimated_hours`: Primary time estimate in hours
- `estimated_minutes`: Primary time estimate in minutes
- `best_case_hours`: Optimistic scenario (best historical performance)
- `worst_case_hours`: Pessimistic scenario (worst historical performance)
- `avg_items_per_hour`: Historical average throughput
- `avg_minutes_per_item`: Historical average time per item
- `confidence_level`: "high" (≥20 samples), "medium" (≥10), or "low" (<10)

##### User Estimates
- `user`: User name
- `actual_items_per_hour`: Current/actual performance rate
- `optimal_items_per_hour`: Target efficiency goal
- `estimated_hours`: Estimated completion time for this user
- `estimated_minutes`: Same in minutes
- `capacity_utilization_percentage`: (actual / optimal) × 100
- `sessions_analyzed`: Number of historical sessions included
- `minutes_per_item`: Average time per item for this user

##### Parallel Processing
- `enabled`: Whether multiple users are available
- `estimated_hours`: Combined parallel processing time
- `users_count`: Number of users working in parallel

##### Historical Analysis
- `sample_size`: Number of sessions analyzed
- `total_items_analyzed`: Total items in historical data
- `data_period`: Time range of analysis
- `similar_projects`: Array of historically similar projects

##### Capacity Analysis
- `using_optimal`: Whether optimal capacity mode was used
- `avg_capacity_utilization`: Average % of target capacity being used

---

## Usage Examples

### Example 1: Basic Estimation

Estimate time for 200 items with no specific filters:

```bash
curl -X POST http://localhost:5001/api/project/estimate-time \
  -H "Content-Type: application/json" \
  -d '{
    "items": 200
  }'
```

### Example 2: Specific Users with Optimal Capacity

Estimate using target efficiency goals for NESTING and OPUS:

```bash
curl -X POST http://localhost:5001/api/project/estimate-time \
  -H "Content-Type: application/json" \
  -d '{
    "items": 150,
    "assigned_users": ["NESTING", "OPUS"],
    "use_optimal_capacity": true
  }'
```

### Example 3: Project Type with Similar Projects

Estimate NESTING work and find similar historical projects:

```bash
curl -X POST http://localhost:5001/api/project/estimate-time \
  -H "Content-Type: application/json" \
  -d '{
    "items": 180,
    "project_type": "NESTING_PROCESSING",
    "project": "P240912-002"
  }'
```

### Example 4: Python Client

```python
import requests
import json

def estimate_project_time(items, users=None, use_optimal=False):
    url = "http://localhost:5001/api/project/estimate-time"

    payload = {
        "items": items,
        "use_optimal_capacity": use_optimal
    }

    if users:
        payload["assigned_users"] = users

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"Estimated Time: {data['global_estimate']['estimated_hours']}h")
        print(f"Best Case: {data['global_estimate']['best_case_hours']}h")
        print(f"Worst Case: {data['global_estimate']['worst_case_hours']}h")

        if data['parallel_processing']['enabled']:
            print(f"Parallel Time: {data['parallel_processing']['estimated_hours']}h")

        return data
    else:
        print(f"Error: {response.status_code}")
        return None

# Usage
result = estimate_project_time(items=200, users=["NESTING", "OPUS"])
```

### Example 5: JavaScript/Frontend

```javascript
async function estimateProjectTime(items, options = {}) {
  const payload = {
    items: items,
    ...options
  };

  try {
    const response = await fetch('/api/project/estimate-time', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (data.success) {
      console.log(`Estimated: ${data.global_estimate.estimated_hours}h`);

      // Display per-user estimates
      data.user_estimates.forEach(user => {
        console.log(`${user.user}: ${user.estimated_hours}h`);
      });

      return data;
    } else {
      console.error('API Error:', data.error);
    }
  } catch (error) {
    console.error('Request failed:', error);
  }
}

// Usage
estimateProjectTime(150, {
  assigned_users: ['NESTING', 'OPUS'],
  use_optimal_capacity: true,
  project_type: 'NESTING_PROCESSING'
});
```

---

## Calculation Methodology

### 1. Historical Performance Analysis

The system analyzes the last 90 days of completed sessions to calculate:

- **Items per Hour**: `(item_count × 60) / work_duration_minutes`
- **Minutes per Item**: `work_duration_minutes / item_count`

For SCANNER sessions (batch processing), time is allocated proportionally based on item count:

```
allocated_time = (session_items / total_daily_items) × total_daily_duration
```

### 2. Time Estimation

**Basic Formula**:
```
estimated_hours = items / avg_items_per_hour
```

**Optimal Capacity Mode**:
```
estimated_hours = items / optimal_items_per_hour
```

Where `optimal_items_per_hour` comes from the efficiency targets in `config.json`.

### 3. Parallel Processing

When multiple users are assigned:

```
combined_throughput = sum(user_items_per_hour for all users)
parallel_hours = items / combined_throughput
```

### 4. Confidence Levels

- **High Confidence**: ≥20 historical sessions analyzed
- **Medium Confidence**: 10-19 sessions analyzed
- **Low Confidence**: <10 sessions analyzed

### 5. Best/Worst Case

- **Best Case**: `items / max_historical_items_per_hour`
- **Worst Case**: `items / min_historical_items_per_hour`

---

## Error Handling

### Error Responses

#### 400 Bad Request
```json
{
  "success": false,
  "error": "Valid items count is required"
}
```

Causes:
- Missing `items` parameter
- `items` ≤ 0
- Invalid data types

#### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Database connection failed"
}
```

Causes:
- Database connectivity issues
- SQL query errors
- Unexpected exceptions

---

## Integration Points

### 1. Statistics Page

Add time estimation widget to statistics page:

```html
<div class="time-estimator-widget">
  <input type="number" id="estimateItems" placeholder="Enter items">
  <button onclick="quickEstimate()">Estimate Time</button>
  <div id="estimateResult"></div>
</div>

<script>
async function quickEstimate() {
  const items = document.getElementById('estimateItems').value;
  const response = await fetch('/api/project/estimate-time', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({items: parseInt(items)})
  });

  const data = await response.json();
  document.getElementById('estimateResult').innerHTML =
    `Estimated: ${data.global_estimate.estimated_hours}h`;
}
</script>
```

### 2. Project Detail Page

Show estimated completion time for active projects:

```python
# In project detail route
@app.route('/project/<project_name>')
def project_detail(project_name):
    # ... existing code ...

    # Get remaining items
    remaining_items = total_items - completed_items

    # Estimate remaining time
    estimate_data = {
        'items': remaining_items,
        'project_type': session_type
    }

    # Call estimation API internally
    estimate = estimate_project_time_internal(estimate_data)

    return render_template('project_detail.html',
                         project=project,
                         estimated_completion=estimate)
```

### 3. Dashboard

Add real-time capacity monitoring:

```javascript
// Update dashboard with capacity utilization
async function updateCapacityMetrics() {
  // Get all active projects
  const projects = await fetchActiveProjects();

  // Calculate total workload
  const totalItems = projects.reduce((sum, p) => sum + p.remaining_items, 0);

  // Get time estimate
  const estimate = await estimateProjectTime(totalItems, {
    use_optimal_capacity: true
  });

  // Display capacity utilization
  displayCapacityStatus(estimate.capacity_analysis);
}
```

---

## Performance Considerations

- **Data Period**: Analysis limited to 90 days for performance
- **Minimum Sessions**: Requires ≥3 sessions per user for inclusion
- **Caching**: Consider caching estimates for identical parameters
- **Parallel Queries**: Multiple CTE queries may be slow on large datasets

### Optimization Tips

1. **Index Requirements**:
```sql
CREATE INDEX IF NOT EXISTS idx_sessions_completed ON sessions(status, start_time);
CREATE INDEX IF NOT EXISTS idx_sessions_user_type ON sessions(user, session_type, status);
CREATE INDEX IF NOT EXISTS idx_project_sessions_project ON project_sessions(project, status);
```

2. **Batch API Calls**: When estimating multiple projects, batch requests:
```python
estimates = []
for project in projects:
    estimates.append(estimate_project_time(project['items']))
```

---

## Testing

Run the included test script:

```bash
cd /mnt/c/Users/Rob/Desktop/Test-thuis/BarcodeMaster/database
python3 test_time_estimation.py
```

The test script includes:
- Basic estimation tests
- Optimal capacity mode tests
- User-specific estimation tests
- Similar projects analysis tests
- Edge case validation

---

## Configuration

### Efficiency Targets

Edit `config.json` to set optimal capacity targets:

```json
{
  "efficiency_targets": {
    "NESTING": 25,
    "ACCURA": 20,
    "OPUS": 15,
    "KL GANNOMAT": 15,
    "BOERE": 20
  }
}
```

These values represent target items per hour for each user.

### Work Hours

The estimation respects configured work hours from `config.json`:

```json
{
  "work_hours": {
    "monday": {"start": 7.5, "end": 16.0},
    "tuesday": {"start": 7.5, "end": 16.0},
    ...
  }
}
```

---

## Web Interface

Access the interactive calculator at:

```
http://localhost:5001/time-estimation
```

Features:
- Visual form for entering project parameters
- Real-time calculation
- Interactive results display
- User capacity comparison charts
- Historical project comparison
- Export-ready estimates

---

## Future Enhancements

Potential improvements:
1. Machine learning model for more accurate predictions
2. Seasonal trend analysis
3. Department-specific estimation
4. Project complexity factors
5. Real-time capacity monitoring
6. Automated workload balancing
7. Integration with ERP/MES systems
8. Mobile app support

---

## Support

For issues or questions:
- Check API logs in `db_log_api.log`
- Verify database connectivity
- Ensure sufficient historical data exists
- Review efficiency targets in config

## Changelog

### Version 1.0 (2025-10-10)
- Initial release
- Historical performance analysis
- Per-user capacity tracking
- Optimal vs. current capacity modes
- Parallel processing calculations
- Similar projects analysis
- Web interface calculator
