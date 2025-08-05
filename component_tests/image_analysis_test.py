import datetime
import io
import time

import cv2
import numpy as np
from libcamera import Transform
from picamera2 import Picamera2

from utils.analysis import image_mean_brightness, image_green_proportion

resolution = (3280, 2464)
transform = Transform(hflip=True, vflip=True)
controls = {
    "Brightness": 0,  # Range from -1 (dark) to 1 (bright),
    "Contrast": 1,  # 0 = No contrast, 1=normal, >1= more contrast
    "Saturation": 1,  # 0 = Greyscale, 1=normal, >1= more saturation
    "Sharpness": 1,  # 0 = No sharpening, 1=normal, >1= more sharpening range (0 - 16.0)
    # "ExposureTime": # in microseconds
}

camera = Picamera2()

config = camera.create_still_configuration(
    main={
        "size": resolution
    },
    lores={
        "size": (640, 480),
    },
    transform=transform,
    controls=controls
)

camera.configure(config)

camera.start()

while True:
    stream = io.BytesIO()
    print("Try to take image")
    camera.capture_file(stream, format="jpeg")

    nparr = np.frombuffer(stream.getvalue(), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    green = image_green_proportion(img)
    brightness = image_mean_brightness(img)

    print(f"{datetime.datetime.now()}: B: {brightness}, G: {green}")
    time.sleep(1)
