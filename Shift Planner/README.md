# Shift Planner

A comprehensive shift planning system that optimizes worker assignments based on skills, job priorities, and machine requirements.

## Features

- **Smart Scheduling Algorithm**: Automatically assigns workers to machines based on skill levels (1-5)
- **Priority Management**: High priority jobs get preferential scheduling
- **Precision Jobs**: Jobs requiring Level 4+ operators for quality-critical work
- **Machine Routing**: Jobs can require sequential machine operations
- **Progress Tracking**: Right-click assignments to update job progress
- **Availability Management**: Track vacations and absences
- **Job Templates**: Create reusable templates for common jobs (#101, #102, etc.)
- **Visual Timeline**: Week-based view with color-coded skill levels
- **CSV Export**: Export schedules for external use

## Installation

### Requirements
- Python 3.7 or higher
- Web browser (Chrome, Firefox, Edge, Safari)

### Quick Start

#### Windows:
```bash
run.bat
```

#### Linux/Mac:
```bash
chmod +x run.sh
./run.sh
```

#### Manual Installation:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## Usage

1. **Access the Application**: Open http://localhost:5003 in your browser

2. **Initial Setup**:
   - Add Machines: Click "Add Machine" in the right sidebar
   - Add People: Click "Add Person" and set their skill levels for each machine
   - Create Job Templates: Set up common job types with predefined machine sequences

3. **Adding Jobs**:
   - Click "Add Job" in the right sidebar
   - Select a template or create a custom job
   - Set quantity, due date, and priority
   - Check "Precision Required" for quality-critical jobs

4. **Generating Schedule**:
   - Click "Generate Schedule" in the header
   - The algorithm will optimize assignments based on:
     - Worker skill levels
     - Job priorities and due dates
     - Precision requirements (Level 4+ only)
     - Machine availability

5. **Managing Progress**:
   - Right-click on any assignment to update progress
   - Enter completed quantity and remaining hours
   - Jobs automatically carry over if not completed

6. **Availability**:
   - Mark vacations/absences in the left sidebar
   - Schedule regenerates around unavailable workers

## Color Coding

### Skill Levels:
- **Red** (Level 1): Beginner
- **Orange** (Level 2): Basic
- **Yellow** (Level 3): Competent
- **Light Green** (Level 4): Advanced (Precision capable)
- **Green** (Level 5): Expert (Precision capable)

### Job Priority:
- **Pulsing Red Border**: High priority job
- **Normal**: Standard priority

## Database Structure

The system uses SQLite for data persistence with the following tables:
- **people**: Worker information
- **machines**: Machine specifications and throughput
- **skills**: Person-machine skill mappings
- **jobs**: Job queue with progress tracking
- **job_templates**: Reusable job configurations
- **schedule**: Generated assignments
- **availability**: Vacation/absence tracking

## Algorithm Logic

The scheduling algorithm considers:
1. **Skill Matching**: Higher skilled workers complete jobs faster
2. **Precision Requirements**: Only Level 4+ for precision jobs
3. **Priority Handling**: High priority jobs scheduled first
4. **Sequential Operations**: Jobs requiring multiple machines in order
5. **Bottleneck Prevention**: Avoids creating downstream delays
6. **Daily Carryover**: Incomplete jobs automatically continue next day

## File Structure

```
shift_planner/
├── app.py                 # Flask backend
├── scheduling_algorithm.py # Core scheduling logic
├── shift_planner.db       # SQLite database (created on first run)
├── templates/
│   └── index.html        # Main interface
├── static/
│   ├── css/
│   │   └── style.css     # Styling
│   └── js/
│       └── app.js        # Frontend logic
├── exports/              # CSV export directory
└── requirements.txt      # Python dependencies
```

## Troubleshooting

- **Port 5003 in use**: Change the port in app.py: `app.run(debug=True, port=5004)`
- **Database locked**: Ensure only one instance is running
- **Schedule not generating**: Check that people have skills assigned for required machines

## License

MIT License - Feel free to modify and use for your needs.