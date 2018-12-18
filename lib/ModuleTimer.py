#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import traceback
from threading import Timer

from lib.Module import Module


class ModuleTimer(Module):
    module_mqtt = None

    timer = None
    delay = 0

    def __init__(self, debug=False):
        super(ModuleTimer, self).__init__(debug=debug)

    def initialize(self):
        super(ModuleTimer, self).initialize()
        if self.module_mqtt is not None:
            self.module_mqtt.publish("state", "OFF", module=self)

    def on_mqtt_message(self, path, payload):
        if len(path) > 0 and path[0] == "delay":
            self.delay = 0 if (payload == "OFF") else float(payload)
            if self.delay <= 0:
                self.delay = 0
            if self.module_mqtt is not None:
                self.module_mqtt.publish("delay", str(self.delay), module=self)
            self.logger.info("Measuring distance each " + str(self.delay) + "s")
            if self.delay > 0:
                self.start_timer(self.delay)
            else:
                self.stop()

    def trigger(self):
        self.logger.info("Trigger not implemented!")

    def __trigger__(self):
        try:
            self.trigger()
            self.timer = Timer(self.delay, self.__trigger__).start()
        except:
            self.logger.error("Unexpected Error!")
            traceback.print_exc()

    def start(self):
        self.logger.warn("Use start_timer(delay) instead of start() -> skipping")

    def start_timer(self, delay):
        super(ModuleTimer, self).on_start()
        if delay > 0 and self.timer is None:
            self.delay = delay
            self.on_start()
            if self.module_mqtt is not None:
                self.module_mqtt.publish("state", "ON", module=self)
            self.timer = Timer(self.delay, self.__trigger__).start()

    def stop(self):
        super(ModuleTimer, self).on_stop()
        if self.timer is not None:
            self.timer.cancel()
            self.on_stop()
            if self.module_mqtt is not None:
                self.module_mqtt.publish("state", "OFF", module=self)
        self.timer = None
