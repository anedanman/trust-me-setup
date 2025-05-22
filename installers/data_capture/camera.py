import os
import time
from datetime import datetime
from abc import ABC
from utils import save_pid
import cv2
import multiprocessing

def formatted_time():
    return "{:%Y-%m-%d$%H-%M-%S-%f}".format(datetime.now())


class Camera(ABC):
    def __init__(self, fps, resolution, save_directory="data/rgb", chunk_size=3600):
        self.fps = fps
        self.resolution = resolution
        self.save_directory = save_directory
        self.chunk_size = chunk_size

    def initCamera(self):
        """Initialize camera object"""

    def configureCamera(self):
        """Set camera parameters etc."""

    def captureImages(self, name, seconds, show_video):
        "Capture data"


class RGBCamera(Camera):
    """Camera class supporting image capture on a standard RGB camera."""

    def __init__(
        self,
        fps=30,
        resolution=(1920, 1080),
        save_directory="data/rgb",
        channel=0,
        store_video=True,
        chunk_size=3600,
    ):
        super(RGBCamera, self).__init__(fps, resolution, save_directory, chunk_size)

        self.channel = channel
        self.store_video = store_video
        print(f"RGBCamera set with FPS: {self.fps} and resolution: {self.resolution}!")

    def initCamera(self, camera_id=1):
        """Returns capture object of the camera."""

        cap = cv2.VideoCapture(camera_id)

        if not cap.isOpened():
            print("Cannot open camera")
            exit()

        self.cap = cap

        self.fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    def configureCamera(self):
        """Configures camera resolution"""
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))

    def captureImages(self, termFlag, name="out", seconds=10, show_video=False, start_event=None, process_type="streamcam"):
        
        self.initCamera(camera_id=self.channel)
        self.configureCamera()

        if start_event:
            start_event.wait()

        if seconds is None or seconds < 0:
            seconds = float("inf")

        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)

        start_time = time.time()
        chunk_index = 0
        img_id = 0 
        timestamps = []
        time_for_timestamps = formatted_time()
        
        """This variable is used to prevent releasing VideoWriter twice"""
        released = False
        
        f_open = False
        # NOT NEEDED to open the files here and then again in the loop. Now the files are only opened in the loop.
        # f = open(f"{self.save_directory}/{name}_timestamps_{time_for_timestamps}.txt", "w")
        #f.write("frame_number, timestamp\n")
        
        # if self.store_video:
        #     out = cv2.VideoWriter(
        #         f"{self.save_directory}/{name}_chunk{chunk_index}_{formatted_time()}.mp4",
        #        self.fourcc,
        #        self.fps,
        #        self.resolution,
       #     )
        try:
            while time.time() - start_time < seconds and termFlag.value != 1:
                chunk_start_time = time.time()
                fmtd_time = formatted_time()
                if self.store_video or out == None:
                    out = cv2.VideoWriter(
                        f"{self.save_directory}/{name}_chunk{chunk_index}_{fmtd_time}.mp4",
                        self.fourcc,
                        self.fps,
                        self.resolution,
                    )
                    
                    released = False # recording started; reset release
                    chunk_index += 1
                # Open timestamps in any case
                if f_open: f.close();
                
                f = open(f"{self.save_directory}/{name}_timestamps_{fmtd_time}.txt", "w")
                f.write("frame_number, timestamp\n")
                f_open = True
                while time.time() - chunk_start_time < self.chunk_size and termFlag.value != 1:
                    ret, frame = self.cap.read()
                    if not ret:
                        print("Can't receive frame (stream end?). Exiting ...")
                        break
                     # Get the current timestamp
                    formatted_timestamp = formatted_time()
                    timestamps.append((img_id, formatted_timestamp))

                    f.write(f"{img_id},{formatted_timestamp}\n")
                    
                    if self.store_video:
                        out.write(frame)
                    else:
                        cv2.imwrite(
                            f"{self.save_directory}/{name}_{img_id}_{formatted_timestamp}.jpg",
                            frame,
                        )
                    img_id += 1

                    # if show_video:
                        # cv2.imshow("rec", frame)
                        # if cv2.waitKey(1) == ord("q"):
                            # break
                if self.store_video:
                    out.release()
                    released = True # flag that we already released it here
                print("Before exiting:", termFlag.value)
            if(termFlag.value == 1):
                print("Termination flag detected. Video recording has been forced to end.")
                
        except KeyboardInterrupt:
            print("KeyboardInterrupt [camera.py]")

        finally:
            if f_open: f.close()
            self.cap.release()
            if not released and self.store_video: #release if not already
                out.release()
            print("Stored RGB.")

            if show_video:
                cv2.destroyAllWindows()
                
if __name__ == "__main__":
     start = time.time()
     camera = RGBCamera(
         channel=0, fps=30.0, store_video=True, resolution=(1920, 1080), chunk_size=30
     )

     camera.captureImages(seconds=-1, show_video=False)
