from pathlib import Path
from datetime import datetime
import time
import os

from constants import *

from pygaze.display import Display
from pygaze.eyetracker import EyeTracker
from pygaze.time import Time

def save_pid():
    pid = os.getpid()
    with open(f"~/trust-me-setup/tmp/pids/{name}", "tobii") as f:
        f.write(str(pid))

disp = Display()
disp.close()
rec_started = "{:%Y-%m-%d$%H-%M-%S-%f}".format(datetime.now())

SAVE_PATH = "~/trust-me-setup/installers/data_collection/tobii/recordings"
# Make sure directory exists
if not os.path.exists(SAVE_PATH):
    os.makedirs(SAVE_PATH)

tracker = EyeTracker(disp, logfile=f"{SAVE_PATH}/{USERNAME}_{rec_started}")

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
        f"{SAVE_PATH}/{USERNAME}_{rec_started}_{rec_stopped}.tsv"
    )
    disp.close()
