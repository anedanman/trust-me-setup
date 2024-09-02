import os
import numpy as np
import h5py
import matplotlib.pyplot as plt

def save_pid(name):
    pid = os.getpid()
    with open(f"tmp/pids/{name}", "w") as f:
        f.write(str(pid))

def decode_h5(file):
    with h5py.File(f, "r") as hdf:
        data = hdf["depth"][()]
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
