import time
from typing import Union

from apis.gpiozero_ext.led import LedDevice
from config import ScheduleItem
from modules import TimelineModule


class LightModule(TimelineModule):
    def __init__(
            self,
            timeline: list[ScheduleItem],
            enable_pin: str,
            pwm_pin: str,
            pwm_frequency: float,
            update_frequency: float = 30
    ):
        super().__init__(update_frequency=update_frequency, timeline=timeline)
        self.led = LedDevice(
            pwm_pin=pwm_pin,
            pwm_frequency=pwm_frequency,
            enable_pin=enable_pin
        )

    def setup(self, app: "MainBoard"):
        super().setup(app)
        self.led.on()
        self.led.brightness = 0

    def _update(self, t: float):
        super()._update(t)
        value = self.get_value_from_schedule(t)
        self.logger.debug(f"Light enabled: {self.led.is_enabled}, PWM Value: {self.led.brightness}")
        self.logger.debug(f"New light value: {value}")
        self.led.brightness = value
        self.app.log_telemetry({
            "duty_cycle": value,
            "led_enable": self.led.is_enabled,
            "time": t,
        },
            self
        )

    def test(self):
        super().test()
        pretest_brightness = self.led.brightness
        self.logger.debug("TESTING: Toggle On")
        self.led.enable.on()
        self.set_brightness(1)
        time.sleep(1)
        max_n = 1000
        # Fade in
        for i in range(max_n):
            self.set_brightness(i / max_n)
            time.sleep(5 / max_n)
        time.sleep(2)

        # Fade out
        for i in range(max_n):
            self.set_brightness(1 - i / max_n)
            time.sleep(5 / max_n)

        for _ in range(5):
            max_n = 100
            for i in range(max_n):
                self.set_brightness(i / max_n)
                time.sleep(0.5 / max_n)
            for i in range(max_n):
                self.set_brightness(1 - i / max_n)
                time.sleep(0.5 / max_n)

        # Reset to old state
        self.logger.debug(f"TESTING: Reset to {pretest_brightness}")
        self.set_brightness(pretest_brightness)

    def turn_lights_on(self):
        self.logger.debug("Lights on!")
        self.led.brightness = 1
        self.led.enable.on()

    def turn_lights_off(self):
        self.logger.debug("Lights off!")
        self.led.brightness = 0
        self.led.enable.off()

    def set_brightness(self, value: float):
        self.led.brightness = value

    def status_dict(self) -> dict[str, Union[str, int, float, bool]]:
        res = super().status_dict()
        res["pwm_pin"] = self.led.led_pwm.pwm_pin
        res["pwm_frequency"] = self.led.pwm_frequency
        res["pwm_duty_cycle"] = self.led.value
        return res
