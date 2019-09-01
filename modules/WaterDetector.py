#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import RPi.GPIO as GPIO

from lib.Module import Module


class WaterDetector(Module):
    """Water detector module with Flying Fish MH Sensor"""

    module_mqtt = None

    def __init__(self, pin=23, debug=False):
        super(WaterDetector, self).__init__(debug=debug)
        self.logger.debug("PIN: " + str(pin))
        self.pin = pin

        GPIO.setup(pin, GPIO.IN)
        # GPIO.add_event_detect(PIR_PIN, GPIO.RISING, callback=__motion__)
        # GPIO.add_event_detect(PIR_PIN, GPIO.FALLING, callback=__motion__)
        GPIO.add_event_detect(pin, GPIO.BOTH, callback=self.__water__)

    def initialize(self):
        super(WaterDetector, self).initialize()
        state = not GPIO.input(self.pin)
        self.logger.info("Initializing: " + ("Water detected!" if state else "No water."))

        if self.module_mqtt is not None:
            self.module_mqtt.publish("", "OPEN" if state else "CLOSED", module=self)

        for listener in self.listeners:
            if hasattr(listener, 'on_water_change'):
                listener.on_water_change(state)

    def __water__(self, pin):
        state = not GPIO.input(pin)
        self.logger.info("Water detected!" if state else "No water.")

        if self.module_mqtt is not None:
            self.module_mqtt.publish("", "OPEN" if state else "CLOSED", module=self)

        for listener in self.listeners:
            if hasattr(listener, 'on_water_change'):
                listener.on_water_change(state)