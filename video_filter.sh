#!/bin/bash

# Script to filter videos from eye tracking data for today's date
# Uses conda environment 'tobii' and reads username from tmp/current_username

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Initialize conda
source "$HOME/miniconda3/etc/profile.d/conda.sh"

if ! conda info > /dev/null 2>&1; 
then
  echo "Initializing conda"
  conda init
  exec bash
fi

# Activate the tobii environment
echo "Activating conda environment 'tobii'..."
conda activate tobii

# Get today's date in YYYY-MM-DD format
TODAY=$(date +%Y-%m-%d)
echo "Processing video filtering for date: $TODAY"

# Read username from tmp/current_username file
USERNAME_FILE="$SCRIPT_DIR/tmp/current_username"
if [ -f "$USERNAME_FILE" ]; then
    USERNAME=$(cat "$USERNAME_FILE" | tr -d '\n\r')
    echo "Using username: $USERNAME"
else
    echo "Warning: Username file not found at $USERNAME_FILE, using default TEST_SUBJECT"
    USERNAME="TEST_SUBJECT"
fi

# Define paths using SCRIPT_DIR
VIDEO_DIR="$SCRIPT_DIR/data/$USERNAME/hires/"

echo "Video directory: $VIDEO_DIR"

# Check if video directory exists
if [ ! -d "$VIDEO_DIR" ]; then
    echo "Error: Video directory not found at $VIDEO_DIR"
    exit 1
fi

# Change to the script directory
cd "$SCRIPT_DIR"

# Check if video_filter.py exists
if [ ! -f "video_filter.py" ]; then
    echo "Error: video_filter.py not found in $SCRIPT_DIR"
    exit 1
fi

# Run the video filtering script with in-place modification for today's date
echo "Starting video filtering for $TODAY..."
echo "Processing videos in-place (original files will be overwritten)..."

python video_filter.py \
    --folder "$VIDEO_DIR" \
    --date "$TODAY" \
    --in-place \
    --min-zero-seconds 2.0

echo "Video filtering completed!"
echo "Face counts have been added to timestamp files"
