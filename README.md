# Main Board
This repository contains the software for the main board which runs on a Raspberry Pi Zero 2W for the [Glücksklee project](https://gluecksklee.space).
The software is written in a modular way with different components which can be easily extended for different projects.
The current modules are:
- `camera`: Camera controller for images and videos
- `light`: Light controller pulse width modulation (PWM)
- `fan`: Fan controller using PWM
- `heartbeat`: Sending regular Heartbeat over GPIO
- Sensors:
  - `bme680`: Environmental sensor
  - `co2`: Interface for EE895 sensor
  - `fan_tacho`: Reads fan speed for radial fan HY45T05A
  - `imu`: Interface for MPU-6881
  - `internal`: Reads RPI specific
  - `msp`: Interface to communicate with MSP430G2403 (see other repository TODO: Add Link)
  - `o2`: Interface for O2 sensor EC Sense TB200B-ES1
- Logger:
  - `database`: Saves all sensor data in an sql database and logs media to local storage
  - `spacetango_logger`: Sends sensor data via socket using spacetango communication protocol. Saves media to local storage
  - `tcp_logger`: Sends data via REST Api

## Setup
```shell
sudo pip install -r requirements.txt
cd src
sudo python main.py
```

### Activate pigpio
Start:
```shell
sudo pigpiod -s 2
```

Disable:
```shell
sudo killall pigpio
```



### VLC Stream
```shell
raspivid -o - -t 9999999 |cvlc -vvv stream:///dev/stdin --sout '#rtp{sdp=rtsp://:8554/}' :demux=h264
```