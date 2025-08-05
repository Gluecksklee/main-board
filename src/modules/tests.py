import time

from modules import GKBaseModule


class TimeoutTest(GKBaseModule):
    def __init__(
            self,
            update_frequency: float,
            timeout: float,
    ):
        super().__init__(update_frequency=update_frequency)
        self.timeout = timeout

    def setup(self, app: "MainBoard"):
        super().setup(app)

    def _update(self, t: float):
        super()._update(t)
        time.sleep(self.timeout)
