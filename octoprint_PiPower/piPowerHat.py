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
		
		setting = settings.get(["pcbTemperatureSensorId"]);
		self._logger.warn("Read temperature. Sensor: " + setting)
		pcbTemperature = self.read_temp(setting)
		self._logger.warn("Got PCB Temperature")

		#pcbTemperature = self.read_temperature_for_setting(settings, "pcbTemperatureSensorId")
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
	def read_temperature_for_setting(self, settings, settingsKey):

		try: 
			sensor = settings.get([settingsKey])

			if sensor:
				self._logger.warn("Reading sensor: " + sensor)
				return self.read_temp(sensor)
			else:
				self._logger.warn("No sensor for setting: " + settingsKey)
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
