#!/bin/bash

# Improvement idea: Remap the power button to run this script and add "shutdown now" at the end of this file.

pgid_path="/home/trustme/trust-me-setup/tmp/startup_script.pid"

echo $(ls /home/trustme/trust-me-setup/tmp)

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
