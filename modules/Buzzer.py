#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import RPi.GPIO as GPIO
from threading import Timer
from lib.ModuleMQTT import ModuleMQTT


class Buzzer(ModuleMQTT):
    def __init__(self, client, service_name, pin=4, debug=False):
        super(Buzzer, self).__init__(client, service_name, "buzzer", debug)
        self.pin = pin

        GPIO.setup(self.pin, GPIO.OUT)

        self.off()

    def on_mqtt_message(self, path, payload):
        if len(path) == 0:               # {service}/control/{module}
            if payload == "ON":
                self.on()
            else:
                self.off()

    def beep(self, delay):
        self.on()
        Timer(delay, self.off).start()

    def on(self):
        GPIO.output(self.pin, GPIO.HIGH)
        self.publish("", "ON", 1, True)

    def off(self):
        GPIO.output(self.pin, GPIO.LOW)
        self.publish("", "OFF", 1, True)
