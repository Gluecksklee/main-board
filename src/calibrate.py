import json
import os
import pwd
import socket
import subprocess
import time
from pathlib import Path

import cutie
import tqdm
from smbus import SMBus

from apis.i2c_modules.MPU6500 import MPU6500
from apis.i2c_modules.bme680_lib import BME680
from apis.i2c_modules.ee895 import EE895
from apis.i2c_modules.o2 import TB200B

i2cbus = SMBus(1)


def calibrate_gyro():
    print("\n> Calibrate Gyroscope <")
    file = choose_file("/calibration/imu.json")
    imu = MPU6500(address=0x69, smbus=i2cbus)

    ticks = int(cutie.default_input("Count", "256"))
    delay = float(cutie.default_input("Delay between measurements in seconds", "0.2"))

    print("Testing before calibration...")
    for i in range(10):
        print(imu.gyro)

    print(f"Total calibration time: {ticks * delay / 1000} seconds")

    values = imu.calibrate_gyro(count=ticks, delay=delay)
    print(f"Calibration complete. Calibration parameters: {values}")
    print("Testing calibration...")
    for i in range(10):
        print(imu.gyro)

    save_to_file(file, {
        "gyro_offset": values
    })


def calibrate_bme(index):
    print(f"\n> Calibrate BME {index} <")
    file = choose_file(f"/calibration/bme{index}.json")

    address = [
        0x77,  # Biochamber
        0x76  # Techpart
    ][index - 1]

    bme = BME680(address, smbus=i2cbus)
    sources = [
        "O2 Sensor",
        "CO2 Sensor",
        "IMU Sensor",
        "Manual input",
    ]
    calibration_source = sources[cutie.select(sources)]

    if calibration_source == "O2 Sensor":
        o2 = TB200B(0x24, smbus=i2cbus)

        def source():
            o2.sample()
            return o2.temperature
    elif calibration_source == "CO2 Sensor":
        co2 = EE895(0x5E, smbus=i2cbus)

        def source():
            co2.sample()
            return co2.temperature
    elif calibration_source == "IMU Sensor":
        imu = MPU6500(0x69, smbus=i2cbus)

        def source():
            return imu.temperature
    elif calibration_source == "Manual input":
        reference_value = float(input("Reference temperature: ").replace(",", "."))

        def source():
            return reference_value
    else:
        print("Invalid input")
        return

    ticks = int(cutie.default_input("Count", "256"))
    delay = float(cutie.default_input("Delay between measurements in seconds", "0.002"))

    print(f"Total expected calibration time: {ticks * delay} seconds")

    # Get calibration parameter
    values = []
    pbar = tqdm.tqdm(range(ticks), total=ticks, desc=f"Calibrate BME {index}")
    for i in pbar:
        bme.get_sensor_data()
        measurement = bme.temperature
        reference = source()
        values.append(reference - measurement)
        pbar.set_postfix({
            "M": measurement,
            "R": reference,
            "D": reference - measurement
        })
        time.sleep(delay)

    pbar.close()

    value = sum(values) / len(values)
    print(f"Calibration complete. Temperature offset: {value}")

    # Calibrate bme
    bme.sensor.set_temp_offset(value)

    # Test
    print("Check calibration")
    for i in range(10):
        bme.get_sensor_data()
        measurement = bme.temperature
        reference = source()
        print({
            "M": measurement,
            "R": reference,
            "D": reference - measurement
        })
        time.sleep(delay)

    pbar.close()

    save_to_file(file, {
        "value": value
    })


def calibrate_camera():
    print(f"\n> Calibrate Camera <")
    resolutions = [
        "640x480",
        "800x400",
        "1024x768",
        "1280x960",
        "1920x1080",

    ]
    resolution = resolutions[cutie.select(resolutions, selected_index=3)]
    fps = cutie.default_input("Frames per second", "24")
    port = cutie.default_input("Port", "8554")

    width, height = resolution.split("x")

    ip_addr = socket.gethostbyname_ex(socket.gethostname())[-1]
    print(f"Open VLC with media url: tcp/h264://{ip_addr}:{port}")

    libcamera = subprocess.Popen(
        [
            "libcamera-vid",
            "--inline",
            "--listen",
            "-o",
            "tcp://0.0.0.0:8888",
            "-hf",
            "-w",
            width,
            "-h",
            height,
            "-fps",
            fps
        ]
    )
    libcamera.wait()


def save_to_file(file: Path, content: dict):
    file.parent.mkdir(exist_ok=True, parents=True)
    file.write_text(json.dumps(content))


def choose_file(default_file: str) -> Path:
    return Path(cutie.default_input("In which file should values be written?", default_file))


def choose_calibration():
    sensors = [
        "Sensors",
        "IMU Gyroscope",
        "BME1",
        "BME2",
        "Camera",
        "Special",
        "ALL",
        "QUIT",
    ]
    print("Choose sensor to calibrate")
    sensor = sensors[cutie.select(sensors, caption_indices=[0, 5])]
    if sensor == "IMU Gyroscope":
        calibrate_gyro()
    elif sensor == "BME1":
        calibrate_bme(1)
    elif sensor == "BME2":
        calibrate_bme(2)
    elif sensor == "Camera":
        calibrate_camera()
    elif sensor == "ALL":
        print("Calibrating all sensors. Press Enter on input to use default values")
        calibrate_gyro()
        calibrate_bme(1)
        calibrate_bme(2)
        calibrate_camera()
    elif sensor == "QUIT":
        raise KeyboardInterrupt


if __name__ == '__main__':
    while True:
        try:
            choose_calibration()
        except KeyboardInterrupt:
            print("Quit...")
            break
