#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import time
import traceback
from threading import *

import Adafruit_DHT

from lib.Module import Module


class DHT11(Module):
    module_mqtt = None

    __timer = None

    def __init__(self, pin=4, interval=60, debug=False):
        super(DHT11, self).__init__(debug=debug)
        self.__interval = interval
        self.logger.debug("Pin: " + str(pin) + ", interval: " + str(interval))
        
    def initialize(self):
        super(DHT11, self).initialize()
        self.__trigger()

    def finalize(self):
        super(DHT11, self).finalize()
        if self.__timer is not None:
            self.__timer.cancel()

    def on_mqtt_message(self, path, payload):
        if len(path) == 0:
            if payload == "ON":
                self.__trigger()
            elif self.__timer is not None:
                self.__timer.cancel()
        if len(path) == 1 and path[0] == "interval":
            try:
                self.__interval = float(payload)
                self.__trigger()
            except:
                self.logger.error("Unexpected Error!")
                traceback.print_exc()

    def __trigger(self):
        if self.__timer is not None:
            self.__timer.cancel()
        humidity, temperature = Adafruit_DHT.read_retry(11, 4)
        self.logger.debug("Temperature=" + str(temperature) + ", Humidity=" + str(humidity))
        if self.module_mqtt is not None:
            self.module_mqtt.publish("humidity", str(humidity), retrain=True, module=self)
            self.module_mqtt.publish("temperature", str(temperature), retrain=True, module=self)
            self.module_mqtt.publish("last-update", str(int(round(time.time()))), retrain=True, module=self)

        if not self.finalizing:
            self.__timer = Timer(self.__interval, self.__trigger)
            self.__timer.start()
