import subprocess
import os
import json

with open("installers/data_capture/hardware_config.json", "r") as fp:
    config = json.load(fp)
    print(config)
    
    devices = subprocess.check_output(["lsusb"])

    devices = devices.decode("utf-8")
    devices = devices.split("\n")

    for dev in devices:
        dev = dev.lower()

        if "stream" in dev:
            config["rgb"]["channel"] = int(dev.split(" ")[3].replace(":", ""))
            print(f"Found Streamcam ({config['rgb']['channel']})")
        elif "brio" in dev:
            config["hires"]["channel"] = int(dev.split(" ")[3].replace(":", ""))
            print(f"Found Brio ({config['hires']['channel']})")
    fp.close()
    
    with open("installers/data_capture/hardware_config.json", "w") as wfp:
        print(config)
        json.dump(config, wfp)
        wfp.close()
