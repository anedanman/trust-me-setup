#!/bin/bash

# Run the poetry command
poetry run aw-watcher-input &

# Schedule a recurring job using wget every 2 hours
while true; do
    wget http://localhost:5600/api/0/export -O ./data/export.json
    sleep 30  # Sleep for 7200 seconds (2 hours)
done