# Adapted from https://github.com/wallarug/CircuitPython_MPU9250
import time
from typing import Optional

from apis.i2c_modules import I2C_Module
from smbus import SMBus

try:
    import struct
except ImportError:
    import ustruct as struct

_GYRO_CONFIG = 0x1b
_ACCEL_CONFIG = 0x1c
_ACCEL_CONFIG2 = 0x1d
_INT_PIN_CFG = 0x37
_ACCEL_XOUT_H = 0x3b
_ACCEL_XOUT_L = 0x3c
_ACCEL_YOUT_H = 0x3d
_ACCEL_YOUT_L = 0x3e
_ACCEL_ZOUT_H = 0x3f
_ACCEL_ZOUT_L = 0x40
_TEMP_OUT_H = 0x41
_TEMP_OUT_L = 0x42
_GYRO_XOUT_H = 0x43
_GYRO_XOUT_L = 0x44
_GYRO_YOUT_H = 0x45
_GYRO_YOUT_L = 0x46
_GYRO_ZOUT_H = 0x47
_GYRO_ZOUT_L = 0x48
_WHO_AM_I = 0x75

# _ACCEL_FS_MASK = 0b00011000
ACCEL_FS_SEL_2G = 0b00000000
ACCEL_FS_SEL_4G = 0b00001000
ACCEL_FS_SEL_8G = 0b00010000
ACCEL_FS_SEL_16G = 0b00011000

_ACCEL_SO_2G = 16384  # 1 / 16384 ie. 0.061 mg / digit
_ACCEL_SO_4G = 8192  # 1 / 8192 ie. 0.122 mg / digit
_ACCEL_SO_8G = 4096  # 1 / 4096 ie. 0.244 mg / digit
_ACCEL_SO_16G = 2048  # 1 / 2048 ie. 0.488 mg / digit

# _GYRO_FS_MASK = 0b00011000
GYRO_FS_SEL_250DPS = 0b00000000
GYRO_FS_SEL_500DPS = 0b00001000
GYRO_FS_SEL_1000DPS = 0b00010000
GYRO_FS_SEL_2000DPS = 0b00011000

_GYRO_SO_250DPS = 131
_GYRO_SO_500DPS = 62.5
_GYRO_SO_1000DPS = 32.8
_GYRO_SO_2000DPS = 16.4

_TEMP_SO = 333.87
_TEMP_OFFSET = 21

# Used for enabling and disabling the i2c bypass access
_I2C_BYPASS_MASK = 0b00000010
_I2C_BYPASS_EN = 0b00000010
_I2C_BYPASS_DIS = 0b00000000

SF_G = 1
SF_M_S2 = 9.80665  # 1 g = 9.80665 m/s2 ie. standard gravity
SF_DEG_S = 1
SF_RAD_S = 0.017453292519943  # 1 deg/s is 0.017453292519943 rad/s


class MPU6500(I2C_Module):
    """Class which provides interface to MPU6500 6-axis motion tracking device."""

    _BUFFER = bytearray(6)

    def __init__(
            self,
            address,
            *,
            smbus: Optional[SMBus] = None,
            accel_fs=ACCEL_FS_SEL_2G,
            gyro_fs=GYRO_FS_SEL_500DPS,
            accel_sf=SF_M_S2,
            gyro_sf=_GYRO_SO_500DPS,
            gyro_offset=(0, 0, 0)
    ):
        super().__init__(address, smbus=smbus)

        a = self.read_whoami()
        if 0x78 != a:
            raise RuntimeError(f"MPU6500 not found in I2C bus (0x{a:x} != 0x71)")

        self._accel_so = self._accel_fs(accel_fs)
        self._gyro_so = self._gyro_fs(gyro_fs)
        self._accel_sf = accel_sf
        self._gyro_sf = gyro_sf
        self._gyro_offset = gyro_offset

        # Enable I2C bypass to access for MPU9250 magnetometer access.
        char = self._read_u8(_INT_PIN_CFG)
        char &= ~_I2C_BYPASS_MASK  # clear I2C bits
        char |= _I2C_BYPASS_EN
        self._write_u8(_INT_PIN_CFG, char)

    def read_acceleration(self):
        """
        Acceleration measured by the sensor. By default will return a
        3-tuple of X, Y, Z axis acceleration values in m/s^2 as floats. Will
        return values in g if constructor was provided `accel_sf=SF_M_S2`
        parameter.
        """
        so = self._accel_so
        sf = self._accel_sf

        xyz = self._read_bytes(_ACCEL_XOUT_H, 6)
        return tuple([value / so * sf for value in xyz])

    @property
    def acceleration(self):
        """The accelerometer X, Y, Z axis values as a 3-tuple of
        m/s^2 values.
        """
        raw = self.read_acceleration()
        return raw

    def read_gyro(self):
        """
        X, Y, Z radians per second as floats.
        """
        so = self._gyro_so
        ox, oy, oz = self._gyro_offset
        gyro_scale = self._gyro_sf

        raw = self._read_bytes(_GYRO_XOUT_H, 6)

        gyro_x = (raw[0] / gyro_scale) - ox
        gyro_y = (raw[1] / gyro_scale) - oy
        gyro_z = (raw[2] / gyro_scale) - oz

        return (gyro_x, gyro_y, gyro_z)

    @property
    def gyro(self):
        """The gyroscope X, Y, Z axis values as a 3-tuple of
        degrees/second values.
        """
        raw = self.read_gyro()
        return raw

    def read_temperature(self):
        """
        Die temperature in celsius as a float.
        """
        temp = self._read_bytes(_TEMP_OUT_H, 2)
        return ((temp - _TEMP_OFFSET) / _TEMP_SO) + _TEMP_OFFSET

    @property
    def temperature(self):
        """The temperature of the sensor in degrees Celsius."""
        raw = self.read_temperature()
        return raw

    def read_whoami(self):
        """ Value of the whoami register. """
        return self._read_u8(_WHO_AM_I)

    def calibrate_gyro(self, count=256, delay=0):
        ox, oy, oz = (0.0, 0.0, 0.0)
        self._gyro_offset = (0.0, 0.0, 0.0)
        n = float(count)

        while count:
            time.sleep(delay / 1000)
            gx, gy, gz = self.read_gyro()
            ox += gx
            oy += gy
            oz += gz
            count -= 1

        self._gyro_offset = (ox / n, oy / n, oz / n)
        return self._gyro_offset

    def _accel_fs(self, value):
        self._write_u8(_ACCEL_CONFIG, value)

        # Return the sensitivity divider
        if ACCEL_FS_SEL_2G == value:
            return _ACCEL_SO_2G
        elif ACCEL_FS_SEL_4G == value:
            return _ACCEL_SO_4G
        elif ACCEL_FS_SEL_8G == value:
            return _ACCEL_SO_8G
        elif ACCEL_FS_SEL_16G == value:
            return _ACCEL_SO_16G

    def _gyro_fs(self, value):
        self._write_u8(_GYRO_CONFIG, value)

        # Return the sensitivity divider
        if GYRO_FS_SEL_250DPS == value:
            return _GYRO_SO_250DPS
        elif GYRO_FS_SEL_500DPS == value:
            return _GYRO_SO_500DPS
        elif GYRO_FS_SEL_1000DPS == value:
            return _GYRO_SO_1000DPS
        elif GYRO_FS_SEL_2000DPS == value:
            return _GYRO_SO_2000DPS

    def _read_u8(self, address):
        return self.smbus.read_byte_data(self.address, address)

    def _read_bytes(self, address, count):
        buffer = self.smbus.read_i2c_block_data(self.address, address, 8)
        if count == 2:
            buf = bytearray(4)
            buf[0] = buffer[0]
            buf[1] = buffer[1]
            return struct.unpack(">hh", buf)[0]
        buf = bytearray(6)
        for i in range(count):
            buf[i] = buffer[i]
        return struct.unpack(">hhh", buf)

    def _write_u8(self, address, val):
        return self.smbus.write_byte_data(self.address, address, val)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass
