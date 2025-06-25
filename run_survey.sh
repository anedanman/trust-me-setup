#!/bin/bash

# Script to launch the online survey monitoring system
# IMPORTANT: do not forget to put .env file into online-survey/core and update WATCH_DIR in core/config.py and recipient email in .env

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SURVEY_DIR="$SCRIPT_DIR/online-survey"

# Check if the online-survey directory exists
if [ ! -d "$SURVEY_DIR" ]; then
    echo "Error: online-survey directory not found at $SURVEY_DIR"
    exit 1
fi

# Change to the online-survey directory
cd "$SURVEY_DIR"

# Activate virtual environment
source venv/bin/activate

# Launch the core.main module
echo "Starting survey monitoring system..."
python -m core.main