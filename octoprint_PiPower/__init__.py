# coding=utf-8
from __future__ import absolute_import

__author__ = "Stephen Harrison <Stephen.Harrison@AnalysisUK.com>"
__license__ = 'Creative Commons Share Alike 4.0'
__copyright__ = "Copyright (C) 2017 Analysis UK Ltd - Released under terms of the CC-SA-4.0 License"

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin
from octoprint.util import RepeatedTimer

import flask

import sys
import os
import time

import logging
import logging.handlers
#import RPi.GPIO as GPIO 

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# TODO: Include events so that the fans can be switched on
# when a print is finished.
class PipowerPlugin(octoprint.plugin.StartupPlugin,
					octoprint.plugin.SettingsPlugin,
                    octoprint.plugin.AssetPlugin,
                    octoprint.plugin.TemplatePlugin,
					octoprint.plugin.SimpleApiPlugin):

	def __init__(self):
		#self.isRaspi = False
        #self.debugMode = False      # to simulate temp on Win/Mac
        #self.displayRaspiTemp = True
		self._readPiPowerValuesTimer = None

	def on_after_startup(self):
		self._logger.info("Pi Power plugin startup. Starting timer.")
		self.startTimer(10.0)

	def initialize(self):
		self._logger.setLevel(logging.DEBUG)
		
		#self._logger.info("Running RPi.GPIO version '{0}'...".format(GPIO.VERSION))
		#if GPIO.VERSION < "0.6":
		#	raise Exception("RPi.GPIO must be greater than 0.6")
			
		#GPIO.setmode(GPIO.BCM)
		#GPIO.setwarnings(False)
		
		self._logger.info("Pi Power Plugin [%s] initialized..."%self._identifier)

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			pcbTemperatureSensorCaption="PSU PCB",
			pcbTemperatureSensorId="28-000007538f5b", 
			internalTemperatureSensorCaption="Internal Air",
			internalTemperatureSensorId="28-0000070e4078",
			externalTemperatureSensorCaption="External Air",
			externalTemperatureSensorId="",
			extraTemperatureSensorCaption="Extra",
			extraTemperatureSensorId="",
			fan0Caption="Cooling Fan",
			fan1Caption="Pi Fan",
			lightSensorCaption = "Light Level",
			ledsCaption = "LEDs",
			gpioPin16Caption = "GPIO Pin 16",
			gpioPin26Caption = "GPIO Pin 26",

			# V1.2 PCB
			# GPIO 2x pins (enable gpio option)
			# DotStar pins (enable dotstar option)
			# 
			)

	def get_template_configs(self):
		return [
			#dict(type="navbar", custom_bindings=False),
			dict(type="settings", custom_bindings=False),
			dict(type="tab", name="Pi Power")
		]

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/PiPower.js"],
			css=["css/PiPower.css"],
			less=["less/PiPower.less"]
		)

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			PiPower=dict(
				displayName="PiPower Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="BookSwapSteve",
				repo="OctoPrint-PiPower",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/BookSwapSteve/OctoPrint-PiPower/archive/{target_version}.zip"
			)
		)

	# API POST command options
	def get_api_commands(self):
		return dict(
			setGPIO16=["value"],
			setGPIO26=["value"],
			setFan0=["percentage"],
			setFan1=["percentage"]
		)

	# API POST command
	# POST: http://localhost:5000/api/plugin/pipower
	# X-Api-Key: <key>
	# {
	#	"command": "setFan0",
	#	"percentage": "100"
	# }
	def on_api_command(self, command, data):
		if command == "setGPIO16":
			self._logger.info("setGPIO16 called, value = {value}".format(**data))
		elif command == "setGPIO26":
			self._logger.info("setGPIO26 called, value = {value}".format(**data))
		elif command == "setFan0":
			self._logger.info("setFan0 called, percentage is {percentage}".format(**data))
		elif command == "setFan1":
			self._logger.info("setFan1 called, percentage is {percentage}".format(**data))

	# API GET command
	# GET: http://localhost:5000/api/plugin/pipower?apikey=<key>
	def on_api_get(self, request):
		self._logger.info("API Request: {}".format(request))
		sensorData = self.getPiPowerValues()
		return flask.jsonify(sensorData)

	def startTimer(self, interval):
		self._readPiPowerValuesTimer = RepeatedTimer(interval, self.getPiPowerValues, None, None, True)
		self._readPiPowerValuesTimer.start()
		self._logger.info("Started timer")

	def getPiPowerValues(self):
		self._logger.info("Getting values from PiPower...")

		if sys.platform == "linux2":
			self._logger.info("Getting values from PiPower PCB")
			pcbTemperature = self.read_temperature_for_setting("pcbTemperatureSensorId")
			internalTemperature = self.read_temperature_for_setting("internalTemperatureSensorId")
			externalTemperature = self.read_temperature_for_setting("externalTemperatureSensorId")
			extraTemperature = self.read_temperature_for_setting("extraTemperatureSensorId")

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
		else:
			self._logger.debug("Making up values for debug")
			import random
			def randrange_float(start, stop, step):
				return random.randint(0, int((stop - start) / step)) * step + start

			# make some values up.
			extraTemperature = None
			externalTemperature = randrange_float(30, 60, 0.1)
			internalTemperature = randrange_float(30, 60, 0.1)
			pcbTemperature = randrange_float(30, 60, 0.1)
			voltage = randrange_float(11, 13, 0.01)
			currentMilliAmps = randrange_float(600, 1500, 0.1)
			lightLevel = randrange_float(0, 100, 1)
			fan0Speed = randrange_float(0, 100, 1)
			fan1Speed = randrange_float(0, 100, 1)
			gpioPin16Value = "HIGH"
			gpioPin26Value = "LOW"
			leds = "on"           

		self._logger.info("Publishing values")
		pluginData = dict(
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

		self._plugin_manager.send_plugin_message(self._identifier, pluginData)

		return pluginData;

	# Pass in the key for the settings we want the temperature for
	# and read the temperature if the sensor is defined.
	def read_temperature_for_setting(settingsKey):
		sensor = self._settings.get([settingsKey])

		if sensor:
			return self.read_temp(sensor)
		else:
			return None;

	# Read the temperature from the sensor.
	def read_temp(sensor):

		lines = temp_raw(sensor)
		while lines[0].strip()[-3:] != 'YES':
			time.sleep(0.2)
			lines = temp_raw(sensor)

		temp_output = lines[1].find('t=')

		if temp_output != -1:
			temp_string = lines[1].strip()[temp_output+2:]
			temp_c = float(temp_string) / 1000.0
			return round(temp_c,1)

	# Read temperature raw output from sensor	
	def temp_raw(sensor):

		sensorPath = "/sys/bus/w1/devices/{}/w1_slave".format(sensor[1])
		f = open(sensorPath, 'r')
		lines = f.readlines()
		f.close()
		return lines



# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "PiPower"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PipowerPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

