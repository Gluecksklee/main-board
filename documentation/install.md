# Installation on Pi
> [!WARNING]
> This Install documentation might be outdated. Please use the [Ansible Repository](https://github.com/gluecksklee/ansible) instead!

## RPI-Config

* wpa_config
* Activate I2C
* Activate PiCamera


### Dev

* vlc (for streaming)
* tmux
* git
* Python:
  * colorlog
* i2c-tools

## Python Packages

* picamera (preinstalled)
* gpiozero (preinstalled)
* bme680
* hydra-core
* [rpi-hardware-pwm](https://pypi.org/project/rpi-hardware-pwm/)
    * `echo "dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4" >> /boot/config.txt`
* sqlmodel
* rpi-hardware-pwm




## New Raspberry Pi
1. Flash Image on SD-Card
  * Setup hostname
  * Setup password
  * Setup Wifi
2. `sudo raspi-config`
3. `sudo reboot`
4. `sudo apt update && sudo apt upgrade -y`
5. `sudo reboot`
6. `sudo apt install tmux git python3-pip i2c-tools`
7. `sudo echo 'dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4' >> /boot/config.txt` 
8. `python -m pip install bme680 hydra-core rpi-hardware-pwm hydra-core sqlmodel colorlog picamera`
9. `sudo reboot`

````shell
sudo apt update && sudo apt upgrade -y && sudo apt install -y tmux git python3-pip && sudo python -m pip install bme680 hydra-core rpi-hardware-pwm hydra-core sqlmodel colorlog picamera
````
