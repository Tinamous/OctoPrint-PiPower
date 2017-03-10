# coding=utf-8
from __future__ import absolute_import

__author__ = "Stephen Harrison <Stephen.Harrison@AnalysisUK.com>"
__license__ = 'Creative Commons Share Alike 4.0'
__copyright__ = "Copyright (C) 2017 Analysis UK Ltd - Released under terms of the CC-SA-4.0 License"

import flask

import sys
import os
import time

import logging
import logging.handlers

# Mocked hardware for development
class MockPiPowerHat:
	def __init__(self):
		self._logger = logging.getLogger(__name__)

	def initialize(self):
		self._logger.setLevel(logging.DEBUG)
		self._logger.warn("MockPiPowerHat. GPIO not initialized")

	def getPiPowerValues(self, settings):
		self._logger.debug("Making up values for debug")
		
		settingsKey = "pcbTemperatureSensorId";
		sensor = settings.get([settingsKey])
		self._logger.warn(settingsKey + " == " + sensor)

		import random
		def randrange_float(start, stop, step):
			return random.randint(0, int((stop - start) / step)) * step + start

		# make some values up.
		voltage = randrange_float(11, 13, 0.01)
		currentMilliAmps = randrange_float(600, 1500, 0.1)

		return dict(
			externalTemperature= randrange_float(30, 60, 0.1), 
			internalTemperature= randrange_float(30, 60, 0.1),
			pcbTemperature = randrange_float(30, 60, 0.1),
			extraTemperature = None,
			voltage = round(voltage,1),
			currentMilliAmps = round(currentMilliAmps,1),
			powerWatts = round(voltage * (currentMilliAmps/1000),0),
			lightLevel = randrange_float(0, 100, 1),
			fan0Speed = randrange_float(0, 100, 1),
			fan1Speed = randrange_float(0, 100, 1),
			leds = "on",
			gpioPin16Value = "HIGH",
			gpioPin26Value = "LOW"
			)
