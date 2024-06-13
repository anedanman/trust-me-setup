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

# from pygaze.plugins.aoi import AOI
# from pygaze.plugins.frl import FRL
# from pygaze.plugins.gazecursor import GazeCursor
 
 
# # # # #
# directory stuff
 
DIR = os.path.split(os.path.abspath(__file__))[0]
# soundfile = os.path.join(DIR, 'bark.ogg')
# imagefile = os.path.join(DIR, 'kitten.png')
 
 
# # # # #
# create instances
 
# initialize the display
disp = Display()
 
# initialize a screen
scr = Screen()
 
# initialize an EyeTracker
tracker = EyeTracker(disp)
 
# initialize a keyboard
kb = Keyboard(keylist=['space'],timeout=None)
 
# initialize a sound
# snd = Sound(soundfile=soundfile)
 
# initialize a Timer
# initialize the current time for the file name

timer = Time()
 
# create a new logfile
log = Logfile(filename="test")
log.write(["test", "time"])
 
 
# # # # #
# welcome
 
scr.draw_text("Welcome to the PyGaze Supertest!\n\nYou're going to be testing \
your PyGaze installation today, using this interactive tool. Press Space \
to start!\n\n\nP.S. If you see this, the following functions work: \
\n- Screen.draw_text \
\n- Disp.fill \
\n- Disp.show \
\nAwesome!",colour=(0, 0, 0),fontsize=30)
disp.fill(scr)
t1 = disp.show()
t1='{:%Y-%m-%d$%H-%M-%S}'.format(datetime.now())
log.write(["welcome", t1])
kb.get_key()
 
 
# # # # #
# test EyeTracker
 
#EyeTracker.connected
#EyeTracker.log_var
#EyeTracker.pupil_size
#EyeTracker.send_command
#EyeTracker.wait_for_event
 
scr.clear()
scr.draw_text("We're now going to test the eyetracker module. Press Space to start!",colour=(0, 0, 0),fontsize=30)
disp.fill(scr)
t1 = disp.show()
t1='{:%Y-%m-%d$%H-%M-%S}'.format(datetime.now())
log.write(["EyeTracker", t1])
kb.get_key()
 
# tracker.calibrate
tracker.calibrate()
 
# tracker.sample()
scr.clear()
scr.draw_text("The dot should follow your eye movements",colour=(0, 0, 0),fontsize=30)
disp.fill(scr)
disp.show()

scr.clear()
 
 
# # # # #
# close down
 
# ending screen
scr.clear()
scr.draw_text("That's all folks! Press Space to quit.",colour=(0, 0, 0),fontsize=30)
disp.fill(scr)
t1 = disp.show()
t1='{:%Y-%m-%d$%H-%M-%S}'.format(datetime.now())
log.write(["ending", t1])
kb.get_key()
 
# close
log.close()
tracker.close()
# change file name
# from pathlib import Path

# Path(tracker.datafile.name).rename(f"./recordings/calibrationUSER{USERNAME}.tsv")

disp.close()
# timer.expend()
 
