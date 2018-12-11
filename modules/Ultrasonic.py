#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import time
import RPi.GPIO as GPIO
from rx import Observable
from lib.ModuleLooper import ModuleLooper


class Ultrasonic(ModuleLooper):

    delay = 0

    def __init__(self, client, service_name, pin_trigger=22, pin_echo=27, debug=False):
        super(Ultrasonic, self).__init__(client, service_name, "ultrasonic", "Ultrasonic", debug)
        self.pin_echo = pin_echo
        self.pin_trigger = pin_trigger
        self.source = Observable.interval(1000).map(lambda i: self.get_distance())

        GPIO.setup(self.pin_trigger, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.pin_echo, GPIO.IN)

        self.publish("delay", str(self.delay), 1, False)

    def on_mqtt_message(self, path, payload):
        self.logger.info("Message: " + "/".join(path) + ": " + payload)
        if len(path) == 0 and (payload == "" or payload == "MEASURE"):
            distance = self.get_distance()
            self.logger.info("Measuring distance: " + str(distance))
            self.publish("", distance, 1, False)
        elif len(path) > 0 and path[0] == "delay":
            self.delay = float(payload)
            if self.delay > 0:
                self.start()
            else:
                self.stop()
        else:
            super(Ultrasonic, self).on_mqtt_message(path, payload)

    def looper(self):
        distance = self.get_distance()
        self.logger.info("Distance: " + str(distance) + "mm")
        self.publish("", str(distance), 1, False)
        time.sleep(self.delay)

    def get_distance(self):
        self.logger.debug("Getting distance...")
        GPIO.output(self.pin_trigger, GPIO.HIGH)
        time.sleep(0.000015)
        GPIO.output(self.pin_trigger, GPIO.LOW)
        while not GPIO.input(self.pin_echo):
            pass
        t1 = time.time()
        while GPIO.input(self.pin_echo):
            pass
        t2 = time.time()
        return (t2 - t1) * 340000 / 2

    def subscribe(self, on_next):
        return self.source.subscribe(
            on_next=on_next,
            on_error=lambda e: self.logger.error(str(e)),
            on_completed=lambda: self.logger.info("Subscription completed"))
