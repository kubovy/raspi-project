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

    state = NONE

    control = "OFF"

    roll = 50
    pitch = 50

    buzzer = None
    servo = None
    wheels = None

    def __init__(self, client, service_name, pin_center=7, pin_a=8, pin_b=9, pin_c=10, pin_d=11, debug=False):
        super(Joystick, self).__init__(client, service_name, "joystick", "Joystick", debug)
        self.pin_center = pin_center
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.pin_c = pin_c
        self.pin_d = pin_d

        GPIO.setup(self.pin_center, GPIO.IN, GPIO.PUD_UP)
        GPIO.setup(self.pin_a, GPIO.IN, GPIO.PUD_UP)
        GPIO.setup(self.pin_b, GPIO.IN, GPIO.PUD_UP)
        GPIO.setup(self.pin_c, GPIO.IN, GPIO.PUD_UP)
        GPIO.setup(self.pin_d, GPIO.IN, GPIO.PUD_UP)

        self.publish("button", "NONE", 1, True)
        self.publish("center", "OFF", 1, True)
        self.publish("up", "OFF", 1, True)
        self.publish("right", "OFF", 1, True)
        self.publish("down", "OFF", 1, True)
        self.publish("left", "OFF", 1, True)

        self.publish("control", "OFF", 1, True)

    def on_start(self):
        super(Joystick, self).on_start()
        if self.control != "OFF":
            self.publish("control", self.control, 1, True)

    def on_stop(self):
        super(Joystick, self).on_stop()
        if self.control != "OFF":
            self.publish("control", "OFF", 1, True)
        self.control = "OFF"

    def on_mqtt_message(self, path, payload):
        if len(path) > 0 and path[0] == "state":       # {service}/control/joystick/state
            if payload == "ON":
                self.start("OFF")
            else:
                self.stop()
        elif len(path) > 0 and path[0] == "control":   # {service}/control/joystick/control
            if payload == "MOVEMENT":
                self.start("MOVEMENT")
            elif payload == "CAMERA":
                self.start("CAMERA")
            else:
                self.stop()

    def looper(self):
        if GPIO.input(self.pin_center) == 0:
            if self.state != self.pin_center:
                self.logger.info("CENTER")
                self.publish("button", "CENTER", 1, True)
                self.publish("center", "OPEN", 1, True)
                self.state = self.pin_center
            if self.control == "CAMERA" and self.servo is not None:
                if self.buzzer is not None:
                    self.buzzer.on()
            if self.control == "MOVEMENT" and self.wheels is not None:
                self.wheels.halt()
                if self.buzzer is not None:
                    self.buzzer.on()
        elif GPIO.input(self.pin_a) == 0:
            if self.state != self.pin_a:
                self.logger.info("UP")
                self.publish("button", "UP", 1, True)
                self.publish("up", "OPEN", 1, True)
                self.state = self.pin_a
            if self.control == "CAMERA" and self.servo is not None:
                self.pitch += 5
                self.servo.set_position_percent(1, self.pitch)
            elif self.control == "MOVEMENT" and self.wheels is not None:
                self.wheels.move(50, 50, 1.0)
        elif GPIO.input(self.pin_b) == 0:
            if self.state != self.pin_b:
                self.logger.info("RIGHT")
                self.publish("button", "RIGHT", 1, True)
                self.publish("right", "OPEN", 1, True)
                self.state = self.pin_b
            if self.control == "CAMERA" and self.servo is not None:
                self.roll += 5
                self.servo.set_position_percent(0, self.roll)
            elif self.control == "MOVEMENT" and self.wheels is not None:
                self.wheels.move(-50, 50, 1.0)
        elif GPIO.input(self.pin_c) == 0:
            if self.state != self.pin_c:
                self.logger.info("LEFT")
                self.publish("button", "LEFT", 1, True)
                self.publish("left", "OPEN", 1, True)
                self.state = self.pin_c
            if self.control == "CAMERA" and self.servo is not None:
                self.roll -= 5
                self.servo.set_position_percent(0, self.roll)
            elif self.control == "MOVEMENT" and self.wheels is not None:
                self.wheels.move(50, -50, 1.0)
        elif GPIO.input(self.pin_d) == 0:
            if self.state != self.pin_d:
                self.logger.info("DOWN")
                self.publish("button", "DOWN", 1, True)
                self.publish("down", "OPEN", 1, True)
                self.state = self.pin_d
            if self.control == "CAMERA" and self.servo is not None:
                self.pitch -= 5
                self.servo.set_position_percent(1, self.pitch)
            elif self.control == "MOVEMENT" and self.wheels is not None:
                self.wheels.move(-50, -50, 1.0)
        else:
            if self.state != self.NONE:
                self.logger.info("NONE")
                self.publish("button", "NONE", 1, True)
                if self.state == self.pin_center:
                    self.publish("center", "CLOSED", 1, True)
                elif self.state == self.pin_a:
                    self.publish("up", "CLOSED", 1, True)
                elif self.state == self.pin_b:
                    self.publish("right", "CLOSED", 1, True)
                elif self.state == self.pin_c:
                    self.publish("down", "CLOSED", 1, True)
                elif self.state == self.pin_d:
                    self.publish("left", "CLOSED", 1, True)
                self.state = self.NONE
                if self.buzzer is not None:
                    self.buzzer.off()
                if self.wheels is not None:
                    self.wheels.halt()

        time.sleep(0.2)

    def start(self, control="OFF"):
        self.control = control
        super(Joystick, self).start()
