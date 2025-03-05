from pathlib import Path
from datetime import datetime
import time
import os
import sys

from distance_tobii import DistanceTobii

from pygaze.display import Display
from pygaze.eyetracker import EyeTracker
from pygaze.time import Time

def save_pid(base_path):
    pid = os.getpid()
    with open(f"{base_path}/tmp/pids/tobii", "w") as f:
        f.write(str(pid))

def main():
    # Get username from command line argument or file or default
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = "user1"
    
    # Get base path from command line argument or use default
    base_path = sys.argv[2] if len(sys.argv) > 2 else "/home/$(whoami)/trust-me-setup"
    
    print(f"Tobii recording with username: {username}")
    print(f"Using base path: {base_path}")

    disp = Display()
    disp.close()
    rec_started = "{:%Y-%m-%d$%H-%M-%S-%f}".format(datetime.now())

    # Make sure directory exists
    data_dir = f"{base_path}/installers/data_collection/data/tobii"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    tracker = DistanceTobii(disp, logfile=f"{data_dir}/{username}_{rec_started}")

    timer = Time()
    tracker.start_recording()
    print("Recording started")
    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nRecording stopped")
        tracker.stop_recording()
        rec_stopped = "{:%Y-%m-%d$%H-%M-%S-%f}".format(datetime.now())
        Path(tracker.datafile.name).rename(
            f"{data_dir}/{username}_{rec_started}_{rec_stopped}.tsv"
        )
        disp.close()

if __name__ == "__main__":
    main()
