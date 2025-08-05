from pathlib import Path
from typing import Union, Optional

from apis.i2c_modules.bme680_lib import BME680
from modules.sensors import SensorModule


class BME680Module(SensorModule):
    def __init__(
            self,
            *,
            i2c_address: int,
            update_frequency: float = 10,
            calibration_file: Optional[Union[Path, str]] = None
    ):
        super().__init__(update_frequency=update_frequency, calibration_file=calibration_file)
        self.i2c_address = i2c_address
        self._bme680: Optional[BME680] = None

    def setup(self, app: "MainBoard"):
        super().setup(app)

        self._bme680 = BME680(self.i2c_address, smbus=app.smbus)
        calibration_data = {
            "value": 0
        }
        calibration_data.update(self.calibration_data)
        self._bme680.sensor.set_temp_offset(**calibration_data)

    @property
    def bme680(self) -> BME680:
        if self._bme680 is None:
            raise ValueError("BME not initialized")
        return self._bme680

    def sample(self) -> dict[str, Union[float, int]]:
        self.bme680.get_sensor_data()
        result = {
            "temperature": self.bme680.temperature,
            "humidity": self.bme680.humidity,
            "pressure": self.bme680.pressure,
            "voc": self.bme680.voc,
        }
        return result
