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


DIR = os.path.split(os.path.abspath(__file__))[0]

# initialize the display
disp = Display()

# initialize a screen
scr = Screen()

# initialize an EyeTracker
tracker = EyeTracker(disp)

# initialize a keyboard
kb = Keyboard(keylist=["space"], timeout=None)

# initialize a Timer
timer = Time()

# create a new logfile
log = Logfile(filename="test")
log.write(["test", "time"])


# welcome
scr.draw_text(
    "Welcome to the PyGaze Supertest!\n\nYou're going to be testing \
your PyGaze installation today, using this interactive tool. Press Space \
to start!\n\n\nP.S. If you see this, the following functions work: \
\n- Screen.draw_text \
\n- Disp.fill \
\n- Disp.show \
\nAwesome!",
    colour=(0, 0, 0),
    fontsize=50,
)
disp.fill(scr)
t1 = disp.show()
t1 = "{:%Y-%m-%d$%H-%M-%S}".format(datetime.now())
log.write(["welcome", t1])
kb.get_key()


scr.clear()
scr.draw_text(
    "We're now going to test the eyetracker module. Press Space to start!",
    colour=(0, 0, 0),
    fontsize=50,
)
disp.fill(scr)
t1 = disp.show()
t1 = "{:%Y-%m-%d$%H-%M-%S}".format(datetime.now())
log.write(["EyeTracker", t1])
kb.get_key()

# tracker.calibrate
tracker.calibrate()

# tracker.sample()
scr.clear()
scr.draw_text("The dot should follow your eye movements", colour=(0, 0, 0), fontsize=50)
disp.fill(scr)
disp.show()

scr.clear()

# ending screen
scr.clear()
scr.draw_text("That's all folks! Press Space to quit.", colour=(0, 0, 0), fontsize=50)
disp.fill(scr)
t1 = disp.show()
t1 = "{:%Y-%m-%d$%H-%M-%S}".format(datetime.now())
log.write(["ending", t1])
kb.get_key()

# close
log.close()
tracker.close()
disp.close()
