#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import time

import RPi.GPIO as GPIO

from lib.ModuleLooper import ModuleLooper


class IRSensor(ModuleLooper):
    __state = []
    __handlers = []

    def __init__(self, pins=None, debug=False):
        super(IRSensor, self).__init__(debug=debug)
        self.__pins = [19, 16] if pins is None else pins

        for i in range(0, len(self.__pins)):
            self.__state.append(1)
            GPIO.setup(self.__pins[i], GPIO.IN, GPIO.PUD_UP)

    def initialize(self):
        super(IRSensor, self).initialize()
        for i in range(0, len(self.__pins)):
            if self.module_mqtt is not None:
                self.module_mqtt.publish(str(i), "OFF", module=self)

    def subscribe(self, handler):
        self.__handlers.append(handler)

    def unsubscribe(self, handler):
        try:
            self.__handlers.remove(handler)
        except ValueError:
            self.logger.warn("Not subscribed")

    def looper(self):
        state = self.__get_state()
        self.logger.debug("State: " + str(state))
        if self.module_mqtt is not None:
            for i in range(0, len(state)):
                if state[i] != self.__state[i]:
                    self.__state[i] = state[i]
                    payload = "OPEN" if self.__state[i] == 0 else "CLOSED"
                    self.module_mqtt.publish(str(i), payload, module=self)
        for handler in self.__handlers:
            handler(state)
        time.sleep(0.05)

    def __get_state(self):
        result = []
        for pin in self.__pins:
            result.append(GPIO.input(pin))
        return result
