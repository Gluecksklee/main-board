import logging

from sqlalchemy.engine import Engine
from sqlmodel import create_engine

from modules import GKBaseModule


def build_modules_list(**kwargs) -> list[GKBaseModule]:
    logger = logging.getLogger("BuildModulesList")
    modules = []
    errors = []
    for name, module in kwargs.items():
        # Requires GKBaseModules
        if not isinstance(module, GKBaseModule):
            logger.error(f"Not a module: {module}")
            errors.append(module)
            continue
        module.set_name(name)
        modules.append(module)

    # If error: Raise Exception
    if len(errors) != 0:
        raise TypeError(f"Found {len(errors)} invalid modules: {errors}")
    return modules


def create_database_engine(url, **kwargs) -> Engine:
    filtered_kwargs = {}
    for kwarg in kwargs:
        if kwarg.startswith("__"):
            continue
        filtered_kwargs[kwarg] = kwargs[kwarg]

    return create_engine(url=url, **filtered_kwargs)
