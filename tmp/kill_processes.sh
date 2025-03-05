#!/bin/bash
echo "Killing PIDs"

# Use $(whoami) to get the current username dynamically
PREFIX="/home/$(whoami)/trust-me-setup/tmp"
echo "Using prefix path: $PREFIX"

# List of PID files
filenames=("pids/audio" "pids/brio" "pids/depth" "pids/thermal" "pids/tobiish" "pids/tobii" "pids/capture_data.pid")

# Loop over each filename and attempt to kill the process
for filename in "${filenames[@]}"; do
  fullpath="$PREFIX/$filename"

  if [[ -f "$fullpath" ]]; then
    # Read the first line of the file (PID)
    pid=$(head -n 1 "$fullpath")

    # Check if it's a valid PID (numeric)
    if [[ $pid =~ ^[0-9]+$ ]]; then
      echo "Sending SIGINT to PID $pid (from $filename)"
      kill -2 "$pid"
    else
      echo "Invalid PID: $pid in $fullpath"
    fi
  else
    echo "File not found: $fullpath"
  fi
done

