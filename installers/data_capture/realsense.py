import os
import time
from datetime import datetime

import cv2
import h5py
import numpy as np
import pyrealsense2 as rs
from camera import Camera
from utils import save_pid

######################################################################
# Stores both RGB (as video) and depth (gzip compressed) into chunks.
# For decoding the h5 see the decode_depth.py script. 
# Each .h5 file holds [1, fps * 1800] images
######################################################################

def formatted_time():
    return "{:%Y-%m-%d$%H-%M-%S-%f}".format(datetime.now())


class Realsense(Camera):
    """Camera class for RGB & Depth image capture"""

    def __init__(self, fps=30, resolution=(640, 480), chunk_size=30*60, save_directory="data/realsense"):
        super(Realsense, self).__init__(fps, resolution, save_directory)

        self.chunk_size = chunk_size
        
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
        save_pid("depth")
        self.initCamera()
        self.configureCamera()

        if start_event:
            start_event.wait()

        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)
            os.makedirs(f"{self.save_directory}/rgb")
            os.makedirs(f"{self.save_directory}/depth")

        try:
            self.pipeline.stop()
        except:
            pass
       
        self.profile = self.pipeline.start(self.config)

        if seconds is None or seconds < 0:
            seconds = float("inf")

        start_time = time.time()

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        current_ft = formatted_time()

        out = cv2.VideoWriter(
            f"{self.save_directory}/rgb/{name}_{current_ft}.mp4",
            fourcc,
            self.fps,
            self.resolution,
        )
        saved = False
        try:
            # Initialize containers for depth frames and timestamps
            chunk_frames = []
            chunk_timestamps = []

            # Ensure directories exist
            os.makedirs(f"{self.save_directory}/rgb", exist_ok=True)
            os.makedirs(f"{self.save_directory}/depth", exist_ok=True)

            # For depth, capture at 10 FPS
            counter = 0
            while time.time() - start_time < seconds:
                saved = False
                frames = self.pipeline.wait_for_frames(10000)

                # Retrieve depth and RGB frames
                depth_frame = frames.get_depth_frame()
                color_frame = frames.get_color_frame()

                if not depth_frame or not color_frame:
                    print("No frame received, skipping...")
                    continue
                counter += 1

                # Convert frames to numpy arrays
                depth_image = np.asanyarray(depth_frame.get_data(), dtype=np.float32) / 65535.0
                depth_image = np.array(depth_image, dtype=np.float16)  # Cast to float16 for efficiency
                color_image = np.asanyarray(color_frame.get_data())

                # Timestamp for the current frame
                timestamp = formatted_time()

                # Save color frame to video
                out.write(color_image)

                # Store depth frame and timestamp in memory
                if counter % 3 == 0:
                    chunk_frames.append(depth_image)
                    chunk_timestamps.append(timestamp)

                # Check if the chunk is full (30 minutes of data)
                if len(chunk_frames) // (self.fps // 3) >= self.chunk_size:
                    depth_chunk_path = f"{self.save_directory}/depth/{name}_{current_ft}.h5"
                    save_depth_chunk(depth_chunk_path, chunk_frames, chunk_timestamps)

                    # Reset chunk containers
                    chunk_frames = []
                    chunk_timestamps = []
                    current_ft = formatted_time()  # Update timestamp for new chunk

            # Save any remaining frames at the end

        except KeyboardInterrupt:
            print("Recording interrupted by user.")

        finally:
            depth_chunk_path = f"{self.save_directory}/depth/{name}_{current_ft}.h5"
            save_depth_chunk(depth_chunk_path, chunk_frames, chunk_timestamps)
            out.release()
            self.pipeline.stop()


def save_depth_chunk(filename, depth_frames, timestamps):
    """Saves a chunk of depth frames and timestamps to an HDF5 file."""
    with h5py.File(filename, 'w') as hf:
        hf.create_dataset(
            "depth", 
            data=np.array(depth_frames), 
            compression="gzip", 
            compression_opts=9
        )
        hf.create_dataset(
            "timestamps", 
            data=np.array(timestamps, dtype='S'),  # Store timestamps as strings
            compression="gzip"
        )
    print(f"Depth frames and timestamps saved to {filename}")


if __name__ == "__main__":
    cam = Realsense()
    cam.initCamera()
    cam.configureCamera()
    cam.captureImages(seconds=15)
