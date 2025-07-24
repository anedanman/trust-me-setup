#!/usr/bin/env python3
"""
Data Monitoring Script
Checks data folder sizes every 3 hours and sends email alerts if folders haven't grown.
"""

import os
import json
import time
import smtplib
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
from email.message import EmailMessage

def load_env_file(env_path):
    """Load environment variables from .env file"""
    env_vars = {}
    try:
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
            print(f"Loaded {len(env_vars)} variables from {env_path}")
        else:
            print(f"Environment file not found: {env_path}")
    except Exception as e:
        print(f"Error loading .env file: {e}")
    return env_vars

# Load email configuration from online-survey .env file
SCRIPT_DIR = Path(__file__).parent.resolve()
env_file = SCRIPT_DIR / "online-survey" / "core" / ".env"
env_vars = load_env_file(env_file)

# Email configuration (try .env file first, then environment variables)
SMTP_SERVER = env_vars.get("SMTP_SERVER", os.environ.get("SMTP_SERVER", "smtp.gmail.com"))
SMTP_PORT = int(env_vars.get("SMTP_PORT", os.environ.get("SMTP_PORT", "587")))
SMTP_USERNAME = env_vars.get("SMTP_USERNAME", os.environ.get("SMTP_USERNAME", ""))
SMTP_PASSWORD = env_vars.get("SMTP_PASSWORD", os.environ.get("SMTP_PASSWORD", ""))
FROM_EMAIL = env_vars.get("FROM_EMAIL", os.environ.get("FROM_EMAIL", ""))

print("Using email configuration from online-survey/core/.env")
print(f"SMTP Server: {SMTP_SERVER}")
print(f"SMTP Port: {SMTP_PORT}")
print(f"SMTP Username: {SMTP_USERNAME}")
print(f"SMTP Password: {'***' if SMTP_PASSWORD else 'Not set'}")
print(f"From Email: {FROM_EMAIL}")

# Configuration - can be overridden by environment variables
USERNAME_FILE = SCRIPT_DIR / "tmp" / "current_username"
STATE_FILE = SCRIPT_DIR / "tmp" / "data_monitor_state.json"
CHECK_INTERVAL = 1 * 60 * 60  # 1 hour in seconds

# Data Monitor specific recipient email
RECIPIENT_EMAIL = ""

print(f"Recipient Email: {RECIPIENT_EMAIL if RECIPIENT_EMAIL else 'Not configured'}")
print("=" * 50)

# Devices to monitor (subfolder names in data/USERNAME/)
DEVICES = ["audio", "hires", "tobii"]

def get_username():
    """Read username from tmp/current_username file"""
    try:
        if USERNAME_FILE.exists():
            username = USERNAME_FILE.read_text().strip()
            print(f"Using username: {username}")
            return username
        else:
            print(f"Warning: Username file not found at {USERNAME_FILE}, using default")
            return "Dani_Test"
    except Exception as e:
        print(f"Error reading username file: {e}, using default")
        return "Dani_Test"

def get_folder_size(folder_path):
    """Get the total size of a folder in bytes"""
    try:
        if not folder_path.exists():
            return 0
        
        # Use du command for accurate folder size
        result = subprocess.run(
            ["du", "-sb", str(folder_path)], 
            capture_output=True, 
            text=True, 
            check=True
        )
        size_bytes = int(result.stdout.split()[0])
        return size_bytes
    except (subprocess.CalledProcessError, ValueError, IndexError) as e:
        print(f"Error getting size for {folder_path}: {e}")
        return 0

def load_state():
    """Load previous state from JSON file"""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        else:
            return {}
    except Exception as e:
        print(f"Error loading state: {e}")
        return {}

def save_state(state):
    """Save current state to JSON file"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Error saving state: {e}")

def format_size(size_bytes):
    """Format size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def send_email_alert(subject, body):
    """Send email alert"""
    if not all([SMTP_USERNAME, SMTP_PASSWORD, FROM_EMAIL, RECIPIENT_EMAIL]):
        print("Warning: Email configuration incomplete. Skipping email alert.")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        return False
    
    try:
        msg = EmailMessage()
        msg['From'] = FROM_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = subject
        msg.set_content(body)
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"Email alert sent successfully to {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def check_data_folders():
    """Check data folder sizes and send alerts if needed"""
    username = get_username()
    current_time = datetime.now()
    current_timestamp = current_time.isoformat()
    
    # Load previous state
    state = load_state()
    
    # Base data directory for the user
    user_data_dir = SCRIPT_DIR / "data" / username
    
    if not user_data_dir.exists():
        print(f"Warning: User data directory not found: {user_data_dir}")
        return
    
    alerts = []
    current_sizes = {}
    
    print(f"\n=== Data Monitor Check - {current_time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    for device in DEVICES:
        device_folder = user_data_dir / device
        current_size = get_folder_size(device_folder)
        current_sizes[device] = {
            "size": current_size,
            "timestamp": current_timestamp,
            "path": str(device_folder)
        }
        
        print(f"{device:12}: {format_size(current_size):>10} ({device_folder})")
        
        # Check if we have previous data for this device
        if device in state:
            previous_size = state[device].get("size", 0)
            previous_timestamp = state[device].get("timestamp", "unknown")
            
            # If size hasn't increased, create alert
            if current_size <= previous_size:
                time_diff = "unknown"
                try:
                    prev_time = datetime.fromisoformat(previous_timestamp)
                    time_diff = current_time - prev_time
                    time_diff_str = f"{time_diff.total_seconds() / 3600:.1f} hours"
                except:
                    time_diff_str = "unknown duration"
                
                alert_msg = (
                    f"Device '{device}' folder has not grown since last check.\n"
                    f"  Current size: {format_size(current_size)}\n"
                    f"  Previous size: {format_size(previous_size)}\n"
                    f"  Time since last check: {time_diff_str}\n"
                    f"  Folder path: {device_folder}"
                )
                alerts.append(alert_msg)
                print(f"  ⚠️  ALERT: No growth detected!")
            else:
                growth = current_size - previous_size
                print(f"  ✅ Growth: +{format_size(growth)}")
        else:
            print(f"  ℹ️  First check for this device")
    
    # Send email if there are alerts
    if alerts:
        subject = f"Data Monitor Alert - {username} - {current_time.strftime('%Y-%m-%d %H:%M')}"
        body = (
            f"Data monitoring alert for user: {username}\n"
            f"Check time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"The following devices have not recorded new data since the last check:\n\n"
        )
        body += "\n\n".join(alerts)
        body += f"\n\nThis check was performed at: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        send_email_alert(subject, body)
    else:
        print("✅ All devices are recording data normally")
    
    # Save current state
    save_state(current_sizes)
    print(f"State saved to: {STATE_FILE}")

def main():
    """Main monitoring loop"""
    print("Starting Data Monitor...")
    print(f"Check interval: {CHECK_INTERVAL / 3600} hours")
    print(f"Monitoring devices: {', '.join(DEVICES)}")
    print(f"Email alerts to: {RECIPIENT_EMAIL if RECIPIENT_EMAIL else 'Not configured'}")
    
    # Create keepalive file path
    keepalive_file = SCRIPT_DIR / "tmp" / "keepalive.td"
    
    while True:
        # Check if keepalive file exists (system is running)
        if not keepalive_file.exists():
            print("Keepalive file not found. System may be shutting down. Exiting monitor.")
            break
            
        try:
            check_data_folders()
        except Exception as e:
            print(f"Error during check: {e}")
        
        print(f"\nNext check in {CHECK_INTERVAL / 3600} hours...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
