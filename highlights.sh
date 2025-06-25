#!/bin/bash

# Script to generate highlights from eye tracking and video data
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
echo "Processing highlights for date: $TODAY"

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
EYE_DIR="$SCRIPT_DIR/installers/data_collection/$USERNAME/tobii/"
VIDEO_DIR="$SCRIPT_DIR/installers/data_collection/$USERNAME/hires/"
HIGHLIGHT_DIR="$SCRIPT_DIR/highlights/"

echo "Eye tracking data directory: $EYE_DIR"
echo "Video directory: $VIDEO_DIR"
echo "Highlights output directory: $HIGHLIGHT_DIR"

# Check if directories exist
if [ ! -d "$EYE_DIR" ]; then
    echo "Error: Eye tracking directory not found at $EYE_DIR"
    exit 1
fi

if [ ! -d "$VIDEO_DIR" ]; then
    echo "Error: Video directory not found at $VIDEO_DIR"
    exit 1
fi

# Create highlights directory if it doesn't exist
mkdir -p "$HIGHLIGHT_DIR"

# Change to the script directory
cd "$SCRIPT_DIR"

# Run the highlights.py script
echo "Starting highlights generation..."
python highlights.py \
    --date "$TODAY" \
    --user "$USERNAME" \
    --eye-dir "$EYE_DIR" \
    --video-dir "$VIDEO_DIR" \
    --highlight-dir "$HIGHLIGHT_DIR" \
    --highlights 4 \
    --separation 18 # 30 minutes separation

echo "Highlights generation completed!"