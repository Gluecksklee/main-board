import logging

from smbus import SMBus
import time

from apis.i2c_modules.o2 import TB200B

MSP_ADDRESS = 0x24


def main():
    logging.basicConfig(level=logging.NOTSET)
    i2cbus = SMBus(1)
    # delay recommended according to this stackoverflow post
    # https://stackoverflow.com/questions/52735862/getting-ioerror-errno-121-remote-i-o-error-with-smbus-on-python-raspberry-w
    time.sleep(1)

    o2_sensor = TB200B(MSP_ADDRESS, await_uart_timeout=10, uart_buffer_size=13, smbus=i2cbus, uart_ready_delay=0.1)
    print("O2 Concentration")
    print(o2_sensor.read_o2_concentration())

    print("O2 Data")
    print(o2_sensor.read_data())

    print("Light state")
    print(o2_sensor.query_light_state())

    print("Turn lights off")
    print(o2_sensor.turn_off_lights())

    print("Light state")
    print(o2_sensor.query_light_state())

    time.sleep(1)

    print("Turn lights on")
    print(o2_sensor.turn_on_lights())

    print("Light state")
    print(o2_sensor.query_light_state())


if __name__ == "__main__":
    main()
