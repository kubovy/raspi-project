#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
from threading import Timer

import RPi.GPIO as GPIO

from lib.Module import Module


class Buzzer(Module):
    """Buzzer module"""

    module_mqtt = None

    def __init__(self, pin=4, debug=False):
        super(Buzzer, self).__init__(debug=debug)
        self.__pin = pin

        GPIO.setup(self.__pin, GPIO.OUT)

        self.off()

    def beep(self, delay):
        """Beeps for `delay` seconds"""
        self.on()
        Timer(delay, self.off).start()

    def on(self):
        """Turns beeper on"""
        GPIO.output(self.__pin, GPIO.HIGH)
        if self.module_mqtt is not None:
            self.module_mqtt.publish("", "ON", module=self)

    def off(self):
        """Turns beeper off"""
        GPIO.output(self.__pin, GPIO.LOW)
        if self.module_mqtt is not None:
            self.module_mqtt.publish("", "OFF", module=self)

    def on_mqtt_message(self, path, payload):
        if len(path) == 0:  # {service}/control/{module}
            if payload == "ON":
                self.on()
            else:
                self.off()
