#! /usr/bin/python
import time

from gpiozero import OutputDevice
from rpi_hardware_pwm import HardwarePWM

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from libcamera import Transform


# Configuration
CHANNEL_LED = 1   # GPIO12 = 0, GPIO13 = 1  https://pypi.org/project/rpi-hardware-pwm/
CHANNEL_FAN = 0   # GPIO12 = 0, GPIO13 = 1  https://pypi.org/project/rpi-hardware-pwm/
FREQUENCY = 20000
LED_ENABLE_PIN = "GPIO16"

# Setup Pin
print("Set GPIO mode")
print(f"Setup PWM_LED (channel={CHANNEL_LED}, frequency={FREQUENCY})")
print(f"Setup PWM_FAN (channel={CHANNEL_FAN}, frequency={FREQUENCY})")
print(f"Setup LED_ENABLE on pin={LED_ENABLE_PIN}")
led_enable = OutputDevice(LED_ENABLE_PIN)
pwm_fan = HardwarePWM(pwm_channel=CHANNEL_FAN, hz=FREQUENCY)
pwm_led = HardwarePWM(pwm_channel=CHANNEL_LED, hz=FREQUENCY)
pwm_led.start(100)
pwm_fan.start(30)
led_enable.on()


camera = Picamera2()

config = camera.create_video_configuration(
    main={
        "size": (1920, 1080)
        # "size": (3280, 2464)
    },
    lores={
        "size": (640, 480),
    },
    transform=Transform(hflip=True, vflip=True),
)

camera.configure(config)

encoder = H264Encoder(bitrate=10000000)

# Procedure
try:
    duty_cycle = 0
    while True:
        # duty_cycle = input("New duty cycle or [E]nable/[D]isable: ")
        if duty_cycle > 1:
            break
        else:
            try:
                duty_cycle = float(duty_cycle)
            except ValueError:
                print("Invalid input")
                continue
            pwm_fan.change_duty_cycle(min(100, duty_cycle * 100))
            print(f"Record video for duty cycle: {duty_cycle}...")
            camera.start_recording(encoder, f"/root/data/videos/plants_{duty_cycle:.2f}.h264")
            time.sleep(10)
            camera.stop_recording()
        duty_cycle += 0.05


except KeyboardInterrupt:
    print("KB Interrupt")
except:
    print("Exception raised. Cleanup...")
    pwm_led.stop()
    pwm_fan.stop()
    raise

pwm_fan.stop()
pwm_led.stop()
