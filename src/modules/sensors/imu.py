import math
from pathlib import Path
from typing import Optional, Union

from apis.i2c_modules.MPU6500 import MPU6500
from modules.sensors import SensorModule
from utils.analysis import imu_in_motion
from utils.datatypes import TelemetryType


class IMUModule(SensorModule):
    def __init__(
            self,
            *,
            i2c_address: int,
            update_frequency: float = 1,
            calibration_file: Optional[Union[Path, str]] = None,
            imu_motion_threshold: float = 1.5,
    ):
        super().__init__(update_frequency=update_frequency, calibration_file=calibration_file)
        self.i2c_address = i2c_address
        self.imu: Optional[MPU6500] = None
        self.imu_motion_threshold = imu_motion_threshold

        self._old_vector = 0, 0, 0

    def setup(self, app: "MainBoard"):
        super().setup(app)
        self.imu = MPU6500(self.i2c_address, smbus=app.smbus, **self.calibration_data)

    def sample(self) -> TelemetryType:
        ax, ay, az = self.imu.acceleration
        gyro = self.imu.gyro
        temperature = self.imu.temperature
        total_acc = math.sqrt(ax ** 2 + ay ** 2 + az ** 2)

        # Update in motion
        new_vector = ax, ay, az
        in_motion = imu_in_motion(self._old_vector, new_vector, self.imu_motion_threshold)
        in_motion = in_motion or total_acc >= 30
        self._old_vector = new_vector

        return {
            "ax": ax,
            "ay": ay,
            "az": az,
            "a": total_acc,
            "gx": gyro[0],
            "gy": gyro[1],
            "gz": gyro[2],
            "temperature": temperature,
            "in_motion": in_motion
        }
