#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
from threading import Timer
import traceback
from ModuleMQTT import ModuleMQTT


class ModuleTimer(ModuleMQTT):
    timer = None
    delay = 0

    def __init__(self, client, service_name, module_name, debug=False):
        super(ModuleTimer, self).__init__(client, service_name, module_name, debug)

        self.publish("state", "OFF", 1, True)

    def on_start(self):
        pass

    def on_stop(self):
        pass

    def on_mqtt_message(self, path, payload):
        if len(path) > 0 and path[0] == "delay":
            self.delay = 0 if (payload == "OFF") else float(payload)
            if self.delay <= 0:
                self.delay = 0
            self.publish("delay", str(self.delay), 1, False)
            self.logger.info("Measuring distance each " + str(self.delay) + "s")
            if self.delay > 0:
                self.start(self.delay)
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

    def start(self, delay):
        self.logger.info("Starting...")
        if delay > 0 and self.timer is None:
            self.delay = delay
            self.on_start()
            self.publish("state", "ON", 1, False)
            self.timer = Timer(self.delay, self.__trigger__).start()

    def stop(self):
        self.logger.info("Stopping...")
        if self.timer is not None:
            self.timer.cancel()
            self.on_stop()
            self.publish("state", "OFF", 1, False)
        self.timer = None
