#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import Adafruit_DHT
import time
from threading import *
import traceback
from ModuleMQTT import ModuleMQTT


class DHT11(ModuleMQTT):
    timer = None

    def __init__(self, client, service_name, pin=4, interval=60, debug=False):
        super(DHT11, self).__init__(client, service_name, "dht11", debug)
        self.pin = pin
        self.interval = interval
        self.trigger()

    def on_mqtt_message(self, path, payload):
        if len(path) == 0:
            if payload == "ON":
                self.trigger()
            else:
                self.timer.cancel()
        if len(path) == 1 and path[0] == "interval":
            try:
                self.interval = float(payload)
                self.trigger()
            except:
                self.logger.error("Unexpected Error!")
                traceback.print_exc()

    def trigger(self):
        if self.timer is not None: self.timer.cancel()
        humidity, temperature = Adafruit_DHT.read_retry(11, 4)
        self.logger.debug("Temperature=" + str(temperature) + ", Humidity=" + str(humidity))
        self.publish("humidity", str(humidity), 1, True)
        self.publish("temperature", str(temperature), 1, True)
        self.publish("last-update", str(int(round(time.time()))))

        if not self.finalizing:
            self.timer = Timer(self.interval, self.trigger)
            self.timer.start()

    def finalize(self):
        super(DHT11, self).finalize()
        if self.timer is not None: self.timer.cancel()
