#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import RPi.GPIO as GPIO
from ModuleMQTT import ModuleMQTT


class MotionDetector(ModuleMQTT):
    """
    HC-SR501 PIR (https://www.mpja.com/download/31227sc.pdf)
    """

    def __init__(self, client, service_name, pin=7, debug=False):
        super(MotionDetector, self).__init__(client, service_name, "motion", debug)
        self.logger.debug("PIN: " + str(pin))
        self.pin = pin

        self.publish("", "CLOSED", 1, True)

        GPIO.setup(pin, GPIO.IN)
        # GPIO.add_event_detect(PIR_PIN, GPIO.RISING, callback=__motion__)
        # GPIO.add_event_detect(PIR_PIN, GPIO.FALLING, callback=__motion__)
        GPIO.add_event_detect(self.pin, GPIO.BOTH, callback=self.__motion__)

    def __motion__(self, pin):
        if GPIO.input(pin):
            self.logger.info("Motion Detected!")
            self.publish("", "OPEN", 1, True)
        else:
            self.logger.info("Motion stopped.")
            self.publish("", "CLOSED", 1, True)
