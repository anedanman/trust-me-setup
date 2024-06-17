import numpy as np

path = "data/realsense/depth"
# if not os.path.exists(path):
#    print("Ne zmišljuj si filov")
#
# cap = cv2.VideoCapture(path)
#
#
# ret, frame = cap.read()
#
# if not ret:
#    print("no frame")
#    exit()
#
# plt.imshow(frame)
# plt.show()

import h5py

with h5py.File("test.h5", "w") as hf:
    hf.create_dataset(
        "test",
        data=np.load(path + "/trojer_test_0_1717055030_2479937.npy"),
        compression="gzip",
    )
