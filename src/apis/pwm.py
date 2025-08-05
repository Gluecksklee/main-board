from utils.utils import GKBase
from rpi_hardware_pwm import HardwarePWM

PWM_GPIO_MAPPING = {
    "GPIO12": 0,
    "GPIO13": 1,
}


class PWMDevice(GKBase):
    def __init__(
            self,
            pwm_pin: str,
            frequency: float
    ):
        super().__init__()
        pwm_channel = PWM_GPIO_MAPPING.get(pwm_pin, None)
        if pwm_channel is None:
            raise ValueError(f"Could not find {pwm_pin} in PWM Mapping ({PWM_GPIO_MAPPING})")

        self.logger.debug(f"Create Hardware PWM for channel {pwm_channel} with frequency {frequency}")
        self.pwm = HardwarePWM(pwm_channel=pwm_channel, hz=frequency)
        self.frequency = frequency
        self._value = 0
        self.closed = True
        self.pwm_pin = pwm_pin

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value: float):
        self._value = value
        self.logger.debug(f"Change duty cycle to {value}")
        self.pwm.change_duty_cycle(value * 100)

    def on(self):
        self._value = 1
        self.pwm.start(100)
        self.closed = False

    def close(self):
        self._value = 0
        self.pwm.stop()
        self.closed = True
