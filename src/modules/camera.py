import abc
import io
import pprint
import time
from pathlib import Path
from threading import Thread
from typing import Optional, Union

import cv2
import numpy as np
from libcamera import Transform
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput

from modules import GKBaseModule
from utils.datatypes import TelemetryType
from utils.analysis import image_mean_brightness, image_green_proportion
from utils.utils import get_time, json_dump_compact


class CameraModule(GKBaseModule, abc.ABC):
    def __init__(
            self,
            *,
            file_extension="jpeg",
            image_resolution: tuple[int, int] = (3280, 2464),
            video_resolution: Optional[tuple[int, int]] = (1920, 1080),
            transform: Transform = Transform(),
            cycle_delay: float = 0.1,
            update_frequency: float = 10,
            controls: Optional[dict[str, float]] = None,
            min_video_duration: float = 20,
            imu_threshold: float = 15,
            analyze_images: bool = False,
            camera_start_delay: float = 1,
    ):
        super().__init__(update_frequency=update_frequency)

        # Config
        self._cycle_delay = cycle_delay
        self.image_resolution = tuple(image_resolution)
        self.video_resolution = tuple(video_resolution) if video_resolution else video_resolution
        self.file_extension = file_extension
        self.transform = transform
        self.controls = dict(controls) if controls is not None else {}
        self.imu_threshold = imu_threshold
        self.min_video_duration = min_video_duration
        self.analyze_images = analyze_images
        self.camera_start_delay = camera_start_delay

        # States
        self.images_taken = 0
        self.videos_taken = 0
        self.camera_thread: Optional[Thread] = None
        self.next_image_filename: Optional[Path] = None
        self.video_until: Optional[float] = None

    def setup(self, app: "MainBoard"):
        super().setup(app)

        # Start camera thread
        self.camera_thread = Thread(target=CameraModule._cam_thread, args=(self,))
        self.camera_thread.start()

    def _update(self, t: float):
        super()._update(t)
        timestamp_str = f"{t:.3f}".replace(".", "_")

        self.next_image_filename = f"{timestamp_str}.{self.file_extension}"

    def _cam_thread(self):
        self.logger.debug(f"Initialize PiCamera")

        # Creating PiCam
        try:
            camera = Picamera2()
        except:
            self.logger.error("Error initializing camera")
            self.disable()
            return

        # Configuring PiCam
        try:
            self.logger.debug("Camera modes")
            self.logger.debug(pprint.pformat(camera.sensor_modes))
            preview_config = camera.create_preview_configuration()
            image_config = camera.create_still_configuration(
                main={
                    "size": self.image_resolution
                },
                lores={
                    "size": (480, 270)
                },
                transform=self.transform,
                controls=self.controls,
            )
            video_config = camera.create_video_configuration(
                main={
                    "size": self.video_resolution,
                },
                lores={
                    "size": (480, 270)
                },
                transform=self.transform,
                controls=self.controls,
            )

            camera.configure(preview_config)

            self.logger.info("Starting camera...")
            camera.start()

        except BaseException as e:
            self.logger.error(f"Error while creating PiCamera: {e}")
            camera.stop()
            self.disable()
            return

        self.logger.debug(f"Initialize PiCamera - FINISHED")

        # Loop image retrieval
        while self.is_enabled and self.app_running:
            if self.next_image_filename is not None:
                self.logger.info("Taking image...")
                camera.stop()
                camera.configure(image_config)
                self.take_image(camera)
                camera.stop()
                camera.configure(preview_config)

            if self.video_until is not None:
                self.logger.info("Taking video...")
                camera.stop()
                camera.configure(video_config)
                self.take_video(camera)
                camera.stop()
                camera.configure(preview_config)

            time.sleep(self._cycle_delay)

        camera.stop()

    def take_image(self, camera: Picamera2):
        try:
            stream = io.BytesIO()
            self.logger.info("Try to take image")

            camera.start()
            self.logger.info("Camera started")
            time.sleep(self.camera_start_delay)
            metadata = camera.capture_file(stream, format=self.file_extension)
            self.logger.info(f"Image taken by camera: {metadata}")

            self.app.log_media(self.next_image_filename, stream.getvalue(), origin=self)
            log_data = {
                "time": get_time(),
                "file_metadata": json_dump_compact(metadata),
                "file_name": self.next_image_filename,
                "file_type": "image",
            }
            if self.analyze_images:
                log_data.update(self.image_analysis_data(stream))
            self.app.log_telemetry(log_data, self)

            self.images_taken += 1
        except BaseException as e:
            self.logger.error(f"Error while taking a picture ({e})")
        self.next_image_filename = None

    def take_video(self, camera: Picamera2):
        try:
            start_time = get_time()
            timestamp_str = f"{start_time:.3f}".replace(".", "_")
            video_filename = f"/download/camera_{timestamp_str}.h264"
            output = FileOutput(video_filename)
            self.logger.info("Try to take video")
            encoder = H264Encoder(bitrate=10000000)
            self.logger.info(f"Start recording at {start_time}")
            camera.start_recording(encoder, output)
            metadata = camera.capture_metadata()

            while self.video_until is not None and get_time() < self.video_until:
                time.sleep(max((self.video_until - get_time()) / 2, 0.1))
            self.video_until = None

            end_time = get_time()
            self.logger.info(f"Video taken by camera until {end_time} ({end_time - start_time:.2f} seconds)")

            log_data = {
                "time": start_time,
                "file_metadata": json_dump_compact(metadata),
                "file_name": video_filename,
                "file_type": "video",
                "video_duration": end_time - start_time
            }

            self.app.log_telemetry(log_data, self)
            self.videos_taken += 1
        except BaseException as e:
            self.logger.error(f"Error while taking a picture ({e})")

        camera.stop_recording()

    def log_telemetry(self, data: TelemetryType, origin: "GKBaseModule"):
        # Only check for imu
        if origin.__name__ != "imu":
            return

        # Only use motion data from imu
        if "in_motion" not in data:
            self.logger.warning("`in_motion` not found in data")
            return

        # Threshold
        if data["in_motion"]:
            self.video_until = get_time() + self.min_video_duration
            self.logger.info(f"Request video until {self.video_until}")

    def image_analysis_data(self, stream: io.BytesIO):
        # Convert image
        nparr = np.frombuffer(stream.getvalue(), np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Analyze image
        data = {}
        # try:
        #     data["green"] = image_green_proportion(image)
        # except:
        #     self.logger.warning("Error while calculating green value")

        try:
            data["brightness"] = image_mean_brightness(image)
        except:
            self.logger.warning("Error while calculating mean brightness")
            pass

        return data

    def status_dict(self) -> dict[str, Union[str, int, float, bool]]:
        res = super().status_dict()
        res["video_until"] = self.video_until
        res["images_taken"] = self.images_taken
        res["videos_taken"] = self.videos_taken
        res["analyze_images"] = self.analyze_images

        return res
