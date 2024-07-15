## Installing streamdeck


```sh
bash install_streamdeck.sh
```

## Running streamdeck


```sh
cd ..  # Go to parent dir to run the file ( Depending on where your path
python run_streamdeck.py
```

## Saving
Recordings are saved to `./Recording`

## If streamdeck not detected
Create new file: `sudo nano /etc/udev/rules.d/50-elgato.rules`
Write `SUBSYSTEM=="usb", ATTR{idVendor}=="0fd9", MODE="0666"`

Reload udev rules: 
`sudo udevadm control --reload-rules`
`sudo udevadm trigger`



