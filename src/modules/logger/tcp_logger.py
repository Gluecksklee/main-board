import json

import requests
import socket

from modules import GKBaseModule
from utils.datatypes import TelemetryType
from utils.utils import get_time


class TCPLogger(GKBaseModule):
    def __init__(
            self,
            root_url: str,
            update_frequency: float,
    ):
        super().__init__(update_frequency)
        self.root_url = root_url
        self.device_id = socket.gethostname()

    def send(self, command, *, json=None, timeout=2) -> requests.Response:
        return requests.post(
            f"http://{self.root_url}/{self.device_id}/{command}",
            json=json or {},
            timeout=timeout
        )

    def setup(self, app: "MainBoard"):
        super().setup(app)
        self.send("connect", json=self.app.status_dict())

    def _update(self, t: float):
        super()._update(t)
        self.logger.debug(f"Status dict: {self.app.status_dict()}")
        resp = self.send("update", json=self.app.status_dict())
        try:
            commands = json.loads(resp.text)
            self.logger.info(f"Received commands: {commands}")
            for command, data in commands.items():
                self.app.receive_command(command, data)
        except:
            self.logger.error(f"Error parsing commands: {resp.text}")

    def destroy(self):
        super().destroy()
        self.send("disconnect", json=self.app.status_dict())

    def log_telemetry(self, data: TelemetryType, origin: "GKBaseModule"):
        body = data
        body["origin"] = origin.__name__
        body["time"] = data.get("time", get_time())
        self.send("telemetry", json=body)

    def log_media(self, name: str, data: bytes, origin: "GKBaseModule"):
        body = {
            "name": name,
            "data": data.decode("latin"),
            "time": get_time(),
            "origin": origin.__name__
        }
        self.send("media", json=body, timeout=5)
