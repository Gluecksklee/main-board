import time
import tqdm as tqdm


# Configuration
PWM_PIN = 12
FREQUENCY = 23000
PROCEDURE_START = 0
PROCEDURE: list[tuple[float, float]] = [
    (3, 0),
    (5, 0.35),
    (5, 1),
    (5, 0.5),
    (5, 0.3),
    (5, 0),
]

# Setup Pin
print("Set GPIO mode")
GPIO.setmode(GPIO.BOARD)

print(f"Setup PWM_PIN (channel={PWM_PIN}, frequency={FREQUENCY})")
GPIO.setup(PWM_PIN, GPIO.OUT)
p = GPIO.PWM(PWM_PIN, FREQUENCY)

p.start(PROCEDURE_START)

# Procedure
try:
    for sleep_time, value in PROCEDURE:
        print(f"Set Duty Cycle to {value}")
        p.ChangeDutyCycle(value)
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
    p.stop()
    GPIO.cleanup()
    raise

print("Cleanup")
p.stop()
GPIO.cleanup()
