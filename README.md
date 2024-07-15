# TRUST-ME setup

Install the TRUST-ME setup on Linux:

- Download the latest release: `wget https://github.com/pietrobarbiero/trust-me-setup/archive/main.zip`.
- Unzip the archive: `unzip main.zip`
- Make setup script executable: `chmod u+x ./trust-me-setup-main/linux/trust-me-installer.sh`
- Execute the setup script: `./trust-me-setup-main/linux/trust-me-installer.sh`

## Device Installation and Calibration

#### Device and Series
- Tobii Pro Spark eye-tracker [#TODO]
- your workspace device
- your workspace screen
- one guest device.

#### Software and Installation
- [#TODO]

#### Installation Steps
- Following the [instructions](https://www.tobii.com/products/eye-trackers/screen-based/tobii-pro-spark), fix the eye-tracker to your workspace screen and install the software to the guest device.
- Connect the eye-tracker to the **guest device**.     
Connect your workspace screen to the **guest device**.
- Calibrate with the workspace screen. Please **zoom in the calibration to cover the full screen you will be working on**. [#TODO]    
Make sure the calibration is successful by checking the cursor is following your gaze points.
- Disconnect the workspace screen with the **guest device**.     
Connect the workspace screen with your **workspace device**.
- Installation done. Track and store your data to the guest device.

#### FAQ
- **How large is the area the eye-tracker works?**        
The eye-tracker will be working well within (probably slightly outside of? #TODO) your calibration area.

- **Does it work when I move around?**      
The experiment shows it tolerates tilting to left/right by roughly no more than a 30-45° angle, and moving backward/forward slightly. This is related to the FOV of Tobii camera.

- **Do I need to recalibrate every time before using?**       
Unless you are changing your workspace screen size, or adjusting your seating with large distance shifts, you don’t have to recalibrate.

#### Future work
- The thresholds for valid data collection: limitation of noise.

### Cleaning large files from git history
[Repo cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
[git-repo-filter](https://github.com/newren/git-filter-repo/blob/main/Documentation/converting-from-filter-branch.md#cheat-sheet-conversion-of-examples-from-the-filter-branch-manpage)
