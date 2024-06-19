import cv2

for cid in range(10):
    cap = cv2.VideoCapture(cid)

    # 0 - realsense
    # 1 - streamcam
    # 2 - hires

    try:
        ret, frame = cap.read()

        if not ret:
            print("No frame")

        cv2.imshow(f"{cid}", frame)

        if cv2.waitKey(0) == "q":
            continue
    except:
        pass
    finally:
        cap.release()
