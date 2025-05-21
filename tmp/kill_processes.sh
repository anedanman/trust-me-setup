#!/bin/bash
echo "Killing PIDs"

# Use $(whoami) to get the current username dynamically
PREFIX="/home/$(whoami)/trust-me-setup/tmp"
echo "Using prefix path: $PREFIX"

# List of PID files
filenames=("pids/audio" "pids/brio" "pids/tobiish" "pids/tobii" "pids/capture_data.pid")

# Define base path
BASE_PATH="$HOME/trust-me-setup"

# Paths
KEEPALIVE_PATH="$BASE_PATH/tmp/keepalive.td"

# Delete the keepalive file and the processes will kill themselves -> let the processes kill themselves
if [ -f "$KEEPALIVE_PATH" ];
then
	rm -f "$KEEPALIVE_PATH"
	echo "The KEEPALIVE file was deleted! Termination started..."
fi
sleep 0.4
done

