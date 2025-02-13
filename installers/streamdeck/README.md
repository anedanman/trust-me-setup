## Installing streamdeck

```sh
bash install_streamdeck.sh
```

## Running streamdeck

```sh
cd ..  # Go to parent dir to run the file ( Depending on where your path
python run_streamdeck.py

# an old version for 6-button streamdeck
# python run_streamdeck_6.py
```
## How to use
### sleeping mode
the device shows "trust me" with icons for different questions on the panel after launching.

### self-report/free-report
During sleeping mode, users can freely update their status anytime for any one from the questionnaires during the process.

- Click on one of the `questions`
- Give feedback (or press `Back` as of a misclicking)

OR

- Click on `ME`
- Give feedbacks to all questions

### fixed-report
For every 2 hours, questionnaire will be blinking at a random timestamp for updating users' current status.

- Give feedbacks until finishing all questions (**can not skip or go back** in fixed-report)

device will go back to sleeping mode after fixed-report.

### Timestamp when you start gaming
Click on `U` to record your start moment of gaming.

## Saving
Recordings are saved to `./Recording`

## If streamdeck not detected
Create new file: `sudo nano /etc/udev/rules.d/50-elgato.rules`
Write `SUBSYSTEM=="usb", ATTR{idVendor}=="0fd9", MODE="0666"`

Reload udev rules: 
`sudo udevadm control --reload-rules`
`sudo udevadm trigger`


