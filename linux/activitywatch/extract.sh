#!/bin/bash

extract_zip() {
    local file_name="$1"
    local extract_dir="$2"

    local path_folder="$extract_dir/$file_name"

    echo "Unzipping file..."
    unzip -o "$path_folder" -d "$extract_dir"

    # Check if the unzip was successful
    return $?
}
