import datetime
import logging
import time
from pathlib import Path
from pprint import pprint
from smbus import SMBus

from picamera2 import Picamera2
from libcamera import Transform

DATA_LOCATION = Path("/root/data/camera_test")
logger = logging.getLogger("Cameratest")


def focus(val, smbus):
    value = (val << 4) & 0x3ff0
    data1 = (value >> 8) & 0x3f
    data2 = value & 0xf0
    print(f"focus value: {val}")

    smbus.write_byte_data(0x0c, data1, data2)


def cam_thread(*, cycle_delay=5):
    logger.debug(f"Initialize PiCamera")

    smbus = SMBus(0)

    # Creating PiCam
    try:
        camera = Picamera2()
        logger.debug("Camera modes")
        pprint(camera.sensor_modes)
        logger.debug("Create config")
        config = camera.create_still_configuration(
            main={
                # "size": (640, 480),
                "size": (1280, 720),
                # "size": (2560, 1440),
                # "size": (3840, 2160),
                # "size": (4656, 3496),
            },
            lores={
                "size": (640, 480),
            },
            transform=Transform(hflip=True, vflip=True),
            controls={
                "Brightness": 0,  # Range from -1 (dark) to 1 (bright),
                "Contrast": 1,  # 0 = No contrast, 1=normal, >1= more contrast
                "Saturation": 1,  # 0 = Greyscale, 1=normal, >1= more saturation
                "Sharpness": 1,  # 0 = No sharpening, 1=normal, >1= more sharpening range (0 - 16.0)
                # "ExposureTime": # in microseconds
            }
        )

        logger.debug("Configure")
        camera.configure(config)
        # TODO: set resolution
        # Camera settings
        # camera.rotation = self.rotation
        # TODO: Add additional settings
        # camera.brightness =
        # camera.contrast =
        logger.debug("Start")
        camera.start()

    except Exception as e:
        logger.error(f"Error while creating PiCamera: {e}")
        raise

    logger.debug(f"Initialize PiCamera - FINISHED")

    # Loop image retrieval
    focal_distance = 10
    while True:
        focus(focal_distance, smbus)
        try:
            image_name = f"{datetime.datetime.now():%Y%m%d_%H%M%S}_focal_{focal_distance:04d}.jpg"
            image_path = DATA_LOCATION / image_name
            image_path.parent.mkdir(exist_ok=True, parents=True)
            logger.info(f"Saving image at {image_path.absolute().resolve()}")
            camera.capture_file(image_path, format="jpeg")
        except Exception as e:
            logger.error(f"Error while taking a picture ({e})")
            raise

        focal_distance += 15
        if focal_distance > 1000:
            break

        # time.sleep(cycle_delay)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,format="%(asctime)s %(levelname)s %(threadName)s %(name)s")
    logging.getLogger("picamera2").setLevel(logging.WARN)

    try:
        cam_thread()
    except KeyboardInterrupt:
        print("Camera finished")
        pass
