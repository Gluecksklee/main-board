from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from gpiozero.pins.pi import PiFactory
from gpiozero.pins.rpigpio import RPiGPIOFactory
from omegaconf import OmegaConf
from smbus import SMBus

from modules import GKBaseModule


@dataclass
class ScheduleItem:
    duration: int
    value: Any


OmegaConf.register_new_resolver("hex", lambda arg: int(arg, 16))
OmegaConf.register_new_resolver("path", lambda arg: Path(arg))
OmegaConf.register_new_resolver("tuple", lambda *args: tuple(args))
OmegaConf.register_new_resolver("schedule", lambda duration, value: ScheduleItem(duration, value))


@dataclass
class HydraConfig:
    # General Software
    smbus: SMBus
    cycle_delay: float  # Small delay preventing cpu from unnecessary overusing
    update_timeout: int  # Time after which a module receives a timeout
    multi_threading: bool

    # Data
    data_location: str

    # Modules
    modules: dict[str, GKBaseModule]

    # Raspberry Pi Configs
    pin_factory: PiFactory = RPiGPIOFactory()
    config_yaml: Optional[str] = None

    @classmethod
    def from_hydra(cls, **kwargs) -> "HydraConfig":
        config = cls(**kwargs)
        if config.modules is None:
            config.modules = {}

        return config
