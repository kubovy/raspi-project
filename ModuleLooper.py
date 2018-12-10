#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import threading
import time
import prctl

from ModuleMQTT import *


class ModuleLooper(ModuleMQTT):
    interrupted = False
    thread = None

    def __init__(self, client, service_name, module_name, thread_name, debug=False):
        super(ModuleLooper, self).__init__(client, service_name, module_name, debug)

        self.thread_name = thread_name
        self.publish("state", "OFF", 1, True)

    def on_mqtt_message(self, path, payload):
        if len(path) > 0 and path[0] == "state":  # {service}/control/{module}/state
            if payload == "ON":
                self.start()
            else:
                self.stop()

    def looper(self):
        self.logger.info("Looper not implemented!")
        time.sleep(5)

    def __looper__(self):
        prctl.set_name(self.thread_name + " Loop")
        while not self.interrupted:
            try:
                self.looper()
            except:
                self.logger.error("Unexpected Error!")
                traceback.print_exc()
        self.logger.info("Exiting looper")

    def start(self):
        self.logger.info("Starting...")
        if self.thread is None:
            self.on_start()
            self.publish("state", "ON", 1, True)
            self.interrupted = False
            self.thread = threading.Thread(target=self.__looper__)
            self.thread.daemon = True
            self.thread.start()
        return self.thread

    def stop(self):
        self.logger.info("Stopping...")
        self.interrupted = True
        if self.thread is not None:
            self.on_stop()
            self.publish("state", "OFF", 1, True)
            self.thread.join(5)

        self.thread = None
