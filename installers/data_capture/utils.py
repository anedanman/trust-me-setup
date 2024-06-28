import os
import numpy as np
import h5py
import matplotlib.pyplot as plt


def decode_h5(file):
	with h5py.File(f, "r") as hdf:
		for key in hdf.keys():
			data = hdf[key][()]
			arr = np.array(data)

			return arr

		
if __name__ == "__main__":
	for f in os.listdir("."):

		if ".py" in f or ".npy" in f:
			continue
		
		arr = decode_h5(f)			
		
		np.save(f.replace(".h5", ".npy"), arr)

		plt.imshow(arr)

		plt.show()

