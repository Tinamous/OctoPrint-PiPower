# coding=utf-8
from __future__ import absolute_import

__author__ = "Stephen Harrison <Stephen.Harrison@AnalysisUK.com>"
__license__ = 'Creative Commons Share Alike 4.0'
__copyright__ = "Copyright (C) 2017 Analysis UK Ltd - Released under terms of the CC-SA-4.0 License"

import flask

import sys
import os
import time
import random
import logging
import logging.handlers

# Mocked hardware for development
class MockPiPowerHat:
	def __init__(self):
		self._logger = logging.getLogger(__name__)
		# The requested speed of the fan
		self._fanSpeeds = [100,100]
		# If the fan is on or off
		self._fanStates = [False,False]
		self._settings = None

		# Initialzie a 40 pin array for IO set values
		# ignore 0 as their is no pin 0
		self._gpioPinSetValue = []
		for pin in range(4, 40):
			self._gpioPinSetValue.append(0)

	def initialize(self, settings):
		self._logger.setLevel(logging.DEBUG)
		self._logger.warn("MockPiPowerHat. GPIO not initialized")
		self._settings = settings

	# ===========================================
	# Power
	# ===========================================
	def getPiPowerValues(self, settings):
		#self._logger.debug("Making up values for debug")

		#settingsKey = "pcbTemperatureSensorId";
		#sensor = settings.get([settingsKey])
		#self._logger.warn(settingsKey + " == " + sensor)

		measured_temperatures = self.read_temperatures(settings)

		# make some values up.
		voltage = self.randrange_float(11, 13, 0.01)
		currentMilliAmps = self.randrange_float(900, 1200, 0.1)

		lightLevel = self.read_light_level(settings)

		gpio_pin_values = self.read_gpio_values(settings)
		#gpio_pin_values = []
		#gpio_pin_values.append(dict(pin="16", value=))
		#gpio_pin_values.append(dict(pin="26", value=self.randrange_float(0, 1, 1)))
		#gpio_pin_values.append(dict(pin="998", value="Disabled"))
		#gpio_pin_values.append(dict(pin="999", value=""))

		return dict(
			temperatures=measured_temperatures,
			voltage=round(voltage,1),
			currentMilliAmps=round(currentMilliAmps,1),
			powerWatts=round(voltage * (currentMilliAmps/1000),0),
			lightLevel=lightLevel,
			fans = [
				self.get_fan_details(0),
				self.get_fan_details(1),
				# Fan 3 is always on
				dict(fanId=2, state=True, speed=100, setSpeed=100),
			],
			gpioValues = gpio_pin_values
			)

	# ===========================================
	# Temperature
	# ===========================================
	def getTemperatureSensors(self):
		return ['', '28-000007538f5b', '28-0000070e4078', '28-0000070e3270', '28-000007538a2b']

	def read_temperatures(self, settings):
		temperatures = []
		for sensor in settings.get(['temperatureSensors']):
			sensorId = sensor['sensorId']
			if sensorId:
				value = self.read_temperature(sensorId)
				temperature = dict(sensorId=sensorId, value=value)
				temperatures.append(temperature)

		return temperatures

	def read_temperature(self, sensor):
		temperature = random.randint(0, 1000) * 0.1 + 20
		return temperature

	# ===========================================
	# Fans
	# ===========================================
	def set_fan(self, fan_id, state, speed):
		self._logger.info("Setting fan: {0}, State: {1} Speed: {2}".format(fan_id, state, speed))
		previousSpeed = self._fanSpeeds[fan_id]
		self._fanSpeeds[fan_id] = speed
		self._fanStates[fan_id] = state
		# No other implementation...

	def set_fan_state(self, fan_id, state):
		self._logger.warn("****Setting fan: {0}, State: {1}".format(fan_id, state))
		speed = self._fanSpeeds[fan_id];

		self.set_fan(fan_id, state, speed)

	def set_fan_speed(self, fan_id, speed):
		self._logger.warn("****Setting fan: {0}, Speed: {1}".format(fan_id, speed))
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
		return dict(fanId=fan_id, state=self._fanStates[fan_id], speed=self.get_fan_speed(fan_id), setSpeed=self._fanSpeeds[fan_id]);

	# ===========================================
	# Light Sensor
	# ===========================================
	def read_light_level(self, settings):
		return self.randrange_float(0, 255, 1)

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
			return self.randrange_float(0, 1, 1)


	def set_gpio(self, pin, state):
		self._logger.info("Setting GPIO Pin: {0}, State: {1}".format(pin, state))

		# TODO: Ensure the pin is defined as output.

		if state:
			value = 1
		else:
			value = 0

		# record the value set to display in the UI.
		self._gpioPinSetValue[pin] = value

	# ===========================================
	# Helpers
	# ===========================================
	def randrange_float(self, start, stop, step):
		return random.randint(0, int((stop - start) / step)) * step + start