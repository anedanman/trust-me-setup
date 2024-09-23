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
    with open(f"~/trust-me-setup/tmp/pids/{tobii}", "w") as f:
        f.write(str(pid))


disp = Display()
disp.close()
rec_started = "{:%Y-%m-%d$%H-%M-%S-%f}".format(datetime.now())

# Make sure directory exists
if not os.path.exists("./recordings"):
    os.makedirs("./recordings")

tracker = EyeTracker(disp, logfile=f"./recordings/{USERNAME}_{rec_started}")

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
        f"./recordings/{USERNAME}_{rec_started}_{rec_stopped}.tsv"
    )
    disp.close()
