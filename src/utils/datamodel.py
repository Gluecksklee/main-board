from typing import Optional

from sqlmodel import SQLModel, Field


class RestartLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    time: float
    event: str
    config: str
    git_version: str
    git_branch: str


class Telemetry(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    time: float
    name: str


class CO2Data(Telemetry, table=True):
    co2: float
    temperature: float
    pressure: float


class EnvironmentalData(Telemetry, table=True):
    temperature: float
    pressure: float
    humidity: float
    voc: float


class InternalData(Telemetry, table=True):
    cputemperature: float
    cpuloadavg: float
    freespace: float  # in percent
    ramusage: float  # in mb


class FanTachoData(Telemetry, table=True):
    rpm: float


class MSPRebootData(Telemetry, table=True):
    active: bool
    state: int
    counter: int


class O2Data(Telemetry, table=True):
    o2: float
    o2_ppb: float
    temperature: float
    humidity: float


class IMUData(Telemetry, table=True):
    ax: float
    ay: float
    az: float
    gx: float
    gy: float
    gz: float
    a: float
    temperature: float
    in_motion: bool


class PWMData(Telemetry, table=True):
    duty_cycle: float


class LightPWMData(Telemetry, table=True):
    duty_cycle: float
    led_enable: bool


class CameraData(Telemetry, table=True):
    file_metadata: str
    file_type: str
    file_name: str
    green: Optional[float] = None
    brightness: Optional[float] = None
    video_duration: Optional[float] = None
