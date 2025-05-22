#!/bin/bash

# Get the last logged in user
LAST_USER=$(last -n 1 | grep -v reboot | head -1 | awk '{print $1}')

# If we found a user
if [ ! -z "$LAST_USER" ]; then
    # Define base path
    BASE_PATH="/home/$LAST_USER/trust-me-setup"
    echo "Base path: $BASE_PATH" > /tmp/shutdown_log.txt
    
    # Paths
    KEEPALIVE_PATH="$BASE_PATH/tmp/keepalive.td"
    
    # Delete the keepalive file
    if [ -f "$KEEPALIVE_PATH" ]; then
        echo "Removing keepalive file" >> /tmp/shutdown_log.txt
        rm -f "$KEEPALIVE_PATH"
    else
        echo "Keepalive file not found" >> /tmp/shutdown_log.txt
    fi
else
    echo "No user found" > /tmp/shutdown_log.txt
fi

sleep 0.4