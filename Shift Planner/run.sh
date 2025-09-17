#!/bin/bash

echo "Shift Planner - Starting..."
echo "=========================="

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "Python 3 is not installed. Please install Python 3.7+ to run this application."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt -q

# Start the application
echo "Starting Shift Planner..."
echo "=========================="
echo "Access the application at: http://localhost:5003"
echo "Press Ctrl+C to stop the server"
echo ""

python app.py