import subprocess
import os
import json
import glob
from copy import deepcopy

#####################################################################
# This script maps video devices from /dev/video* 
# to their product names. 
# Currently we only need to know ID of StreamCam [FHD] and Brio [4K]
# There can still be some problems for devices with multiple cameras.
#####################################################################


def dev_info(dev):
    cmd = f"udevadm info --query=all --name={dev}"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.stdout

    
with open("installers/data_capture/hardware_config.json", "r") as fp:
    config = json.load(fp)
    original = deepcopy(config)
    devs = glob.glob("/dev/video*")
    
    for dev in devs:
    
        info = dev_info(dev).lower()
        if not "capture" in info:
            continue
    
        if "streamcam" in info:
            try: 
                channel = int(dev[-2:])
            except ValueError:
                channel = int(dev[-1])
            config["rgb"]["channel"] = channel
            print(f"StreamCam channel: {channel}")
        elif "brio" in info:
            try:
                channel = int(dev[-2:])
            except ValueError:
                channel = int(dev[-1])
            config["hires"]["channel"] = channel
            print(f"Brio channel: {channel}")
    
    fp.close()

    if config == original:
        exit()
        
    with open("installers/data_capture/hardware_config.json", "w") as wfp:
        json.dump(config, wfp)
        wfp.close()
