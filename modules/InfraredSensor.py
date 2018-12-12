#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import RPi.GPIO as GPIO
import time
from rx import Observable
from lib.ModuleLooper import ModuleLooper


class InfraredSensor(ModuleLooper):

    state = []

    def __init__(self, client, service_name, pins=None, debug=False):
        super(InfraredSensor, self).__init__(client, service_name, "ir-sensor", "IR Sensor", debug)
        self.pins = [19, 16] if pins is None else pins
        self.source = Observable.interval(50).map(lambda x: self.get_state())

        for i in range(0, len(self.pins)):
            self.state.append(1)
            GPIO.setup(self.pins[i], GPIO.IN, GPIO.PUD_UP)
            self.publish(str(i), "OFF", 1, True)

    def get_state(self):
        result = []
        for pin in self.pins:
            result.append(GPIO.input(pin))
        return result

    def subscribe(self, on_next):
        return self.source.subscribe(
            on_next=on_next,
            on_error=lambda e: self.logger.error(str(e)),
            on_completed=lambda: self.logger.info("Subscription completed"))

    def looper(self):
        state = self.get_state()
        self.logger.debug("State: " + str(state))
        for i in range(0, len(state)):
            if state[i] != self.state[i]:
                self.state[i] = state[i]
                payload = "OPEN" if self.state[i] == 0 else "CLOSED"
                self.publish(str(i), payload, 0, False)
        time.sleep(0.05)
