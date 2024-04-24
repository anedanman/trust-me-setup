@echo off
:: Start the watcher command in a new window
start cmd /c poetry run aw-watcher-input

:: Run the export loop command in the current window or a new one based on your preference
call export_loop.bat