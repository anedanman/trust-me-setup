import os
import time
import datetime
from abc import ABC

import cv2


def formatted_time():
    return '{:%Y-%m-%d$%H-%M-%S-%f}'.format(datetime.now())


class Camera(ABC):
    def __init__(self, fps, resolution, save_directory="data/rgb"):
        self.fps = fps
        self.resolution = resolution
        self.save_directory = save_directory

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
    ):
        super(RGBCamera, self).__init__(fps, resolution, save_directory)

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

    def configureCamera(self):
        """Configures camera resolution"""
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))

    def captureImages(self, name="out", seconds=10, show_video=False, start_event=None):
        """
        Records a sequence of images from the camera for the specified number of seconds.
        If you want to record indefinitely, set seconds to -1.
        """

        self.initCamera(camera_id=self.channel)
        self.configureCamera()

        if start_event:
            start_event.wait()

        if seconds is None or seconds < 0:
            seconds = float("inf")

        # Set directory where the frames are saved and make sure it exists
        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)

        if self.store_video:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(
                f"{self.save_directory}/{name}_{formatted_time()}.mp4",
                fourcc,
                self.fps,
                self.resolution,
            )

        # Record for specified number of seconds
        try:
            img_id = 0
            start_time = time.time()
            while time.time() - start_time < seconds:
                # Read frame
                ret, frame = self.cap.read()
                if not ret:
                    print("Can't receive frame (stream end?). Exiting ...")
                    break

                if self.store_video and time.time():
                    out.write(frame)
                else:
                    # write the frame
                    cv2.imwrite(
                        f"{self.save_directory}/{name}_{img_id}_{formatted_time()}.jpg",
                        frame,
                    )
                    img_id += 1

                # Show the frame
                if show_video:
                    cv2.imshow("rec", frame)

                    if cv2.waitKey(1) == ord("q"):
                        break

        except KeyboardInterrupt:
            print("KeyboardInterrupt [camera.py]")

        finally:
            # Release everything if job is finished
            self.cap.release()

            if self.store_video:
                out.release()

            print("Stored RGB.")

            if show_video:
                cv2.destroyAllWindows()


if __name__ == "__main__":
    start = time.time()
    camera = RGBCamera(channel=3, fps=30.0, store_video=True, resolution=(1920, 1080))

    camera.captureImages(show_video=True)
