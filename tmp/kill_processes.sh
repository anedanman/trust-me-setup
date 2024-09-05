#!/bin/bash
echo "Killing PIDS"

filenames=("pids/audio" "pids/brio" "pids/depth" "pids/streamcam" "pids/thermal" "pids/tobii" "pids/capture_data.pid")

for filename in "${filenames[@]}"; do
  if [[ -f "$filename" ]]; then  # Fixed: added a space before ]]
    pid=$(head -n 1 "$filename")

    # Send interrupt signal
    if [[ $pid =~ ^[0-9]+$ ]]; then
      kill -2 "$pid"
    else
      echo "Invalid PID: $pid in $filename"
    fi
  else
    echo "File not found: $filename"
  fi
done
