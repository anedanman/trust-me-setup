#!/bin/bash

install_activitywatch() {
  local extract_dir="$1"
  local script_dir="$2"

  file_name="activitywatch-v0.12.2-linux-x86_64.zip"
  zip_url="https://github.com/ActivityWatch/activitywatch/releases/download/v0.12.2/$file_name"

  # Run the download script
  source "$script_dir/download.sh"
  download_file "$file_name" "$zip_url" "$extract_dir" || exit 1

  # Run the extract script
  source "$script_dir/extract.sh"
  extract_zip "$file_name" "$extract_dir" || exit 1

  # Run the autostart script
  source "$script_dir/autostart.sh"
  autostart_script "aw-qt" "$extract_dir"
}
