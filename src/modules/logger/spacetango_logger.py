import datetime
import time
from pathlib import Path
from threading import Thread, Lock
from typing import Optional, Union

from modules import GKBaseModule
from utils.datatypes import TelemetryType
import serial

from utils.utils import get_time


class SpaceTangoLogger(GKBaseModule):
    def __init__(
            self,
            update_frequency: float,
            host: str,
            baudrate: int,
            maximum_packet_size: int,
            minimum_packet_delay: float,
            media_path: Union[Path, str],
            time_quantization: float,
            data_timeout: float,
            serial_timeout: float,
            telecomando_directory: str,
            float_precision: int = 3
    ):
        super().__init__(update_frequency)
        self.host = host
        self.baudrate = baudrate
        self.maximum_packet_size = maximum_packet_size
        self.minimum_packet_delay = minimum_packet_delay
        self.media_path = Path(media_path)
        self.time_quantization = float(time_quantization)  # Make sure time_quantization is a float, so time is a float
        self.data_timeout = data_timeout
        self.serial_timeout = serial_timeout
        self.telecomando_directory = Path(telecomando_directory)
        self.float_precision = float_precision

        self._serial: Optional[serial.Serial] = None
        self.queue_processing_thread: Optional[Thread] = None
        self.queue_lock = Lock()
        self.data_queue: dict[tuple[float, str], Union[str, float, int]] = {}

        # Status information
        self.stats = {}
        self.reset_stats()

    @property
    def serial(self) -> serial.Serial:
        if self._serial is None:
            self._serial = serial.Serial(self.host, self.baudrate, timeout=self.serial_timeout)

        return self._serial

    def setup(self, app: "MainBoard"):
        super().setup(app)

        self.logger.info(f"Creating directory for telecommandos: {self.telecomando_directory.absolute().resolve()}")
        self.telecomando_directory.mkdir(exist_ok=True, parents=True)

        # Start processing queue in another thread
        self.queue_processing_thread = Thread(target=self.process_queue, daemon=True)
        self.queue_processing_thread.start()

    def reset(self):
        # Delete media
        if self.media_path is not None:
            for file in self.media_path.iterdir():
                if file.is_file():
                    file.unlink(missing_ok=True)

    def process_queue(self):
        last_packet_sent = datetime.datetime.now()
        while self.app_running:
            time.sleep(0.1)

            # Wait until next package can be sent
            if (datetime.datetime.now() - last_packet_sent).total_seconds() < self.minimum_packet_delay:
                continue

            # Wait until data exists to sent
            if len(self.data_queue) == 0:
                continue

            with self.queue_lock:
                # Clean timeouted data
                current_time = get_time()
                current_cmd_time = None
                while len(self.data_queue) > 0:
                    first_key = tuple(self.data_queue.keys())[0]
                    current_cmd_time = first_key[0]
                    if current_time - current_cmd_time > self.data_timeout:
                        self.logger.warning(f"Data timeout: {first_key} -> {self.data_queue[first_key]}")
                        self.stats["telemetry_discarded"] += 1
                        self.data_queue.pop(first_key)
                    else:
                        break

                # Build command string
                cmd_str = self.key_value_to_cmd_str("time", current_cmd_time, float_precision=1)
                n_data_fields = 0
                while len(self.data_queue) > 0:
                    t, name = tuple(self.data_queue.keys())[0]

                    value = self.data_queue[(t, name)]

                    # Stop if another timestamp in next data
                    if t != current_cmd_time:
                        break

                    # Generate cmd part
                    new_cmd_part = self.key_value_to_cmd_str(name, value, float_precision=self.float_precision)

                    # Stop if max length exceeded
                    if len(cmd_str) + len(new_cmd_part) + 2 > self.maximum_packet_size:  # +1 for "," and "\n"
                        break

                    cmd_str = f"{cmd_str},{new_cmd_part}"
                    n_data_fields += 1

                    # Remove data from queue
                    self.data_queue.pop((t, name))

                # Termination character
                cmd_str += "\n"

            # Send command via serial connection
            encoded_cmd = cmd_str.encode("latin")
            self.logger.info(f"Write cmd {encoded_cmd}")
            self.serial.write(encoded_cmd)
            last_packet_sent = datetime.datetime.now()

            self.stats["telemetry_messages"] += 1
            self.stats["telemetry_fields"] += n_data_fields
            self.stats["telemetry_bytes"] += len(cmd_str)

    def _update(self, t: float):
        super()._update(t)

        for file in self.telecomando_directory.iterdir():
            tc_type = file.name
            tc_content = file.read_text()
            self.app.receive_command(tc_type, tc_content)
            file.unlink(missing_ok=True)

        log_data = {
            "time": t,
            # "media_n": self.stats["media_n"],
            # "media_mb": self.stats["media_bytes"] / 1000000,
            "tm_discarded": self.stats["telemetry_discarded"],
            # "tm_n": self.stats["telemetry_messages"],
            # "tm_fields": self.stats["telemetry_fields"],
            # "tm_bytes": self.stats["telemetry_bytes"],
        }

        self.log_telemetry(log_data, self)

    def destroy(self):
        super().destroy()
        if self._serial is not None:
            self._serial.close()

    def log_telemetry(self, data: TelemetryType, origin: "GKBaseModule"):
        # Omit image telemetry from camera
        if origin.__name__ == "camera":
            data.pop("file_metadata")
            data.pop("file_name")
            data.pop("file_type")

        # Get timestamp
        if "time" not in data:
            self.logger.warning(f"Time not found in data for {origin.__name__}. Adding own timestamp.")
            data["time"] = get_time()

        experiment_time = data.pop("time")  # Remove from dict, as this is handled separately

        # Quantize time
        experiment_time = experiment_time // self.time_quantization * self.time_quantization

        # Get queue data
        new_queue_data = {
            (experiment_time, f"{origin.__name__}_{key}"): value
            for key, value in data.items()
        }

        with self.queue_lock:
            self.data_queue.update(new_queue_data)

        self.logger.debug(f"Added {len(new_queue_data)} items to data queue")

    def log_media(self, name: str, data: bytes, origin: "GKBaseModule"):
        filepath = self.media_path / f"{origin.__name__}_{name}"
        self.logger.debug(f"Save media at {filepath}")
        filepath.parent.mkdir(exist_ok=True, parents=True)
        filepath.write_bytes(data)
        self.stats["media_n"] += 1
        self.stats["media_bytes"] += len(data)

    @staticmethod
    def key_value_to_cmd_str(name: str, value: Union[str, float, int], *, float_precision=3) -> str:
        value_str = None
        if isinstance(value, str):
            value_str = f'"{value}"'
        elif isinstance(value, int):
            value_str = f"{value:d}"
        elif isinstance(value, float):
            value_str = f"{value:.{float_precision}f}"

            value_str = value_str.rstrip("0")
            if value_str[-1] == ".":
                value_str += "0"

        return f'"{name}":{value_str}'

    def status_dict(self) -> dict[str, Union[str, int, float, bool]]:
        res = super().status_dict()
        res["baudrate"] = self.baudrate
        res["host"] = self.host
        res["maximum_packet_size"] = self.maximum_packet_size
        res["minimum_packet_delay"] = self.minimum_packet_delay
        res["media_path"] = str(self.media_path.absolute())
        res["time_quantization"] = self.time_quantization
        res["data_timeout"] = self.data_timeout
        res["serial_timeout"] = self.serial_timeout
        res["telecomando_directory"] = str(self.telecomando_directory.absolute())
        res["statistics"] = self.stats  # noqa
        res["statistics"]["total_bytes"] = self.stats["media_bytes"] + self.stats["telemetry_bytes"]  # noqa
        return res

    def reset_stats(self):
        self.stats = {
            "media_n": 0,
            "media_bytes": 0,
            "telemetry_discarded": 0,
            "telemetry_messages": 0,
            "telemetry_fields": 0,
            "telemetry_bytes": 0,
        }
