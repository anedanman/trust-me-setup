#!/bin/bash

download_file() {
    local file_name="$1"
    local zip_url="$2"
    local extract_dir="$3"
    local zip_path="$extract_dir/$file_name"

    # Check if the zip file already exists
    if [ -e "$zip_path" ]; then
        echo "Zip file already exists. Skipping download."
        return 0
    fi

    mkdir -p "$extract_dir"

    echo "Downloading zip file..."
    wget "$zip_url" -O "$zip_path"

    # Check if the download was successful
    return $?
}
