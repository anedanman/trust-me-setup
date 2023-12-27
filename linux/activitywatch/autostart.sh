#!/bin/bash

autostart_script() {
    local script_name="$1"
    local extract_dir="$2"

    local script_path="$extract_dir/activitywatch/$script_name"

    echo "Making the script executable..."
    chmod +x "$script_path"

    echo "Creating a .desktop file..."
    desktop_file="$HOME/.config/autostart/$script_name.desktop"
    echo "[Desktop Entry]" > "$desktop_file"
    echo "Name=ActivityWatch" >> "$desktop_file"
    echo "Exec=$script_path" >> "$desktop_file"
    echo "Type=Application" >> "$desktop_file"
    echo "X-GNOME-Autostart-enabled=true" >> "$desktop_file"
    echo "Hidden=false" >> "$desktop_file"
    echo "NoDisplay=false=true" >> "$desktop_file"

    echo "Script is now executable and added to autostart applications."

    # Continue with other commands in the main script
    echo "Starting ActivityWatch..."

    # Run the script
    "$script_path" & disown
}
