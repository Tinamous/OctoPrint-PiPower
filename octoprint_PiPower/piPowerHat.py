# coding=utf-8
from __future__ import absolute_import

__author__ = "Stephen Harrison <Stephen.Harrison@AnalysisUK.com>"
__license__ = 'Creative Commons Share Alike 4.0'
__copyright__ = "Copyright (C) 2017 Analysis UK Ltd - Released under terms of the CC-SA-4.0 License"

import octoprint.plugin
from octoprint.util import RepeatedTimer

import flask

import sys
import os
import time
import subprocess
import glob
import logging
import logging.handlers

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# Fan Controll:
# For a quiet fan (and to properly control the 4 pin PWM fan)
# PWM frequency of 20-25kHZ is needed

# RPi.GPIO library uses software and can not run at this frequency
# WiringPi needs root access for PWM control
# pigpio uses 25% CPU for 20kHz frequency.
# so....
# RPi.GPIO library appears to be the easiest for now....

# Current monitor/
# See https://github.com/chrisb2/pi_ina219/blob/master/README.md
# and https://www.hackster.io/chrisb2/raspberry-pi-ina219-voltage-current-sensor-library-f3bb54
SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 3.0

# Interface for real hardware.
class PiPowerHat:
	def __init__(self):
		self._logger = logging.getLogger(__name__)
		self._settings = None

		# PWM Fan control
		# The requested speed of the fan
		# Default to 100% fan speed
		self._fanSpeeds = [100,100]
		# If the fan is on or off
		self._fanStates = [False,False]
		self._fan_pwm_pins = [18, 13]
		self._fan_pwm = []

		# Current monitoring with INA219
		self._ina = None

		# TODO: figure out if we have one.
		self._tsl2561  = None
		self._has_light_sensor = False

		# Initialzie a 40 pin array for IO set values
		# ignore 0 as their is no pin 0
		self._gpioPinSetValue = []
		for pin in range(4, 40):
			self._gpioPinSetValue.append(0)

	def initialize(self, settings):
		self._logger.setLevel(logging.INFO)
		self._logger.info("PiPowerHat initializing")
		self._settings = settings
		import RPi.GPIO as GPIO

		self._logger.info("Running RPi.GPIO version '{0}'...".format(GPIO.VERSION))

		if GPIO.VERSION < "0.6":
			raise Exception("RPi.GPIO must be greater than 0.6")
			
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(True)

		# Setup the fan PWMs. Pi (V3) only supports 2 hardware PWM channels.
		# Need to use 20-25kHz PWM frequency for proper fan control which
		# is difficult to acheive without high CPU or root access.

		self._logger.info("Initializing PWM Fans.")

		pwmFrequency = int(self._settings.get(["pwmFrequency"]))
		self._logger.info("Pwm Frequency: {0}".format(pwmFrequency))

		# FAN 0 (Pin 12 - BCM/GPIO 18)
		# FAN 1 (Pin 33 - BCM/GPIO 13)
		for fan_pin in self._fan_pwm_pins:
			self._logger.info("Initializing PWM for fan on pin: {0}, frequency: {1}".format(fan_pin, pwmFrequency))
			GPIO.setup(fan_pin, GPIO.OUT)
			pwm = GPIO.PWM(fan_pin, pwmFrequency)
			pwm.start(0)
			# Store the reference the the pwm instance for later speed use
			self._fan_pwm.append(pwm)


		# Setup the INA219 Power monitor

		self._logger.info("Initializing INA219")
		from ina219 import INA219
		from ina219 import DeviceRangeError

		try:
			# Expect a 0R1 resistor on the PCB
			self._ina = INA219(SHUNT_OHMS)
			# Default to 32V max range. (device supports 26V max)
			self._ina.configure()
			self._logger.info("INA219 Configured. Reading values.")

			self._logger.info("Bus Voltage: %.3f V" % self._ina.voltage())
			self._logger.info("Bus Current: %.3f mA" % self._ina.current())
			self._logger.info("Power: %.3f mW" % self._ina.power())
			self._logger.info("Shunt voltage: %.3f mV" % self._ina.shunt_voltage())
		except:
			self._logger.warn("Initializing INA219 FAILED")

		self.setup_lightsensor()

		# Setup GPIO Pins
		self._logger.info("Initializing GPIO Pins")
		for gpio_option in settings.get(['gpioOptions']):
			self.setup_gpio(gpio_option)

		self._logger.info("PiPowerHat. GPIO initialized")

	def setup_lightsensor(self):

		from tsl2561 import TSL2561
		from tsl2561.constants import *  # pylint: disable=unused-wildcard-import
		try:
			self._has_light_sensor = False
			self._logger.info("Initializing TSL2561 Light Sensor")
			# See https://github.com/sim0nx/tsl2561/blob/master/tsl2561/tsl2561.py
			# address=None, busnum=None, integration_time=TSL2561_INTEGRATIONTIME_402MS, gain=TSL2561_GAIN_1X, autogain=False, debug=False
			# TODO: Allow config of gain and integration time and maybe address?
			self._tsl2561 = TSL2561(address=TSL2561_ADDR_LOW)
			self._logger.info("TSL2561 Light Sensor configured")
			self._has_light_sensor = True
		except Exception as e:
			self._logger.warn("Initialzing TSL2561 FAILED. Error: {0}".format(e))


	def setup_gpio(self, gpio_option):
		self._logger.info("Initialize GPIO pin: {0}, assigned as: {1}".format(gpio_option['pin'], gpio_option['caption']))
		import RPi.GPIO as GPIO

		# Mode: Disabled = 0, Input = 1, Input pull down = 2, Input pull up = 3, Output = 4
		mode = int(gpio_option['mode'])
		pin = gpio_option['pin']

		if mode == 0:
			self._logger.warn("GPIO Pin {0} Disabled".format(pin))
			# Disabled
			return;

		self._logger.debug("Setting pin {0} mode: {1}".format(pin, mode))

		if mode == 1:
			# Input
			GPIO.setup(pin, GPIO.IN)
		elif mode == 2:
			GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
		elif mode == 3:
			GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		elif mode == 4:
			# Output
			GPIO.setup(pin, GPIO.OUT)
		else:
			self._logger.warn("Unknown pin mode")


	# Read the parameters from the Pi Power Hat
	def getPiPowerValues(self, settings):
		self._logger.debug("Getting values from PiPower")

		try:
			self._logger.debug("Reading Temperatures.")
			measured_temperatures = self.read_temperatures(settings)

			self._logger.debug("Reading Power.")
			power = self.read_power(settings)

			# V1.2 PCB only and may not be fitted
			self._logger.debug("Reading Light Level.")
			lightLevel = self.read_light_level(settings)

			self._logger.debug("Reading GPIOs.")
			gpio_pin_values = self.read_gpio_values(settings)

			return dict(
				temperatures= measured_temperatures,
				voltage = round(power['voltage'],2),
				currentMilliAmps = round(power['currentMilliAmps'],2),
				powerWatts = round(power['power'],2),
				lightLevel = lightLevel,
				fans = [
					self.get_fan_details(0),
					self.get_fan_details(1),
					# Fan 3 is always on
					dict(fanId=2, state=True, speed=100, setSpeed=100),
				],
				gpioValues = gpio_pin_values
				)
		except Exception as e:
			self._logger.exception("Exception reading PowerHat values. Exception: {0}".format(e))

	# ===========================================
	# Power
	# ===========================================
	def read_power(self, settings):
		from ina219 import INA219
		from ina219 import DeviceRangeError

		# TODO: Ensure self._ina is not null.

		# make some values up.
		# extraTemperature = null
		voltage = self._ina.voltage()
		currentMilliAmps = self._ina.current()
		# Power is in mW, convert it to Watts
		power = (self._ina.power() / 1000);

		return dict(
			voltage=voltage,
			currentMilliAmps=currentMilliAmps,
			power=power
		)

	# ===========================================
	# Temperature
	# ===========================================

	# Get the list of available sensors on the system
	# This is called before settings/logger are available
	# and before initialzie is called.
	def getTemperatureSensors(self):
		# return ['','28-000007538f5b','28-0000070e4078','28-0000070e3270','28-000007538a2b' ]

		try:
			base_dir = '/sys/bus/w1/devices/'
			folders = glob.glob(base_dir + '28*')
			# self._logger.info("Got folders: {0}.".format(folders))

			sensors = ['']

			for folder in folders:
				# self._logger.info("Sensor: {0}.".format(folder))
				# Need to remove the start /sys/bus/w1/devices/ from the folder.
				folder = folder.replace("/sys/bus/w1/devices/", "")
				sensors.append(folder)

			return sensors

		except Exception as e:
			# self._logger.exception("Failed to get list of sensors. Exception: {0}".format(e))
			return ['']

	# Read the temperatures for each of the sensors defined in the settings
	def read_temperatures(self, settings):
		temperatures = []
		for sensor in settings.get(['temperatureSensors']):
			sensorId = sensor['sensorId']
			if sensorId:
				value = self.read_temperature(sensorId)
				temperature = dict(sensorId=sensorId, value=value)
				temperatures.append(temperature)

		return temperatures

	# Read the temperature from the sensor.
	def read_temperature(self, sensor_id):
		lines = self.read_temp_raw(sensor_id)

		while lines[0].strip()[-3:] != 'YES':
			time.sleep(0.2)
			lines = self.read_temp_raw(sensor_id)

		# TypeError
		temp_output = lines[1].find('t=')

		if temp_output != -1:
			temp_string = lines[1].strip()[temp_output+2:]
			temp_c = float(temp_string) / 1000.0
			return round(temp_c,1)

	# Read temperature raw output from sensor	
	# From Adafruit: https://cdn-learn.adafruit.com/downloads/pdf/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing.pdf
	def read_temp_raw(self, sensor_id):
		sensorPath = "/sys/bus/w1/devices/{}/w1_slave".format(sensor_id)
		catdata = subprocess.Popen(['cat', sensorPath], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out,err = catdata.communicate()
		out_decode = out.decode('utf-8')
		lines = out_decode.split('\n')
		return lines

	# ===========================================
	# Fans
	# ===========================================
	def set_fan(self, fan_id, state, speed):
		self._logger.info("Setting fan: {0}, State: {1} Speed: {2}".format(fan_id, state, speed))
		previousSpeed = self._fanSpeeds[fan_id]
		self._fanSpeeds[fan_id] = speed
		self._fanStates[fan_id] = state

		try:
			import RPi.GPIO as GPIO

			# GPIO Library PWM controller for the fan
			pwm = self._fan_pwm[fan_id]

			if state:
				# If the speed is below 50% and the fan is running slow the fan may not respond well.
				# So run the fan at full speed for 2s to get it going before setting the required level.
				if speed < 50 and previousSpeed < speed:
					pwm.ChangeDutyCycle(100.0)
					# This isn't ideal but it will do for now.
					self._logger.info("Set fan to 100% and sleeping for 2 seconds to allow the fan to come to speed properly")
					time.sleep(2)

				pwm.ChangeDutyCycle(float(speed))
				self._fanSpeeds[fan_id] = speed
			else:
				pwm.ChangeDutyCycle(0.0)

		except:
			self._logger.error("Failed to change fan speed")

	# Switch the fan on/off. Uses the previously set fan speed
	def set_fan_state(self, fan_id, state):
		self._logger.info("Setting fan: {0}, State: {1}".format(fan_id, state))
		speed = self._fanSpeeds[fan_id];

		self.set_fan(fan_id, state, speed)

	# Sets the fan speed. Will not switch the fan on or off.
	def set_fan_speed(self, fan_id, speed):
		self._logger.info("Setting fan: {0}, Speed: {1}".format(fan_id, speed))
		state = self._fanStates[fan_id]

		self.set_fan(fan_id, state, speed)

	def get_fan_speed(self, fan_id):
		# We don't have a way to measure the actual fan speed.
		# Just report back the set speed if it is on
		# or 0 it is not

		if self._fanStates[fan_id]:
			return  self._fanSpeeds[fan_id]
		else:
			return 0

	def get_fan_details(self, fan_id):
		return dict(fanId=0, state=self._fanStates[fan_id], speed=self.get_fan_speed(fan_id), setSpeed=self._fanSpeeds[fan_id]);
	# ===========================================
	# Light Sensor
	# ===========================================
	def read_light_level(self, settings):

		if not self._has_light_sensor:
			return -1

		from tsl2561 import TSL2561
		lux = self._tsl2561.lux()
		self._logger.info("Lux measured: {0}".format(lux))
		return lux

	# ===========================================
	# GPIO Pins
	# ===========================================
	def read_gpio_values(self, settings):
		gpio_pin_values = []

		try:
			# import RPi.GPIO as GPIO
			for gpio_option in settings.get(["gpioOptions"]):
				#self._logger.debug("Getting GPIO for: {0}.".format(gpio_option))
				pin = gpio_option["pin"]
				value = self.get_gpio_pin_value(gpio_option)
				gpio_pin_values.append(dict(pin=pin, value=value))
		except Exception as e:
			self._logger.exception("Failed to read GPIO pins. Exception: {0}".format(e))

		return gpio_pin_values

	def get_gpio_pin_value(self, gpio_pin_options):
		# TODO: Store set value and return that for output options
		# Disabled = 0, Input = 1, Input pull down = 2, Input pull up = 3, Output = 4

		mode = int(gpio_pin_options["mode"])
		pin = int(gpio_pin_options["pin"])

		if mode == 0:
			# Disabled
			return None
		elif mode == 4:
			# Output
			return self._gpioPinSetValue[pin]
		else:
			# Using BCM pin nuimber
			import RPi.GPIO as GPIO
			return GPIO.input(pin)

	def set_gpio(self, pin, state):
		self._logger.info("Setting GPIO Pin: {0}, State: {1}".format(pin, state))
		import RPi.GPIO as GPIO

		# TODO: Ensure the pin is defined as output.

		value = 0
		if state:
			value = 1
		else:
			value = 0

		GPIO.output(pin, value)
		# record the value set to display in the UI.
		self._gpioPinSetValue[pin] = value

