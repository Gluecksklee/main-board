import time
from enum import Enum
from typing import Optional

from smbus import SMBus

from apis.i2c_modules import I2C_Module


class MSP_Command(Enum):
    VERSION = 0xFF

    # UART
    UART_READY = 0x00
    UART_SET_COMMAND = 0x01
    UART_RECEIVE_DATA = 0x02
    UART_SEND_COMMAND = 0x03
    UART_SET_RECEIVE = 0x04
    UART_RESET = 0x0A

    # Fan
    FAN_TACHO = 0x05
    FAN_PWM = 0x06

    # LED
    LED_ENABLE = 0x07
    LED_PWM = 0x08

    # Debug-LED
    DEBUG_LED_SET = 0x10
    DEBUG_LED_STATUS = 0x11
    DEBUG_LED_TOGGLE = 0x12

    # Reboot
    REBOOT_STATUS = 0x20
    REBOOT_CONTROL = 0x21
    REBOOT_GET_COUNTER = 0x22


class UARTTimeout(Exception):
    pass


class MSP(I2C_Module):

    def __init__(
            self,
            i2c_address,
            *,
            await_uart_timeout=10,
            uart_buffer_size=13,
            uart_ready_delay=0.1,
            smbus: Optional[SMBus]
    ):
        super().__init__(i2c_address, smbus=smbus)

        self.await_uart_timeout = await_uart_timeout
        self.uart_buffer_size = uart_buffer_size
        self.uart_ready_delay = uart_ready_delay

        try:
            self._read(MSP_Command.UART_READY)
            version = self.version()
            self.logger.info(f"MSP-Lib version: {version}")
        except IOError:
            raise RuntimeError(f"Unable to identify MSP at 0x{i2c_address:02x} (IOError)")

    def _write(self, cmd: MSP_Command, data: list[int]):
        return self.smbus.write_i2c_block_data(self.address, cmd.value, data)

    def _read(self, cmd: MSP_Command, expected_bytes: int = 1) -> list[int]:
        return self.smbus.read_i2c_block_data(self.address, cmd.value, expected_bytes)

    def version(self) -> int:
        version_low, version_high = self._read(MSP_Command.VERSION, 2)
        version = (version_high << 8) + version_low
        return version

    def _pad_uart_cmd(self, command: list[int]) -> list[int]:
        return command + [0] * (self.uart_buffer_size - len(command))

    def uart_send_receive(self, command: list[int], expected_receive: int) -> list[int]:
        self.logger.debug("UART")
        # Write Command to buffer
        self._write(MSP_Command.UART_SET_COMMAND, self._pad_uart_cmd(command))

        # Write number of expected received data to buffer
        self._write(MSP_Command.UART_SET_RECEIVE, [expected_receive])

        self.logger.debug(f"Send Command to UART to address {self.address}: {command}, {expected_receive}")
        # Send command (First action from MSP to UART)
        self._write(MSP_Command.UART_SEND_COMMAND, [len(command)])

        # Await UART return data
        self.logger.debug(f"Waiting for UART Ready")
        start_t = time.time()
        while self._read(MSP_Command.UART_READY)[0] == 0:
            # Check timeout
            if time.time() - start_t > self.await_uart_timeout:
                raise UARTTimeout()
            time.sleep(self.uart_ready_delay)

        self.logger.debug(f"UART Ready after {time.time() - start_t}s")

        # Receive data
        data = self._read(MSP_Command.UART_RECEIVE_DATA, self.uart_buffer_size)
        data = data[:expected_receive]
        self.logger.debug(f"Received data: {data}")
        return data

    # Fan
    def fan_tacho(self) -> float:
        """
        :return: RPM
        """
        self.logger.debug("Fan Tacho")
        fan_low, fan_high = self._read(MSP_Command.FAN_TACHO, 2)

        time_between_ticks = (fan_high << 8) + fan_low
        if time_between_ticks == 0 or time_between_ticks == 0xffff:
            return 0
        else:
            # 2 ticks per round
            # 1MHz MSP Frequency
            # (1 / (time_between_ticks * 2 / 1e6) -> rps; rps * 60 -> rpm
            return 1e6 / time_between_ticks * 30

    def fan_pwm(self, duty_cycle: int):
        self._write(MSP_Command.FAN_PWM, [duty_cycle, 0])  # Second value is dummy

    # Led
    def led_pwm(self, duty_cycle: int):
        self._write(MSP_Command.LED_PWM, [duty_cycle, 0])  # Second value is dummy

    def led_enable(self, value: bool):
        self._write(MSP_Command.LED_ENABLE, [int(value), 0])  # Second value is dummy

    # Debug Led
    def debug_led_toggle(self):
        self.logger.debug("Debug Led Toggle")
        self._read(MSP_Command.DEBUG_LED_TOGGLE, 0)

    def debug_led_status(self) -> bool:
        self.logger.debug("Debug Led Status")
        return self._read(MSP_Command.DEBUG_LED_STATUS, 1) == 1

    def debug_led_set(self, value: bool):
        self.logger.debug(f"Debug Led set to {value}")
        return self._write(MSP_Command.DEBUG_LED_SET, [int(value), 0])  # Second value is dummy

    # Reboot
    def reboot_status(self) -> tuple[bool, int]:
        data, _ = self._read(MSP_Command.REBOOT_STATUS, 2)
        active = (data & 0x80) >> 7
        state = data & 0x03
        return bool(active), state

    def reboot_counter(self) -> int:
        counter_low, counter_high = self._read(MSP_Command.REBOOT_GET_COUNTER, 2)
        counter = (counter_high << 8) + counter_low
        return counter

    def reboot_control(self, active: int, state: Optional[int] = None):
        """
        :param active: failure recovery active
        :param state:
            0 = init
            1 = run/wait for heartbeats
            2 = start reboot
            3 = timeout mode
        """
        data = 0
        if active:
            data |= 0x80
        if state is not None:
            data |= 0x04  # Force state overwrite
            data |= (state & 0x3)
        self._write(MSP_Command.REBOOT_CONTROL, [data, 0])
