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
import logging
import logging.handlers




os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# Real hardware
class PiPowerHat:
	def __init__(self):
		self._logger = logging.getLogger(__name__)
		self._fanSpeeds = [0,0]
		self._fanStates = [0,0]
		self._fan_pwm_pins = [18, 13]
		self._settings = None

	def initialize(self, settings):
		self._logger.info("PiPowerHat. GPIO initializing")
		self._logger.setLevel(logging.DEBUG)
		self._settings = settings
		import RPi.GPIO as GPIO

		# Needed for hardware PWM usage
		# This has to be done locally as it doesn't
		# install on Windows and hence breaks loading
		import wiringpi

		self._logger.info("Running RPi.GPIO version '{0}'...".format(GPIO.VERSION))
		self._logger.info("Running WiringPi2 Pi Board Version: '{0}'...".format(wiringpi.piBoardRev()))

		if GPIO.VERSION < "0.6":
			raise Exception("RPi.GPIO must be greater than 0.6")
			
		#GPIO.setmode(GPIO.BCM)
		#GPIO.setwarnings(True)

		# Setup to use BCM pin numbers.
		wiringpi.wiringPiSetupGpio()

		# Setup the fan PWMs. Pi (V3) only supports 2 hardware PWM channels.
		# Need to use 20-25kHz PWM frequency for proper fan control which
		# is not available in other libraries.

		self._logger.info("Initializing PWM Fans.")
		# This is the clock divisor, not the actual clock frequency
		# Pi 3 divisor of 10 gets about 20kHz
		wiringpi.pwmSetClock(10)
		# Set range to 100 rather than 1024 for easier %
		wiringpi.pwmSetRange(100)

		# 0 = I think is this Balanced, it works better anyway
		# Keeps the frequency constant with a larger/smaller on time
		# Mode 1 changes the frequency which messes with the fans.
		wiringpi.pwmSetMode(0)

		# FAN 0 (Pin 12 - BCM/GPIO 18)
		# FAN 1 (Pin 33 - BCM/GPIO 13)
		for fan_pin in self._fan_pwm_pins:
			self._logger.info("Initializing PWM for fan on pin '{0}'...".format(fan_pin))
			wiringpi.pinMode(fan_pin, 2) # mode 2 = pwm
			wiringpi.pwmWrite(fan_pin, 0) # turn off


		wiringpi.pinMode(13, 2)
		wiringpi.pwmWrite(13, 0)  # duty cycle between 0 and 1024. 0 = off, 1024 = fully on

		self._logger.info("PiPowerHat. GPIO initialized")

	def getPiPowerValues(self, settings):
		self._logger.info("Getting values from PiPower")			

		self._logger.info("Reading temperatures.")			
		pcbTemperature = self.read_temperature_for_setting(settings, "pcbTemperatureSensorId")
		internalTemperature = self.read_temperature_for_setting(settings, "internalTemperatureSensorId")
		externalTemperature = self.read_temperature_for_setting(settings, "externalTemperatureSensorId")
		extraTemperature = self.read_temperature_for_setting(settings, "extraTemperatureSensorId")

		self._logger.info("Reading Power.")			
		# make some values up.
		# extraTemperature = null
		voltage = 24.3
		currentMilliAmps = 23.3

		self._logger.info("Reading Light Level.")			
		# V1.2 PCB only
		lightLevel = 128
		

		self._logger.info("Reading GPIOs.")			
		# TODO: Determine if input or outputs.
		gpioPin16Value = "LOW"
		gpioPin26Value = "HIGH"

		# These should be local variables as to how the fan/leds were set.
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
			fan0On= self._fanStates[0],
			fan0Speed = self._fanSpeeds[0],
			fan1On= self._fanStates[1],
			fan1Speed = self._fanSpeeds[1],
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


	def set_fan(self, fan_id, state, speed, frequency):
		self._logger.warn("****Setting fan: {0}, State: {1} Speed: {2} Frequency: {3}".format(fan_id, state, speed, frequency))
		self._fanSpeeds[fan_id] = speed
		self._fanStates[fan_id] = state

		import wiringpi

		if state:
			wiringpi.pwmWrite(self._fan_pwm_pins[fan_id], speed)
		else:
			wiringpi.pwmWrite(self._fan_pwm_pins[fan_id], 0)



