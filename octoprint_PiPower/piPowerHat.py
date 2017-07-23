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
		self._fanSpeeds = [0,0]
		self._fanStates = [0,0]
		self._fan_pwm_pins = [18, 13]
		self._fan_pwm = []

		# Current monitoring with INA219
		self._ina = None

	def initialize(self, settings):
		self._logger.info("PiPowerHat. GPIO initializing")
		self._logger.setLevel(logging.DEBUG)
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

		self._logger.warn("Initializing INA219")
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


		# Setup GPIO Pins 16 and 26.
		# TODO: Allow settings to device input or output.
		GPIO.setup(16, GPIO.IN)
		GPIO.setup(26, GPIO.IN)


		self._logger.info("PiPowerHat. GPIO initialized")

	def getTemperatureSensors(self):
		#return ['','28-000007538f5b','28-0000070e4078','28-0000070e3270','28-000007538a2b' ]

		try:
			base_dir = '/sys/bus/w1/devices/'
			folders = glob.glob(base_dir + '28*')
			self._logger.info("Got folders: {0}.".format(folders))

			sensors = ['']

			for folder in folders:
				self._logger.info("Sensor: {0}.".format(folder))
				# Need to remove the start /sys/bus/w1/devices/ from the folder.
				folder = folder.replace("/sys/bus/w1/devices/", "")
				sensors.append(folder)

			return sensors

		except Exception as e:
			self._logger.exception("Failed to get list of sensors. Exception: {0}".format(e))
			return ['']

	def getPiPowerValues(self, settings):
		self._logger.info("Getting values from PiPower")			

		self._logger.info("Reading temperatures.")			
		pcbTemperature = self.read_temperature_for_setting(settings, "pcbTemperatureSensorId")
		internalTemperature = self.read_temperature_for_setting(settings, "internalTemperatureSensorId")
		externalTemperature = self.read_temperature_for_setting(settings, "externalTemperatureSensorId")
		extraTemperature = self.read_temperature_for_setting(settings, "extraTemperatureSensorId")

		self._logger.info("Reading Power.")

		from ina219 import INA219
		from ina219 import DeviceRangeError

		# make some values up.
		# extraTemperature = null
		voltage = self._ina.voltage()
		currentMilliAmps = self._ina.current()
		# Power is in mW, convert it to Watts
		power = (self._ina.power() / 1000);

		self._logger.info("Reading Light Level.")			
		# V1.2 PCB only
		lightLevel = 128
		

		self._logger.info("Reading GPIOs.")
		import RPi.GPIO as GPIO

		gpio_pin_values = []
		for gpio_pin in settings.get(["gpioOptions"]):
			self._logger.info("Getting GPIO for pin: {0}.".format(gpio_pin))
			if gpio_pin["gpio"] == 16:
				self._logger.info("Getting GPIO 16.")
				gpioPin16Value = self.get_gpio_pin_value(gpio_pin)
				gpio_pin_values.append(dict(pin=gpio_pin["gpio"], value=gpioPin16Value))
			if gpio_pin["gpio"] == 26:
				self._logger.info("Getting GPIO 26.")
				gpioPin26Value = self.get_gpio_pin_value(gpio_pin)
				gpio_pin_values.append(dict(pin=gpio_pin["gpio"], value=gpioPin16Value))


		# These should be local variables as to how the fan/leds were set.
		leds = "off"

		return dict(
			externalTemperature= externalTemperature, 
			internalTemperature= internalTemperature,
			pcbTemperature = pcbTemperature,
			extraTemperature = extraTemperature,
			voltage = round(voltage,2),
			currentMilliAmps = round(currentMilliAmps,2),
			powerWatts = round(power,2),
			lightLevel = lightLevel,
			fan0On= self._fanStates[0],
			fan0Speed = self._fanSpeeds[0],
			fan1On= self._fanStates[1],
			fan1Speed = self._fanSpeeds[1],
			leds = leds,
			gpioPin16Value = gpioPin16Value,
			gpioPin26Value = gpioPin26Value,
			gpioValues = gpio_pin_values
			)

	def get_gpio_pin_value(self, gpio_pin_options):
		# TODO: Store set value and return that.
		# Mode: Input = 0, Input pull down = 1, Input pull up = 2, Output = 3
		if gpio_pin_options["mode"] == 3:
			return "" # Unknown
		else:
			# Using BCM pin nuimber
			import RPi.GPIO as GPIO
			return GPIO.input(gpio_pin_options["gpio"])

	# Pass in the key for the settings we want the temperature for
	# and read the temperature if the sensor is defined.
	def read_temperature_for_setting(self, settings, settingsKey):

		try: 
			sensor = settings.get([settingsKey])

			if sensor:
				self._logger.info("Reading sensor: " + sensor)
				return self.read_temp(sensor)
			else:
				# self._logger.info("No sensor for setting: " + settingsKey)
				return None;
		except Exception as e:
			self._logger.exception("Error reading temperature.")
			raise

	# Read the temperature from the sensor.
	def read_temp(self, sensor):
		lines = self.read_temp_raw(sensor)

		while lines[0].strip()[-3:] != 'YES':
			time.sleep(0.2)
			lines = self.read_temp_raw(sensor)

		# TypeError
		temp_output = lines[1].find('t=')

		if temp_output != -1:
			temp_string = lines[1].strip()[temp_output+2:]
			temp_c = float(temp_string) / 1000.0
			return round(temp_c,1)

	# Read temperature raw output from sensor	
	# From Adafruit: https://cdn-learn.adafruit.com/downloads/pdf/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing.pdf
	def read_temp_raw(self, sensor):
		sensorPath = "/sys/bus/w1/devices/{}/w1_slave".format(sensor)
		catdata = subprocess.Popen(['cat', sensorPath], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out,err = catdata.communicate()
		out_decode = out.decode('utf-8')
		lines = out_decode.split('\n')
		return lines


	def set_fan(self, fan_id, state, speed):
		self._logger.warn("Setting fan: {0}, State: {1} Speed: {2}".format(fan_id, state, speed))
		previousSpeed = self._fanSpeeds[fan_id]
		self._fanSpeeds[fan_id] = speed
		self._fanStates[fan_id] = state

		try:

			import RPi.GPIO as GPIO

			pwm = self._fan_pwm[fan_id]

			if state:
				# If the speed is below 50% and the fan is running slow the fan may not respond well.
				# So run the fan at full speed for 2s to get it going before setting the required level.
				if speed < 50 and previousSpeed < speed:
					self._fanSpeeds[fan_id] = 100
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

	def set_gpio(self, pin, state):
		self._logger.warn("Setting GPIO Pin: {0}, State: {1}".format(pin, state))
		import RPi.GPIO as GPIO

		# TODO: Ensure the pin is defined as output.

		if state:
			GPIO.output(pin, 1)
		else:
			GPIO.output(pin, 0)
