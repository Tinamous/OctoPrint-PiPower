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

	def on_after_startup(self):
		self._logger.info("Pi Power plugin startup. Starting timer.")
		self.startTimer(10.0)

	def initialize(self):
		self._logger.setLevel(logging.DEBUG)

		if sys.platform == "linux2":
			self._powerHat = PiPowerHat();
		else:
			self._powerHat = MockPiPowerHat();

		# Do we have settings at this time.
		self._powerHat.initialize(self._settings);
		self._logger.info("Pi Power Plugin [%s] initialized..."%self._identifier)

		fan0Caption = self._settings.get(["fan0Caption"])
		self._logger.info("Pi Power Plugin. Settings Fan 0 Caption: {0}.".format(fan0Caption))

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			pcbTemperatureSensorCaption="PSU PCB",
			pcbTemperatureSensorId="28-0000070e3270",
			internalTemperatureSensorCaption="Internal Air",
			internalTemperatureSensorId="28-000007538a2b",
			externalTemperatureSensorCaption="External Air",
			externalTemperatureSensorId="",
			extraTemperatureSensorCaption="Extra",
			extraTemperatureSensorId="",
			fan0Caption="Cooling Fan",
			fan1Caption="Pi Fan",
			pwmFrequency=200,
			lightSensorCaption = "Light Level",
			ledsCaption = "LEDs",
			gpioPin16Caption = "GPIO Pin 16",
			gpioPin26Caption = "GPIO Pin 26",
			temperatureSensors = ['','28-000007538f5b','28-0000070e4078','28-0000070e3270','28-000007538a2b' ]
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
			setGPIO16=["value"],
			setGPIO26=["value"],
			setFan=["fanId", "speed", "state"],
		)

	# API POST command
	# POST: http://localhost:5000/api/plugin/pipower
	# X-Api-Key: <key>
	# {
	#	"command": "setFan",
	#   "fanId": "1",
	#	"speed": "100",
	#   "frequency": "20000"
	# }
	def on_api_command(self, command, data):
		if command == "setGPIO16":
			self._logger.info("setGPIO16 called, value = {value}".format(**data))
		elif command == "setGPIO26":
			self._logger.info("setGPIO26 called, value = {value}".format(**data))
		elif command == "setFan":
			self._logger.info("setFan called, percentage is {speed}".format(**data))
			self._powerHat.set_fan(data['fanId'], data['state'], data['speed'], data['frequency'])

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

