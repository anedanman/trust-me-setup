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

VERBOSE = False # Debug
DURATION = 10800 # set glocal sleep time in seconds (3 HRS)
CURRENT_Q = 1 # current question
NEED_PRESS = False
USERNAME = 'user1'

# define subprocess
import subprocess
level1 = f"/bin/bash -c 'echo \"$(date) Feedback Level: 1.\" >> /home/$(whoami)/trust-me-setup/installers/streamdeck/Recording/{USERNAME}_$(date +\"%Y-%m-%d\")'"
level2 = f"/bin/bash -c 'echo \"$(date) Feedback Level: 2.\" >> /home/$(whoami)/trust-me-setup/installers/streamdeck/Recording/{USERNAME}_$(date +\"%Y-%m-%d\")'"
level3 = f"/bin/bash -c 'echo \"$(date) Feedback Level: 3.\" >> /home/$(whoami)/trust-me-setup/installers/streamdeck/Recording/{USERNAME}_$(date +\"%Y-%m-%d\")'"
level4 = f"/bin/bash -c 'echo \"$(date) Feedback Level: 4.\" >> /home/$(whoami)/trust-me-setup/installers/streamdeck/Recording/{USERNAME}_$(date +\"%Y-%m-%d\")'"
level5 = f"/bin/bash -c 'echo \"$(date) Feedback Level: 5.\" >> /home/$(whoami)/trust-me-setup/installers/streamdeck/Recording/{USERNAME}_$(date +\"%Y-%m-%d\")'"
# labels = {0: 'Very Happy', 1: 'Happy', 2: 'Fine', 3: 'Unhappy', 4: 'Angry'}


from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

# Folder location of image assets used by this example.
ASSETS_PATH = os.path.join(os.path.dirname(__file__), "Assets")

def alarm(deck):
    global NEED_PRESS

    # update icon, not sleeping
    for key in range(deck.key_count()):
        update_key_image(deck, key, False)

    if not deck.is_open():
        return
    while NEED_PRESS:
        time.sleep(1)
        deck.set_brightness(0)
        time.sleep(1)
        deck.set_brightness(100)

    # finished, back sleep
    for key in range(deck.key_count()):
        update_key_image(deck, key, False)

    return

def timer_function(deck):
    global NEED_PRESS
    while deck.is_open():
        # create a new sleep time:
        time_sleep = random.randint(0,DURATION)
        time_sleep_left = DURATION - time_sleep

        for i in range(time_sleep): # Wait for SLEEP_TIME seconds
            if not deck.is_open():
                break
            time.sleep(1)
        NEED_PRESS = True
        alarm(deck)  # Function to call every 10 seconds
        time.sleep(time_sleep_left)



# Generates a custom tile with run-time generated text and custom image via the
# PIL module.
def render_key_image(deck, icon_filename, font_filename, label_text):
    # Resize the source image asset to best-fit the dimensions of a single key,
    # leaving a margin at the bottom so that we can draw the key title
    # afterwards.
    icon = Image.open(icon_filename)
    image = PILHelper.create_scaled_key_image(deck, icon, margins=[0, 0, 20, 0])

    # Load a custom TrueType font and use it to overlay the key index, draw key
    # label onto the image a few pixels from the bottom of the key.
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_filename, 14)
    draw.text((image.width / 2, image.height - 5), text=label_text, font=font, anchor="ms", fill="white")

    return PILHelper.to_native_key_format(deck, image)


# Returns styling information for a key based on its position and state.
def get_key_style(deck, key, state): # device, int, False
    global NEED_PRESS   
    global CURRENT_Q
    # Last button in the example application is the exit button.
    # exit_key_index = deck.key_count() - 1   # 5

    # if key == exit_key_index:
    #     name = "exit"
    #     icon = "{}.png".format("Exit")
    #     font = "Roboto-Regular.ttf"
    #     label = "Bye" if state else "Exit"
    # else:
    #     name = "emoji"
    #     icon = "{}{}.png".format("Pressed" if state else "Released",key)
    #     font = "Roboto-Regular.ttf"
    #     label = "Recorded" if state else labels[key]

    question_button = 1  # 1

    # sleeping render
    if not NEED_PRESS: 
        name = "Sleep"
        icon = "{}.png".format("sleep")
        font = "Roboto-Regular.ttf"
        label = ""   

    elif key == question_button:
        name = "question"
        icon = "{}{}.png".format("Q",CURRENT_Q)
        font = "Roboto-Regular.ttf"
        label = ""

    elif key == 0:
        name = "level"
        icon = "{}{}.png".format("Pressed" if state else "L",1)
        font = "Roboto-Regular.ttf"
        label = "Recorded" if state else ""
    
    else:
        name = "level"
        icon = "{}{}.png".format("Pressed" if state else "L",key)
        font = "Roboto-Regular.ttf"
        label = "Recorded" if state else ""


    return {
        "name": name,
        "icon": os.path.join(ASSETS_PATH, icon),
        "font": os.path.join(ASSETS_PATH, font),
        "label": label
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


# Prints key state change information, updates rhe key image and performs any
# associated actions when a key is pressed.
def key_change_callback(deck, key, state):
    global NEED_PRESS

    # not recorded if no need to
    if not NEED_PRESS:
        return

    # else starting from Q1
    global CURRENT_Q
    
    print(CURRENT_Q)

    update_key_image(deck, 1, state) # question key 
    update_key_image(deck, key, state)
    key_style = get_key_style(deck, key, state)

    # dont press the question
    if key == 1:
        return

    # dont care realizing key
    if not state:
        return

    subprocess.run(f"/bin/bash -c 'echo \"$(date) CURRENT QUESTION: {CURRENT_Q}\" >> /home/$(whoami)/trust-me-setup/installers/streamdeck/Recording/{USERNAME}_$(date +\"%Y-%m-%d\")'", shell=True, check=True)

    # not last question
    if CURRENT_Q <9:
        if key==0:
            subprocess.run(level1, shell=True, check=True)
        elif key==2:
            subprocess.run(level2, shell=True, check=True)
        elif key==3:
            subprocess.run(level3, shell=True, check=True)
        elif key==4:
            subprocess.run(level4, shell=True, check=True)
        else:
            subprocess.run(level5, shell=True, check=True)
        CURRENT_Q = CURRENT_Q + 1

    # last question
    else:
        if key==0:
            subprocess.run(level1, shell=True, check=True)
        elif key==2:
            subprocess.run(level2, shell=True, check=True)
        elif key==3:
            subprocess.run(level3, shell=True, check=True)
        elif key==4:
            subprocess.run(level4, shell=True, check=True)
        else:
            subprocess.run(level5, shell=True, check=True)
        CURRENT_Q = 1
        NEED_PRESS = False

    # Print new key state
    # if VERBOSE:
    #     print("Key {} = {}".format(key, state), flush=True)
    # Update the key image based on the new key state.
    # update_key_image(deck, key, state)

    # # Check if the key is changing to the pressed state.
    # if state:
    #     key_style = get_key_style(deck, key, state)

    #     if key_style["name"] != "exit":
    #         if key==0:
    #             subprocess.run(command_very_happy, shell=True, check=True)
    #         elif key==1:
    #             subprocess.run(command_happy, shell=True, check=True)
    #         elif key==2:
    #             subprocess.run(command_fine, shell=True, check=True)
    #         elif key==3:
    #             subprocess.run(command_unhappy, shell=True, check=True)
    #         else:
    #             subprocess.run(command_angry, shell=True, check=True)
    #         NEED_PRESS = False

        # When an exit button is pressed, close the application.
        # if key_style["name"] == "exit":
        #     # Use a scoped-with on the deck to ensure we're the only thread
        #     # using it right now.
        #     with deck:
        #         # Reset deck, clearing all button images.
        #         dec                passk.reset()

        #         # Close deck handle, terminating internal worker threads.
        #         deck.close()


if __name__ == "__main__":
    streamdecks = DeviceManager().enumerate()

    if len(streamdecks) and VERBOSE:
        print("Streamdeck Found.")

    for index, deck in enumerate(streamdecks):

        deck.open()
        deck.reset()
        deck.set_brightness(90)

        timer_thread = threading.Thread(target=timer_function, args=(deck,))
        timer_thread.daemon = True  # This makes the timer_thread terminate when the main program exits
        timer_thread.start()

        # Set initial key images.
        for key in range(deck.key_count()):
            update_key_image(deck, key, False)


        # Register callback function for when a key state changes.
        while deck.is_open():
            deck.set_key_callback(key_change_callback)


        # Wait until all application threads have terminated (for this example,
        # this is when all deck handles are closed).
        for t in threading.enumerate():
            try:
                t.join()
            except RuntimeError:
                pass
