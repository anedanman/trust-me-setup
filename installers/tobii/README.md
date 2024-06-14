# Tobii eyetracker setup
To set up the Tobii eyetracker, follow these steps.

Create corresponding conda env:
```
conda create -n tobii python=3.8
```

Run the `install.sh` script to install the necessary dependencies. Some of the tobii libraries might be not compatible with the latest python versions, in our case it is working with python 3.8.19.

Edit constants in the `constants.py` file according to your setup.

Launch the `tobii_calibration.py` script and follow the displayed steps to calibrate the eyetracker. The calibration may not function correctly if the screen scale is not set to 100%. You may need to adjust your screen resolution in the `constants.py` file or set the scale to 100% for the duration of the calibration.

After calibration, you can check if the eyetracker is working properly by running the `trackertest.py` script.

Finally, use the `run_tobii.py` script to collect the data with the Tobii eyetracker.

## Automatic launching
To setup automatic launching on every boot do the following:|

Make sure `run_tobii.sh` is executable:
```
chmod +x run_tobii.sh
```
Open cron:
```
crontab -e
```
And put the following line there:
```
@reboot /bin/bash /home/$(whoami)/trust-me-setup/installers/tobii/run_tobii.sh >> /home/$(whoami)/trust-me-setup/installers/tobii/logfile.log 2>&1
```