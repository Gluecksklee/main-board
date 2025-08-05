import time
from typing import Optional

from smbus import SMBus

from apis.i2c_modules import I2C_Module


class EE895_InvalidValues(BaseException):
    pass


class EE895(I2C_Module):
    DATA_REGISTER = 0x00

    def __init__(self, address, *, smbus: Optional[SMBus]):
        super().__init__(address, smbus=smbus)

        try:
            self.smbus.read_i2c_block_data(self.address, self.DATA_REGISTER, 8)
        except IOError:
            raise RuntimeError("Unable to identify CO2-Sensor at 0x{:02x} (IOError)".format(address))

        self._co2: Optional[int] = None
        self._temperature: Optional[float] = None
        self._timestamp: Optional[float] = None
        self._pressure: Optional[float] = None

    def sample(self):
        self.logger.debug("Sample")
        read_data = self.smbus.read_i2c_block_data(self.address, self.DATA_REGISTER, 8)
        # read_data contains ints, which we need to convert to bytes and merge
        # see datasheet
        co2_raw = read_data[0].to_bytes(1, 'big') + read_data[1].to_bytes(1, 'big')
        temperature_raw = read_data[2].to_bytes(1, 'big') + read_data[3].to_bytes(1, 'big')
        # reserved value - useful to check that the sensor is reading out correctly
        # this should be 0x8000
        resvd_raw = read_data[4].to_bytes(1, 'big') + read_data[5].to_bytes(1, 'big')
        pressure_raw = read_data[6].to_bytes(1, 'big') + read_data[7].to_bytes(1, 'big')

        self.logger.debug(f"Raw data: {resvd_raw}, {co2_raw}, {temperature_raw}, {pressure_raw}")
        resvd = int.from_bytes(resvd_raw, "big")
        if not resvd == 0x8000:
            raise EE895_InvalidValues()

        self._co2 = int.from_bytes(co2_raw, "big")
        self._temperature = int.from_bytes(temperature_raw, "big") / 100
        self._pressure = int.from_bytes(pressure_raw, "big") / 10
        self._timestamp = time.time()

    @property
    def co2(self) -> int:
        if self._co2 is None:
            self.sample()
        return self._co2

    @property
    def temperature(self) -> float:
        if self._temperature is None:
            self.sample()
        return self._temperature

    @property
    def timestamp(self) -> float:
        if self._timestamp is None:
            self.sample()
        return self._timestamp

    @property
    def pressure(self) -> float:
        if self._pressure is None:
            self.sample()
        return self._pressure
