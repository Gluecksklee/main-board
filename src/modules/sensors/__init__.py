import abc
import json
from pathlib import Path
from typing import Union, Optional

from modules import GKBaseModule
from utils.datatypes import TelemetryType


class SensorModule(GKBaseModule, abc.ABC):
    def __init__(self, update_frequency: float, calibration_file: Optional[Union[Path, str]] = None):
        super().__init__(update_frequency)
        self.latest_data = {}
        self.calibration_file = None if calibration_file is None else Path(calibration_file)

    @property
    def calibration_data(self) -> dict:
        if self.calibration_file is not None:
            if Path(self.calibration_file).exists():
                return json.loads(self.calibration_file.read_text())
            else:
                self.logger.warning(f"Calibration file at {Path(self.calibration_file)} does not exist!")
        return {}

    def status_dict(self) -> dict[str, Union[str, int, float, bool]]:
        res = super().status_dict()
        res["sensor_data"] = self.latest_data # noqa
        return res

    def test(self):
        super().test()
        self.latest_data = self.sample()
        self.logger.info(self.latest_data)

    def _update(self, t: float):
        self.latest_data = self.sample()
        self.logger.info(self.latest_data)
        data = self.latest_data
        if "time" not in data:
            data["time"] = t
        self.app.log_telemetry(data, self)

    @abc.abstractmethod
    def sample(self) -> TelemetryType:
        """ Samples values and returns values as dictionary[name -> value]"""
        pass
