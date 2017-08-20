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
		# TODO: Dispose of these when we exit.
		self._readPiPowerValuesTimer = None
		self._publishPiPowerValuesTimer = None

		if sys.platform == "linux2":
			self._powerHat = PiPowerHat();
		else:
			self._powerHat = MockPiPowerHat();

		self._temperatureSensors = self._powerHat.getTemperatureSensors()

	def on_after_startup(self):
		self._logger.info("Pi Power plugin startup. Starting timer.")
		timerInterval = self._settings.get(["timerInterval"])
		eventTimerInterval = self._settings.get(["eventTimerInterval"])
		self.start_timer(timerInterval, eventTimerInterval)

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
			# TODO: Inject this at on_settings_load as it won't update.
			temperatureSensorOptions=self._temperatureSensors,
			temperatureSensors = [
				dict(sensorId="", caption="PSU PCB"),
				dict(sensorId="", caption="Internal Air"),
				dict(sensorId="", caption="External Air"),
				dict(sensorId="", caption="Extra"),
			],
			fans = [
				dict(fanId=0,
				     name="Fan 0",  # Caption in settings
					 enabled=True,
					 caption="3 Pin Small Fan",
					 defaultSpeed=0, # 0 = stoppepd
					 pwmFrequency=200),
				dict(fanId=1,
				     name="Fan 1", # Caption in settings
				     enabled=True,
				     caption="4 Pin Fan",
				     defaultSpeed=0,  # 0 = stoppepd
				     pwmFrequency=200)
			],
			fan0Caption="Cooling Fan",
			fan1Caption="Pi Fan",
			pwmFrequency=200,
			lightSensorCaption = "Light Level",
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
				dict(
					pin=20,  # BCM Number
					caption="GPIO 20",
					# Disabled = 0, Input = 1, Input pull down = 2, Input pull up = 3, Output = 4
					mode=1,
				),
				dict(
					pin=21,  # BCM Number
					caption="GPIO 21",
					# Disabled = 0, Input = 1, Input pull down = 2, Input pull up = 3, Output = 4
					mode=1,
				),
				dict(
					pin=11,  # LED D7 on Pi Power Hat 1.2.1
					caption="GPIO 11",
					# Disabled = 0, Input = 1, Input pull down = 2, Input pull up = 3, Output = 4
					mode=4,
				),
			],
			timerInterval = 2.0,
			eventTimerInterval=30.0,
			automationOptions = [
				# Fan speed will go to default speed, then be increased to the maximum fanSpeed
				# from the matching automation options
				# Device is Fan or GPIO or Printer (for pause)
				# DeviceId is Fan Number or GPIO Pin
				dict(enabled=True, name="Print Started", eventName="OctoPrint: Print Started Event", action="Set Fan Speed", device="Fan 1", setValue=0, timer=0),
				dict(enabled=True, name="Print Done", eventName="PrintDone", action="Set Fan Speed", device="Fan 1", setValue=100, timer=60),
				dict(enabled=True, name="Print Failed", eventName="PrintFailed", action="Set Fan Speed", device="Fan 1", setValue=100, timer=60),
				# Custom event from Pi Power Plugin (ohh, that's us!)
				dict(enabled=True, name="Above Temperature", eventName="AboveTemperature", action="Set Fan Speed", device="Fan 0", setValue=60, timer=3600, value=50),
				dict(enabled=True, name="Above LightLevel", eventName="AboveLightLevel", action="Set Fan Speed", device="Fan 1", setValue=60, timer=60, value=50),
			],
			fanSpeedOptions=[0, 20, 40, 60, 80, 100],
			# Fan: Set speed (0==off, 20-100=on)
			# GPIO: Set value for pin
			# Printer options: Pause (e.g. filament change)
			# OctoPrint option: Fire an event (PrintStarted, PrintDone" etc.
			actionOptions=["Set Fan Speed", "Set GPIO Pin", "Send Printer Command", "Raise OctoPrint Event"],
			automationEventOptions = ["OctoPrint: Print Started Event", "PrintDone", "PrintFailed", "AboveTemperature", "AboveLightLevel", "BelowLightLevel"]
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
				displayName="Pi Power",
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
			self._logger.info("setGPID called. Pin: {0}, Value: {1}".format(data['pin'], data['value']))
			self._powerHat.set_gpio(data['pin'], data['value'])
		elif command == "setFanState":
			self._logger.info("setFanState called.")
			self._powerHat.set_fan_state(data['fanId'], data['state'])
		elif command == "setFanSpeed":
			self._logger.info("setFanSpeed called.")
			self._powerHat.set_fan_speed(data['fanId'], data['speed'])
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

	def start_timer(self, interval, event_timer_interval):
		self._readPiPowerValuesTimer = RepeatedTimer(interval, self.getPiPowerValues, None, None, True)
		self._readPiPowerValuesTimer.start()
		self._logger.info("Started timer. Interval: {0}s".format(interval))

		self._publishPiPowerValuesTimer = RepeatedTimer(event_timer_interval, self.publish_pi_power_event, None, None, True)
		self._publishPiPowerValuesTimer .start()
		self._logger.info("Started event publisher timer. Interval: {0}s".format(event_timer_interval))


	def getPiPowerValues(self):
		#self._logger.debug("Getting values from PiPower...")

		try:
			pluginData = self._powerHat.getPiPowerValues(self._settings)

			#self._logger.info("Publishing PiPower values")
			self._plugin_manager.send_plugin_message(self._identifier, pluginData)

			return pluginData
		except Exception as e:
			self._logger.warn("Errir getting the power value: {0}".format(e))


	# A less frequent pi measurements publisher
	# for other plugins (e.g. Tinamous) to use
	def publish_pi_power_event(self):
		pluginData = self._powerHat.getPiPowerValues(self._settings)

		# Publish the measurements on the event bus for others.
		self._event_bus.fire("PiPowerMeasured", pluginData)

# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Pi Power"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PipowerPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

