# OctoPrint-PiPower

OctoPrint plugin to monitor the Pi Power (Hat). (See: https://github.com/Tinamous/PiPowerHat)

## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/Tinamous/OctoPrint-PiPower/archive/master.zip

**TODO:** Describe how to install your plugin, if more needs to be done than just installing it via pip or through
the plugin manager.

## Configuration

**TODO:** Describe your plugin's configuration options (if any).

## Config changes required

### 1-Wire temperature sensors.

To read 1-Wire values (i.e. the DS18B20 temperature sensor) we need to enable 1-Wire
on GPIO pin 4:

Add the following to /boot/config.txt
dtoverlay=w1-gpio,gpiopin=4

Use:

sudo modprobe w1-therm
sudo modprobe w1-therm
ls /sys/bus/w1/devices

to list the devices (ignore w1_bus_master).

28- is that 28B20... devices?

cd /sys/bus/w1/devices/<deviceId>/w1_slave
cat w1_slave

### For the I2C device (voltage/current monitor + possible I2C light level

Use
sudo raspi-config
and enable I2C and ...

### For Fan PWM control

We need to use hardware (PWM) which is not accessible when not running as root.
I tried pigpio but that needed extra install steps and used 25% CPU.
RPi.GPIO is used and works with software PWM. You may wish to test FAN1 with different
PWM frequencies to see which gives the best (least noise), otherwise run it as on/off only.

Fan 0 may not function as PWM fans need a 21-26 kHz PWM frequency which we can't provice.




