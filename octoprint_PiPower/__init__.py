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

from .mockPiPowerHat import MockPiPowerHat
from .piPowerHat import PiPowerHat

# TODO: Include events so that the fans can be switched on
# when a print is finished.
class PipowerPlugin(octoprint.plugin.StartupPlugin,
					octoprint.plugin.SettingsPlugin,
                    octoprint.plugin.AssetPlugin,
                    octoprint.plugin.TemplatePlugin,
					octoprint.plugin.SimpleApiPlugin):

	def __init__(self):
		self._readPiPowerValuesTimer = None

		if sys.platform == "linux2":
			self._powerHat = PiPowerHat();
		else:
			self._powerHat = MockPiPowerHat();

		self._temperatureSensors = self._powerHat.getTemperatureSensors()

	def on_after_startup(self):
		self._logger.info("Pi Power plugin startup. Starting timer.")
		timerInterval = self._settings.get(["timerInterval"])
		self.startTimer(timerInterval)

	def initialize(self):
		self._logger.setLevel(logging.DEBUG)

		# Do we have settings at this time.
		self._powerHat.initialize(self._settings);
		self._logger.info("Pi Power Plugin [%s] initialized..."%self._identifier)

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		self._logger.info("Getting available temperature sensors for settings.")

		return dict(
			# Initialize temperature sensors to empty otherwise
			# if sensor is not found it hangs.
			temperatureSensorOptions=self._temperatureSensors,
			temperatureSensors = [
				dict(sensorId="", caption="PSU PCB"),
				dict(sensorId="", caption="Internal Air"),
				dict(sensorId="", caption="External Air"),
				dict(sensorId="", caption="Extra"),
			],
			fan0Caption="Cooling Fan",
			fan1Caption="Pi Fan",
			pwmFrequency=200,
			lightSensorCaption = "Light Level",
			ledsCaption = "LEDs",
			gpioOptions = [
				dict(
					pin=16,  #BCM Number
					caption="GPIO 16",
					# Disabled = 0, Input = 1, Input pull down = 2, Input pull up = 3, Output = 4
					mode=1,
				),
				dict(
					pin=26,  # BCM Number
					caption="GPIO 26",
					# Disabled = 0, Input = 1, Input pull down = 2, Input pull up = 3, Output = 4
					mode=1,
				),
			],
			timerInterval = 2.0
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
				user="Tinamous",
				repo="OctoPrint-PiPower",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/Tinamous/OctoPrint-PiPower/archive/{target_version}.zip"
			)
		)

	# API POST command options
	def get_api_commands(self):
		return dict(
			setGPIO=["pin", "value"],
			setFanState=["fanId", "state"], # On/Off
			setFanSpeed=["fanId", "speed"],
			setLEDsState=["state"],
			setLEDsMode=["mode"],
			setDisplayBacklight=["state"],
		)

	# API POST command
	# POST: http://localhost:5000/api/plugin/pipower
	# X-Api-Key: <key>
	# {
	#	"command": "setFan",
	#   "fanId": "1",
	#	"speed": "100",
	# }
	def on_api_command(self, command, data):
		if command == "setGPIO":
			self._logger.info("setGPID called. Options: {Options}".format(**data))
			self._powerHat.set_gpio(data['pin'], data['value'])
		elif command == "setFanState":
			self._logger.info("setFanState called.")
			self._powerHat.set_fan_state(data['fanId'], data['state'])
		elif command == "setFanSpeed":
			self._logger.info("setFanSpeed called.")
			self._powerHat.set_fan_speed(data['fanId'], data['speed'])
		elif command == "setLEDs":
			self._logger.info("seltLEDs called. Options: {Options}".format(**data))
		elif command == "setDisplayBacklight":
			self._logger.info("setDisplayBacklight called. Options: {Options}".format(**data))

		# Update the power values measured after the change.
		self.getPiPowerValues()


	# API GET command
	# GET: http://localhost:5000/api/plugin/pipower?apikey=<key>
	def on_api_get(self, request):
		self._logger.info("API Request: {}".format(request))
		sensorData = self.getPiPowerValues()
		return flask.jsonify(sensorData)

	def startTimer(self, interval):
		self._readPiPowerValuesTimer = RepeatedTimer(interval, self.getPiPowerValues, None, None, True)
		self._readPiPowerValuesTimer.start()
		self._logger.info("Started timer. Intervale: {0}".format(interval))

	def getPiPowerValues(self):
		#self._logger.info("Getting values from PiPower...")

		pluginData = self._powerHat.getPiPowerValues(self._settings)

		#self._logger.info("Publishing PiPower values")
		self._plugin_manager.send_plugin_message(self._identifier, pluginData)

		return pluginData;

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

