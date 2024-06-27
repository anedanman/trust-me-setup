#!/bin/bash

# Save PID
pid=$$
pgid=$(ps -o pgid= -p "$pid")

echo $pgid > $HOME/trust-me-setup/tmp/startup_script.pid

source "$HOME/miniconda3/etc/profile.d/conda.sh"
echo $(conda --version)

while [ ! -e /dev/video0 ];
do
  echo "Waiting for /dev/video0..."
  sleep 5
done

echo "Video now available. Starting script..."

if ! conda info > /dev/null 2>&1; 
then
  echo "Initializing conda"
  conda init
  exec bash
fi

cd "$HOME/trust-me-setup/"

# Paths
TOBII_PATH="$HOME/trust-me-setup/installers/tobii/run_tobii.sh";
RGB_PATH="$HOME/trust-me-setup/installers/data_capture/capture_data.py";

# Activate environment
conda activate tobii

if [ ! -f "$TOBII_PATH" ];
then
  echo "Error! Tobii script not found at $TOBII_PATH"
  exit 1
fi

if [ ! -f "$RGB_PATH" ];
then
  echo "Error! RGB script not found at $RGB_PATH"
  exit 1
fi

chmod +x "$TOBII_PATH"

# Run process in background
$("$TOBII_PATH") &
echo "Started recording tobii"

python "$HOME/trust-me-setup/installers/data_capture/auto_config_hw.py"

# Run process in background
$(python "$RGB_PATH") &
echo "Started recording RGB"


wait
echo "Done"
