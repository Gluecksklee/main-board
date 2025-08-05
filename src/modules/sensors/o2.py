from typing import Union, Optional

from apis.i2c_modules.o2 import TB200B
from modules.sensors import SensorModule


class O2Module(SensorModule):
    def __init__(
            self,
            *,
            msp_address: int = 0x24,
            uart_buffer_size: int = 13,
            await_uart_timeout: float = 5,
            uart_ready_delay: float = 0.1,
            update_frequency: int = 10
    ):
        super().__init__(update_frequency=update_frequency)
        self.msp_address = msp_address
        self.await_uart_timeout = await_uart_timeout
        self.uart_buffer_size = uart_buffer_size
        self.uart_ready_delay = uart_ready_delay
        self.tb200b: Optional[TB200B] = None

    def setup(self, app: "MainBoard"):
        super().setup(app)
        self.tb200b = TB200B(
            msp_address=self.msp_address,
            await_uart_timeout=self.await_uart_timeout,
            uart_buffer_size=self.uart_buffer_size,
            uart_ready_delay=self.uart_ready_delay,
            smbus=app.smbus
        )

        light_state = self.tb200b.query_light_state()
        self.logger.info(f"Light state: {light_state}")
        if light_state:
            self.logger.info("Turning lights off.")
            self.tb200b.turn_off_lights()
            light_state = self.tb200b.query_light_state()
            self.logger.info(f"New light state: {light_state}")

    def sample(self) -> dict[str, Union[float, int]]:
        o2, range_, o2_ppb, temperature, humidity = self.tb200b.read_data()
        result = {
            "o2": o2,
            "o2_ppb": o2_ppb,
            "temperature": temperature,
            "humidity": humidity,
        }
        return result
