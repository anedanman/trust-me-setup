import os
import time

import cv2
import h5py
import numpy as np
import pyrealsense2 as rs
from camera import Camera


def formatted_time():
    return str(time.time()).replace(".", "_")


class Realsense(Camera):
    """Camera class for RGB & Depth image capture"""

    def __init__(self, fps=30, resolution=(640, 480), save_directory="data/realsense"):
        super(Realsense, self).__init__(fps, resolution, save_directory)

        print(
            f"Realsense camera set with FPS: {self.fps} and resolution: {self.resolution}!"
        )

    def initCamera(self):
        self.pipeline = rs.pipeline()

    def configureCamera(self):
        """Config pipeline, add parameters if needed."""
        self.config = rs.config()

        self.config.enable_stream(
            rs.stream.color,
            self.resolution[0],
            self.resolution[1],
            rs.format.bgr8,
            int(self.fps),
        )

        self.config.enable_stream(
            rs.stream.depth,
            self.resolution[0],
            self.resolution[1],
            rs.format.z16,
            int(self.fps),
        )

    def applyColormap(self, depth_image):
        # Apply colormap to visualize depth values
        return cv2.applyColorMap(
            cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET
        )

    def captureImages(self, name="out", seconds=10, start_event=None):
        self.initCamera()
        self.configureCamera()

        if start_event:
            start_event.wait()

        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)
            os.makedirs(f"{self.save_directory}/rgb")
            os.makedirs(f"{self.save_directory}/depth")

        self.profile = self.pipeline.start(self.config)

        if seconds is None or seconds < 0:
            seconds = float("inf")

        start_time = time.time()

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(
            f"{self.save_directory}/rgb/{name}_{formatted_time()}.mp4",
            fourcc,
            self.fps,
            self.resolution,
        )

        try:
            img_id = 0
            while time.time() - start_time < seconds:
                frames = self.pipeline.wait_for_frames(10000)

                # Presume depth will always be captured
                depth_frame = frames.get_depth_frame()
                color_frame = frames.get_color_frame()

                if not depth_frame or not color_frame:
                    print("No frame...")
                    continue

                # Convert to numpy
                depth_image = (
                    np.asanyarray(depth_frame.get_data(), dtype=np.float32) / 65535.0
                )
                color_image = np.asanyarray(color_frame.get_data())

                timestamp = formatted_time()

                # Store depth
                with h5py.File(
                    f"{self.save_directory}/depth/{name}_{img_id}_{timestamp}.h5", "w"
                ) as hf:
                    hf.create_dataset(
                        f"{self.save_directory}/depth/{name}_{img_id}_{timestamp}",
                        data=depth_image,
                        compression="gzip",
                        compression_opts=9,
                    )

                out.write(color_image)

        except KeyboardInterrupt:
            pass

        finally:
            out.release()
            self.pipeline.stop()


if __name__ == "__main__":
    cam = Realsense()
    cam.initCamera()
    cam.configureCamera()
    cam.captureImages(seconds=10)
