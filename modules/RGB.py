#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import time

import pigpio

from lib.ModuleLooper import ModuleLooper


class RGB(ModuleLooper):
    """RGB strip module"""

    PIN_RED = 17
    PIN_GREEN = 22
    PIN_BLUE = 24

    PATTERN_FADEIN = "fade-in"
    PATTERN_FADEOUT = "fade-out"

    INTERVAL_DEFAULT = 0.05  # Seconds
    STEP_DEFAULT = 5  # Percent
    COUNT_DEFAULT = 1  # Count

    module_mqtt = None

    __red = 0
    __green = 0
    __blue = 0
    __pattern = ""
    __step = STEP_DEFAULT
    __interval = INTERVAL_DEFAULT
    __count = COUNT_DEFAULT
    __iteration = 0

    def __init__(self, debug=False):
        super(RGB, self).__init__(debug=debug)
        self.__pi = pigpio.pi()

    def initialize(self):
        super(RGB, self).initialize()
        self.set_color()

    def finalize(self):
        super(RGB, self).finalize()
        self.__pi.stop()

    def set_color(self, red=None, green=None, blue=None, update=False):
        red = red if red is not None else self.__red
        green = green if green is not None else self.__green
        blue = blue if blue is not None else self.__blue
        self.logger.debug("Setting to " + str(red) + "," + str(green) + "," + str(blue))
        self.__pi.set_PWM_dutycycle(self.PIN_RED, red)
        self.__pi.set_PWM_dutycycle(self.PIN_GREEN, green)
        self.__pi.set_PWM_dutycycle(self.PIN_BLUE, blue)
        if update and self.module_mqtt is not None:
            self.module_mqtt.publish("", str(red) + "," + str(green) + "," + str(blue), module=self)
            for listener in self.listeners:
                if hasattr(listener, 'on_rgb_change'):
                    listener.on_rgb_change(red, green, blue)

    def on_mqtt_message(self, path, payload):
        rgb = payload.split(",")
        if payload.upper() in ["ON", "OFF"]:
            self.__red = self.__green = self.__blue = 255 if payload.upper() == "ON" else 0
            self.__pattern = ""
            self.set_color(update=True)
        elif len(rgb) == 1:
            self.__red = self.__green = self.__blue = int(rgb[0])
            self.__pattern = ""
            self.set_color(update=True)
        else:
            self.__red = int(rgb[0])
            self.__green = int(rgb[1])
            self.__blue = int(rgb[2])
            self.logger.debug("Got " + str(self.__red) + "," + str(self.__green) + "," + str(self.__blue))

            if len(path) > 0:  # {service}/control/rgb/{pattern}
                if path[0] == self.PATTERN_FADEIN or path[0] == self.PATTERN_FADEOUT:
                    self.__step = int(rgb[3]) if len(rgb) > 3 else self.STEP_DEFAULT
                    self.__interval = float(rgb[4]) / 1000.0 if len(rgb) > 4 else self.INTERVAL_DEFAULT
                    self.__count = int(rgb[5]) if len(rgb) > 5 else self.COUNT_DEFAULT
                    self.__iteration = 0
                self.__pattern = path[3]
                self.start()
            else:  # {service}/control/rgb
                self.__pattern = ""
                self.set_color(update=True)

    def looper(self):
        if (self.__pattern == self.PATTERN_FADEIN or self.__pattern == self.PATTERN_FADEOUT) \
                and (self.__count is None or self.__iteration < self.__count):
            percent_range = range(0, 100, self.__step) if self.__pattern == self.PATTERN_FADEIN \
                else range(100, 0, -self.__step)

            for percent in percent_range:
                self.logger.debug("Percent: " + str(percent))
                red = int(float(self.__red) * float(percent) / 100.0)
                green = int(float(self.__green) * float(percent) / 100.0)
                blue = int(float(self.__blue) * float(percent) / 100.0)
                self.set_color(red=red, green=green, blue=blue, update=False)
                time.sleep(self.__interval)
                if self.is_interrupted():
                    break

            self.set_color(red=self.__red if self.__pattern == self.PATTERN_FADEIN else 0,
                           green=self.__green if self.__pattern == self.PATTERN_FADEIN else 0,
                           blue=self.__blue if self.__pattern == self.PATTERN_FADEIN else 0,
                           update=self.__iteration == 0)
            self.__iteration = self.__iteration + 1
        else:
            time.sleep(0.5)
