import time
from typing import Optional

from modules import GKBaseModule
from gpiozero import OutputDevice, LED


class MockLED:
    def on(self):
        pass

    def off(self):
        pass

    def toggle(self):
        pass

    def close(self):
        pass


class HeartbeatModule(GKBaseModule):
    def __init__(
            self,
            update_frequency: float,
            heartbeat_pin: str,
            led_pin: Optional[str] = None,
            debug_led_enable: Optional[str] = None,
    ):
        super().__init__(update_frequency=update_frequency)
        self.heartbeat = OutputDevice(heartbeat_pin)

        # Debug LED
        # This is used to show the heartbeat if provided (e.g. in debug mode)
        if led_pin is not None:
            self.led = LED(led_pin)
            self.logger.debug(f"Using Pin {led_pin} for debug led")
        else:
            self.led = MockLED()
            self.logger.debug("Using MockLED for debug led")

        # Debug LED enable.
        # If False -> Debug LEDs are turned off
        # If True -> Debug LEDs act corresponding to their designed behaviour
        if debug_led_enable is not None:
            self.debug_led_enable = LED(debug_led_enable)
            self.logger.debug(f"Using Pin {debug_led_enable} for debug led enable")
        else:
            self.debug_led_enable = MockLED()
            self.logger.debug("Using MockLED for debug led enable")

    def setup(self, app: "MainBoard"):
        super().setup(app)
        self.led.on()
        self.debug_led_enable.off()

    def test(self):
        super().test()
        n = 10
        for i in range(n):
            self.heartbeat.on()
            self.led.toggle()
            self.heartbeat.off()
            time.sleep(1 / n)

    def destroy(self):
        super().destroy()
        self.led.close()
        self.heartbeat.close()

    def _update(self, t: float):
        super()._update(t)
        self.heartbeat.on()
        self.led.toggle()
        self.heartbeat.off()
