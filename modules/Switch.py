#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import time

import pigpio

from lib.ModuleLooper import ModuleLooper


class Switch(ModuleLooper):
    """Switch module"""

    PATTERN_FADEIN = "fade-in"
    PATTERN_FADEOUT = "fade-out"

    INTERVAL_DEFAULT = 0.05  # Seconds
    STEP_DEFAULT = 5  # Percent
    COUNT_DEFAULT = None

    __value = 0
    __pattern = ""
    __step = STEP_DEFAULT
    __interval = INTERVAL_DEFAULT
    __count = COUNT_DEFAULT
    __iteration = 0

    def __init__(self, pin=17, debug=False):
        super(Switch, self).__init__(debug=debug)
        self.__pin = pin
        self.__pi = pigpio.pi()
        self.set_value()

    def on_mqtt_message(self, path, payload):
        if payload.upper() in ["ON", "OFF"]:
            self.__value = 255 if payload.upper() == "ON" else 0
            self.__pattern = ""
            self.set_value(update=True)
        elif len(path) == 1 and path[0] == "percent":
            self.__value = int(255 * int(payload) / 100.0)
            self.__pattern = ""
            self.set_value(update=True)
        else:
            value = payload.split(",")
            self.__value = int(value[0])

            if len(path) > 0:  # {service}/control/switch/{pattern}
                if path[0] == self.PATTERN_FADEIN or path[0] == self.PATTERN_FADEOUT:
                    self.__step = int(value[1]) if len(value) > 1 else self.STEP_DEFAULT
                    self.__interval = float(value[2]) / 1000.0 if len(value) > 2 else self.INTERVAL_DEFAULT
                    self.__count = int(value[3]) if len(value) > 3 else self.COUNT_DEFAULT
                    self.__iteration = 0
                self.__pattern = path[0]
                self.start()
            else:  # {service}/control/switch
                self.__pattern = ""
                self.set_value(update=True)

    def set_value(self, value=None, update=False):
        value = value if value is not None else self.__value
        self.logger.debug("Setting to " + str(value))
        self.__pi.set_PWM_dutycycle(self.__pin, value)

        if update and self.module_mqtt is not None:
            self.module_mqtt.publish("", str(value), module=self)
            self.module_mqtt.publish("percent", int(value * 100.0 / 255.0))
            for listener in self.listeners:
                if hasattr(listener, 'on_switch_change'):
                    listener.on_switch_change(value)

    def looper(self):
        if (self.__pattern == self.PATTERN_FADEIN or self.__pattern == self.PATTERN_FADEOUT) \
                and (self.__count is None or self.__iteration < self.__count):
            percent_range = range(0, 100, self.__step) if self.__pattern == self.PATTERN_FADEIN \
                else range(100, 0, -self.__step)

            for percent in percent_range:
                self.logger.debug("Percent: " + str(percent))
                value = int(float(self.__value) * float(percent) / 100.0)
                self.set_value(value=value, update=False)
                time.sleep(self.__interval)
                if self.is_interrupted():
                    break

            self.set_value(value=self.__value if self.PATTERN_FADEIN else 0, update=self.__iteration == 0)
            self.__iteration = self.__iteration + 1
        else:
            time.sleep(0.5)

    def finalize(self):
        super(Switch, self).finalize()
        self.__pi.stop()
