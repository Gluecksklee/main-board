#!/usr/bin/env python3
import logging
import sys

import hydra
from hydra.utils import instantiate
from omegaconf import DictConfig, OmegaConf

from config import HydraConfig
from mainboard import MainBoard


@hydra.main(config_name="base_config", version_base=None, config_path="../config")
def main(cfg: DictConfig):
    config_yaml = OmegaConf.to_yaml(cfg)
    print(f"Python version: {sys.version}")
    print(config_yaml)

    config = instantiate(cfg)
    config.config_yaml = config_yaml
    assert isinstance(config, HydraConfig)

    # Disable 3rd party logger
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("picamera2").setLevel(logging.WARNING)

    mainboard = MainBoard(config)
    mainboard.start()


if __name__ == '__main__':
    main()
