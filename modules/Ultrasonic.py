#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import time

import RPi.GPIO as GPIO
from rx import Observable

from lib.ModuleLooper import ModuleLooper


class Ultrasonic(ModuleLooper):
    """Ultrasonic sensor module"""

    __delay = 0

    def __init__(self, pin_trigger=22, pin_echo=27, debug=False):
        super(Ultrasonic, self).__init__(debug=debug)
        self.__pin_echo = pin_echo
        self.__pin_trigger = pin_trigger
        self.__source = Observable.interval(1000).map(lambda i: self.get_distance())

        GPIO.setup(self.__pin_trigger, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.__pin_echo, GPIO.IN)

    def initialize(self):
        super(Ultrasonic, self).initialize()
        if self.module_mqtt is not None:
            self.module_mqtt.publish("delay", str(self.__delay), module=self)

    def get_distance(self):
        self.logger.debug("Getting distance...")
        GPIO.output(self.__pin_trigger, GPIO.HIGH)
        time.sleep(0.000015)
        GPIO.output(self.__pin_trigger, GPIO.LOW)
        while not GPIO.input(self.__pin_echo):
            pass
        t1 = time.time()
        while GPIO.input(self.__pin_echo):
            pass
        t2 = time.time()
        return (t2 - t1) * 340000 / 2

    def subscribe(self, on_next):
        return self.__source.subscribe(
            on_next=on_next,
            on_error=lambda e: self.logger.error(str(e)),
            on_completed=lambda: self.logger.info("Subscription completed"))

    def on_mqtt_message(self, path, payload):
        self.logger.info("Message: " + "/".join(path) + ": " + payload)
        if len(path) == 0 and (payload == "" or payload == "MEASURE"):
            distance = self.get_distance()
            self.logger.info("Measuring distance: " + str(distance))
            if self.module_mqtt is not None:
                self.module_mqtt.publish("", distance, module=self)
        elif len(path) > 0 and path[0] == "delay":
            self.__delay = float(payload)
            if self.__delay > 0:
                self.start()
            else:
                self.stop()
        else:
            super(Ultrasonic, self).on_mqtt_message(path, payload)

    def looper(self):
        distance = self.get_distance()
        self.logger.info("Distance: " + str(distance) + "mm")
        if self.module_mqtt is not None:
            self.module_mqtt.publish("", str(distance), module=self)
        time.sleep(self.__delay)
