import datetime
import json
import logging
import signal
import subprocess
import time
import traceback
from pathlib import Path
from threading import Thread
from typing import Union, Optional

from gpiozero import Device

from config import HydraConfig
from modules import GKBaseModule
from modules.fan import FanControllerModule
from modules.light import LightModule
from utils.datatypes import TelemetryType
from utils.utils import get_time, get_git_version, get_git_branch


class MainModule(GKBaseModule):
    def __init__(self):
        super().__init__(10000)
        self.set_name("main")


class MainBoard:
    def __init__(self, config: HydraConfig):
        super().__init__()
        self.logger = logging.getLogger("klee.main")
        self.logger.debug("Logger initialized")
        self.logger.debug(f"Using config `{config.__class__.__name__}`")

        # Config
        self.config_yaml = config.config_yaml  # Save full configuration
        self.smbus = config.smbus
        self.cycle_delay = config.cycle_delay  # Seconds
        if self.cycle_delay >= 1:
            self.logger.warning(f"Cycle delay is >= 1 second ({self.cycle_delay})")
        self.update_timeout = int(config.update_timeout)  # Seconds
        if self.update_timeout < 1:
            self.logger.warning(f"Update timeout is < 1 seconds (int({config.update_timeout}) -> {self.update_timeout})")
        self.data_location = Path(config.data_location)
        self.data_location.mkdir(exist_ok=True, parents=True)
        Device.pin_factory = config.pin_factory
        self.git_version = get_git_version()
        self.git_branch = get_git_branch()
        self.logger.info(f"Running on git version: {self.git_version}")
        self.logger.info(f"Running on git branch: {self.git_branch}")

        # Modules
        self.main_module = MainModule()
        self.modules: list[GKBaseModule] = config.modules or []
        if len(self.modules) == 0:
            self.logger.warning(f"No modules loaded!")
        self.logger.debug(f"{len(self.modules)} modules loaded.")

        # Multithreading
        self.multithreading_activated = config.multi_threading
        self.logger.debug(f"Multithreading: {self.multithreading_activated}")
        if self.multithreading_activated:
            self.running_threads: dict[str, Thread] = {}
            self.update_module = self._update_module_multi_thread
        else:
            self.update_module = self._update_module_single_thread

        # Set signal handler
        def raise_timeout(signum, frame):
            self.logger.exception("TIMEOUT")
            raise TimeoutError()

        def set_quit(signum, frame):
            self.logger.warning(f"Received {signal.getsignal(signum)}! Quitting now...")
            self.running = False

        signal.signal(signal.SIGALRM, raise_timeout)
        signal.signal(signal.SIGTERM, set_quit)

        # Mainboard state
        self.running: bool = True
        self.quit_time: Optional[float] = None
        self.start_time: float = get_time()
        self._updates_per_second: int = 0

    def start(self):
        try:
            self.initialize()
            self.update_loop()
        except KeyboardInterrupt:
            self.logger.warning("Keyboard Interrupt detected. Shutting down program...")
        except BaseException as e:
            self.logger.error(f"Exception raised! {e}. Trying to shut down gracefully")
            self.destroy()
            raise

        self.destroy()

    def initialize(self):
        self.logger.debug(f"Initializing modules")
        i = 0
        for module in self.modules:
            try:
                module.setup(self)
                i += 1
            except KeyboardInterrupt:
                raise
            except BaseException as e:
                module.disable()
                self.logger.error(f"Error while initializing {module} ({e})")

        self.logger.info(f"Initialize complete. ({i}/{len(self.modules)})")

    def destroy(self):
        self.logger.debug(f"Destroying modules")
        self.running = False
        for module in self.modules:
            try:
                module.destroy()
            except KeyboardInterrupt:
                raise
            except BaseException as e:
                self.logger.error(f"Error while destroying {module} ({e})")

    def update_loop(self):
        self.logger.debug(f"Starting update loop")
        full_second = 0
        updates = 0
        while self.running:
            t = get_time()
            # Check whether shutdown is due
            if self.quit_time is not None and t > self.quit_time:
                self.running = False
                break

            # Calculate updates per second
            this_full_second = t // 1
            if this_full_second != full_second:
                full_second = this_full_second
                self._updates_per_second = updates
                updates = 0
            updates += 1

            # Update modules
            for module in self.modules:
                self.update_module(module, t)

            # Reduce CPU load with small cycle_delay
            if self.cycle_delay is not None:
                time.sleep(self.cycle_delay)

    def log_telemetry(self, data: TelemetryType, origin: "GKBaseModule"):
        for module in self.modules:
            if module.is_enabled and module != origin:
                try:
                    module.log_telemetry(data, origin=origin)
                except KeyboardInterrupt:
                    raise
                except BaseException as e:
                    self.logger.error(f"Error while logging telemetry to {module} (data={data}, Exception={e})")

    def log_media(self, name: str, data: bytes, origin: "GKBaseModule"):
        for module in self.modules:
            if module.is_enabled and module != origin:
                try:
                    module.log_media(name, data, origin=origin)
                except KeyboardInterrupt:
                    raise
                except BaseException as e:
                    self.logger.error(f"Error while logging media to {module} ({e})")

    @property
    def updates_per_second(self) -> int:
        return self._updates_per_second

    def _update_module_single_thread(self, module: GKBaseModule, t: float):
        signal.alarm(self.update_timeout)
        module.update(t)
        signal.alarm(0)

    def _update_module_multi_thread(self, module: GKBaseModule, t: float):
        if not module.expects_next_execution(t):
            return

        thread_name = module.__name__

        # Multithread Thread
        if thread_name in self.running_threads:
            self.logger.warning(f"Thread {thread_name} already running!")
            return

        def remove_thread_on_exit():
            self.logger.debug(f"Starting thread for module `{thread_name}`")
            signal.alarm(self.update_timeout)
            try:
                module.update(t)
                signal.alarm(0)
            except KeyboardInterrupt:
                self.running_threads.pop(thread_name)
                raise

            self.running_threads.pop(thread_name)
            self.logger.debug(f"Thread finished for module `{thread_name}`")

        thread = Thread(target=remove_thread_on_exit, daemon=True)
        self.running_threads[thread_name] = thread
        thread.start()

    def status_dict(self) -> dict[str, Union[str, int, float, bool]]:
        modules_status = {}
        for module in self.modules:
            modules_status[module.__name__] = module.status_dict()

        return {
            "modules": modules_status,
            "time": get_time(),
            "start_time": self.start_time,
            "running": self.running,
            "multithreading": self.multithreading_activated,
            "cycle_delay": self.cycle_delay,
            "data_location": str(self.data_location.absolute()),
            "git_version": self.git_version,
            "git_branch": self.git_branch,
            "quit_time": self.quit_time,
        }

    def receive_command(self, command_type: str, data: str):
        """
        Same as self._receive_command, but wraps with try/except
        """
        try:
            self._receive_command(command_type.lower(), data)
        except KeyboardInterrupt:
            raise
        except:
            self.logger.error(f"Executing {command_type} failed with data \"{data}\"")
            self.logger.error(traceback.format_exc())

    def _receive_command(self, command_type: str, data: str):
        tc_handlers = {
            "database": self._tc_download_database,
            "status": self._tc_get_current_status,
            "test": self._tc_test,
            "reset": self._tc_reset,
            "quit": self._tc_quit,
            "abort_quit": self._tc_abort_quit,
            "camera": self._tc_camera_image,
            "video": self._tc_camera_video,
            "debug_led_enable": self._tc_debug_led_enable,
            "shell": self._tc_shell,
        }

        tc_handler = tc_handlers.get(command_type, None)

        if tc_handler is None:
            self.logger.error(f"Could not find handler for {command_type}.")
            return
        self.logger.info(f"Received command: {command_type}")
        tc_handler(data)
        return

    def get_module(self, module_name) -> Optional[GKBaseModule]:
        for module in self.modules:
            if module.__name__ == module_name:
                return module
        return None

    def _tc_download_database(self, data: str):
        # Get db and spacetango looger
        db = self.get_module("database")
        if db is None:
            self.logger.warning("No database module loaded")
            return

        if not data.strip():
            # Get default path for saving
            spacetango_logger = self.get_module("tango")
            if spacetango_logger is None:
                self.logger.warning("No SpaceTangoLogger module loaded")
                return
            from modules.logger.spacetango_logger import SpaceTangoLogger
            assert isinstance(spacetango_logger, SpaceTangoLogger)

            data = spacetango_logger.media_path / f"db_{datetime.datetime.now():%Y%m%d_%H%M%S}.sqlite"

        from modules.logger.database import DatabaseModule
        assert isinstance(db, DatabaseModule)
        self.logger.info(f"DATA DB: {data}")
        db.copy_database(data)

    def _tc_get_current_status(self, data: str):
        if not data:
            # Get default path for saving
            spacetango_logger = self.get_module("tango")
            if spacetango_logger is None:
                self.logger.warning("No SpaceTangoLogger module loaded")
                return
            from modules.logger.spacetango_logger import SpaceTangoLogger
            assert isinstance(spacetango_logger, SpaceTangoLogger)

            data = spacetango_logger.media_path / f"status_{datetime.datetime.now():%Y%m%d_%H%M%S}.json"

        status = self.status_dict()
        path = Path(data)
        self.logger.info(f"Save current status at {path}.")
        path.parent.mkdir(exist_ok=True, parents=True)
        with path.open("w", encoding="latin") as d:
            json.dump(status, d, indent=2)

    def _tc_test(self, data: str):
        for module in self.modules:
            module.test()

    def _tc_reset(self, data: str):
        for module in self.modules:
            try:
                module.reset()
            except:
                pass

        subprocess.Popen("rm -f /download/*", shell=True)
        subprocess.Popen("systemctl restart greenhouse.service", shell=True)

    def _tc_quit(self, data: str):
        timer = 0
        if data:
            try:
                timer = float(data)
            except ValueError:
                self.logger.warning(f"Could not interpret data as float. Shutdown aborted! ({data})")
                self.quit_time = None

        if timer < 0:
            self.quit_time = None
            self.logger.warning("Shutdown aborted!")
        else:
            shutdown_time = get_time() + timer
            shutdown_date = datetime.datetime.fromtimestamp(shutdown_time)
            self.logger.warning(f"Shutdown scheduled in {timer} seconds ({shutdown_date :%Y-%m-%d %H:%M:%S.%f})!")
            self.quit_time = shutdown_time

    def _tc_abort_quit(self, data: str):
        self.quit_time = None
        self.logger.warning(f"Shutdown aborted!")

    def _tc_camera_image(self, data: str):
        camera = self.get_module("camera")
        if camera is None:
            self.logger.warning("Camera does not exist.")
            return

        print(f"DATA: {data}")
        if data.strip():
            filename = data.strip()
            if not filename.endswith(camera.file_extension):
                filename += f".{camera.file_extension}"
        else:
            timestamp_str = f"{get_time():.3f}".replace(".", "_")
            filename = f"{timestamp_str}.{camera.file_extension}"

        camera.next_image_filename = filename

    def _tc_camera_video(self, data: str):
        camera = self.get_module("camera")
        if camera is None:
            self.logger.warning("Camera does not exist.")
            return

        if data:
            duration = float(data)
        else:
            duration = camera.min_video_duration

        camera.video_until = get_time() + duration

    def _tc_debug_led_enable(self, data: str):
        heartbeat = self.get_module("heartbeat")
        if heartbeat is None:
            self.logger.warning("Heartbeat does not exist")
            return

        if data.lower() in ["1", "true", "on"]:
            heartbeat.debug_led_enable.on()
        elif data.lower() in ["0", "false", "off"]:
            heartbeat.debug_led_enable.off()
        else:
            heartbeat.debug_led_enable.toggle()

    def _tc_shell(self, data: str):
        script_path = self.data_location / "shell" / datetime.datetime.now().strftime("shell_%Y%m%d_%H%M%s.sh")
        script_path.parent.mkdir(exist_ok=True, parents=True)

        script_path.write_text(data)

        process = subprocess.run(["sh", script_path.absolute()], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.log_media(script_path.name, data.encode("utf-8"), self.main_module)
        self.log_media(f"{script_path.name}.stdout", process.stdout, self.main_module)
        self.log_media(f"{script_path.name}.stderr", process.stderr, self.main_module)
