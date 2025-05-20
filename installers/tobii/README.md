# Tobii eyetracker setup

## New Mini-PC Setup

### 1. Download and Install Tobii Pro Spark Driver

First, manually download the Tobii Pro Spark driver from the following link:

- [TobiiProSpark_2.2.3.0_x64.deb](https://s3.eu-west-1.amazonaws.com/tobiipro.eyetracker.manager/downloadable-content/drivers/Spark/TobiiProSparkRuntime_2.2.3.0_x64.deb/TobiiProSpark_2.2.3.0_x64.deb)

Install the driver:
```
sudo dpkg -i TobiiProSpark_2.2.3.0_x64.deb
```

### 2. Download and Install Tobii Pro Eye Tracker Manager

Download the Eye Tracker Manager version 2.6.1:

- [TobiiProEyeTrackerManager-2.6.1.deb](https://s3.eu-west-1.amazonaws.com/tobiipro.eyetracker.manager/linux/TobiiProEyeTrackerManager-2.6.1.deb)

Install the manager:
```
sudo dpkg -i TobiiProEyeTrackerManager-2.6.1.deb
```

### 3. Calibrate the Eyetracker

Open the Tobii Pro Eye Tracker Manager application. The tracker should be detected by the application.  
Use the application to perform the calibration.

### 4. Test the Tracker

After calibration, test the tracker using the provided script:
```
python trackertest.py
```
This script displays the data that will be recorded with `run_tobii.py` later.


---

## Old Setup

**Important:**  
Before proceeding, make sure to install the Tobii Pro Eye Tracker Manager and the driver for Tobii Pro Spark. These are required for the eyetracker to function properly.

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
To setup automatic launching on every boot do the following:

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

---

