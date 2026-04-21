from config import url

import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

import cv2

url = url

cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
print("opened:", cap.isOpened())

ret, frame = cap.read()
print("ret:", ret)

if ret:
    print(frame.shape)

cap.release()