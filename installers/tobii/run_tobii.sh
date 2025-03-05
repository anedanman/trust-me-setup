#!/bin/bash

# Define base path
BASE_PATH="/home/$(whoami)/trust-me-setup"
PID_DIR="$BASE_PATH/tmp/pids/tobiish"
echo $$ > "$PID_DIR"

# Get username from parameter or file
USERNAME=${1:-$(cat "$BASE_PATH/tmp/current_username" 2>/dev/null || echo "user1")}

cd "$BASE_PATH/installers/tobii"
/home/$(whoami)/miniconda3/envs/tobii/bin/python run_tobii.py "$USERNAME" "$BASE_PATH"

