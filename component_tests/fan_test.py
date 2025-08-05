#! /usr/bin/python
import time
import tqdm as tqdm

from gpiozero import PWMOutputDevice, Device, Button, DigitalOutputDevice
from gpiozero.pins.pigpio import PiGPIOFactory

# Configuration
Device.pin_factory = PiGPIOFactory()
PWM_PIN = "GPIO12"
ALERT_PIN = "GPIO18"
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
print(f"Setup PWM_PIN (channel={PWM_PIN}, frequency={FREQUENCY})")
p = PWMOutputDevice(PWM_PIN, frequency=FREQUENCY)
p.on()

change_signal = DigitalOutputDevice("GPIO26")
button = Button(ALERT_PIN, bounce_time=0.001)
button.when_pressed = timer
# Procedure
try:
    for sleep_time, value in PROCEDURE:
        print(f"Set Duty Cycle to {value}")
        p.value = value
        t1 = time.perf_counter()
        progress = tqdm.tqdm(desc=f"Duty Cycle: {value}", total=sleep_time)
        last_t = t1
        while last_t - t1 < sleep_time:
            t = time.perf_counter()
            # progress.update(t - last_t)
            last_t = t
        progress.close()
except KeyboardInterrupt:
    print("KB Interrupt")
except:
    print("Cleanup")
    p.off()
    change_signal.off()
    raise

p.off()
change_signal.off()
