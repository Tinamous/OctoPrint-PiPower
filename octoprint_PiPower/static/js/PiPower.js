/*
 * View model for OctoPrint-PiPower
 *
 * Author: Stephen Harrison
 * License: CC-SA 4.0
 */
$(function() {
	function PiPowerFanViewModel(caption, fanId) {
        var self = this;

        self.caption = ko.observable(caption);
        self.fanId = fanId;
        self.state = ko.observable(false);
        // Currently selected speed to shpw
        self.speed = ko.observable();
        self.speedOptions = ko.observableArray([0, 20, 40, 60, 80, 100]);
        self.selectedSpeedOption = ko.observable(0);

        self.on = function () {
            console.log("Switch fan on");
            self.state(true);
            self.setFanParameters();
        }

        self.off = function () {
            console.log("Switch fan off");
            self.state(false);
            self.setFanParameters();
        }

        self.update = function () {
        	self.setFanParameters();
        }

		self.setFanParameters = function() {

            var payload = {
                fanId: self.fanId,
				state: self.state(),
				speed: self.selectedSpeedOption()
            };
            OctoPrint.simpleApiCommand("pipower", "setFan", payload, {});
            self.speed(self.selectedSpeedOption());
		}

		return self;
	}

	function PiPowerLedViewModel(caption) {
		var self = this;
		self.caption = ko.observable(caption);
		self.value = ko.observable();

		self.ledModes = ko.observableArray(["White", "Red", "Green", "Blue"]);
		self.selectedLedMode = ko.observable("White");

		self.setMode = function() {
			console.log("Set LED more");
		}

		self.on = function() {
			console.log("Switch on LEDs");
		}

		self.off = function() {
			console.log("Switch off LEDs");
		}

		return self;
	}

	function PiPowerGPIOViewModel(caption) {
		var self = this;
		self.caption = ko.observable(caption);
		self.value = ko.observable();

		self.setLow = function() {
			console.log("GPIO Set Low");
		}

		self.setHigh = function() {
			console.log("GPIO Set High");
		}

		return self;
	}

	// View model for measured values (temperature, voltage, current etc).
	function PiPowerMeasuredValueViewModel(caption, enabled) {
		var self = this;
		self.enabled = ko.observable(enabled);
		self.caption = ko.observable(caption);
		self.value = ko.observable();
		self.valueHistory = [];

		self.setValue = function(value) {
			self.value(value);
			self.valueHistory.push([Date.now(),value]);
			// 6 points per minute, 1 hour history
			if (self.valueHistory.length > 6 * 60) {
				self.valueHistory.shift(0, 1);
			}
		}

		return self;
	}

    function PiPowerViewModel(parameters) {
        var self = this;

        // assign the injected parameters, e.g.:

		// parameters are defined by the second part of the OCTOPRINT_VIEWMODELS below.
		//self.loginState = parameters[0];
//		self.settings = parameters[0];
		self.global_settings = parameters[0];
		self.printer = parameters[1];
		console.log("Global Settings: " + self.global_settings );
		//self.navBarTempModel = parameters[0];

		self.externalTemperature = new PiPowerMeasuredValueViewModel("External", false); // ko.observable();
		self.internalTemperature = new PiPowerMeasuredValueViewModel("Internal", false); //ko.observable();
		self.pcbTemperature = new PiPowerMeasuredValueViewModel("PCB", true); //ko.observable();
		self.extraTemperature = new PiPowerMeasuredValueViewModel("Extra", false); //ko.observable();

		self.temperatures = [self.externalTemperature, self.internalTemperature, self.pcbTemperature, self.extraTemperature]

		self.voltage = new PiPowerMeasuredValueViewModel("Voltage", true);
		self.current = new PiPowerMeasuredValueViewModel("Current", true);
		self.power = new PiPowerMeasuredValueViewModel("Power", true);

		//self.powerMeasurements = [self.voltage, self.current, self.power];
		// V & I only, makes plotting difficult otherwise.
		self.powerMeasurements = [self.voltage, self.current];

		self.lightLevel = new PiPowerMeasuredValueViewModel("Light Level")
		self.leds = new PiPowerLedViewModel("LEDs");

		self.fan0 = new PiPowerFanViewModel("F0", 0);
		self.fan1 = new PiPowerFanViewModel("F1", 1);

		self.gpioPin16 = new PiPowerGPIOViewModel("16");
		self.gpioPin26 = new PiPowerGPIOViewModel("26");

		self.onBeforeBinding = function () {
            self.settings = self.global_settings.settings.plugins.pipower;
			console.log("PiPower Settings: " + self.settings );

			self.fan0.caption(self.settings.fan0Caption());
			self.fan1.caption(self.settings.fan1Caption());
			self.gpioPin16.caption(self.settings.gpioPin16Caption());
			self.gpioPin26.caption(self.settings.gpioPin26Caption());

			self.externalTemperature.caption(self.settings.externalTemperatureSensorCaption());
			self.internalTemperature.caption(self.settings.internalTemperatureSensorCaption());
			self.pcbTemperature.caption(self.settings.pcbTemperatureSensorCaption());
			self.extraTemperature.caption(self.settings.extraTemperatureSensorCaption());

			self.leds.caption(self.settings.ledsCaption());

			self.updateTemperaturePlot();
			self.updatePowerPlot();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "pipower") {
                return;
            }

            if (!data.internalTemperature) {
                self.internalTemperature.enabled(false);
            } else {
				self.internalTemperature.enabled(true);
                self.internalTemperature.setValue(data.internalTemperature);
            }

			if (!data.externalTemperature) {
                self.externalTemperature.enabled(false);
            } else {
				self.externalTemperature.enabled(true);
                self.externalTemperature.setValue(data.externalTemperature);
            }

			if (!data.pcbTemperature) {
                self.pcbTemperature.enabled(false);
            } else {
				self.pcbTemperature.enabled(true);
                self.pcbTemperature.setValue(data.pcbTemperature);
            }

			if (!data.extraTemperature) {
                self.extraTemperature.enabled(false);
            } else {
				self.extraTemperature.enabled(true);
                self.extraTemperature.setValue(data.extraTemperature);
            }

			self.voltage.setValue(data.voltage);
			self.current.setValue(data.currentMilliAmps);
			self.power.setValue(data.powerWatts);

			self.lightLevel.setValue(data.lightLevel);
			self.leds.value(data.leds);

			self.fan0.speed(data.fan0Speed);
			self.fan1.speed(data.fan1Speed);

			self.gpioPin16.value(data.gpioPin16Value);
			self.gpioPin26.value(data.gpioPin26Value);

			self.updateTemperaturePlot();
			self.updatePowerPlot();
	    };

		// Stolen from temperature.js
		self.temperaturePlotOptions = {
            yaxis: {
                min: 20,
                max: 60,
                ticks: 10
            },
            xaxis: {
                mode: "time",
                minTickSize: [2, "minute"],
                tickFormatter: function(val, axis) {
                    if (val == undefined || val == 0)
                        return ""; // we don't want to display the minutes since the epoch if not connected yet ;)

                    // current time in milliseconds in UTC
                    var timestampUtc = Date.now();

                    // calculate difference in milliseconds
                    var diff = timestampUtc - val;

                    // convert to minutes
                    var diffInMins = Math.round(diff / (60 * 1000));
                    if (diffInMins == 0)
                        return gettext("just now");
                    else
                        return "- " + diffInMins + " " + gettext("min");
                }
            },
            legend: {
                position: "sw",
                noColumns: 2,
                backgroundOpacity: 0
            }
        };

		// Stolen from temperature.js
		self.updateTemperaturePlot = function() {
			//console.log("Updating temperatures chart");
            var graph = $("#pipower-temperature-graph");
            if (graph.length) {
                var data = [];

                var maxTemps = [310/1.1];

                _.each(self.temperatures, function(temperature) {

					if (temperature.enabled())
					{
						var actuals = temperature.valueHistory;

						data.push({
							label: temperature.caption(),
							//color: 'red',
							data: actuals
						});

	                    //maxTemps.push(self.getMaxTemp(actuals, targets));
					}
                });

                //self.plotOptions.yaxis.max = Math.max.apply(null, maxTemps) * 1.1;
                $.plot(graph, data, self.temperaturePlotOptions);
            }
        };

		self.powerPlotOptions = {
            yaxis: {
                min: 0,
                max: 100,
                ticks: 10
            },
			yaxes: [{
				// Voltage
                min: 0,
                max: 30,
                ticks: 5
            },{
				// Current
                min: 0,
                max: 3000,
                ticks: 100,
				alignTicksWithAxis: 1,
				position: "right",
            }],
            xaxis: {
                mode: "time",
                minTickSize: [2, "minute"],
                tickFormatter: function(val, axis) {
                    if (val == undefined || val == 0)
                        return ""; // we don't want to display the minutes since the epoch if not connected yet ;)

                    // current time in milliseconds in UTC
                    var timestampUtc = Date.now();

                    // calculate difference in milliseconds
                    var diff = timestampUtc - val;

                    // convert to minutes
                    var diffInMins = Math.round(diff / (60 * 1000));
                    if (diffInMins == 0)
                        return gettext("just now");
                    else
                        return "- " + diffInMins + " " + gettext("min");
                }
            },
            legend: {
                position: "sw",
                noColumns: 2,
                backgroundOpacity: 0
            }
        };

		self.updatePowerPlot = function() {
			//console.log("Updating Power chart");
            var graph = $("#pipower-power-graph");
            if (graph.length) {
                var data = [];

                var maxTemps = [310/1.1];
				var axis = 1;

                _.each(self.powerMeasurements, function(powerMeasurement) {

					if (powerMeasurement.enabled())
					{
						var actuals = powerMeasurement.valueHistory;

						data.push({
							label: powerMeasurement.caption(),
							//color: 'red',
							data: actuals,
							yaxis: axis++,
						});

	                    //maxTemps.push(self.getMaxTemp(actuals, targets));
					}
                });

                //self.plotOptions.yaxis.max = Math.max.apply(null, maxTemps) * 1.1;
                $.plot(graph, data, self.powerPlotOptions);
            }
        };
	};

    // view model class, parameters for constructor, container to bind to
    OCTOPRINT_VIEWMODELS.push([
        PiPowerViewModel,
		["settingsViewModel", "printerStateViewModel"],
		["#navbar_plugin_pipower", "#tab_plugin_pipower"]
    ]);
});

/* Stolen from NavBar Temperature plugin. */
function formatBarTemperature(toolName, actual, target) {
    var output = toolName + ": " + _.sprintf("%.1f&deg;C", actual);

    if (target) {
        var sign = (target >= actual) ? " \u21D7 " : " \u21D8 ";
        output += sign + _.sprintf("%.1f&deg;C", target);
    }

    return output;
};
