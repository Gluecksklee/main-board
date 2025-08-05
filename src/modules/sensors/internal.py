import os
import shutil
from typing import Union
import psutil

from gpiozero import LoadAverage

from modules.sensors import SensorModule


class RPiTelemetryModule(SensorModule):
    @staticmethod
    def get_cpu_temp() -> float:
        # https://helloacm.com/how-to-monitor-the-cpu-temperature-of-raspberry-pi-using-python-script/
        cpu_temp = os.popen("vcgencmd measure_temp").readline()
        cpu_temp = float(cpu_temp.lstrip("temp=").rstrip("'C\n"))

        return cpu_temp

    @staticmethod
    def get_cpu_usage() -> float:
        return LoadAverage(minutes=1).load_average

    @staticmethod
    def get_ram_usage() -> float:
        # https://psutil.readthedocs.io/en/latest/index.html?highlight=virtual_memory#psutil.virtual_memory
        return psutil.virtual_memory().available / 1048576

    @staticmethod
    def get_disk_usage() -> float:
        """ sd card free space in percent """
        total, used, free = shutil.disk_usage("/")
        return free / total
    @staticmethod
    def get_free_space() -> float:
        """ sd card free space in mb """
        total, used, free = shutil.disk_usage("/")
        return free / 1048576

    def sample(self) -> dict[str, Union[float, int]]:
        return {
            "cputemperature": self.get_cpu_temp(),
            "cpuloadavg": self.get_cpu_usage(),
            "freespace": self.get_free_space(),
            "ramusage": self.get_ram_usage()
            # "diskusage": self.get_disk_usage(),
            # "updates_per_second": self.app.updates_per_second
        }
