#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import time
import pigpio
from ModuleLooper import ModuleLooper


class RGB(ModuleLooper):

    PIN_RED   = 17
    PIN_GREEN = 22
    PIN_BLUE  = 24

    PATTERN_FADEIN  = "fade-in"
    PATTERN_FADEOUT = "fade-out"

    INTERVAL_DEFAULT = 0.05  # Seconds
    STEP_DEFAULT     = 5     # Percent

    red      = 0
    green    = 0
    blue     = 0
    pattern  = ""
    step = STEP_DEFAULT
    interval = INTERVAL_DEFAULT

    interrupted = False
    thread = None

    def __init__(self, client, service_name, debug=False):
        super(RGB, self).__init__(client, service_name, "rgb", "RGB", debug)
        self.pi = pigpio.pi()
        self.set_color()

    def on_message(self, path, payload):
        rgb = payload.split(",")
        self.red = int(rgb[0])
        self.green = int(rgb[1])
        self.blue = int(rgb[2])
        self.logger.debug("Got " + str(self.red) + "," + str(self.green) + "," + str(self.blue))

        if len(path) > 3:                                  # {service}/control/rgb/{pattern}
            if path[3] == self.PATTERN_FADEIN or path[3] == self.PATTERN_FADEOUT:
                self.step = int(rgb[3]) if len(rgb) > 3 else self.STEP_DEFAULT
                self.interval = float(rgb[4]) / 1000.0 if len(rgb) > 4 else self.INTERVAL_DEFAULT
            self.pattern = path[3]
            self.start()
        else:                                              # {service}/control/rgb
            self.pattern = ""
            self.set_color(update=True)

    def set_color(self, red=None, green=None, blue=None, update=False):
        red = red if red is not None else self.red
        green = green if green is not None else self.green
        blue = blue if blue is not None else self.blue
        self.logger.debug("Setting to " + str(red) + "," + str(green) + "," + str(blue))
        self.pi.set_PWM_dutycycle(self.PIN_RED, red)
        self.pi.set_PWM_dutycycle(self.PIN_GREEN, green)
        self.pi.set_PWM_dutycycle(self.PIN_BLUE, blue)
        if update:
            self.client.publish(self.service_name + "/state/rgb", str(red) + "," + str(green) + "," + str(blue), 1, True)

    def looper(self):
        if self.pattern == self.PATTERN_FADEIN or self.pattern == self.PATTERN_FADEOUT:
            percent_range = range(0, 100, self.step) if self.pattern == self.PATTERN_FADEIN \
                else range(100, 0, -self.step)

            for percent in percent_range:
                self.logger.debug("Percent: " + str(percent))
                red = int(float(self.red) * float(percent) / 100.0)
                green = int(float(self.green) * float(percent) / 100.0)
                blue = int(float(self.blue) * float(percent) / 100.0)
                self.set_color(red=red, green=green, blue=blue, update=False)
                time.sleep(self.interval)
                if self.interrupted: break

            if self.pattern == self.PATTERN_FADEOUT: self.red = self.green = self.blue = 0
            self.set_color(update=True)

    def finalize(self):
        super(RGB, self).finalize()
        self.pi.stop()

