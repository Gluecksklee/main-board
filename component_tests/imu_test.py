import math

from apis.i2c_modules.AK8963 import AK8963
from apis.i2c_modules.MPU6500 import MPU6500
import time
from smbus import SMBus

from utils.analysis import imu_in_motion

if __name__ == '__main__':
    i2cbus = SMBus(1)

    imu1 = MPU6500(address=0x69, smbus=i2cbus)
    imu2 = AK8963(address=0x69, smbus=i2cbus)

    ret = imu1.calibrate_gyro()
    # ret = imu2.calibrate()
    # print(f"Calibration:")
    # print(ret)
    #
    # exit()

    old_vec = (0, 0, 0)
    while True:
        acc = imu1.acceleration
        print(f"{imu1.temperature}°C\t{imu1.gyro}\t{acc}")
        print(f"Total acc: {math.sqrt(acc[0] ** 2 + acc[1] ** 2 + acc[2] ** 2)}")

        value = imu_in_motion(old_vec, acc)
        print(f"In Motion: {value}")
        old_vec = acc

        time.sleep(0.01)
        print()
