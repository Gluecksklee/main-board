import abc
import datetime
import logging
import time
from typing import Optional, Union

from utils.datatypes import TelemetryType
from utils.utils import GKBase


class GKBaseModule(GKBase, abc.ABC):
    def __init__(self, update_frequency: float):
        super().__init__()
        # Config
        self.update_frequency = update_frequency

        # State
        self.is_enabled = True
        self.last_execution_time = 0
        self.last_execution_duration = None
        self._app: Optional["MainBoard"] = None

    def set_name(self, name: str):
        self.__name__ = name
        self.logger = logging.getLogger(f"{self.__class__.__qualname__} ({self.__name__})")

    def setup(self, app: "MainBoard"):
        self.logger.debug(f"Setup {self.__class__.__qualname__} ({self.__name__})")
        self._app = app

    def destroy(self):
        self.logger.debug(f"Destroy {self.__class__.__qualname__} ({self.__name__})")

    def update(self, t: float) -> bool:
        """
        Updates the module if
        - module is enabled
        - module was not updated in the last `update_frequency` seconds

        :return True if update function called, otherwise False
        """
        if self.expects_next_execution(t):
            try:
                t1 = time.perf_counter()
                self._update(t)
                t2 = time.perf_counter()
                self.last_execution_duration = t2 - t1
            except KeyboardInterrupt:
                raise
            except BaseException as e:
                self.logger.error(f"Exception raised in {self.__name__} ({e})")
            self.last_execution_time = t
            return True
        return False

    def _update(self, t: float):
        self.logger.debug(f"Update (t={t})")

    def log_telemetry(self, data: TelemetryType, origin: "GKBaseModule"):
        pass

    def log_media(self, name: str, data: bytes, origin: "GKBaseModule"):
        pass

    def test(self):
        self.logger.info(f"========== Testing {self.__name__}... ==========")

    def reset(self):
        pass

    def status_dict(self) -> dict[str, Union[str, int, float, bool]]:
        return {
            "__class__": self.__class__.__name__,
            "enabled": self.is_enabled,
            "last_execution_time": self.last_execution_time,
            "last_execution_duration": self.last_execution_duration,
            "update_frequency": self.update_frequency,
        }

    @property
    def app(self) -> "MainBoard":
        if self._app is None:
            raise ValueError(f"{self.__name__} not initialized with app yet! Please call `.setup(app)`.")
        return self._app

    @property
    def app_running(self) -> bool:
        return self.app.running

    def expects_next_execution(self, t: float) -> bool:
        return self.is_enabled and t - self.last_execution_time > self.update_frequency

    def enable(self):
        self.logger.info(f"Module `{self.__name__}` got enabled")
        self.is_enabled = True

    def disable(self):
        self.logger.warning(f"Module `{self.__name__}` got disabled")
        self.is_enabled = False


class TimelineModule(GKBaseModule, abc.ABC):
    def __init__(self, update_frequency: float, timeline: list["ScheduleItem"]):
        super().__init__(update_frequency)
        self.timeline = timeline
        self.total_timeline_duration: float = sum(map(lambda item: item.duration, self.timeline))

        self.logger.debug(f"Total timeline duration: {datetime.timedelta(seconds=self.total_timeline_duration)}")

    def get_value_from_schedule(self, t):
        mode_timestamp = t % self.total_timeline_duration
        self.logger.debug(f"Mode Timestamp: {mode_timestamp}")
        sum_t = 0
        for item in self.timeline:
            sum_t += item.duration
            if sum_t >= mode_timestamp:
                return item.value

        raise ValueError(
            f"Mode not found. This should never happen! "
            f"Someone messed up the calculation for total_timeline_duration ({self.total_timeline_duration})"
        )
