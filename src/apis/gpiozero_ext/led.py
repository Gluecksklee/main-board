import logging
import time

from gpiozero import Device, OutputDevice

from apis.pwm import PWMDevice


class LedDevice(Device):
    def __init__(
            self,
            pwm_pin,
            pwm_frequency,
            enable_pin,
    ):
        super().__init__()

        self.led_pwm = PWMDevice(pwm_pin=pwm_pin, frequency=pwm_frequency)
        self.enable = OutputDevice(enable_pin)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.pwm_pin = pwm_pin

    @property
    def pwm_frequency(self) -> float:
        return self.led_pwm.frequency

    @property
    def value(self) -> float:
        return self.led_pwm.value

    def on(self):
        self.led_pwm.on()
        self.led_pwm.value = 1
        self.enable.on()

    def off(self):
        self.led_pwm.value = 0
        self.enable.off()

    def close(self):
        self.led_pwm.close()
        self.enable.close()

    @property
    def closed(self):
        return self.led_pwm.closed and self.enable.closed

    @property
    def brightness(self):
        return self.led_pwm.value

    @brightness.setter
    def brightness(self, value: float):
        if not (0 <= value <= 1):
            raise ValueError(f"Only accepts values between 0..1. Got: {value}")

        self.led_pwm.value = value

        if value == 0 and self.is_enabled:
            self.logger.debug("Disable led_enable")
            self.enable.off()
        elif value > 0 and not self.is_enabled:
            self.logger.debug("Enable led_enable")
            self.enable.on()

    @property
    def is_enabled(self):
        return self.enable.value


if __name__ == '__main__':
    led = LedDevice("GPIO13", 20000, "GPIO6")
    led.set_led_value(0.5)
    time.sleep(4)
    led.set_led_value(1)
    time.sleep(4)
    led.set_led_value(0.1)
    time.sleep(10)
    led.set_led_value(0)
    led.close()
