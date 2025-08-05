from typing import Union, Optional

from apis.i2c_modules.ee895 import EE895
from modules.sensors import SensorModule


class CO2Module(SensorModule):
    def __init__(
            self,
            *,
            i2c_address: int,
            update_frequency: int = 10
    ):
        super().__init__(update_frequency=update_frequency)
        self.i2c_address = i2c_address
        self.ee895: Optional[EE895] = None

    def setup(self, app: "MainBoard"):
        super().setup(app)
        self.ee895 = EE895(self.i2c_address, smbus=app.smbus)

    def sample(self) -> dict[str, Union[float, int]]:
        self.ee895.sample()
        result = {
            "co2": self.ee895.co2,
            "temperature": self.ee895.temperature,
            "pressure": self.ee895.pressure,
            "time": self.ee895.timestamp,
        }
        return result
