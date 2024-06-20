import argparse
import json
import multiprocessing
import time

# If running capture_data.py (this file)
from camera import RGBCamera
from microphone import Mic
from realsense import Realsense
from thermal import Thermal

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

# Add command line arguments
parser = argparse.ArgumentParser(
    prog="Data Capture",
    description="Run to simultaneously capture data from multiple devices",
    epilog="Any bugs in the code are property of JSI",
)

parser.add_argument("-n", "--name", default="test", type=str)
parser.add_argument("-d", "--duration", default="-1", type=int)


hw_config = None


class CaptureData:
    WARMUP_TIME = 60

    def __init__(self, filename="test", seconds=10, show_rgb=False):
        global hw_config

        self.show_rgb = show_rgb
        self.hw_config = hw_config

        self.init_objects()
        self.config(name=filename, seconds=seconds)

    def init_objects(self):
        """Creates objects with properties specified in the hardware_config.json"""

        # Channel = camera id, that determines which of the cameras is the RGB one - configure for your setup
        self.rgb = RGBCamera(
            fps=self.hw_config["rgb"]["fps"],
            resolution=(
                self.hw_config["rgb"]["resolution_x"],
                self.hw_config["rgb"]["resolution_y"],
            ),
            channel=self.hw_config["rgb"]["channel"],
            store_video=True,
        )

        self.hires = RGBCamera(
            fps=self.hw_config["hires"]["fps"],
            resolution=(
                self.hw_config["hires"]["resolution_x"],
                self.hw_config["hires"]["resolution_y"],
            ),
            channel=self.hw_config["hires"]["channel"],
            store_video=True,
            save_directory="data/hires",
        )

        self.realsense = Realsense(
            fps=self.hw_config["depth"]["fps"],
            resolution=(
                self.hw_config["depth"]["resolution_x"],
                self.hw_config["depth"]["resolution_y"],
            ),
        )

        self.thermal = Thermal(
            fps=self.hw_config["thermal"]["fps"],
            resolution=(
                self.hw_config["thermal"]["resolution_x"],
                self.hw_config["thermal"]["resolution_y"],
            ),
        )

        self.audio = Mic(
            sampling_rate=self.hw_config["audio"]["sampling_rate"],
            n_channels=self.hw_config["audio"]["n_channels"],
            chunk_length=self.hw_config["audio"]["chunk_length"],
        )

    def config(self, name, seconds):
        """Creates video and audio processes.

        Args:
            seconds (int, optional): Defaults to 10.
            name (str, optional): Defaults to "test".
        """

        # Event to trigger all processes at once
        self.start_event = multiprocessing.Event()

        #  RGB
        self.rgb_process = multiprocessing.Process(
            target=self.rgb.captureImages,
            args=(name, seconds, self.show_rgb, self.start_event),
        )

        self.hires_process = multiprocessing.Process(
            target=self.hires.captureImages,
            args=(name, seconds, self.show_rgb, self.start_event),
        )

        self.audio_process = multiprocessing.Process(
            target=self.audio.record, args=(name, seconds, self.start_event)
        )

        self.realsense_process = multiprocessing.Process(
            target=self.realsense.captureImages,
            args=(name, seconds, self.start_event),
        )

        self.thermal_process = multiprocessing.Process(
            target=self.thermal.captureImages,
            args=(name, seconds, True, self.start_event),
        )

    def capture(self):
        process_list = [
            self.rgb_process,
            self.hires_process,
            self.thermal_process,
            self.realsense_process,
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
            for process in process_list:
                process.join()
                if process.exitcode == 0:
                    print(f"Process {process.name} exited successfully.")
                else:
                    if process.exitcode != None:
                        print(
                            f"Process {process.name} exited with exit code {process.exitcode}"
                        )

            time.sleep(3)

            print("All processes finished. Recording stopped and saved")
            exit()


if __name__ == "__main__":
    print("Run capture_data.py -h for usage tips.")
    args = parser.parse_args()

    with open("installers/data_capture/hardware_config.json", "r") as fp:
        hw_config = json.load(fp)

        capture = CaptureData(seconds=args.duration, filename=args.name)
        capture.capture()
