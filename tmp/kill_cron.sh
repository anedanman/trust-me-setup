#!/bin/bash

pgid_path="$HOME/trust-me-setup/tmp/startup_script.pid"

# Read the PID from the file
if [ -f "$pgid_path" ]; then
    PGID=$(cat "$pgid_path")
    echo "Sending SIGINT to PGID $PGID"
    kill -SIGINT -- -$PGID
    rm "$pgid_path"  # Clean up the PID file
else
    echo "PGID file not found. Is your_script.sh running?"
fi

