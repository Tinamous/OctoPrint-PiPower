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
		self._fanSpeeds = [0,0]
		self._fanStates = [0,0]
		self._fanFrequency = [2000, 2000]

	def initialize(self):
		self._logger.setLevel(logging.DEBUG)
		self._logger.warn("MockPiPowerHat. GPIO not initialized")

	def getPiPowerValues(self, settings):
		#self._logger.debug("Making up values for debug")

		settingsKey = "pcbTemperatureSensorId";
		sensor = settings.get([settingsKey])
		#self._logger.warn(settingsKey + " == " + sensor)

		# make some values up.
		voltage = self.randrange_float(11, 13, 0.01)
		currentMilliAmps = self.randrange_float(600, 1500, 0.1)

		return dict(
			externalTemperature= self.read_temperature("1"),
			internalTemperature= self.read_temperature("2"),
			pcbTemperature = self.read_temperature("3"),
			extraTemperature = None,
			voltage = round(voltage,1),
			currentMilliAmps = round(currentMilliAmps,1),
			powerWatts = round(voltage * (currentMilliAmps/1000),0),
			lightLevel = self.randrange_float(0, 100, 1),
			fan0On= self._fanStates[0],
			fan0Speed = self._fanSpeeds[0],
			fan1On= self._fanStates[1],
			fan1Speed = self._fanSpeeds[1],
			leds = "on",
			gpioPin16Value = "HIGH",
			gpioPin26Value = "LOW"
			)

	def read_temperature(self, sensor):
		temperature = random.randint(0, 1000) * 0.1 + 20
		return temperature

	def randrange_float(self, start, stop, step):
		return random.randint(0, int((stop - start) / step)) * step + start

	def set_fan(self, fan_id, state, speed, frequency):
		self._logger.warn("****Setting fan: {0}, State: {1} Speed: {2} Frequency: {3}".format(fan_id, state, speed, frequency))
		self._fanSpeeds[fan_id] = speed
		self._fanStates[fan_id] = state
		self._fanFrequency[fan_id] = frequency
