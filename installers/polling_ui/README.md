# Streamdeck data collection 

The code in this folder is designed to allow users to trigger a poll on the machine by pressing a button on the stream deck that corresponds to a certain physio/psychological construct.


## How to use 
After running `pip install -r requirements.txt` make sure StreamDeck is connected. Then start the button press listener by running `python streamdeck.py`.

## Debugging
If you encounter an error saying there is no HID API DLL on your machine, copy the contents of the `hidapi/` folder to your environment, for example if you use "trust-me" environment with miniconda, that path would  be C://Users/user/miniconda3/envs/trust-me.

## Technical details

`ui.py` contains a Tkinter class that defines the window of the poll and loads the questions with the configuration that is passed to its constructor (as an array of Question objects).
Once it receives the questions, it will display the question on the screen, save our answer and continue until done. 

`streamdeck.py` acts as a main loop that utilizes what's in `ui.py` by calling it with the corresponding questions whenever a streamdeck button is pressed.
