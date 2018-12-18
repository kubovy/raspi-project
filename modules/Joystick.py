#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import time

import RPi.GPIO as GPIO

from lib.ModuleLooper import ModuleLooper


class Joystick(ModuleLooper):
    NONE = 0

    module_buzzer = None
    module_servo = None
    module_wheels = None

    __state = NONE
    __control = "OFF"
    __roll = 50
    __pitch = 50

    def __init__(self, pin_center=7, pin_a=8, pin_b=9, pin_c=10, pin_d=11, debug=False):
        super(Joystick, self).__init__(debu=debug)
        self.__pin_center = pin_center
        self.__pin_a = pin_a
        self.__pin_b = pin_b
        self.__pin_c = pin_c
        self.__pin_d = pin_d

        GPIO.setup(self.__pin_center, GPIO.IN, GPIO.PUD_UP)
        GPIO.setup(self.__pin_a, GPIO.IN, GPIO.PUD_UP)
        GPIO.setup(self.__pin_b, GPIO.IN, GPIO.PUD_UP)
        GPIO.setup(self.__pin_c, GPIO.IN, GPIO.PUD_UP)
        GPIO.setup(self.__pin_d, GPIO.IN, GPIO.PUD_UP)

    def initialize(self):
        super(Joystick, self).initialize()
        if self.module_mqtt is not None:
            self.module_mqtt.publish("button", "NONE", module=self)
            self.module_mqtt.publish("center", "OFF", module=self)
            self.module_mqtt.publish("up", "OFF", module=self)
            self.module_mqtt.publish("right", "OFF", module=self)
            self.module_mqtt.publish("down", "OFF", module=self)
            self.module_mqtt.publish("left", "OFF", module=self)
            self.module_mqtt.publish("control", "OFF", module=self)

    def start(self, control="OFF"):
        self.__control = control
        super(Joystick, self).start()

    def on_start(self):
        super(Joystick, self).on_start()
        if self.__control != "OFF" and self.module_mqtt is not None:
            self.module_mqtt.publish("control", self.__control, module=self)

    def on_stop(self):
        super(Joystick, self).on_stop()
        if self.__control != "OFF" and self.module_mqtt is not None:
            self.module_mqtt.publish("control", "OFF", module=self)
        self.__control = "OFF"

    def on_mqtt_message(self, path, payload):
        if len(path) > 0 and path[0] == "state":  # {service}/control/joystick/state
            if payload == "ON":
                self.start("OFF")
            else:
                self.stop()
        elif len(path) > 0 and path[0] == "control":  # {service}/control/joystick/control
            if payload == "MOVEMENT":
                self.start("MOVEMENT")
            elif payload == "CAMERA":
                self.start("CAMERA")
            else:
                self.stop()

    def looper(self):
        if GPIO.input(self.__pin_center) == 0:
            if self.__state != self.__pin_center:
                self.logger.info("CENTER")
                if self.module_mqtt is not None:
                    self.module_mqtt.publish("button", "CENTER", module=self)
                    self.module_mqtt.publish("center", "OPEN", module=self)
                self.__state = self.__pin_center
            if self.__control == "CAMERA" and self.module_buzzer is not None:
                if self.module_buzzer is not None:
                    self.module_buzzer.on()
            if self.__control == "MOVEMENT" and self.module_wheels is not None:
                self.module_wheels.halt()
                if self.module_buzzer is not None:
                    self.module_buzzer.on()
        elif GPIO.input(self.__pin_a) == 0:
            if self.__state != self.__pin_a:
                self.logger.info("UP")
                if self.module_mqtt is not None:
                    self.module_mqtt.publish("button", "UP", module=self)
                    self.module_mqtt.publish("up", "OPEN", module=self)
                self.__state = self.__pin_a
            if self.__control == "CAMERA" and self.module_servo is not None:
                self.__pitch += 5
                self.module_servo.set_position_percent(1, self.__pitch)
            elif self.__control == "MOVEMENT" and self.module_wheels is not None:
                self.module_wheels.move(50, 50, 1.0)
        elif GPIO.input(self.__pin_b) == 0:
            if self.__state != self.__pin_b:
                self.logger.info("RIGHT")
                if self.module_mqtt is not None:
                    self.module_mqtt.publish("button", "RIGHT", module=self)
                    self.module_mqtt.publish("right", "OPEN", module=self)
                self.__state = self.__pin_b
            if self.__control == "CAMERA" and self.module_servo is not None:
                self.__roll += 5
                self.module_servo.set_position_percent(0, self.__roll)
            elif self.__control == "MOVEMENT" and self.module_wheels is not None:
                self.module_wheels.move(-50, 50, 1.0)
        elif GPIO.input(self.__pin_c) == 0:
            if self.__state != self.__pin_c:
                self.logger.info("LEFT")
                if self.module_mqtt is not None:
                    self.module_mqtt.publish("button", "LEFT", module=self)
                    self.module_mqtt.publish("left", "OPEN", module=self)
                self.__state = self.__pin_c
            if self.__control == "CAMERA" and self.module_servo is not None:
                self.__roll -= 5
                self.module_servo.set_position_percent(0, self.__roll)
            elif self.__control == "MOVEMENT" and self.module_wheels is not None:
                self.module_wheels.move(50, -50, 1.0)
        elif GPIO.input(self.__pin_d) == 0:
            if self.__state != self.__pin_d:
                self.logger.info("DOWN")
                if self.module_mqtt is not None:
                    self.module_mqtt.publish("button", "DOWN", module=self)
                    self.module_mqtt.publish("down", "OPEN", module=self)
                self.__state = self.__pin_d
            if self.__control == "CAMERA" and self.module_servo is not None:
                self.__pitch -= 5
                self.module_servo.set_position_percent(1, self.__pitch)
            elif self.__control == "MOVEMENT" and self.module_wheels is not None:
                self.module_wheels.move(-50, -50, 1.0)
        else:
            if self.__state != self.NONE:
                self.logger.info("NONE")
                if self.module_mqtt is not None:
                    self.module_mqtt.publish("button", "NONE", module=self)
                    if self.__state == self.__pin_center:
                        self.module_mqtt.publish("center", "CLOSED", module=self)
                    elif self.__state == self.__pin_a:
                        self.module_mqtt.publish("up", "CLOSED", module=self)
                    elif self.__state == self.__pin_b:
                        self.module_mqtt.publish("right", "CLOSED", module=self)
                    elif self.__state == self.__pin_c:
                        self.module_mqtt.publish("down", "CLOSED", module=self)
                    elif self.__state == self.__pin_d:
                        self.module_mqtt.publish("left", "CLOSED", module=self)
                self.__state = self.NONE
                if self.module_buzzer is not None:
                    self.module_buzzer.off()
                if self.module_wheels is not None:
                    self.module_wheels.halt()

        time.sleep(0.2)
