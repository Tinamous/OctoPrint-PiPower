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
Add the following to /boot/config.txt
dtoverlay=w1-gpio,gpiopin=4

Use 
sudo raspi-config
and enable I2C and ...


Use:

sudo modprobe w1-therm
sudo modprobe w1-therm
ls /sys/bus/w1/devices

to list the devices (ignore w1_bus_master).

28- is that 28B20... devices?

cd /sys/bus/w1/devices/<deviceId>/w1_slave
cat w1_slave

