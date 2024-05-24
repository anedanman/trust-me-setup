# ActivityWatch installer
First download and install the Activity Watch application from the [official page](https://github.com/ActivityWatch/activitywatch/releases). It supports Windows ([download here](https://github.com/ActivityWatch/activitywatch/releases/download/v0.12.3b16/activitywatch-v0.12.3b16-windows-x86_64-setup.exe)), Linux ([download here](https://github.com/ActivityWatch/activitywatch/releases/download/v0.12.3b16/activitywatch-v0.12.3b16-linux-x86_64.zip)), and MacOS ([download here](https://github.com/ActivityWatch/activitywatch/releases/download/v0.12.3b16/activitywatch-v0.12.3b16-macos-x86_64.dmg)). It will track the active window (application) and log its title. Please allow it to run in the background and start on boot if it asks you to.
# Browser extension
Then install the Activity Watch extension for your browser:
- Firefox: [AW Watcher Web](https://addons.mozilla.org/en-US/firefox/addon/aw-watcher-web/)
- Chrome: [ActivityWatch Web Watcher](https://chromewebstore.google.com/detail/activitywatch-web-watcher/nglaklhklhcoonedhgnpgddginnjdadi)
- Edge: You use Chrome extensions with Edge [(instruction)](https://medium.com/@mariusbongarts/how-to-install-chrome-extensions-in-microsoft-edge-browsers-65914eb61d6)

The extension will track the active browser tab and log URLs and titles of the websites you visit.
# Input monitoring
The next extension to install is the [Input Watcher](https://github.com/pietrobarbiero/trust-me-setup/tree/main/installers/activitywatch/aw-watcher-input) which will track your keypresses frequency and mouse activity. NOTE: This does not track which keys you press, only that you pressed any key some number of times in a given time span. This is not a keylogger.

To install it go to the corresponding folder (`./aw-watcher-input`), make sure you have Python 3.7+ and `poetry` installed. Then run:
```bash
poetry install
poetry run aw-watcher-input
```
## Automatic launching and data collection
By default, the Input Watcher is not starting automatically on boot, so you need to do a few more steps to make it work: 

### MacOs
 Make sure the script `./start-up/watcher_boot.sh` is executable:
```bash
chmod +x ./start-up/watcher_boot.sh
```
Open Automator and select "Application". Drag "Run Shell Script" from the library of actions into the workflow and paste the following code (do not forget to load your specific shell and your specific path to the script):
```bash
# load your shell profile with wget, python and poetry paths
source ~/.zshrc

# open directory with the script and launch it
cd <your_path>/trust-me-setup/installers/activitywatch/aw-watcher-input/start-up && ./watcher_boot.sh
```
You can test it by pressing the "Run" button. If everything works, save the application and add it to the list of applications that start on boot in the System Preferences -> General -> Login Items. Allow the input monitoring whenever it asks you to.

### Windows
1. Open the Start-up folder by pressing `Win + R` and typing `shell:startup` and pressing enter.
2. Create a shortcut to the `./start-up/startup.cmd`. Right-click in the Start-up folder and select New > Shortcut. Click Browse and navigate to the script or type the path directly. Click Next, give your shortcut a name, and click Finish.

### Linux
1. Make sure the script `./start-up/watcher_boot.sh` is executable:
```bash
chmod +x ./start-up/watcher_boot.sh
```
2. Open the terminal and type `crontab -e`.
3. Add the following line to the end of the file (do not forget to paste your specific path to the script):
```bash
@reboot cd <your_path>/trust-me-setup/installers/activitywatch/aw-watcher-input/start-up && ./watcher_boot.sh
```

## Check if it works
If everything is set up correctly, you should see the data in the ActivityWatch dashboard, which is accessible at `http://localhost:5600` and the exported data is located in the `.aw-watcher-input/start-up/data` folder in the raw format as `export.json`.
