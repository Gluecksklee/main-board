from typing import Optional

from apis.gpiozero_ext.fan import FanTacho
from apis.i2c_modules.msplib import MSP
from modules.sensors import SensorModule
from utils.datatypes import TelemetryType


class RebootLogger(SensorModule):
    def __init__(
            self,
            *,
            msp_address: str,
            update_frequency: float,
    ):
        super().__init__(update_frequency)
        self.logger.debug(f"Initializing RebootLogger with address 0x{msp_address:x}")
        self.msp_address = msp_address
        self.msp: Optional[MSP] = None

    def setup(self, app: "MainBoard"):
        super().setup(app)
        self.msp = MSP(self.msp_address, smbus=app.smbus)
        self.msp.debug_led_set(False)

    def destroy(self):
        super().destroy()

    def sample(self) -> TelemetryType:
        active, state = self.msp.reboot_status()
        counter = self.msp.reboot_counter()
        return {
            "active": active,
            "state": state,
            "counter": counter
        }
