import argparse
import json
import multiprocessing
import time
import getpass
import os
from utils import save_pid 
from utils import ka_exists
import subprocess

# If running capture_data.py (this file)
from camera import RGBCamera
from microphone import Mic
# For running from main.py
# from capture_data.camera import Camera
# from capture_data.realsense import Realsense
# from capture_data.thermal import Thermal

# Default values that are already set in the hardware_config.json
# Use only for reference - if you want to change resolutions change corresponding values in the hw_config.json
# RGB_RES = (1920, 1080)
# DEPTH_RES = (640, 480)
# THERM_RES = (160, 120)
# HIGH_RES = (3840, 2160)

# --------------------------------------------------------------------------------------
# Due to multiprocessing we can only initialize the objects in this file - internal
# initializations and configs must happen within the class methods (in the subprocess),
# since multiprocessing attempts to pickle the objects created in the main process,
# which causes an error since objects like VideoCapture() are unpickable.
# --------------------------------------------------------------------------------------

# Get username from file if not specified
try:
    with open("/home/$(whoami)/trust-me-setup/tmp/current_username", "r") as f:
        default_username = f.read().strip()
except:
    default_username = "user1"

# Add command line arguments
parser = argparse.ArgumentParser(
    prog="Data Capture",
    description="Run to simultaneously capture data from multiple devices",
    epilog="Any bugs in the code are property of JSI",
)

parser.add_argument("-n", "--name", default=default_username, type=str)
parser.add_argument("-d", "--duration", default=28800, type=int)

hw_config = None


class CaptureData:
    WARMUP_TIME = 5

    def __init__(self, filename="test", seconds=28800, show_rgb=False):
        global hw_config

        self.show_rgb = show_rgb
        self.hw_config = hw_config

        # This flag is used to announce to the inner threads that they should terminate
        self.termFlag = multiprocessing.Value('i')
        self.termFlag.value = 0
        self.init_objects()
        self.config(name=filename, seconds=seconds)

    def init_objects(self):
        """Creates objects with properties specified in the hardware_config.json"""
        self.audio = Mic(
            sampling_rate=self.hw_config["audio"]["sampling_rate"],
            n_channels=self.hw_config["audio"]["n_channels"],
            chunk_length=self.hw_config["audio"]["chunk_length"],
            save_directory=f"data/{default_username}/audio",
        )

        # self.rgb = RGBCamera(
            # fps=self.hw_config["rgb"]["fps"],
            # resolution=(
                # self.hw_config["rgb"]["resolution_x"],
                # self.hw_config["rgb"]["resolution_y"],
            # ),
            # channel=self.hw_config["rgb"]["channel"],
            # store_video=True,
            # save_directory="installers/data_collection/data/rgb",
            # chunk_size=self.hw_config["rgb"]["chunk_length"],
        # )

        self.hires = RGBCamera(
            fps=self.hw_config["hires"]["fps"],
            resolution=(
                self.hw_config["hires"]["resolution_x"],
                self.hw_config["hires"]["resolution_y"],
            ),
            channel=self.hw_config["hires"]["channel"],
            store_video=True,
            save_directory=f"data/{default_username}/hires",
            chunk_size=self.hw_config["hires"]["chunk_length"],
        )

       
    def config(self, name, seconds):
        """Creates video and audio processes.

        Args:
            seconds (int, optional): Defaults to 10.
            name (str, optional): Defaults to "test".
        """

        # Event to trigger all processes at once
        self.start_event = multiprocessing.Event()

        
        self.audio_process = multiprocessing.Process(
            target=self.audio.record, args=(self.termFlag, name, 1800, self.start_event)
        )
        
        self.hires_process = multiprocessing.Process(
            target=self.hires.captureImages,
            args=(self.termFlag, name, seconds, self.show_rgb, self.start_event),
            kwargs=({"process_type": "brio"})
        )

    def terminate(self):
        process_list = [
            self.hires_process,
            self.audio_process,
            ]
        if not ka_exists():
            self.termFlag.value = 1 # Set the flag to 1 (= termination)
            print("CaptureData: Gracefully terminating 'audio' and 'hires' processes.")
            return True
        return False
            
        

    def capture(self):

        process_list = [
            self.hires_process,
            self.audio_process,
        ]

        try:
            for process in process_list:
                process.start()

            # Warmup time
            time.sleep(CaptureData.WARMUP_TIME)
            print("Starting capture...")

            self.start_event.set()
            
        except Exception as e:
            if isinstance(e, KeyboardInterrupt):
                print(
                    "Keyboard Interrupt detected, stopping recording...[capture_data.py]"
                )
		
            else:
                print("An error occured:", e)
                
        finally:
	    	        
        # finally:
            # for process in process_list:
                # process.join()
                # if process.exitcode == 0:
                    # print(f"Process {process.name} exited successfully.")
                # else:
                    # if process.exitcode != None:
                        # print(
                            # f"Process {process.name} exited with exit code {process.exitcode}"
                        # )

            # time.sleep(3)

            # print("All processes finished. Recording stopped and saved")
            while True:
                if capture.terminate():
                    time.sleep(0.2)
                    break
                time.sleep(0.5)

if __name__ == "__main__":
    print("Run capture_data.py -h for usage tips.")

    args = parser.parse_args()

    # save_pid("capture_data.pid") LEGACY SYSTEM
    
    with open("installers/data_capture/hardware_config.json", "r") as fp:
        hw_config = json.load(fp)
        
        
        
        # print("Username before:", default_username)
        
        """ Update the default user var. """
        default_username = args.name
        
        # print("Username after:", default_username)
        
        capture = CaptureData(seconds=args.duration, filename=args.name)
        
        capture.capture()
