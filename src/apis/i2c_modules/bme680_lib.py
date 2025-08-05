from enum import Enum

import bme680

from apis.i2c_modules import I2C_Module


class Mode(Enum):
    SLEEP = 0
    FORCE = 0b01
    NORMAL = 0b11


class BME680(I2C_Module):
    def __init__(self, address, *, smbus=None):
        super().__init__(address, smbus=smbus)
        self.logger.info(f"Initialising BME680 with address 0x{address:x}")
        self.sensor = bme680.BME680(
            i2c_addr=address,
            i2c_device=smbus
        )
        self._sensor_data = None

    def get_sensor_data(self):
        self.logger.info("Sample new sensor data...")
        self._sensor_data = self.sensor.get_sensor_data()
        self.logger.info(f"Sample new sensor data... -> {self._sensor_data}")
        return self._sensor_data

    @property
    def temperature(self) -> float:
        """ Outputs temperature in °C """
        # if self._sensor_data is None:
        #     self.get_sensor_data()
        return self.sensor.data.temperature

    @property
    def pressure(self) -> float:
        """ Outputs pressure in hPa """
        return self.sensor.data.pressure

    @property
    def humidity(self) -> float:
        """ Outputs humidity %RH """
        return self.sensor.data.humidity

    @property
    def voc(self):
        return self.sensor.data.gas_resistance
