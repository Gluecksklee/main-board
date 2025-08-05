import time
from threading import Thread
from typing import Optional

from gpiozero import InputDevice, Device, GPIODeviceClosed

from apis.pwm import PWMDevice


class FanController(Device):
    def __init__(
            self,
            pwm_pin: str,
            pwm_frequency: float,
    ):
        super().__init__()
        self.pwm = PWMDevice(pwm_pin, frequency=pwm_frequency)
        self.pwm.value = 0
        self.pwm.on()
        self.pwm_pin = pwm_pin

    @property
    def pwm_frequency(self) -> float:
        return self.pwm.frequency

    def on(self):
        self.pwm.value = 1

    def off(self):
        self.pwm.value = 0

    def close(self):
        self.pwm.close()

    @property
    def closed(self):
        return self.pwm.closed

    @property
    def value(self):
        return self.pwm.value

    def set_fan(self, value: float):
        if not (0 <= value <= 1):
            raise ValueError(f"Only accepts values between 0..1. Got: {value}")

        self.pwm.value = value


class FanTacho(InputDevice):
    def __init__(self, tacho_pin: str):
        super().__init__(pin=tacho_pin)

        # State
        self._alarm_thread: Optional[Thread] = None
        self._alarm_values = []

    def on(self):
        self._alarm_thread = Thread(
            target=self._check_alarm_signal,
            name="Fan-Alarm-Thread",
            daemon=True
        )
        self._alarm_thread.start()

    def _clean_alarm_values(self, t=None):
        if t is None:
            t = time.perf_counter()

        t -= 1

        while len(self._alarm_values) > 0 and self._alarm_values[0] < t:
            self._alarm_values.pop(0)

    def _check_alarm_signal(self):
        last_value = False

        while not self.closed:
            t = time.perf_counter()
            self._clean_alarm_values(t=t)

            try:
                this_value = self.is_active
            except RuntimeError:
                continue
            except GPIODeviceClosed:
                break
            if this_value and not last_value:
                self._alarm_values.append(t)

            last_value = this_value

    @property
    def current_rpm(self) -> float:
        return len(self._alarm_values) * 30  # _alarm_values are in 2*rps -> * 60 / 2

    def close(self):
        super().close()
        if self._alarm_thread is not None:
            self._alarm_thread.join(1)


if __name__ == '__main__':
    fan = FanController("GPIO12", 20000)
    fan_tacho = FanTacho("GPIO16")
    fan.set_fan(0.5)
    time.sleep(4)
    fan.set_fan(1)
    time.sleep(4)
    fan.set_fan(0.1)
    time.sleep(10)
    fan.set_fan(0)
    fan.close()
