#! /usr/bin/python
from gpiozero import OutputDevice
from rpi_hardware_pwm import HardwarePWM

# Configuration
CHANNEL = 1   # GPIO12 = 0, GPIO13 = 1  https://pypi.org/project/rpi-hardware-pwm/
FREQUENCY = 20000
LED_ENABLE_PIN = "GPIO16"

# Setup Pin
print("Set GPIO mode")
print(f"Setup PWM_PIN (channel={CHANNEL}, frequency={FREQUENCY})")
print(f"Setup LED_ENABLE on pin={LED_ENABLE_PIN}")
led_enable = OutputDevice(LED_ENABLE_PIN)
pwm = HardwarePWM(pwm_channel=CHANNEL, hz=FREQUENCY)
pwm.start(100)
led_enable.on()


# Procedure
try:
    while True:
        duty_cycle = input("New duty cycle or [E]nable/[D]isable: ")
        if duty_cycle.lower() == "e":
            print("Enable LED_ENABLE")
            led_enable.on()
            continue
        elif duty_cycle.lower() == "d":
            print("Disable LED_ENABLE")
            led_enable.off()
            continue
        elif duty_cycle.lower() == "q":
            print("Quit")
            break
        else:
            try:
                duty_cycle = float(duty_cycle)
            except ValueError:
                print("Invalid input")
                continue
            pwm.change_duty_cycle(duty_cycle * 100)
except KeyboardInterrupt:
    print("KB Interrupt")
except:
    print("Exception raised. Cleanup...")
    pwm.stop()
    raise

pwm.stop()
