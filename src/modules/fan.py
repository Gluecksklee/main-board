import time
from typing import Union

from apis.gpiozero_ext.fan import FanController
from config import ScheduleItem
from modules import TimelineModule


class FanControllerModule(TimelineModule):
    def __init__(
            self,
            pwm_pin: str,
            pwm_frequency: float,
            timeline: list[ScheduleItem],
            update_frequency: float = 10
    ):
        super().__init__(update_frequency=update_frequency, timeline=timeline)
        self.fan = FanController(
            pwm_pin=pwm_pin,
            pwm_frequency=pwm_frequency,
        )

    def setup(self, app: "MainBoard"):
        super().setup(app)
        self.fan.off()

    def destroy(self):
        super().destroy()
        self.fan.close()

    def test(self):
        super().test()
        pretest_fan = self.fan.value

        self.logger.debug("TESTING: Toggle On")
        self.set_fan(1)
        time.sleep(3)

        self.logger.debug("TESTING: Set 75%")
        self.set_fan(.75)
        time.sleep(3)

        self.logger.debug("TESTING: Set 50%")
        self.set_fan(.5)
        time.sleep(3)

        self.logger.debug("TESTING: Set 0%")
        self.set_fan(0)
        time.sleep(3)

        # Reset to old state
        self.logger.debug(f"TESTING: Reset to {pretest_fan}")
        self.set_fan(pretest_fan)

    def _update(self, t: float):
        super()._update(t)
        value = self.get_value_from_schedule(t)
        self.set_fan(value)
        self.app.log_telemetry({"duty_cycle": value, "time": t}, self)

    def set_fan(self, value: float) -> float:
        self.logger.debug(f"Setting fan to {value}.")
        self.fan.set_fan(value)
        return value

    def status_dict(self) -> dict[str, Union[str, int, float, bool]]:
        res = super().status_dict()
        res["pwm_pin"] = self.fan.pwm_pin
        res["pwm_frequency"] = self.fan.pwm_frequency
        res["pwm_duty_cycle"] = self.fan.value
        return res
