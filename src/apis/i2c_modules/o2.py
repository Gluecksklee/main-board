import time
from enum import Enum
from typing import Optional

from smbus import SMBus

from apis.i2c_modules import I2C_Module
from apis.i2c_modules.msplib import MSP
from utils.utils import get_time


class TB200B(I2C_Module):

    def __init__(
            self,
            msp_address,
            *,
            await_uart_timeout: float = 10,
            uart_buffer_size: int = 13,
            uart_ready_delay: float = 0.1,
            smbus: Optional[SMBus] = None
    ):
        super().__init__(msp_address, smbus=smbus)

        self.await_uart_timeout = await_uart_timeout
        self.uart_buffer_size = uart_buffer_size
        self.uart_ready_delay = uart_ready_delay

        self.msp = MSP(
            i2c_address=msp_address,
            await_uart_timeout=await_uart_timeout,
            uart_buffer_size=uart_buffer_size,
            uart_ready_delay=uart_ready_delay,
            smbus=smbus
        )

        self._o2: Optional[float] = None
        self._o2_range: Optional[float] = None
        self._o2_ppb: Optional[float] = None
        self._humidity: Optional[float] = None
        self._temperature: Optional[float] = None
        self._timestamp: Optional[float] = None

    def sample(self):
        self.logger.debug("Sample")

        o2, range_, o2_ppb, temperature, humidity = self.read_data()
        self._o2 = o2
        self._temperature = temperature
        self._humidity = humidity
        self._o2_range = range_
        self._o2_ppb = o2_ppb
        self._timestamp = get_time()

    # Properties
    @property
    def o2(self) -> float:
        if self._o2 is None:
            self.sample()
        return self._o2

    @property
    def o2_ppb(self) -> float:
        if self._o2_ppb is None:
            self.sample()
        return self._o2_ppb

    @property
    def o2_range(self) -> float:
        if self._o2_range is None:
            self.sample()
        return self._o2_range

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
    def humidity(self) -> float:
        if self._humidity is None:
            self.sample()
        return self._humidity

    # Functions
    def switch_to_active_upload(self):
        """
        Command 1
        """
        self.msp.uart_send_receive([0xff, 0x01, 0x78, 0x40, 0x00, 0x00, 0x00, 0x00, 0x47], 1)

    def switch_to_passive_upload(self):
        """
        Command 2
        """
        self.msp.uart_send_receive([0xff, 0x01, 0x78, 0x41, 0x00, 0x00, 0x00, 0x00, 0x47], 1)

    def get_module_information(self):
        """
        Command 3
        """
        self.msp.uart_send_receive([0xD1])

    def read_o2_concentration(self) -> tuple[int, int, int]:
        """
        Command 5
        """
        data = self.msp.uart_send_receive([0xff, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79], 9)
        _, cmd, o2_high, o2_low, range_high, range_low, o2_ppb_high, o2_ppb_low, parity = data

        assert cmd == 0x86

        o2 = (o2_high << 8) + o2_low
        range_ = (range_high << 8) + range_low
        o2_ppb = (o2_ppb_high << 8) + o2_ppb_low
        return o2, range_, o2_ppb

    def read_data(self) -> tuple[int, int, int, float, float]:
        """
        Command 6
        """
        data = self.msp.uart_send_receive([0xff, 0x00, 0x87, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79], 13)
        _, cmd, o2_high, o2_low, range_high, range_low, o2_ppb_high, o2_ppb_low, temp_high, temp_low, hum_high, hum_low, parity = data

        assert cmd == 0x87

        o2 = (o2_high << 8) + o2_low
        range_ = (range_high << 8) + range_low
        o2_ppb = (o2_ppb_high << 8) + o2_ppb_low
        temperature = ((temp_high << 8) + temp_low) / 100
        humidity = ((hum_high << 8) + hum_low) / 100
        return o2, range_, o2_ppb, temperature, humidity

    def turn_off_lights(self):
        """
        Command ?
        """
        data1, data2 = self.msp.uart_send_receive([0xff, 0x01, 0x88, 0x00, 0x00, 0x00, 0x00, 0x00, 0x77], 2)
        assert data1 == 0x4F
        assert data2 == 0x4B

    def turn_on_lights(self):
        """
        Command ?
        """
        data1, data2 = self.msp.uart_send_receive([0xff, 0x01, 0x89, 0x00, 0x00, 0x00, 0x00, 0x00, 0x76], 2)
        assert data1 == 0x4F
        assert data2 == 0x4B

    def query_light_state(self) -> bool:
        """
        Command ?
        """
        _, cmd, state, _, _, _, _, _, checksum = self.msp.uart_send_receive(
            [0xff, 0x01, 0x8A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x75], 9)
        assert cmd == 0x8A

        return state == 1
