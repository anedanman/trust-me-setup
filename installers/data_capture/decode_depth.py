import h5py
import os
import numpy as np
from PIL import Image

def read_and_decode_h5(h5_filepath, save_decoded=False):
    """
    Reads an HDF5 file containing depth frames and timestamps,
    returns the number of images, and optionally saves the decoded
    images in a /decoded subdirectory.
    
    Args:
        h5_filepath (str): Path to the HDF5 file.
        save_decoded (bool): If True, saves the decoded depth images as PNG files.
    
    Returns:
        int: The number of images in the HDF5 file.
    """
    
    # Open the HDF5 file
    with h5py.File(h5_filepath, 'r') as hf:
        print(hf.keys())
        # Read the depth data and timestamps
        depth_data = hf['depth'][:]
        timestamps = hf['timestamps'][:]
        
        # Get the number of images
        num_images = depth_data.shape[0]
        print(f"Number of images in the file: {num_images}")
        
        # Optionally save the decoded images
        if save_decoded:
            # Create the decoded directory if it doesn't exist
            decoded_dir = os.path.join(os.path.dirname(h5_filepath), 'decoded')
            os.makedirs(decoded_dir, exist_ok=True)
            
            # Save each depth image as a PNG file
            for i, depth_image in enumerate(depth_data):
                # Normalize depth image to the range [0, 255] for saving as PNG
                depth_image_normalized = np.uint8((depth_image / np.max(depth_image)) * 255)
                
                # Create a filename using the timestamp
                timestamp_str = timestamps[i].decode('utf-8')  # Convert bytes to string
                image_filename = os.path.join(decoded_dir, f"depth_{timestamp_str}.png")
                
                # Save the depth image as a PNG file
                img = Image.fromarray(depth_image_normalized)
                img.save(image_filename)
                
                print(f"Saved {image_filename}")
    
    return num_images


if __name__ == "__main__":
    h5_file_path = "out_2024-09-20$08-48-40-687401.h5"
    num_images = read_and_decode_h5(h5_file_path, save_decoded=True)
