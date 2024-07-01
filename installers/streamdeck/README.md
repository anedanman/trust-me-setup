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


temp
https://soulofcorn.notion.site/Server-cheatsheet-5d5596862a954a21930cc3ea06dfd03b

## If streamdeck not detected
Create new file: `sudo nano /etc/udev/rules.d/50-elgato.rules`
Write `SUBSYSTEM=="usb", ATTR{idVendor}=="0fd9", MODE="0666"`

Reload udev rules: 
`sudo udevadm control --reload-rules`
`sudo udevadm trigger`



