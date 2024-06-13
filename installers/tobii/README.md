# Tobii eyetracker setup
To set up the Tobii eyetracker, follow these steps:

Run the `install.sh` script to install the necessary dependencies. Some of the tobii libraries might be not compatible with the latest python versions, in our case it is working with python 3.8.19.

Edit constants in the `constants.py` file according to your setup.

Launch the `tobii_calibration.py` script and follow the displayed steps to calibrate the eyetracker.

After calibration, you can check if the eyetracker is working properly by running the `trackertest.py` script.

Finally, use the `run_tobii.py` script to collect the data with the Tobii eyetracker.
