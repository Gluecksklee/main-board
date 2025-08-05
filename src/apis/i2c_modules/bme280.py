import struct
from enum import Enum
from functools import cached_property

from apis.i2c_modules import I2C_Module


class Mode(Enum):
    SLEEP = 0
    FORCE = 0b01
    NORMAL = 0b11


class BME280(I2C_Module):
    def _read(self, *cmd) -> int:
        res = 0
        for c in cmd[::-1]:
            res = res << 8 | self.smbus.read_byte_data(self.address, c)
        return res

    def _read_bytes(self, *cmd) -> bytes:
        res = b""
        for c in cmd[::-1]:
            res += struct.pack("B", self.smbus.read_byte_data(self.address, c))
        return res

    def _read_block(self, *cmd) -> list[int]:
        res = []
        for c in cmd:
            res.append(self.smbus.read_byte_data(self.address, c))
        return res

    def _read_unsigned_short(self, *cmd):
        assert len(cmd) == 2
        return struct.unpack("H", self._read_bytes(*cmd))[0]

    def _read_signed_short(self, *cmd):
        assert len(cmd) == 2
        return struct.unpack("h", self._read_bytes(*cmd))[0]

    def _read_unsigned_char(self, *cmd):
        assert len(cmd) == 1
        return struct.unpack("B", self._read_bytes(*cmd))[0]

    def _read_signed_char(self, *cmd):
        assert len(cmd) == 1
        return struct.unpack("b", self._read_bytes(*cmd))[0]

    @cached_property
    def _dig_T1(self):
        return self._read_unsigned_short(0x88, 0x89)

    @cached_property
    def _dig_T2(self):
        return self._read_signed_short(0x8A, 0x8B)

    @cached_property
    def _dig_T3(self):
        return self._read_signed_short(0x8C, 0x8D)

    @cached_property
    def _dig_P1(self):
        return self._read_unsigned_short(0x8E, 0x8F)

    @cached_property
    def _dig_P2(self):
        return self._read_signed_short(0x90, 0x91)

    @cached_property
    def _dig_P3(self):
        return self._read_signed_short(0x92, 0x93)

    @cached_property
    def _dig_P4(self):
        return self._read_signed_short(0x94, 0x96)

    @cached_property
    def _dig_P5(self):
        return self._read_signed_short(0x96, 0x97)

    @cached_property
    def _dig_P6(self):
        return self._read_signed_short(0x98, 0x99)

    @cached_property
    def _dig_P7(self):
        return self._read_signed_short(0x9A, 0x9B)

    @cached_property
    def _dig_P8(self):
        return self._read_signed_short(0x9C, 0x9D)

    @cached_property
    def _dig_P9(self):
        return self._read_signed_short(0x9E, 0x9F)

    @cached_property
    def _dig_H1(self):
        return self._read_unsigned_char(0xA1)

    @cached_property
    def _dig_H2(self):
        return self._read_signed_short(0xE1, 0xE2)

    @cached_property
    def _dig_H3(self):
        return self._read_unsigned_char(0xE3)

    @cached_property
    def _dig_H4(self):
        return self._read_signed_short(0xE4, 0xE5)

    @cached_property
    def _dig_H5(self):
        return self._read_signed_short(0xE5, 0xE6)

    @cached_property
    def _dig_H6(self):
        return self._read_signed_char(0xE7)

    @property
    def _tfine(self):
        """ Some kind of high resolution temperature... """
        adc_T = self._adc_T
        var1 = ((adc_T >> 3) - (self._dig_T1 << 1)) * (self._dig_T2 >> 11)
        var2 = ((adc_T >> 4) - self._dig_T1) * (adc_T >> 4) - (self._dig_T1 >> 12) * (self._dig_T3 >> 14)
        return var1 + var2

    @property
    def _adc_T(self) -> int:
        block = self._read_block(0xFA, 0xFB, 0xFC)
        print(block)
        return (block[0] << 16 | block[1] << 8 | block[2]) >> 4

    @property
    def _adc_P(self) -> int:
        block = self._read_block(0xF7, 0xF8, 0xF9)
        return (block[0] << 16 | block[1] << 8 | block[2]) >> 4

    @property
    def _adc_H(self) -> int:
        return self._read(0xFD, 0xFE)

    @property
    def temperature(self) -> float:
        """ Outputs temperature in °C """
        return ((self._tfine * 5 + 128) >> 8) / 100

    @property
    def pressure(self) -> float:
        """ Outputs pressure in hPa """
        var1 = self._tfine - 128000
        var2 = var1 * var1 * self._dig_P6
        var2 += (var1 * self._dig_P5) << 17
        var2 += self._dig_P4 << 35
        var1 = ((var1 * var1 * self._dig_P3) >> 8) + ((var1 * self._dig_P2) << 12)
        var1 = (1 << 47 + var1) * self._dig_P1 >> 33
        if var1 == 0:
            return 0

        p = 1048576 - self._adc_P
        p = ((p << 31) - var2) * 3125 / var1
        var1 = (self._dig_P9 * (p >> 13) * (p >> 13)) >> 25
        var2 = (self._dig_P8 * p) >> 19
        p = ((p + var1 + var2) >> 8) + (self._dig_P7 << 4)

        pressure = p / 256 / 100
        return pressure

    @property
    def humidity(self) -> float:
        """ Outputs humidity %RH """
        return ((self._tfine * 5 + 128) >> 8) / 100

    def set_mode(self, mode: Mode):
        current_ctrl_meas = self._read_unsigned_char(0xF4)
        self.smbus.write_byte_data(self.address, 0xF4, current_ctrl_meas & (~0b11) | mode.value)

    @property
    def mode(self) -> Mode:
        return Mode(self._read_unsigned_char(0xF4) & 0b11)
