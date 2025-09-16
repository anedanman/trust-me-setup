#!/bin/bash

# Script to filter all videos in all subdirectories of a data folder
# Usage: ./video_filter_all.sh [data_folder]
# If no folder is provided, uses 'data' as default

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Initialize conda
source "$HOME/miniconda3/etc/profile.d/conda.sh"

if ! conda info > /dev/null 2>&1; then
    echo "Conda not initialized or not available. Ensure Miniconda is installed at $HOME/miniconda3 and try again."
    exit 1
fi

# Activate the tobii environment
echo "Activating conda environment 'tobii'..."
conda activate tobii

# Set data folder
DATA_FOLDER="${1:-data}"
if [[ ! "$DATA_FOLDER" = /* ]]; then
    # If not absolute path, make it relative to script directory
    DATA_FOLDER="$SCRIPT_DIR/$DATA_FOLDER"
fi

echo "Processing all videos in: $DATA_FOLDER"

# Check if data folder exists
if [ ! -d "$DATA_FOLDER" ]; then
    echo "Error: Data folder not found at $DATA_FOLDER"
    exit 1
fi

# Change to the script directory
cd "$SCRIPT_DIR"

# Check if video_filter.py exists
if [ ! -f "video_filter.py" ]; then
    echo "Error: video_filter.py not found in $SCRIPT_DIR"
    exit 1
fi

# Initialize counters
total_processed=0
total_skipped=0
total_errors=0

echo "Searching for 'hires' directories with video files..."

echo "Finding 'hires' directories with video files..."

# Process each directory as it is found (streaming)
found_any=false
while IFS= read -r dir; do
    found_any=true
    echo "===== Processing directory: $dir ====="
    
    # Count videos in this directory
    video_count=$(find "$dir" -maxdepth 1 -name "*.mp4" | wc -l)
    echo "Found $video_count video files in $dir"
    
    if [ "$video_count" -gt 0 ]; then
        # Process videos in this directory
        python video_filter.py \
            --folder "$dir" \
            --in-place \
            --min-zero-seconds 2.0
        
        # Check exit code
        if [ $? -eq 0 ]; then
            echo "✓ Successfully processed $dir"
            total_processed=$((total_processed + video_count))
        else
            echo "✗ Error processing $dir"
            total_errors=$((total_errors + video_count))
        fi
    else
        echo "⚠ No video files found in $dir"
        total_skipped=$((total_skipped + 1))
    fi
    
    echo
done < <(find "$DATA_FOLDER" -type d -name "hires" -exec sh -c 'd="$1"; ls "$d"/*.mp4 >/dev/null 2>&1 && echo "$d"' _ {} \;)

if [ "$found_any" = false ]; then
    echo "No 'hires' directories with video files found in $DATA_FOLDER"
    exit 0
fi

echo "===== SUMMARY ====="
echo "Total videos processed: $total_processed"
echo "Total directories skipped: $total_skipped"
echo "Total videos with errors: $total_errors"
echo "Processing completed!"

# Show which files were already processed (skipped)
echo
echo "===== ALREADY PROCESSED FILES ====="
echo "The following files were skipped because they were already processed:"

find "$DATA_FOLDER" -name "*_timestamps_*.txt" -exec grep -l "face_count" {} \; | while read -r timestamp_file; do
    # Derive the most likely corresponding video name generically by replacing _timestamps_ with _chunk0_
    base=$(basename "$timestamp_file")
    video_name="${base/_timestamps_/_chunk0_}"
    video_name="${video_name%.txt}.mp4"
    video_dir=$(dirname "$timestamp_file")
    echo "  $video_dir/$video_name"
done
