#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import RPi.GPIO as GPIO
import threading
from ModuleMQTT import ModuleMQTT


class Wheels(ModuleMQTT):

    DEFAULT_TIMEOUT = 0.5

    interrupted = False
    thread = None
    timer = None

    left = 0
    right = 0

    def __init__(self, client, service_name,
                 pin_right_forward=13,
                 pin_right_backward=12,
                 pin_right_enabled=6,
                 pin_left_forward=21,
                 pin_left_backward=20,
                 pin_left_enabled=26,
                 debug=False):

        super(Wheels, self).__init__(client, service_name, "wheels", debug)

        self.pin_right_forward = pin_right_forward
        self.pin_right_backward = pin_right_backward
        self.pin_left_forward = pin_left_forward
        self.pin_left_backward = pin_left_backward
        self.pin_right_enabled = pin_right_enabled
        self.pin_left_enabled = pin_left_enabled
        self.right_speed = 50
        self.left_speed = 50

        GPIO.setup(self.pin_right_forward, GPIO.OUT)
        GPIO.setup(self.pin_right_backward, GPIO.OUT)
        GPIO.setup(self.pin_left_forward, GPIO.OUT)
        GPIO.setup(self.pin_left_backward, GPIO.OUT)
        GPIO.setup(self.pin_right_enabled, GPIO.OUT)
        GPIO.setup(self.pin_left_enabled, GPIO.OUT)

        self.pwm_right = GPIO.PWM(self.pin_right_enabled, 500)
        self.pwm_left = GPIO.PWM(self.pin_left_enabled, 500)
        self.pwm_right.start(self.right_speed)
        self.pwm_left.start(self.left_speed)

        self.halt()

    def on_mqtt_message(self, path, payload):
        if len(path) > 0 and path[0] == "move":            # {service}/control/wheels/move/#
            if len(path) > 1 and path[1] == "forward":     # {service}/control/wheels/move/forward
                parts = payload.split(" ")
                if len(parts) > 0:
                    speed = float(parts[0])
                    timeout = float(parts[1]) if len(parts) > 1 else self.DEFAULT_TIMEOUT
                    self.move(speed, speed, timeout)
            elif len(path) > 1and path[1] == "backward":   # {service}/control/wheels/move/backward
                parts = payload.split(" ")
                if len(parts) > 0:
                    speed = float(parts[0])
                    timeout = float(parts[1]) if len(parts) > 1 else self.DEFAULT_TIMEOUT
                    self.move(-speed, -speed, timeout)
            else:                                          # {service}/control/wheels/move
                parts = payload.split(" ")
                if len(parts) > 0:
                    left = float(parts[0])
                    right = float(parts[1]) if len(parts) > 1 else left
                    timeout = float(parts[2]) if len(parts) > 2 else self.DEFAULT_TIMEOUT
                    self.move(left, right, timeout)
        elif len(path) > 0 and path[0] == "rotate":        # {service}/control/wheels/rotate
            parts = payload.split(" ")
            if len(parts) > 0:
                speed = float(parts[0])
                timeout = float(parts[1]) if len(parts) > 1 else self.DEFAULT_TIMEOUT
                if len(path) > 1and path[1] == "right":    # {service}/control/wheels/rotate/right
                    self.move(speed, -speed, timeout)
                elif len(path) > 1 and path[1] == "left":  # {service}/control/wheels/rotate/left
                    self.move(-speed, speed, timeout)
        elif len(path) > 0 and path[0] == "turn":          # {service}/control/wheels/turn
            parts = payload.split(" ")
            if len(parts) > 0:
                speed = float(parts[0])
                timeout = float(parts[1]) if len(parts) > 1 else self.DEFAULT_TIMEOUT
                if len(path) > 1 and path[1] == "right":   # {service}/control/wheels/turn/right
                    self.move(speed, 0, timeout)
                elif len(path) > 1 and path[1] == "left":  # {service}/control/wheels/turn/left
                    self.move(0, speed, timeout)
        elif len(path) > 0 and path[0] == "stop":          # {service}/control/wheels/stop
            self.halt()

    def set_left_speed(self, value):
        self.left_speed = value
        self.pwm_left.ChangeDutyCycle(self.left_speed)

    def set_set_right_speed(self, value):
        self.right_speed = value
        self.pwm_right.ChangeDutyCycle(self.right_speed)

    def set_motor(self, left, right):
        if (right >= 0) and (right <= 100):
            GPIO.output(self.pin_right_forward, GPIO.HIGH)
            GPIO.output(self.pin_right_backward, GPIO.LOW)
            self.pwm_right.ChangeDutyCycle(right)
        elif (right < 0) and (right >= -100):
            GPIO.output(self.pin_right_forward, GPIO.LOW)
            GPIO.output(self.pin_right_backward, GPIO.HIGH)
            self.pwm_right.ChangeDutyCycle(0 - right)
        if (left >= 0) and (left <= 100):
            GPIO.output(self.pin_left_forward, GPIO.HIGH)
            GPIO.output(self.pin_left_backward, GPIO.LOW)
            self.pwm_left.ChangeDutyCycle(left)
        elif (left < 0) and (left >= -100):
            GPIO.output(self.pin_left_forward, GPIO.LOW)
            GPIO.output(self.pin_left_backward, GPIO.HIGH)
            self.pwm_left.ChangeDutyCycle(0 - left)

    def move(self, left=None, right=None, timeout=DEFAULT_TIMEOUT):
        if left is None: left = self.left_speed
        if right is None: right = self.right_speed
        if self.timer is not None: self.timer.cancel()
        if left < -100: left = -100
        if left > 100: left = 100
        if right < -100: left = -100
        if right > 100: left = 100
        self.set_motor(left, right)

        if self.left != left:
            self.publish("move/left", str(left), 1, True)
        if self.right != right:
            self.publish("move/right", str(right), 1, True)
        if self.left != left or self.right != right:
            self.publish("move", str(left) + " " + str(right), 1, True)
            self.logger.info("Moving left at " + str(left) + "%, right at " + str(right) + "%")

        self.left = left
        self.right = right
        if timeout > 0: self.timer = threading.Timer(timeout, self.halt).start()

    def halt(self):
        self.pwm_right.ChangeDutyCycle(0)
        self.pwm_left.ChangeDutyCycle(0)
        GPIO.output(self.pin_right_forward, GPIO.LOW)
        GPIO.output(self.pin_right_backward, GPIO.LOW)
        GPIO.output(self.pin_left_forward, GPIO.LOW)
        GPIO.output(self.pin_left_backward, GPIO.LOW)

        if self.left != 0:
            self.publish("move/left", "0", 1, True)
        if self.right != 0:
            self.publish("move/right", "0", 1, True)
        if self.left != 0 or self.right != 0:
            self.publish("move", "0 0", 1, True)
            self.logger.info("Stop moving")
        self.left = 0
        self.right = 0
