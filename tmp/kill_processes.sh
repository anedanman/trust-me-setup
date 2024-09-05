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

pgid_path="/home/dis/trust-me-setup/tmp/startup_script.pid"

echo $(ls /home/dis/trust-me-setup/tmp)

# Read the PID from the file
if [ -f "$pgid_path" ]; then
    PGID=$(cat "$pgid_path")
    echo "Sending SIGINT to PGID $PGID"
    kill -SIGINT -- -$PGID
else
    echo "PGID file not found. Is your_script.sh running?"
fi

sleep 10

echo "Shutting down..."
