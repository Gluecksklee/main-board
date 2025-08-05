from typing import Optional

from apis.gpiozero_ext.fan import FanTacho
from apis.i2c_modules.msplib import MSP
from modules.sensors import SensorModule
from utils.datatypes import TelemetryType


class FanTachoRPIModule(SensorModule):
    def __init__(
            self,
            *,
            tacho_pin: str,
            update_frequency: float,
    ):
        super().__init__(update_frequency)
        self.logger.debug(f"Initializing FanTacho with pin {tacho_pin}")
        self.tacho = FanTacho(
            tacho_pin=tacho_pin,
        )

    def setup(self, app: "MainBoard"):
        super().setup(app)
        self.tacho.on()

    def destroy(self):
        super().destroy()
        self.tacho.close()

    def sample(self) -> TelemetryType:
        return {
            "rpm": self.tacho.current_rpm
        }


class FanTachoMSPModule(SensorModule):
    def __init__(
            self,
            *,
            msp_address: str,
            update_frequency: float,
    ):
        super().__init__(update_frequency)
        self.logger.debug(f"Initializing FanTacho over MSP with address 0x{msp_address:x}")
        self.msp_address = msp_address
        self.msp: Optional[MSP] = None

    def setup(self, app: "MainBoard"):
        super().setup(app)
        self.msp = MSP(self.msp_address, smbus=app.smbus)

    def destroy(self):
        super().destroy()

    def sample(self) -> TelemetryType:
        return {
            "rpm": self.msp.fan_tacho()
        }
