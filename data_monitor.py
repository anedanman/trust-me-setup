#!/usr/bin/env python3
"""
Data Monitoring Script
Records current data folder sizes and sends an email report with measurement history.
Runs once when launched, keeps history of up to 5 measurements.
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
MAX_HISTORY = 5  # Show up to 5 measurements per device in email (all measurements stored locally)

# Data Monitor specific recipient email
RECIPIENT_EMAIL = "daniil.kirilenko@usi.ch"

print(f"Recipient Email: {RECIPIENT_EMAIL if RECIPIENT_EMAIL else 'Not configured'}")
print("=" * 50)

# Devices to monitor (subfolder names in data/USERNAME/)
DEVICES = ["audio", "hires", "tobii", "streamdeck", "highlights"]

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
        
        # Use du command for accurate folder size (macOS compatible)
        result = subprocess.run(
            ["du", "-sk", str(folder_path)], 
            capture_output=True, 
            text=True, 
            check=True
        )
        size_kb = int(result.stdout.split()[0])
        size_bytes = size_kb * 1024  # Convert KB to bytes
        return size_bytes
    except (subprocess.CalledProcessError, ValueError, IndexError) as e:
        print(f"Error getting size for {folder_path}: {e}")
        # Fallback to Python-based calculation
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, IOError):
                        continue
            return total_size
        except Exception as fallback_e:
            print(f"Fallback size calculation also failed: {fallback_e}")
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

def save_state(new_measurement):
    """Save current measurement to history in JSON file"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing state
        state = load_state()
        
        # Initialize history if it doesn't exist
        if "history" not in state:
            state["history"] = []
        
        # Add new measurement to history (keep all measurements)
        state["history"].append(new_measurement)
        
        # Save updated state (no limit on stored history)
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
    """Check data folder sizes and send email with measurement history"""
    username = get_username()
    current_time = datetime.now()
    current_timestamp = current_time.isoformat()
    
    # Load previous state
    state = load_state()
    history = state.get("history", [])
    
    # Base data directory for the user
    user_data_dir = SCRIPT_DIR / "data" / username
    
    if not user_data_dir.exists():
        print(f"Warning: User data directory not found: {user_data_dir}")
        return
    
    # Current measurement
    current_measurement = {
        "timestamp": current_timestamp,
        "devices": {}
    }
    
    print(f"\n=== Data Monitor Check - {current_time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    for device in DEVICES:
        # Special case for highlights - monitor directly in script directory
        if device == "highlights":
            device_folder = SCRIPT_DIR / "highlights"
        else:
            device_folder = user_data_dir / device
            
        current_size = get_folder_size(device_folder)
        current_measurement["devices"][device] = {
            "size": current_size,
            "path": str(device_folder)
        }
        
        print(f"{device:12}: {format_size(current_size):>10} ({device_folder})")
    
    # Generate email report
    subject = f"Data Monitor Report - {username} - {current_time.strftime('%Y-%m-%d %H:%M')}"
    body = generate_email_report(username, current_time, current_measurement, history)
    
    # Send email
    send_email_alert(subject, body)
    
    # Save current measurement to history
    save_state(current_measurement)
    print(f"Measurement saved to history: {STATE_FILE}")

def generate_email_report(username, current_time, current_measurement, history):
    """Generate detailed email report with measurement history"""
    body = f"Data monitoring report for user: {username}\n"
    body += f"Report generated: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    # Add current measurement info
    body += "=== CURRENT MEASUREMENT ===\n"
    for device in DEVICES:
        size = current_measurement["devices"][device]["size"]
        path = current_measurement["devices"][device]["path"]
        body += f"{device}: {format_size(size)} ({path})\n"
    
    body += "\n=== MEASUREMENT HISTORY ===\n"
    body += f"(Showing last {MAX_HISTORY} measurements per device)\n"
    
    if not history:
        body += "No previous measurements found. This is the first measurement.\n"
    else:
        # Show history for each device
        for device in DEVICES:
            body += f"\n--- {device.upper()} HISTORY ---\n"
            
            # Get device history (including current measurement)
            device_history = []
            for measurement in history:
                if device in measurement.get("devices", {}):
                    device_history.append({
                        "timestamp": measurement["timestamp"],
                        "size": measurement["devices"][device]["size"]
                    })
            
            # Add current measurement
            device_history.append({
                "timestamp": current_measurement["timestamp"],
                "size": current_measurement["devices"][device]["size"]
            })
            
            # Sort by timestamp (oldest first)
            device_history.sort(key=lambda x: x["timestamp"])
            
            # Keep only the last MAX_HISTORY measurements for email display
            if len(device_history) > MAX_HISTORY:
                device_history = device_history[-MAX_HISTORY:]
            
            # Display history
            for i, entry in enumerate(device_history):
                try:
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                    time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    time_str = entry["timestamp"]
                
                size = entry["size"]
                body += f"  {i+1}. {time_str}: {format_size(size)}"
                
                # Check for growth compared to previous measurement
                if i > 0:
                    prev_size = device_history[i-1]["size"]
                    if size > prev_size:
                        growth = size - prev_size
                        body += f" (📈 +{format_size(growth)})"
                    elif size == prev_size:
                        body += f" (⚠️ NO GROWTH)"
                    else:
                        shrinkage = prev_size - size
                        body += f" (📉 -{format_size(shrinkage)})"
                
                # Mark current measurement
                if i == len(device_history) - 1:
                    body += " ← CURRENT"
                
                body += "\n"
            
            # Summary for this device (based on displayed history)
            if len(device_history) > 1:
                first_size = device_history[0]["size"]
                last_size = device_history[-1]["size"]
                total_growth = last_size - first_size
                
                if total_growth > 0:
                    body += f"  📊 Growth in displayed period: +{format_size(total_growth)}\n"
                elif total_growth == 0:
                    body += f"  ⚠️ NO GROWTH in displayed period\n"
                else:
                    body += f"  📉 Shrinkage in displayed period: -{format_size(-total_growth)}\n"
    
    body += f"\n=== SUMMARY ===\n"
    
    # Check if any devices haven't grown since last measurement
    stale_devices = []
    if history:
        last_measurement = history[-1] if history else None
        if last_measurement:
            for device in DEVICES:
                current_size = current_measurement["devices"][device]["size"]
                if device in last_measurement.get("devices", {}):
                    last_size = last_measurement["devices"][device]["size"]
                    if current_size <= last_size:
                        stale_devices.append(device)
    
    if stale_devices:
        body += f"⚠️ Devices with no growth since last measurement: {', '.join(stale_devices)}\n"
    else:
        body += "✅ All devices showed growth since last measurement\n"
    
    body += f"\nTotal measurements in history (local): {len(history) + 1}\n"
    body += f"Measurements shown in email: up to {MAX_HISTORY} per device\n"
    body += f"Report generated at: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    return body

def main():
    """Main function - runs a single check and sends email report"""
    print("Starting Data Monitor...")
    print(f"Monitoring devices: {', '.join(DEVICES)}")
    print(f"Email reports to: {RECIPIENT_EMAIL if RECIPIENT_EMAIL else 'Not configured'}")
    print(f"Showing up to {MAX_HISTORY} measurements per device in email (all stored locally)")
    
    try:
        check_data_folders()
        print("\n✅ Data monitor check completed successfully")
    except Exception as e:
        print(f"❌ Error during check: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
