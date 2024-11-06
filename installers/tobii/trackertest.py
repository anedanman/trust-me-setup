# This script tests all eyetracker functions of PyGaze; run it to see if
# your installation is working as it is supposed to. Remember to adjust the
# constants in the attached constants.py script to the relevant values for
# your system and preference!
#
# contents of the directory in which this script should come:
# PyGaze_supertest.py (this script)
# constants.py (script containing constants)
# bark.ogg (soundfile)
# kitten.png (image file)
#
# version: 22 Dec 2013

import os
import random
import copy

from pygaze.defaults import *
from constants import *

from pygaze.display import Display
from pygaze.screen import Screen
from pygaze.eyetracker import EyeTracker
from pygaze.keyboard import Keyboard
from pygaze.sound import Sound
from pygaze.time import Time
from pygaze.logfile import Logfile
from datetime import datetime

DIR = os.path.split(os.path.abspath(__file__))[0]

# initialize the display
disp = Display()

# initialize a screen
scr = Screen()

# initialize an EyeTracker
tracker = EyeTracker(disp)

# initialize a keyboard
kb = Keyboard(keylist=["space"], timeout=None)

# initialize the current time for the file name
rec_started = "{:%Y-%m-%d$%H-%M-%S-%f}".format(datetime.now())
timer = Time()

scr.draw_text(
    "Welcome to the PyGaze Supertest!\n\nYou're going to be testing \
your PyGaze installation today, using this interactive tool. Press Space \
to start!\n\n\nP.S. If you see this, the following functions work: \
\n- Screen.draw_text \
\n- Disp.fill \
\n- Disp.show \
\nAwesome!",
    fontsize=50
)
disp.fill(scr)
t1 = disp.show()
t1 = "{:%Y-%m-%d$%H-%M-%S}".format(datetime.now())
# log.write(["welcome", t1])



scr.clear()
scr.draw_text(
    "We're now going to test the eyetracker module. Press Space to start!", 
    fontsize=50
)
disp.fill(scr)
t1 = disp.show()
t1 = "{:%Y-%m-%d$%H-%M-%S}".format(datetime.now())
# log.write(["EyeTracker", t1])
kb.get_key()


# tracker.sample()
scr.clear()
disp.fill(scr)
disp.show()
tracker.start_recording()
key = None
while not key == "space":
    # get new key
    key, presstime = kb.get_key(timeout=1)
    # new states
    gazepos = tracker.sample()
    pupil_size = tracker.pupil_size()
    
    # Get latest gaze sample from tracker
    gaze_sample = copy.copy(tracker.gaze[-1])
    print('gaze length:', len(tracker.gaze))

    
    # Calculate distance using both eyes when available
    distance = []
    if gaze_sample['right_gaze_origin_validity']:
                    distance.append(round(gaze_sample['right_gaze_origin_in_user_coordinate_system'][2] / 10, 1))

    if gaze_sample['left_gaze_origin_validity']:
                    distance.append(round(gaze_sample['left_gaze_origin_in_user_coordinate_system'][2] / 10, 1))
    
    distance = tracker._mean(distance)
    
    # draw to screen
    scr.clear()
    distance_text = f"Distance: {distance:.1f} cm" if distance else "Distance: Not available"
    scr.draw_text(f"The dot follows your eyes. Watch your pupil size and distance.\n\nPupil size: {pupil_size:.2f}\n{distance_text}", fontsize=50)
    scr.draw_fixation(
        fixtype="dot", 
        pos=gazepos,
        pw=3, 
        diameter=max(5, (pupil_size - 1) * 30)  # Ensure minimum visible size
    )
    disp.fill(scr)
    disp.show()
tracker.stop_recording()
scr.clear()

# initialize the current time for the file name
rec_stopped = "{:%Y-%m-%d$%H-%M-%S-%f}".format(datetime.now())

# ending screen
scr.clear()
scr.draw_text("That's all folks! Press Space to quit.", fontsize=50)
disp.fill(scr)
t1 = disp.show()
t1 = "{:%Y-%m-%d$%H-%M-%S}".format(datetime.now())
# log.write(["ending", t1])
kb.get_key()

# close
# log.close()
tracker.close()
# change file name
os.rename(tracker.datafile.name, f"USER{USERNAME}_{rec_started}_{rec_stopped}.tsv")
disp.close()
timer.expend()
