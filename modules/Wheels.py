#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import prctl
from threading import Timer

import RPi.GPIO as GPIO

from lib.Module import Module


class Wheels(Module):
    DEFAULT_TIMEOUT = 0.5

    module_mqtt = None

    __timer = None
    __left = 0
    __right = 0

    def __init__(self, pin_right_forward=13, pin_right_backward=12, pin_right_enabled=6, pin_left_forward=21,
                 pin_left_backward=20, pin_left_enabled=26, debug=False):

        super(Wheels, self).__init__(debug=debug)

        self.__pin_right_forward = pin_right_forward
        self.__pin_right_backward = pin_right_backward
        self.__pin_left_forward = pin_left_forward
        self.__pin_left_backward = pin_left_backward
        self.__pin_right_enabled = pin_right_enabled
        self.__pin_left_enabled = pin_left_enabled
        self.__right_speed = 50
        self.__left_speed = 50

        GPIO.setup(self.__pin_right_forward, GPIO.OUT)
        GPIO.setup(self.__pin_right_backward, GPIO.OUT)
        GPIO.setup(self.__pin_left_forward, GPIO.OUT)
        GPIO.setup(self.__pin_left_backward, GPIO.OUT)
        GPIO.setup(self.__pin_right_enabled, GPIO.OUT)
        GPIO.setup(self.__pin_left_enabled, GPIO.OUT)

        self.__pwm_right = GPIO.PWM(self.__pin_right_enabled, 500)
        self.__pwm_left = GPIO.PWM(self.__pin_left_enabled, 500)
        self.__pwm_right.start(self.__right_speed)
        self.__pwm_left.start(self.__left_speed)

    def initialize(self):
        super(Wheels, self).initialize()
        self.halt()

    def on_mqtt_message(self, path, payload):
        if len(path) > 0 and path[0] == "move":  # {service}/control/wheels/move/#
            if len(path) > 1 and path[1] == "forward":  # {service}/control/wheels/move/forward
                parts = payload.split(" ")
                if len(parts) > 0:
                    speed = float(parts[0])
                    timeout = float(parts[1]) if len(parts) > 1 else self.DEFAULT_TIMEOUT
                    self.move(speed, speed, timeout)
            elif len(path) > 1 and path[1] == "backward":  # {service}/control/wheels/move/backward
                parts = payload.split(" ")
                if len(parts) > 0:
                    speed = float(parts[0])
                    timeout = float(parts[1]) if len(parts) > 1 else self.DEFAULT_TIMEOUT
                    self.move(-speed, -speed, timeout)
            else:  # {service}/control/wheels/move
                parts = payload.split(" ")
                if len(parts) > 0:
                    left = float(parts[0])
                    right = float(parts[1]) if len(parts) > 1 else left
                    timeout = float(parts[2]) if len(parts) > 2 else self.DEFAULT_TIMEOUT
                    self.move(left, right, timeout)
        elif len(path) > 0 and path[0] == "rotate":  # {service}/control/wheels/rotate
            parts = payload.split(" ")
            if len(parts) > 0:
                speed = float(parts[0])
                timeout = float(parts[1]) if len(parts) > 1 else self.DEFAULT_TIMEOUT
                if len(path) > 1 and path[1] == "right":  # {service}/control/wheels/rotate/right
                    self.move(speed, -speed, timeout)
                elif len(path) > 1 and path[1] == "left":  # {service}/control/wheels/rotate/left
                    self.move(-speed, speed, timeout)
        elif len(path) > 0 and path[0] == "turn":  # {service}/control/wheels/turn
            parts = payload.split(" ")
            if len(parts) > 0:
                speed = float(parts[0])
                timeout = float(parts[1]) if len(parts) > 1 else self.DEFAULT_TIMEOUT
                if len(path) > 1 and path[1] == "right":  # {service}/control/wheels/turn/right
                    self.move(speed, 0, timeout)
                elif len(path) > 1 and path[1] == "left":  # {service}/control/wheels/turn/left
                    self.move(0, speed, timeout)
        elif len(path) > 0 and path[0] == "stop":  # {service}/control/wheels/stop
            self.halt()

    def set_left_speed(self, value):
        self.__left_speed = value
        self.__pwm_left.ChangeDutyCycle(self.__left_speed)

    def set_set_right_speed(self, value):
        self.__right_speed = value
        self.__pwm_right.ChangeDutyCycle(self.__right_speed)

    def set_motor(self, left, right):
        if (right >= 0) and (right <= 100):
            GPIO.output(self.__pin_right_forward, GPIO.HIGH)
            GPIO.output(self.__pin_right_backward, GPIO.LOW)
            self.__pwm_right.ChangeDutyCycle(right)
        elif (right < 0) and (right >= -100):
            GPIO.output(self.__pin_right_forward, GPIO.LOW)
            GPIO.output(self.__pin_right_backward, GPIO.HIGH)
            self.__pwm_right.ChangeDutyCycle(0 - right)
        if (left >= 0) and (left <= 100):
            GPIO.output(self.__pin_left_forward, GPIO.HIGH)
            GPIO.output(self.__pin_left_backward, GPIO.LOW)
            self.__pwm_left.ChangeDutyCycle(left)
        elif (left < 0) and (left >= -100):
            GPIO.output(self.__pin_left_forward, GPIO.LOW)
            GPIO.output(self.__pin_left_backward, GPIO.HIGH)
            self.__pwm_left.ChangeDutyCycle(0 - left)

    def move(self, left=None, right=None, timeout=DEFAULT_TIMEOUT):
        if left is None:
            left = self.__left_speed
        if right is None:
            right = self.__right_speed
        if self.__timer is not None:
            self.__timer.cancel()
        if left < -100:
            left = -100
        if left > 100:
            left = 100
        if right < -100:
            left = -100
        if right > 100:
            left = 100
        self.set_motor(left, right)

        if self.module_mqtt is not None:
            if self.__left != left:
                self.module_mqtt.publish("move/left", str(left), module=self)
            if self.__right != right:
                self.module_mqtt.publish("move/right", str(right), module=self)
            if self.__left != left or self.__right != right:
                self.module_mqtt.publish("move", str(left) + " " + str(right), module=self)
        if self.__left != left or self.__right != right:
            self.logger.info("Moving left at " + str(left) + "%, right at " + str(right) + "%")

        self.__left = left
        self.__right = right
        if timeout > 0:
            self.__timer = Timer(timeout, self.halt).start()

    def halt(self):
        prctl.set_name("Wheel Timer")
        self.__pwm_right.ChangeDutyCycle(0)
        self.__pwm_left.ChangeDutyCycle(0)
        GPIO.output(self.__pin_right_forward, GPIO.LOW)
        GPIO.output(self.__pin_right_backward, GPIO.LOW)
        GPIO.output(self.__pin_left_forward, GPIO.LOW)
        GPIO.output(self.__pin_left_backward, GPIO.LOW)

        if self.module_mqtt is not None:
            if self.__left != 0:
                self.module_mqtt.publish("move/left", "0", module=self)
            if self.__right != 0:
                self.module_mqtt.publish("move/right", "0", module=self)
            if self.__left != 0 or self.__right != 0:
                self.module_mqtt.publish("move", "0 0", module=self)
        if self.__left != 0 or self.__right != 0:
            self.logger.info("Stop moving")
        self.__left = 0
        self.__right = 0
