
#!/bin/bash

filenames=("audio" "brio" "depth" "streamcam" "thermal" "capture_data.pid")

for filename in "${filenames[@]}"; do
  if [[ -f "$filename"]]; then

    pid=$(head -n 1 "$filename")

    # Send interrupt signal
    if [[ $pid =~ ^[0-9]+$ ]]; then
      kill -2 "$pid"
    fi
  fi
done
