#!/bin/bash

# Directory where you want to unzip the contents
extract_dir="$HOME/trust-me"

#########################
# Install ActivityWatch
#########################

# Directory where scripts are located
activitywatch_script_dir="$(dirname "$0")/activitywatch"

# Run the download script
source "$activitywatch_script_dir/installer.sh"
install_activitywatch "$extract_dir" "$activitywatch_script_dir" || exit 1
