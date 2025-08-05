from pathlib import Path
from typing import Type, Optional

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel

from modules import GKBaseModule
from modules.camera import CameraModule
from modules.fan import FanControllerModule
from modules.light import LightModule
from modules.sensors.bme680 import BME680Module
from modules.sensors.co2 import CO2Module
from modules.sensors.fan_tacho import FanTachoMSPModule, FanTachoRPIModule
from modules.sensors.imu import IMUModule
from modules.sensors.internal import RPiTelemetryModule
from modules.sensors.msp import RebootLogger
from modules.sensors.o2 import O2Module
from utils.datamodel import CO2Data, EnvironmentalData, InternalData, FanTachoData, O2Data, MSPRebootData, RestartLog, \
    IMUData, PWMData, LightPWMData, CameraData
from utils.datatypes import TelemetryType
from utils.utils import get_time


class DatabaseModule(GKBaseModule):
    def __init__(
            self,
            *,
            engine: Engine,
            media_folder: str,
            update_frequency: float,
            db_path: Optional[str] = None
    ):
        super().__init__(update_frequency=update_frequency)
        self.logger.debug(f"Creating Database module with engine: {engine}")
        self.engine = engine
        SQLModel.metadata.create_all(engine)
        self._data_models = _get_all_datamodels()
        self._media_folder = media_folder
        self.media_path: Optional[Path] = None
        self.db_path = db_path

    def setup(self, app: "MainBoard"):
        super().setup(app)

        # Create media folder
        if self._media_folder is not None:
            self.media_path = app.data_location / self._media_folder
            self.logger.info(f"Creating media folder: {self.media_path.absolute()}")
            self.media_path.mkdir(exist_ok=True, parents=True)
        else:
            self.logger.warning(f"Media folder is None. Disable media logging for {self.__name__}")

        self._log_restart("setup")

    def _log_restart(self, event: str):
        # Log that experiment got started
        with Session(self.engine) as session:
            row = RestartLog(
                time=get_time(),
                event=event,
                config=str(self.app.config_yaml),
                git_version=self.app.git_version,
                git_branch=self.app.git_branch
            )
            self.logger.debug(f"Adding telemetry: {row}")
            session.add(row)
            session.commit()

    def reset(self):
        # Delete media
        if self.media_path is not None:
            for file in self.media_path.iterdir():
                if file.is_file():
                    file.unlink(missing_ok=True)

        # Delete database
        if self.db_path is not None:
            Path(self.db_path).unlink(missing_ok=True)
            SQLModel.metadata.create_all(self.engine)
        else:
            self.logger.warning("Resetting database for this engine not supported")

        self._log_restart("reset")

    def test(self):
        super().test()
        self.copy_database("/tests/db.sqlite")

    def log_media(self, name: str, data: bytes, origin: "GKBaseModule"):
        if self.media_path is not None:
            filepath = self.media_path / origin.__name__ / name
            self.logger.info(f"Save media at {filepath}")
            filepath.parent.mkdir(exist_ok=True, parents=True)
            filepath.write_bytes(data)

    def log_telemetry(self, data: TelemetryType, origin: "GKBaseModule"):
        with Session(self.engine) as session:
            row = self.parse_telemetry_data(data, origin)
            if row is None:
                return

            self.logger.debug(f"Adding telemetry: {row}")
            session.add(row)
            session.commit()

    def parse_telemetry_data(self, data: TelemetryType, origin: "GKBaseModule") -> Optional[SQLModel]:
        data_class = self._data_models.get(origin.__class__, None)
        if data_class is None:
            return
        if "time" not in data:
            self.logger.warning(f"Time not found in data for {origin.__name__}. Adding own timestamp.")
            data["time"] = get_time()
        row = data_class(**data, name=origin.__name__)
        return row

    def copy_database(self, path: str):
        if self.db_path is None:
            self.logger.warning("Cannot copy database, because there is no local path!")
            return

        path = Path(path)
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_bytes(Path(self.db_path).read_bytes())


def _get_all_datamodels() -> dict[Type[GKBaseModule], Type[SQLModel]]:
    return {
        CO2Module: CO2Data,
        BME680Module: EnvironmentalData,
        RPiTelemetryModule: InternalData,
        FanTachoMSPModule: FanTachoData,
        FanTachoRPIModule: FanTachoData,
        O2Module: O2Data,
        RebootLogger: MSPRebootData,
        IMUModule: IMUData,
        LightModule: LightPWMData,
        FanControllerModule: PWMData,
        CameraModule: CameraData,
    }
