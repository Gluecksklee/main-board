import time

from typing import Optional
from smbus import SMBus

from apis.i2c_modules import I2C_Module

try:
    import struct
except ImportError:
    import ustruct as struct

_WIA = 0x00
_HXL = 0x03
_HXH = 0x04
_HYL = 0x05
_HYH = 0x06
_HZL = 0x07
_HZH = 0x08
_ST2 = 0x09
_CNTL1 = 0x0a
_ASAX = 0x10
_ASAY = 0x11
_ASAZ = 0x12

_MODE_POWER_DOWN = 0b00000000
MODE_SINGLE_MEASURE = 0b00000001
MODE_CONTINUOUS_MEASURE_1 = 0b00000010  # 8Hz
MODE_CONTINUOUS_MEASURE_2 = 0b00000110  # 100Hz
MODE_EXTERNAL_TRIGGER_MEASURE = 0b00000100
_MODE_SELF_TEST = 0b00001000
_MODE_FUSE_ROM_ACCESS = 0b00001111

OUTPUT_14_BIT = 0b00000000
OUTPUT_16_BIT = 0b00010000

_SO_14BIT = 0.6  # μT per digit when 14bit mode
_SO_16BIT = 0.15  # μT per digit when 16bit mode


class AK8963(I2C_Module):
    """Class which provides interface to AK8963 magnetometer."""

    def __init__(
            self,
            address=0x69,
            *,
            smbus: Optional[SMBus] = None,
            mode=MODE_CONTINUOUS_MEASURE_2,
            output=OUTPUT_16_BIT,
            offset=(0, 0, 0),
            scale=(1, 1, 1)
    ):
        super().__init__(address, smbus=smbus)
        self._offset = offset
        self._scale = scale

        a = self.read_whoami()
        if 0xbf != a:
            raise RuntimeError(f"AK8963 not found in I2C bus. (0x{a:x} != 0xbf)")

        # Sensitivity adjustment values
        self._write_u8(_CNTL1, _MODE_FUSE_ROM_ACCESS)
        asax = self._read_u8(_ASAX)
        asay = self._read_u8(_ASAY)
        asaz = self._read_u8(_ASAZ)
        self._write_u8(_CNTL1, _MODE_POWER_DOWN)

        # Should wait at least 100us before next mode
        time.sleep(100e-6)

        self._adjustment = (
            (0.5 * (asax - 128)) / 128 + 1,
            (0.5 * (asay - 128)) / 128 + 1,
            (0.5 * (asaz - 128)) / 128 + 1
        )

        # Power on
        self._write_u8(_CNTL1, (mode | output))

        if output is OUTPUT_16_BIT:
            self._so = _SO_16BIT
        else:
            self._so = _SO_14BIT

    def read_magnetic(self):
        """
        X, Y, Z axis micro-Tesla (uT) as floats.
        """
        xyz = list(self._read_bytes(_HXL, 6))
        self._read_u8(_ST2)  # Enable updating readings again

        # Apply factory axial sensitivy adjustments
        xyz[0] *= self._adjustment[0]
        xyz[1] *= self._adjustment[1]
        xyz[2] *= self._adjustment[2]

        # Apply output scale determined in constructor
        so = self._so
        xyz[0] *= so
        xyz[1] *= so
        xyz[2] *= so

        # Apply hard iron ie. offset bias from calibration
        xyz[0] -= self._offset[0]
        xyz[1] -= self._offset[1]
        xyz[2] -= self._offset[2]

        # Apply soft iron ie. scale bias from calibration
        xyz[0] *= self._scale[0]
        xyz[1] *= self._scale[1]
        xyz[2] *= self._scale[2]

        return tuple(xyz)

    @property
    def magnetic(self):
        """The magnetometer X, Y, Z axis values as a 3-tuple of
        micro-Tesla (uT) values.
        """
        raw = self.read_magnetic()
        return raw

    def read_whoami(self):
        """ Value of the whoami register. """
        return self._read_u8(_WIA)

    def calibrate(self, count=256, delay=0.200):
        """
        Calibrate the magnetometer.
        The magnetometer needs to be turned in alll possible directions
        during the callibration process. Ideally each axis would once
        line up with the magnetic field.
        count: int
            Number of magnetometer readings that are taken for the calibration.

        delay: float
            Delay between the magntometer readings in seconds.
        """
        self._offset = (0, 0, 0)
        self._scale = (1, 1, 1)

        reading = self.read_magnetic()
        minx = maxx = reading[0]
        miny = maxy = reading[1]
        minz = maxz = reading[2]

        while count:
            time.sleep(delay)
            reading = self.read_magnetic()
            minx = min(minx, reading[0])
            maxx = max(maxx, reading[0])
            miny = min(miny, reading[1])
            maxy = max(maxy, reading[1])
            minz = min(minz, reading[2])
            maxz = max(maxz, reading[2])
            count -= 1

        # Hard iron correction
        offset_x = (maxx + minx) / 2
        offset_y = (maxy + miny) / 2
        offset_z = (maxz + minz) / 2

        self._offset = (offset_x, offset_y, offset_z)

        # Soft iron correction
        avg_delta_x = (maxx - minx) / 2
        avg_delta_y = (maxy - miny) / 2
        avg_delta_z = (maxz - minz) / 2

        avg_delta = (avg_delta_x + avg_delta_y + avg_delta_z) / 3

        scale_x = avg_delta / avg_delta_x
        scale_y = avg_delta / avg_delta_y
        scale_z = avg_delta / avg_delta_z

        self._scale = (scale_x, scale_y, scale_z)

        return self._offset, self._scale

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
