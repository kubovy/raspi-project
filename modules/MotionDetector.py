#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import RPi.GPIO as GPIO

from lib.Module import Module


class MotionDetector(Module):
    """Motion detector module using HC-SR501 PIR (https://www.mpja.com/download/31227sc.pdf)"""

    module_mqtt = None

    def __init__(self, pin=7, debug=False):
        super(MotionDetector, self).__init__(debug=debug)
        self.logger.debug("PIN: " + str(pin))

        GPIO.setup(pin, GPIO.IN)
        # GPIO.add_event_detect(PIR_PIN, GPIO.RISING, callback=__motion__)
        # GPIO.add_event_detect(PIR_PIN, GPIO.FALLING, callback=__motion__)
        GPIO.add_event_detect(pin, GPIO.BOTH, callback=self.__motion__)

    def initialize(self):
        super(MotionDetector, self).initialize()
        if self.module_mqtt is not None:
            self.module_mqtt.publish("", "CLOSED", module=self)

    def __motion__(self, pin):
        state = GPIO.input(pin)
        self.logger.info("Motion " + ("detected!" if state else "stopped."))
        if self.module_mqtt is not None:
            self.module_mqtt.publish("", "OPEN" if state else "CLOSED", module=self)
        for listener in self.listeners:
            if hasattr(listener, 'on_motion_change'):
                listener.on_motion_change(state)
