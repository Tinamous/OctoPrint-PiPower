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
        self.speedOptions = ko.observableArray([20, 40, 60, 80, 100]);
        self.selectedSpeedOption = ko.observable(100);

        self.on = function () {
            console.log("Switch fan on");
            self.setFanState(true);
        };

        self.off = function () {
            console.log("Switch fan off");
            self.setFanState(false);
        };

        self.setFanState = function(state)  {
            self.state(state);
            var payload = {
                fanId: self.fanId,
				state: self.state(),
            };
            OctoPrint.simpleApiCommand("pipower", "setFanState", payload, {});
        };

        self.update = function () {
            self.speed(self.selectedSpeedOption());

        	var payload = {
                fanId: self.fanId,
				speed: self.speed(),
            };
            OctoPrint.simpleApiCommand("pipower", "setFanSpeed", payload, {});

        };

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
		};

		self.on = function() {
			console.log("Switch on LEDs");
		};

		self.off = function() {
			console.log("Switch off LEDs");
		};

		return self;
	}

	function PiPowerGPIOViewModel(pin) {
		var self = this;
		// BCM/GPIO number
		self.pin = ko.observable(pin);
		self.caption = ko.observable("");
		self.value = ko.observable();
		// Disabled = 0, Input = 1, Input pull down = 2, Input pull up = 3, Output = 4
		self.mode = ko.observable(0);

		self.showControl = ko.computed(function() {
            if (self.mode() == 4) {
                return true;
            }
            return false;
        }, this);

		self.modeText = ko.computed(function() {
		    mode = parseInt(self.mode());
		    switch (mode) {
                case 0:
                    return "Disabled";
                case 1:
                    return "Input";
                case 2:
                    return "Input Pull Down";
                case 3:
                    return "Input Pull Up";
                case 4:
                    return "Output";
                default:
                    return "Unknown: " + self.mode();
            }
        });

		self.setSettings = function(settings) {
		    self.caption(settings.caption());
            self.mode(settings.mode());
        };

		self.setLow = function() {
			console.log("GPIO Set Low");
		};

		self.setHigh = function() {
			console.log("GPIO Set High");
		};

		return self;
	}

	// View model for measured values (temperature, voltage, current etc).
	function PiPowerMeasuredValueViewModel(caption, enabled) {
		var self = this;
		self.enabled = ko.observable(enabled);
		self.caption = ko.observable(caption);
		self.sensorId = ko.observable();
		self.value = ko.observable();
		self.maxValue = ko.observable(null);
		self.minValue = ko.observable(null);
		self.valueHistory = [];

		self.setValue = function(value) {
            self.value(value);
            self.valueHistory.push([Date.now(), value]);
            // 60 points per minute, 6 hour history
            if (self.valueHistory.length > 6 * 60) {
                self.valueHistory.shift(0, 1);
            }

            // Ensure Min and Max get initialized on first call.
            if (!self.maxValue()) {
                self.maxValue(value);
            }

            if (!self.minValue()) {
                self.minValue(value)
            }

            // Update min/max
            if (value > self.maxValue()) {
                self.maxValue(value);
            }

            if (value<self.minValue()) {
			    self.minValue(value);
            }
		};

		return self;
	}

    function PiPowerViewModel(parameters) {
        var self = this;

        // Injected in: ["settingsViewModel", "printerStateViewModel"],
		self.global_settings = parameters[0];
		self.printer = parameters[1];
		console.log("Global Settings: " + self.global_settings );

        self.temperatureSensors = ko.observableArray([]);

		self.voltage = new PiPowerMeasuredValueViewModel("Voltage", true);
		self.current = new PiPowerMeasuredValueViewModel("Current", true);
		self.power = new PiPowerMeasuredValueViewModel("Power", true);
        self.currentFiveVoltEquivelant = new PiPowerMeasuredValueViewModel("Current", true);
		self.currentThreeVoltThreeEquivelant = new PiPowerMeasuredValueViewModel("Current", true);

		//self.powerMeasurements = [self.voltage, self.current, self.power];
		// V & I only, makes plotting difficult otherwise.
		self.powerMeasurements = [self.voltage, self.current];

		self.lightLevel = new PiPowerMeasuredValueViewModel("Light Level")
		self.leds = new PiPowerLedViewModel("LEDs");

		self.fan0 = new PiPowerFanViewModel("F0", 0);
		self.fan1 = new PiPowerFanViewModel("F1", 1);

		// This needs to be initialized from settings.gpioOptions
		self.gpioOptions = ko.observableArray([]);

		// ===================================================
        // Before Binding - settings available
        // ===================================================
		self.onBeforeBinding = function () {
            self.settings = self.global_settings.settings.plugins.pipower;
			console.log("PiPower Settings: " + self.settings );

            // Fans
			self.fan0.caption(self.settings.fan0Caption());
			self.fan1.caption(self.settings.fan1Caption());

            // GPIO
			var options = $.map(self.settings.gpioOptions(), function(option) {
			    console.log("Setting options for GPIO: " + option.pin())
                var optionViewModel = new PiPowerGPIOViewModel(option.pin());
                optionViewModel.setSettings(option);
                return optionViewModel;
            });
            self.gpioOptions(options);

            // Temperature Sensors
            var temperatureSensors = $.map(self.settings.temperatureSensors(), function(sensor) {
			    console.log("Setting temperature sensor for: " + sensor.caption())
                var sensorViewModel = new PiPowerMeasuredValueViewModel();
			    sensorViewModel.caption(sensor.caption());
			    sensorViewModel.sensorId(sensor.sensorId());
			    if (sensor.sensorId()) {
                    sensorViewModel.enabled(true);
                }
                return sensorViewModel;
            });
            self.temperatureSensors(temperatureSensors);

			self.leds.caption(self.settings.ledsCaption());

			self.updateTemperaturePlot();
			self.updatePowerPlot();
        };

		// ===================================================
        // Data updated event
        // ===================================================
        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "pipower") {
                return;
            }

            self.setTemperatures(data);

            self.setPowerValues (data);

			self.lightLevel.setValue(data.lightLevel);
			self.leds.value(data.leds);

			self.fan0.speed(data.fan0Speed);
			self.fan1.speed(data.fan1Speed);

            self.updateGPIO(data);

			self.updateTemperaturePlot();
			self.updatePowerPlot();
	    };

        self.updateGPIO = function(data) {
			for (var gpioRead = 0; gpioRead < data.gpioValues.length; gpioRead++) {
			    var gpio = data.gpioValues[gpioRead];

			    for (var option = 0; option < self.gpioOptions().length; option++) {
			        var gpioOption = self.gpioOptions()[option];

			        if (gpio.pin == gpioOption.pin()) {
			            if (gpio.value == 1) {
                            gpioOption.value("HIGH")
                        } else if (gpio.value == 0) {
			                gpioOption.value("LOW")
                        } else {
			                gpioOption.value("?")
                        }
                    }
                }
            }
        }

        self.setTemperatures = function(data) {

            for (var i = 0; i < data.temperatures.length; i++) {
                var temperature = data.temperatures[i];

                for (var j = 0; j < self.temperatureSensors().length; j++) {
                    var sensor = self.temperatureSensors()[j];
                    if (sensor.sensorId() == temperature.sensorId) {
                        sensor.setValue(temperature.value);
                    }
                }
            }
        };

        self.setPowerValues = function(data) {
            try {
                self.voltage.setValue(data.voltage);
                self.current.setValue(data.currentMilliAmps);
                self.power.setValue(data.powerWatts);

                // Convert the power into the equivelant current (mA) for 5 and 3v3
                self.currentFiveVoltEquivelant.setValue(parseInt((data.powerWatts / 5.0) * 1000));
                self.currentThreeVoltThreeEquivelant.setValue(parseInt((data.powerWatts / 3.3) * 1000));
            } catch (e) {
                console.error("Error setting the power values. Error: " + e);
            }
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

                var maxTemps = [60];

                _.each(self.temperatureSensors(), function(temperature) {

					if (temperature.enabled())
					{
						var actuals = temperature.valueHistory;

						data.push({
							label: temperature.caption(),
							//color: 'red',
							data: actuals
						});

	                    maxTemps.push(temperature.maxValue());
					}
                });

                self.temperaturePlotOptions.yaxis.max = Math.max.apply(null, maxTemps) * 1.1;
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

				var axis = 1;

                _.each(self.powerMeasurements, function(powerMeasurement) {

					if (powerMeasurement.enabled())
					{
						var actuals = powerMeasurement.valueHistory;

						data.push({
							label: powerMeasurement.caption(),
							//color: 'red',
							data: actuals,
							yaxis: axis,
						});

						console.log("YAces" + self.powerPlotOptions.yaxes);

						self.powerPlotOptions.yaxes[axis-1].max = powerMeasurement.maxValue() * 1.2;
						axis++;
					}
                });

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
