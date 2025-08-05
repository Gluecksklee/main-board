#! /usr/bin/python
import time

import tqdm as tqdm
from gpiozero import Button, DigitalOutputDevice
from rpi_hardware_pwm import HardwarePWM

# Configuration
CHANNEL = 0   # GPIO12 = 0, GPIO13 = 1  https://pypi.org/project/rpi-hardware-pwm/
ALERT_PIN = "GPIO16"
FREQUENCY = 20000
PROCEDURE_START = 0
PROCEDURE: list[tuple[float, float]] = [
    (3, 0.35),
    (10, 0.1),
    (5, 1),
    (5, 0.5),
    (5, 0.3),
    (5, 0),
]

LAST_T = 0
LAST_F = 1


def timer():
    global LAST_T, LAST_F
    t = time.perf_counter()
    dt = t - LAST_T
    LAST_T = t
    LAST_F = LAST_F * 0.9 + 1 / dt * 0.1
    print("freq: ", LAST_F)


# Setup Pin
print("Set GPIO mode")
print(f"Setup PWM_PIN (channel={CHANNEL}, frequency={FREQUENCY})")
pwm = HardwarePWM(pwm_channel=0, hz=FREQUENCY)
pwm.start(100)

change_signal = DigitalOutputDevice("GPIO26")
button = Button(ALERT_PIN, bounce_time=0.001)
button.when_pressed = timer
# Procedure
try:
    for sleep_time, value in PROCEDURE:
        print(f"Set Duty Cycle to {value}")
        pwm.change_duty_cycle(value * 100)
        t1 = time.perf_counter()
        progress = tqdm.tqdm(desc=f"Duty Cycle: {value}", total=sleep_time)
        last_t = t1
        while last_t - t1 < sleep_time:
            t = time.perf_counter()
            progress.update(t - last_t)
            last_t = t
        progress.close()
except KeyboardInterrupt:
    print("KB Interrupt")
except:
    print("Cleanup")
    pwm.stop()
    change_signal.off()
    raise

pwm.stop()
change_signal.off()
