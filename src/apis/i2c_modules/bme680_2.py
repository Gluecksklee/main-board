import struct
from enum import Enum
from functools import cached_property
from typing import Optional

from smbus import SMBus

from apis.i2c_modules import I2C_Module


class Mode(Enum):
    SLEEP = 0
    FORCE = 0b01
    NORMAL = 0b11


class BME680(I2C_Module):
    def __init__(self, address, *, smbus=None):
        super().__init__(address, smbus=smbus)
        # raise NotImplemented("Currently not implemented or checked... Do not use!")

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
    def _par_T1(self):
        return self._read_signed_short(0xE9, 0xEA)

    @cached_property
    def _par_T2(self):
        return self._read_signed_short(0x8A, 0x8B)

    @cached_property
    def _par_T3(self):
        return self._read_signed_char(0x8C)

    # ==================================

    @cached_property
    def _par_P1(self):
        return self._read_unsigned_short(0x8E, 0x8F)

    @cached_property
    def _par_P2(self):
        return self._read_signed_short(0x90, 0x91)

    @cached_property
    def _par_P3(self):
        return self._read_signed_short(0x92)

    @cached_property
    def _par_P4(self):
        return self._read_signed_short(0x94, 0x95)

    @cached_property
    def _par_P5(self):
        return self._read_signed_short(0x96, 0x97)

    @cached_property
    def _par_P6(self):
        return self._read_signed_char(0x99)

    @cached_property
    def _par_P7(self):
        return self._read_signed_char(0x98)

    @cached_property
    def _par_P8(self):
        return self._read_signed_short(0x9C, 0x9D)

    @cached_property
    def _par_P9(self):
        return self._read_signed_short(0x9E, 0x9F)

    @cached_property
    def _par_P10(self):
        return self._read_signed_short(0xA0)

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
    def _par_H6(self):
        return self._read_signed_char(0xE7)

    @property
    def _tfine(self):
        """ Some kind of high resolution temperature... """
        temp_adc = self._temp_adc
        var1 = ((temp_adc >> 3) - (self._par_T1 << 1))
        var2 = (var1 * self._par_T2) >> 11
        var3 = ((((var1 >> 1) * (var1 >> 1)) >> 12) * (self._par_T3 << 4)) >> 14
        return var2 + var3

    @property
    def _temp_adc(self) -> int:
        block = self._read_block(0x22, 0x23, 0x24)
        return (block[0] << 16 | block[1] << 8 | block[2]) >> 4

    @property
    def _press_adc(self) -> int:
        block = self._read_block(0x21, 0x20, 0x1F)
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
        var1 = (self._tfine >> 1) - 64000
        var2 = ((((var1 >> 2) * (var1 >> 2)) >> 11) * self._par_P6) >> 2
        var2 += (var1 * self._par_P5) << 1
        var2 = (var2 >> 2) + (self._par_P4 << 16)
        var1 = (((((var1 >> 2) * (var1 >> 2)) >> 13) * (self._par_P3 << 5)) >> 3) + ((self._par_P2 * var1) >> 1)
        var1 = var1 >> 18
        var1 = ((32768 + var1) * self._par_P1) >> 15

        press_comp = 1048576 - self._press_adc
        press_comp = (press_comp - (var2 >> 12)) * 3125
        if press_comp >= (1 << 30):
            press_comp = ((press_comp / var1) << 1)
        else:
            press_comp = (press_comp << 1) / var1

        var1 = (self._par_P9 * (((press_comp >> 3) * (press_comp >> 3)) >> 13) >> 12)
        var2 = ((press_comp >> 2) * self._par_P8) >> 13
        var3 = ((press_comp >> 8) * (press_comp >> 8) * (press_comp >> 8) * self._par_P10) >> 17

        press_comp = press_comp + ((var1 + var2 + var3 + (self._par_P7 << 7)) >> 4)

        return press_comp / 100  # Pascal -> Hectopascal

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

    @property
    def voc(self):
        return 0
