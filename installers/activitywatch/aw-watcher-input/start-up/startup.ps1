# Run the initial command
Start-Process -FilePath 'poetry' -ArgumentList 'run aw-watcher-input' -NoNewWindow

# Define a script block for the repeated task
$ScriptBlock = {
    Invoke-WebRequest -Uri 'http://localhost:5600/api/0/export' -OutFile './export.json'
}

# Schedule the script block to run every 5 hours
While ($true) {
    Start-Sleep -Seconds 60 # Sleep for 5 hours
    Invoke-Command -ScriptBlock $ScriptBlock
}