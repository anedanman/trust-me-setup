#!/usr/bin/env python3

#         Python Stream Deck Library
#      Released under the MIT license
#
#   dean [at] fourwalledcubicle [dot] com
#         www.fourwalledcubicle.com
#

# Example script showing basic library usage - updating key images with new
# tiles generated at runtime, and responding to button state change events.

import os
import threading
import time
import random
import subprocess
import sys
import datetime
import getpass
from utils import ka_exists

VERBOSE = True # Debug
DURATION = 10800 # set glocal sleep time in seconds (2 HRS)
# DURATION = 10 # set glocal sleep time in seconds (2 HRS)

CURRENT_Q = 1 # current question
FIXED_FEEDBACK = False
SLEEP_QUESTION = True
FREE_FEEDBACK = False
# Global time parameters for testing
DAY_START_TIME = datetime.time(8, 0, 0)  # 8:30:15 AM
DAY_END_TIME = datetime.time(17, 0, 0)   # 5:45:30 PM

# # # TODO test
# def increase_priority():
#     try:
#         old_nice = os.nice(0)
#         os.nice(-10)
#         new_nice = os.nice(0)
#         print(f"Niceness changed from {old_nice} to {new_nice} (higher priority).")
#     except PermissionError:
#         print("Permission denied: run this script with sudo to set a higher priority.")
#     except Exception as e:
#         print(f"Error while changing niceness: {e}")

# Get username from command line argument or file or default
if len(sys.argv) > 1:
    USERNAME = sys.argv[1]
else:
    try:
        with open(os.path.expanduser("~/trust-me-setup/tmp/current_username"), "r") as f:
            USERNAME = f.read().strip()
    except:
        USERNAME = "user1"

# Get base path from second argument or use default
BASE_PATH = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/trust-me-setup")
# keepalive_path = f"{BASE_PATH}/tmp/keepalive.td"

print(f"StreamDeck using username: {USERNAME}")
print(f"Using base path: {BASE_PATH}")

# Create data directory if it doesn't exist
DATA_DIR = os.path.join(BASE_PATH, f"data/{USERNAME}/streamdeck")
os.makedirs(DATA_DIR, exist_ok=True)

# Generate log filename once (instead of in each subprocess call)
CURRENT_DATE = datetime.datetime.now().strftime("%Y-%m-%d")
LOG_FILE = os.path.join(DATA_DIR, f"{CURRENT_DATE}")

from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

# Folder location of image assets used by this example.
ASSETS_PATH = os.path.join(os.path.dirname(__file__), "Assets")




def is_working_hours():
    """Check if current time is between DAY_START_TIME and DAY_END_TIME"""
    now = datetime.datetime.now()
    current_time = now.time()
    return DAY_START_TIME <= current_time <= DAY_END_TIME

def wait_until_nextday():
    """Wait until next day start time"""
    now = datetime.datetime.now()
    
    # Calculate next start time
    next_start = now.replace(hour=DAY_START_TIME.hour, minute=DAY_START_TIME.minute, second=0, microsecond=0)
    
    # If it's already past start time today, move to tomorrow
    if now.time() >= DAY_START_TIME:
        next_start += datetime.timedelta(days=1)
    
    wait_seconds = (next_start - now).total_seconds()
    print(f"Waiting until {next_start.strftime('%Y-%m-%d %H:%M:%S')} ({wait_seconds/3600:.1f} hours)")
    
    # Sleep in chunks to allow for graceful shutdown
    while wait_seconds > 0 and ka_exists():
        sleep_time = min(60, wait_seconds)  # Sleep max 1 minute at a time
        time.sleep(sleep_time)
        wait_seconds -= sleep_time




def alarm(deck):
    if not ka_exists(): return
    
    global FIXED_FEEDBACK
    global CURRENT_Q

    # update icon, not sleeping
    for key in range(deck.key_count()):
        update_key_image(deck, key, False)
    if not deck.is_open() or not ka_exists(): return
    wasSleep = SLEEP_QUESTION # This flag is used to determine whether the sleep question was ever present with the fixed loop
    while FIXED_FEEDBACK and ((not wasSleep and CURRENT_Q == 1) or (wasSleep and SLEEP_QUESTION)) and ka_exists(): # !!!!!!! - this is the line that caused the Stream Deck to basically become very slow in displaying stuff, because we had a while loop that continuously kept running
        # Sleep in 100 millis intervals for faster response
        for i in range (10):
            time.sleep(0.1)
            if CURRENT_Q != 1 or not FIXED_FEEDBACK or not ka_exists() or (wasSleep and not SLEEP_QUESTION):
                deck.set_brightness(100)
                return
            
        deck.set_brightness(0)
        # Sleep in 100 millis intervals for faster response
        for i in range (10):
            time.sleep(0.1)
            if CURRENT_Q != 1 or not FIXED_FEEDBACK or not ka_exists() or (wasSleep and not SLEEP_QUESTION): break # Break out of for, still in while, thus setting the brightness back to 100 in any case
        deck.set_brightness(100)
        
    # # finished, back sleep
    # for key in range(deck.key_count()):
    #     update_key_image(deck, key, False)

    return

def alarm_self_all_updates(deck):
    global FIXED_FEEDBACK
    global CURRENT_Q

    FIXED_FEEDBACK = True
    # update icon, not sleeping
    for key in range(deck.key_count()):
        update_key_image(deck, key, False)
        
        
def timer_function(deck):
    """Modified timer function with working hours logic"""
    global FIXED_FEEDBACK
    global FREE_FEEDBACK
    
    while deck.is_open() and ka_exists():
        # Only run during working hours
        if not is_working_hours():
            print("Outside working hours. Waiting until next day start...")
            wait_until_nextday()
            continue
            
        # create a new sleep time (only during working hours)
        # Calculate remaining working time for today
        now = datetime.datetime.now()
        end_of_work = now.replace(hour=DAY_END_TIME.hour, minute=DAY_END_TIME.minute, second=0, microsecond=0)
        remaining_work_seconds = (end_of_work - now).total_seconds()
        
        # Don't exceed working hours
        max_sleep_time = min(DURATION, int(remaining_work_seconds))
        if max_sleep_time <= 0:
            continue  # Go back to check working hours
            
        time_sleep = random.randint(0, max_sleep_time)
        time_sleep_left = max_sleep_time - time_sleep

        # Wait for time_sleep seconds, but check working hours
        for i in range(time_sleep):
            if not ka_exists() or not is_working_hours():
                return
            if not deck.is_open():
                break
            time.sleep(1)

        # Check if still in working hours before triggering feedback
        if not is_working_hours():
            continue
            
        # time up, but wait for FREE_FEEDBACK if is active
        while FREE_FEEDBACK or FIXED_FEEDBACK:
            if not ka_exists() or not is_working_hours(): 
                return
            time.sleep(1)
                    
        FIXED_FEEDBACK = True
        alarm(deck)  # Function to call
        
        # Wait remaining time, but respect working hours
        for i in range(time_sleep_left):
            if not ka_exists() or not is_working_hours():
                return
            time.sleep(1)


# Generates a custom tile with run-time generated text and custom image via the PIL module.
def render_key_image(deck, icon_filename, font_filename, label_text):
    # Resize the source image asset to best-fit the dimensions of a single key,
    # leaving a margin at the bottom so that we can draw the key title
    # afterwards.
    icon = Image.open(icon_filename)
    image = PILHelper.create_scaled_key_image(deck, icon, margins=[0, 0, 0, 0])

    # Load a custom TrueType font and use it to overlay the key index, draw key
    # label onto the image a few pixels from the bottom of the key.
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_filename, 2)
    draw.text((image.width / 2, image.height - 5), text=label_text, font=font, anchor="ms", fill="white")

    return PILHelper.to_native_key_format(deck, image)

# Returns styling information for a key based on its position and state.
def get_key_style(deck, key, state): # device, int, False
    global FIXED_FEEDBACK
    global FREE_FEEDBACK   
    global CURRENT_Q
    global SLEEP_QUESTION

    if SLEEP_QUESTION:
        if key == 0:
            icon = "qsleep/1.png"
        elif key == 1:
            icon = "qsleep/2.png"
        elif key == 2:
            icon = "qsleep/3.png"
        elif key == 3:
            icon = "qsleep/4.png"
        elif key == 4:
            icon = "qsleep/5.png"
        elif key == 6:
            icon = "qsleep/6.png"
        elif key == 8:
            icon = "qsleep/back.png"
        elif key == 5:
            icon = "numero/0.png"
        elif key == 10:
            icon = "numero/1.png"
        elif key == 11:
            icon = "numero/2.png"
        elif key == 12:
            icon = "numero/3.png"
        elif key == 13:
            icon = "numero/4.png"
        elif key == 14:
            icon = "numero/5.png"
        elif key == 9:
            icon = "numero/6.png"
        elif key == 7:
            icon = "static/black.png"



    # sleeping render
    elif not FIXED_FEEDBACK and not FREE_FEEDBACK: 
        if key == 0:
            name = "T"
            icon = "T.png"
            label = ""
        elif key == 1:
            name = "R"
            icon = "R.png"
            label = ""
        elif key == 2:
            name = "U"
            icon = "U.png"
            label = ""
        elif key == 3:
            name = "S"
            icon = "S.png"
            label = ""
        elif key == 4:
            name = "T"
            icon = "T.png"
            label = ""
        elif key == 5:
            name = "1"
            icon = "1.png"
            label = ""
        elif key == 6:
            name = "2"
            icon = "2.png"
            label = ""
        elif key == 7:
            name = "3"
            icon = "3.png"
            label = ""
        elif key == 8:
            name = "4"
            icon = "4.png"
            label = ""
        elif key == 9:
            name = "ME"
            icon = "ME.png"
            label = ""
        elif key == 10:
            name = "5"
            icon = "5.png"
            label = ""
        elif key == 11:
            name = "6"
            icon = "6.png"
            label = ""
        elif key == 12:
            name = "7"
            icon = "7.png"
            label = ""
        elif key == 13:
            name = "8"
            icon = "8.png"
            label = ""
        elif key == 14:
            name = "9"
            icon = "9.png"
            label = ""

        icon = "static/"+icon

    # in FIXED_FEEDBACK or FREE_FEEDBACK mode, render questions
    else:

        if CURRENT_Q == 1: #first question
            if key == 0:
                icon = "q1/1.png"
            elif key == 1:
                icon = "q1/2.png"
            elif key == 2:
                icon = "q1/3.png"
            elif key == 3:
                icon = "q1/4.png"
            elif key == 4:
                icon = "q1/5.png"
            elif key == 8:
                icon = "q1/back.png"
            elif key == 5:
                icon = "numero/m3.png"
            elif key == 10:
                icon = "numero/m2.png"
            elif key == 11:
                icon = "numero/m1.png"
            elif key == 12:
                icon = "numero/0.png"
            elif key == 13:
                icon = "numero/1.png"
            elif key == 14:
                icon = "numero/2.png"
            elif key == 9:
                icon = "numero/3.png"
            elif key == 6:
                icon = "static/black.png"
            elif key == 7:
                icon = "static/black.png"

        elif CURRENT_Q == 2: #second question
            if key == 0:
                icon = "q2/1.png"
            elif key == 1:
                icon = "q2/2.png"
            elif key == 2:
                icon = "q2/3.png"
            elif key == 3:
                icon = "q2/4.png"
            elif key == 4:
                icon = "q2/5.png"
            elif key == 8:
                icon = "q2/back.png"
            elif key == 5:
                icon = "numero/0.png"
            elif key == 10:
                icon = "numero/1.png"
            elif key == 11:
                icon = "numero/2.png"
            elif key == 12:
                icon = "numero/3.png"
            elif key == 13:
                icon = "numero/4.png"
            elif key == 14:
                icon = "numero/5.png"
            elif key == 9:
                icon = "numero/6.png"
            elif key == 6:
                icon = "static/black.png"
            elif key == 7:
                icon = "static/black.png"
       
        elif CURRENT_Q == 3: #third question
            if key == 0:
                icon = "q3/1.png"
            elif key == 1:
                icon = "q3/2.png"
            elif key == 2:
                icon = "q3/3.png"
            elif key == 3:
                icon = "q3/4.png"
            elif key == 8:
                icon = "q3/back.png"
            elif key == 5:
                icon = "numero/0.png"
            elif key == 10:
                icon = "numero/1.png"
            elif key == 11:
                icon = "numero/2.png"
            elif key == 12:
                icon = "numero/3.png"
            elif key == 13:
                icon = "numero/4.png"
            elif key == 14:
                icon = "numero/5.png"
            elif key == 9:
                icon = "numero/6.png"
            elif key == 4:
                icon = "static/black.png"
            elif key == 6:
                icon = "static/black.png"
            elif key == 7:
                icon = "static/black.png"

        elif CURRENT_Q == 4: #fourth question
            if key == 0:
                icon = "q4/1.png"
            elif key == 1:
                icon = "q4/2.png"
            elif key == 2:
                icon = "q4/3.png"
            elif key == 3:
                icon = "q4/4.png"
            elif key == 4:
                icon = "q4/5.png"
            elif key == 6:
                icon = "q4/6.png"
            elif key == 8:
                icon = "q4/back.png"
            elif key == 5:
                icon = "numero/0.png"
            elif key == 10:
                icon = "numero/1.png"
            elif key == 11:
                icon = "numero/2.png"
            elif key == 12:
                icon = "numero/3.png"
            elif key == 13:
                icon = "numero/4.png"
            elif key == 14:
                icon = "numero/5.png"
            elif key == 9:
                icon = "numero/6.png"
            elif key == 7:
                icon = "static/black.png"

        elif CURRENT_Q == 5: #fifth question
            if key == 0:
                icon = "q5/1.png"
            elif key == 1:
                icon = "q5/2.png"
            elif key == 2:
                icon = "q5/3.png"
            elif key == 3:
                icon = "q5/4.png"
            elif key == 4:
                icon = "q5/5.png"
            elif key == 8:
                icon = "q5/back.png"
            elif key == 5:
                icon = "numero/0.png"
            elif key == 10:
                icon = "numero/1.png"
            elif key == 11:
                icon = "numero/2.png"
            elif key == 12:
                icon = "numero/3.png"
            elif key == 13:
                icon = "numero/4.png"
            elif key == 14:
                icon = "numero/5.png"
            elif key == 9:
                icon = "numero/6.png"
            elif key == 6:
                icon = "static/black.png"
            elif key == 7:
                icon = "static/black.png"

        elif CURRENT_Q == 6: #sixth question
            if key == 0:
                icon = "q6/1.png"
            elif key == 1:
                icon = "q6/2.png"
            elif key == 2:
                icon = "q6/3.png"
            elif key == 3:
                icon = "q6/4.png"
            elif key == 4:
                icon = "q6/5.png"
            elif key == 6:
                icon = "q6/6.png"
            elif key == 8:
                icon = "q6/back.png"
            elif key == 5:
                icon = "numero/m3.png"
            elif key == 10:
                icon = "numero/m2.png"
            elif key == 11:
                icon = "numero/m1.png"
            elif key == 12:
                icon = "numero/0.png"
            elif key == 13:
                icon = "numero/1.png"
            elif key == 14:
                icon = "numero/2.png"
            elif key == 9:
                icon = "numero/3.png"
            elif key == 7:
                icon = "static/black.png"
 
        elif CURRENT_Q == 7: #seventh question
            if key == 0:
                icon = "q7/1.png"
            elif key == 1:
                icon = "q7/2.png"
            elif key == 2:
                icon = "q7/3.png"
            elif key == 3:
                icon = "q7/4.png"
            elif key == 8:
                icon = "q7/back.png"
            elif key == 5:
                icon = "numero/m3.png"
            elif key == 10:
                icon = "numero/m2.png"
            elif key == 11:
                icon = "numero/m1.png"
            elif key == 12:
                icon = "numero/0.png"
            elif key == 13:
                icon = "numero/1.png"
            elif key == 14:
                icon = "numero/2.png"
            elif key == 9:
                icon = "numero/3.png"
            elif key == 4:
                icon = "static/black.png"
            elif key == 6:
                icon = "static/black.png"
            elif key == 7:
                icon = "static/black.png"

        elif CURRENT_Q == 8: #eighth question
            if key == 0:
                icon = "q8/1.png"
            elif key == 1:
                icon = "q8/2.png"
            elif key == 2:
                icon = "q8/3.png"
            elif key == 3:
                icon = "q8/4.png"
            elif key == 8:
                icon = "q8/back.png"
            elif key == 5:
                icon = "numero/0.png"
            elif key == 10:
                icon = "numero/1.png"
            elif key == 11:
                icon = "numero/2.png"
            elif key == 12:
                icon = "numero/3.png"
            elif key == 13:
                icon = "numero/4.png"
            elif key == 14:
                icon = "numero/5.png"
            elif key == 9:
                icon = "numero/6.png"
            elif key == 4:
                icon = "static/black.png"
            elif key == 6:
                icon = "static/black.png"
            elif key == 7:
                icon = "static/black.png"

        else: #ninth question
            if key == 0:
                icon = "q9/1.png"
            elif key == 1:
                icon = "q9/2.png"
            elif key == 2:
                icon = "q9/3.png"
            elif key == 3:
                icon = "q9/4.png"
            elif key == 4:
                icon = "q9/5.png"
            elif key == 6:
                icon = "q9/6.png"
            elif key == 7:
                icon = "q9/7.png"
            elif key == 8:
                icon = "q9/back.png"
            elif key == 5:
                icon = "numero/0.png"
            elif key == 10:
                icon = "numero/1.png"
            elif key == 11:
                icon = "numero/2.png"
            elif key == 12:
                icon = "numero/3.png"
            elif key == 13:
                icon = "numero/4.png"
            elif key == 14:
                icon = "numero/5.png"
            elif key == 9:
                icon = "numero/6.png"

    return {
        "name": "",
        "icon": os.path.join(ASSETS_PATH, icon),
        "font": os.path.join(ASSETS_PATH, "Roboto-Regular.ttf"),
        "label": ""
    }

# Creates a new key image based on the key index, style and current key state
# and updates the image on the StreamDeck.
def update_key_image(deck, key, state): # device, int, False
    # Determine what icon and label to use on the generated key.
    key_style = get_key_style(deck, key, state)
    # Generate the custom key with the requested image and label.
    image = render_key_image(deck, key_style["icon"], key_style["font"], key_style["label"])

    # Use a scoped-with on the deck to ensure we're the only thread using it
    # right now.
    with deck:
        # Update requested key with the generated image.
        deck.set_key_image(key, image)

# Prints key state change information, updates the key image and performs any
# associated actions when a key is pressed.
def key_change_callback(deck, key, state):
    global FIXED_FEEDBACK
    global FREE_FEEDBACK
    global CURRENT_Q
    global SLEEP_QUESTION
    global USERNAME
    global LOG_FILE


    # one press makes two callbacks (state: True - False)
    # pressed reactions only
    if not state: return

    # print("flag1")
    # print(FIXED_FEEDBACK)
    # print(FREE_FEEDBACK)
        
    if SLEEP_QUESTION:
        # misclick
        if key in [0, 1, 2, 3, 4, 6, 7, 8]:
            return
        
        # feedbacked click
        else:
            # record question
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_FILE, "a") as f:
                f.write(f"{timestamp} CURRENT QUESTION: SLEEP\n")

            # record answer
            default_answer = 0
            if key == 5:
                default_answer = 0
            elif key == 10:
                default_answer = 1
            elif key == 11:
                default_answer = 2
            elif key == 12:
                default_answer = 3
            elif key == 13:
                default_answer = 4
            elif key == 14:
                default_answer = 5
            else:
                default_answer = 6

            default_answer = default_answer

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_FILE, "a") as f:
                f.write(f"{timestamp} FEEDBACK LEVEL: {default_answer}\n")
            
            SLEEP_QUESTION = False

            for key in range(deck.key_count()): # The images must be updated to show the new question!
                update_key_image(deck, key, False)
            
            return



    # receiving feedback from FREE_FEEDBACK
    elif FREE_FEEDBACK:
        # misclick
        if key in [0, 1, 2, 3, 4, 6, 7]:
            return
        
        # back button   
        elif key == 8:
            FREE_FEEDBACK = False
            CURRENT_Q = 1
            # render static and then return
            for key in range(deck.key_count()):
                update_key_image(deck, key, False)
            return
        
        # feedbacked click
        else:
            # record question
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_FILE, "a") as f:
                f.write(f"{timestamp} CURRENT QUESTION: {CURRENT_Q}\n")
            
            # record answer
            default_answer = 0
            if key == 5:
                default_answer = 0
            elif key == 10:
                default_answer = 1
            elif key == 11:
                default_answer = 2
            elif key == 12:
                default_answer = 3
            elif key == 13:
                default_answer = 4
            elif key == 14:
                default_answer = 5
            else:
                default_answer = 6

            if CURRENT_Q in [1,6,7]:
                default_answer = default_answer - 3

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_FILE, "a") as f:
                f.write(f"{timestamp} FEEDBACK LEVEL: {default_answer}\n")
            
            FREE_FEEDBACK = False
            CURRENT_Q = 1
            # render static and then return
            for key in range(deck.key_count()):
                update_key_image(deck, key, False)
            return
            

    # in static, enter FREE_FEEDBACK or misclick
    elif not FIXED_FEEDBACK:

        # misclick
        if key in [0, 1, 3, 4]: return

        # game mode, clicking U
        if key == 2:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_FILE, "a") as f:
                f.write(f"{timestamp} GAME STARTS\n")
            return

        # self all report
        if key == 9:
            # print("flag: open 9")
            alarm_self_all_updates(deck)
            return
        
        # FREE_FEEDBACK
        FREE_FEEDBACK = True
        if key == 5:
            CURRENT_Q = 1
        elif key == 6:
            CURRENT_Q = 2
        elif key == 7:
            CURRENT_Q = 3
        elif key == 8:
            CURRENT_Q = 4
        elif key == 10:
            CURRENT_Q = 5
        elif key == 11:
            CURRENT_Q = 6
        elif key == 12:
            CURRENT_Q = 7
        elif key == 13:
            CURRENT_Q = 8
        elif key == 14:
            CURRENT_Q = 9

        # render question and then return
        for key in range(deck.key_count()):
            update_key_image(deck, key, False)
        return        

    # FIXED_FEEDBACK loop
    else:
        # print("flag3")
        # record question
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"{timestamp} CURRENT QUESTION: {CURRENT_Q}\n")

        #invalid click
        if key in [0,1,2,3,4,6,7,8]:
            return

        # record answer
        default_answer = 0
        if key == 5:
            default_answer = 0
        elif key == 10:
            default_answer = 1
        elif key == 11:
            default_answer = 2
        elif key == 12:
            default_answer = 3
        elif key == 13:
            default_answer = 4
        elif key == 14:
            default_answer = 5
        else:
            default_answer = 6

        if CURRENT_Q in [1,6,7]:
            default_answer = default_answer - 3

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"{timestamp} FEEDBACK LEVEL: {default_answer}\n")
                
        if CURRENT_Q < 9:
            CURRENT_Q += 1
            # print("QUESTION HERE!")
            for key in range(deck.key_count()):
                update_key_image(deck, key, False)
            return
        else:
            # print("FIXED FEEDBACK OFF!")
            CURRENT_Q = 1
            FIXED_FEEDBACK = False  
            for key in range(deck.key_count()):
                update_key_image(deck, key, False)
            return     


# Modified main section
if __name__ == "__main__":
    streamdecks = DeviceManager().enumerate()

    if len(streamdecks) and VERBOSE:
        print("Streamdeck Found.")

    for index, deck in enumerate(streamdecks):
        deck.open()
        deck.reset()
        deck.set_brightness(90)

        # Main loop with daily schedule
        while ka_exists():
            # Wait until working hours if necessary
            if not is_working_hours():
                print("Outside working hours. StreamDeck sleeping...")
                # Turn off display
                deck.reset()
                deck.set_brightness(0)
                wait_until_nextday()
                
                # Check if we should continue
                if not ka_exists():
                    break
                    
                # Reset for new day
                deck.set_brightness(90)
                print("New day started! Resetting to sleep question...")
            
            # Start timer thread for this work day
            timer_thread = threading.Thread(target=timer_function, args=(deck,))
            timer_thread.daemon = True
            timer_thread.start()

            # Reset to sleep question at start of each day
            # global SLEEP_QUESTION, FIXED_FEEDBACK, FREE_FEEDBACK, CURRENT_Q
            SLEEP_QUESTION = True
            FIXED_FEEDBACK = False
            FREE_FEEDBACK = False
            CURRENT_Q = 1
            
            # Set initial key images
            for key in range(deck.key_count()):
                update_key_image(deck, key, False)

            # Register callback function
            deck.set_key_callback(key_change_callback)    

            # Main working hours loop
            while ka_exists() and is_working_hours():
                time.sleep(0.2)
            
            # End of work day - clean up
            print("End of work day. Stopping timer thread...")
            timer_thread.join(timeout=5)  # Wait max 5 seconds for thread to finish
            
            # Log end of day
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_FILE, "a") as f:
                f.write(f"{timestamp} END OF WORK DAY\n")
        
        # Final cleanup
        deck.set_brightness(100)
        deck.reset()
        deck.close()
        
        print("StreamDeck session ended.")
        
        # Wait until all application threads have terminated
        for t in threading.enumerate():
            try:
                t.join()
            except RuntimeError:
                pass
