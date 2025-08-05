import abc
import json
import logging
import subprocess
import time

import numpy as np


class GKBase(abc.ABC):
    def __init__(self):
        self.__name__ = self.__class__.__qualname__

        # Config
        self.logger = logging.getLogger(self.__class__.__qualname__)
        self.logger.debug(f"Initializing module {self.__class__.__qualname__}")


def get_time() -> float:
    # Time in seconds
    return time.time()


def get_git_version() -> str:
    try:
        stdout = subprocess.run(["git", "describe"], stdout=subprocess.PIPE)
        return stdout.stdout.decode("latin")
    except:
        return "GIT_NOT_FOUND"


def get_git_branch() -> str:
    try:
        stdout = subprocess.run(["git", "branch", "--show-current"], stdout=subprocess.PIPE)
        return stdout.stdout.decode("latin")
    except:
        return "GIT_NOT_FOUND"


def json_dump_compact(data) -> str:
    return json.dumps(data, separators=(',', ':'))
