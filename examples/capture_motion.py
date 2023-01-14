"""A basic motion detector.
It simple compares frames and starts
recording if the difference is larger
than a set threshold.

Timestamps are applied to each frame.

Based on official example at
https://github.com/raspberrypi/picamera2/blob/main/examples/capture_motion.py
"""

import datetime
import time

import cv2
import numpy as np
from pathlib import Path

from picamera2 import Picamera2, MappedArray
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput

VIDEOS_DIR = Path().home() / "camera" / "video"
MIN_DURATION_SECS = 5.0


def apply_timestamp(request):
    colour = (0, 255, 0)
    origin = (0, 30)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1
    thickness = 2
    timestamp = time.strftime("%Y-%m-%d %X")
    with MappedArray(request, "main") as m:
        cv2.putText(m.array, timestamp, origin, font, scale, colour, thickness)


lsize = (320, 240)
picam2 = Picamera2()
picam2.pre_callback = apply_timestamp
video_config = picam2.create_video_configuration(
    main={"size": (1280, 720), "format": "XBGR8888"},
    lores={"size": lsize, "format": "YUV420"},
)
picam2.configure(video_config)
camera_controls = picam2.controls
encoder = H264Encoder()
picam2.encoder = encoder
picam2.start()

w, h = lsize
prev = None
encoding = False
ltime = 0

while True:
    cur = picam2.capture_buffer("lores")
    cur = cur[: w * h].reshape(h, w)
    if prev is not None:
        # Measure pixels differences between current and
        # previous frame
        mse = np.square(np.subtract(cur, prev)).mean()
        if mse > 7:
            if not encoding:
                print("New Motion detected with mean-square difference of", mse)
                dateraw = datetime.datetime.now()
                datetimeformat = dateraw.strftime("%Y-%m-%d_%H%M")
                print(f"RPi started taking video at: {datetimeformat}")
                encoder.output = FfmpegOutput(f"{VIDEOS_DIR}/{datetimeformat}.mp4")
                picam2.start_encoder()
                encoding = True
            ltime = time.time()
        else:
            if encoding and time.time() - ltime > MIN_DURATION_SECS:
                picam2.stop_encoder()
                dateraw = datetime.datetime.now()
                datetimeformat = dateraw.strftime("%Y-%m-%d_%H%M")
                print(f"RPi stopped taking video at: {datetimeformat}")
                encoding = False
    prev = cur
