import logging
from typing import Optional

from smbus import SMBus


class I2C_Module:
    def __init__(self, address, *, smbus: Optional[SMBus] = None):
        self.address = address
        self.smbus = smbus or SMBus(1)
        self.logger = logging.getLogger(self.__class__.__name__)
