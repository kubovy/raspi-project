#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import time
import pigpio
from lib.ModuleLooper import ModuleLooper


class Switch(ModuleLooper):

    PIN = 17

    PATTERN_FADEIN = "fade-in"
    PATTERN_FADEOUT = "fade-out"

    INTERVAL_DEFAULT = 0.05  # Seconds
    STEP_DEFAULT = 5     # Percent
    COUNT_DEFAULT = None

    switch = 0
    pattern = ""
    step = STEP_DEFAULT
    interval = INTERVAL_DEFAULT
    count = COUNT_DEFAULT

    iteration = 0

    def __init__(self, client, service_name, debug=False):
        super(Switch, self).__init__(client, service_name, "switch", "Switch", debug)
        self.pi = pigpio.pi()
        self.set_switch()

    def on_mqtt_message(self, path, payload):
        switch = payload.split(",")
        self.switch = int(switch[0])
        self.logger.debug("Got " + str(self.switch) + " " + str(path))

        if len(path) > 0:                                  # {service}/control/switch/{pattern}
            if path[0] == self.PATTERN_FADEIN or path[0] == self.PATTERN_FADEOUT:
                self.step = int(switch[1]) if len(switch) > 1 else self.STEP_DEFAULT
                self.interval = float(switch[2]) / 1000.0 if len(switch) > 2 else self.INTERVAL_DEFAULT
                self.count = int(switch[3]) if len(switch) > 3 else self.COUNT_DEFAULT
                self.iteration = 0
            self.pattern = path[0]
            self.start()
        else:                                              # {service}/control/switch
            self.pattern = ""
            self.set_switch(update=True)

    def set_switch(self, switch=None, update=False):
        switch = switch if switch is not None else self.switch
        self.logger.debug("Setting to " + str(switch))
        self.pi.set_PWM_dutycycle(self.PIN, switch)

        if update:
            self.client.publish(self.service_name + "/state/switch",
                                str(switch), 1, True)

    def looper(self):
        if (self.pattern == self.PATTERN_FADEIN or self.pattern == self.PATTERN_FADEOUT) \
                and (self.count is None or self.iteration < self.count):
            percent_range = range(0, 100, self.step) if self.pattern == self.PATTERN_FADEIN \
                else range(100, 0, -self.step)

            for percent in percent_range:
                self.logger.debug("Percent: " + str(percent))
                switch = int(float(self.switch) * float(percent) / 100.0)
                self.set_switch(switch=switch, update=False)
                time.sleep(self.interval)
                if self.interrupted:
                    break

            if self.pattern == self.PATTERN_FADEOUT:
                self.switch = 0
            self.set_switch(self.switch if self.pattern == self.PATTERN_FADEIN else 0, update=True)
            self.iteration = self.iteration + 1
        else:
            time.sleep(0.5)

    def finalize(self):
        super(Switch, self).finalize()
        self.pi.stop()
