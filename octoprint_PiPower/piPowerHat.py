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

import logging
import logging.handlers

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# Real hardware
class PiPowerHat:
	def __init__(self):
		self._logger = logging.getLogger(__name__)

	def initialize(self):
		self._logger.warn("PiPowerHat. GPIO initializing")
		self._logger.setLevel(logging.DEBUG)
		import RPi.GPIO as GPIO 

		self._logger.info("Running RPi.GPIO version '{0}'...".format(GPIO.VERSION))

		if GPIO.VERSION < "0.6":
			raise Exception("RPi.GPIO must be greater than 0.6")
			
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)

		self._logger.warn("PiPowerHat. GPIO initialized")

	def getPiPowerValues(self, settings):
		self._logger.warn("Getting values from PiPower PCB")
		
		pcbTemperature = self.read_temperature_for_setting(settings, "pcbTemperatureSensorId")
		internalTemperature = self.read_temperature_for_setting(settings, "internalTemperatureSensorId")
		externalTemperature = self.read_temperature_for_setting(settings, "externalTemperatureSensorId")
		extraTemperature = self.read_temperature_for_setting(settings, "extraTemperatureSensorId")

		# make some values up.
		# extraTemperature = null
		voltage = 24.3
		currentMilliAmps = 23.3
		# V1.2 PCB only
		lightLevel = 128
		fan0Speed = 12
		fan1Speed = 23
		gpioPin16Value = "LOW"
		gpioPin26Value = "HIGH"
		leds = "off"

		return dict(
			externalTemperature= externalTemperature, 
			internalTemperature= internalTemperature,
			pcbTemperature = pcbTemperature,
			extraTemperature = extraTemperature,
			voltage = round(voltage,1),
			currentMilliAmps = round(currentMilliAmps,1),
			powerWatts = round(voltage * (currentMilliAmps/1000),0),
			lightLevel = lightLevel,
			fan0Speed = fan0Speed,
			fan1Speed = fan1Speed,
			leds = leds,
			gpioPin16Value = gpioPin16Value,
			gpioPin26Value = gpioPin26Value
			)
		
	# Pass in the key for the settings we want the temperature for
	# and read the temperature if the sensor is defined.
	def read_temperature_for_setting(settings, settingsKey):

		try: 
			self._logger.warn("settingsKey: " + settingsKey)
			sensor = settings.get([settingsKey])
			self._logger.warn(settingsKey + " == " + sensor)

			if sensor:
				self._logger.warn("Reading sensor: " + sensor)
				sensorReading = self.read_temp(sensor)
				self._logger.warn("Read sensor: " + sensor + ":" + sensorReading)
				return sensorReading
			else:
				self._logger.warn("No sensor for setting: " + settingsKey)
				return None;
		except:
			self._logger.warn("Exception in read_temperature_for_settings.")
			pass

	# Read the temperature from the sensor.
	def read_temp(sensor):
		lines = temp_raw(sensor)
		self._logger.info("lines = : " + lines)
		while lines[0].strip()[-3:] != 'YES':
			time.sleep(0.2)
			lines = temp_raw(sensor)

		temp_output = lines[1].find('t=')

		if temp_output != -1:
			temp_string = lines[1].strip()[temp_output+2:]
			temp_c = float(temp_string) / 1000.0
			self._logger.info("Read temperature of : " + temp_c)
			return round(temp_c,1)

	# Read temperature raw output from sensor	
	def temp_raw(sensor):
		sensorPath = "/sys/bus/w1/devices/{}/w1_slave".format(sensor[1])
		f = open(sensorPath, 'r')
		lines = f.readlines()
		f.close()
		return lines

