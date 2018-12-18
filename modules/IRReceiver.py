#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import threading
import time

import RPi.GPIO as GPIO

from lib.ModuleLooper import ModuleLooper


class IRReceiver(ModuleLooper):
    module_buzzer = None
    module_pixels = None
    module_servo = None
    module_wheels = None

    __control = False
    __last_action = None

    __speed = 50
    __roll = 50
    __pitch = 50
    __light_backward = False
    __timer = None

    def __init__(self, pin=17, debug=False):
        super(IRReceiver, self).__init__(debug=debug)

        self.__pin = pin
        GPIO.setup(self.__pin, GPIO.IN)

    def initialize(self):
        super(IRReceiver, self).initialize()
        if self.module_mqtt is not None:
            self.module_mqtt.publish("control", "OFF", module=self)

    def start(self, control=False):
        self.__control = control
        if self.__control != control and self.is_running():
            self.on_start()
        super(IRReceiver, self).start()

    def on_start(self):
        super(IRReceiver, self).on_start()
        if self.__control and self.module_mqtt is not None:
            self.module_mqtt.publish("control", "ON", module=self)

    def on_stop(self):
        super(IRReceiver, self).on_stop()
        if self.__control and self.module_mqtt is not None:
            self.module_mqtt.publish("control", "OFF", module=self)
        self.__control = False

    def on_mqtt_message(self, path, payload):
        if len(path) > 0 and path[0] == "state":  # {service}/control/{module}/state
            if payload == "CONTROL":
                self.start(True)
                if self.module_pixels is not None:
                    self.module_pixels.notify([
                        [[0, 0, 255], [255, 0, 255], [255, 0, 255], [0, 0, 255]],
                        [[0, 255, 0], [0, 0, 0], [0, 0, 0], [0, 255, 0]]
                    ], [0.5, 1.0])
            elif payload == "ON":
                self.start(False)
                if self.module_pixels is not None:
                    self.module_pixels.notify([
                        [[0, 0, 255], [0, 0, 0], [0, 0, 0], [0, 0, 255]],
                        [[0, 255, 0], [0, 0, 0], [0, 0, 0], [0, 255, 0]]
                    ], [0.5, 1.0])
            else:
                self.stop()
                if self.module_pixels is not None:
                    self.module_pixels.notify([
                        [[0, 0, 255], [0, 0, 0], [0, 0, 0], [0, 0, 255]],
                        [[255, 0, 0], [0, 0, 0], [0, 0, 0], [255, 0, 0]]
                    ], [0.5, 1.0])

    def perform(self, action):
        self.logger.info("Performing: " + str(action))
        if action == "MOVE_FORWARD":
            if self.module_wheels is not None:
                self.module_wheels.move(self.__speed, self.__speed, 0.5)
            self.__last_action = action
        elif action == "MOVE_BACKWARD":
            if self.module_wheels is not None:
                self.module_wheels.move(-self.__speed, -self.__speed, 0.5)
            self.__last_action = action
        elif action == "ROTATE_LEFT":
            if self.module_wheels is not None:
                self.module_wheels.move(self.__speed, -self.__speed, 0.1)
            self.__last_action = action
        elif action == "ROTATE_RIGHT":
            if self.module_wheels is not None:
                self.module_wheels.move(-self.__speed, self.__speed, 0.1)
            self.__last_action = action
        elif action == "TURN_LEFT":
            if self.module_wheels is not None:
                self.module_wheels.move(self.__speed, 0, 0.25)
            self.__last_action = action
        elif action == "TURN_RIGHT":
            if self.module_wheels is not None:
                self.module_wheels.move(0, self.__speed, 0.25)
            self.__last_action = action
        elif action == "TURN_BACK_LEFT":
            if self.module_wheels is not None:
                self.module_wheels.move(-self.__speed, 0, 0.25)
            self.__last_action = action
        elif action == "TURN_BACK_RIGHT":
            if self.module_wheels is not None:
                self.module_wheels.move(0, -self.__speed, 0.25)
            self.__last_action = action
        elif action == "SPEED_DECREASE":
            self.__speed += 5
            if self.__speed > 100:
                self.__speed = 100
            self.__last_action = action
        elif action == "SPEED_INCREASE":
            self.__speed -= 5
            if self.__speed < 0:
                self.__speed = 10
            self.__last_action = action
        elif action == "STOP":
            self.perform("LIGHT_BREAK")
            if self.module_wheels is not None:
                self.module_wheels.halt()
            self.__last_action = action
        elif action == "ROLL_LEFT":
            self.__roll -= 5
            if self.module_servo is not None:
                self.module_servo.set_position_percent(0, self.__roll)
            self.__last_action = action
        elif action == "ROLL_RIGHT":
            self.__roll += 5
            if self.module_servo is not None:
                self.module_servo.set_position_percent(0, self.__roll)
            self.__last_action = action
        elif action == "PITCH_UP":
            self.__pitch += 5
            if self.module_servo is not None:
                self.module_servo.set_position_percent(1, self.__pitch)
            self.__last_action = action
        elif action == "PITCH_DOWN":
            self.__pitch -= 5
            if self.module_servo is not None:
                self.module_servo.set_position_percent(1, self.__pitch)
            self.__last_action = action
        elif action == "BLINK_LEFT":
            self.__last_action = action
            if self.module_pixels is not None:
                self.module_pixels.notify([
                    [[0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 128, 0]],
                    [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 128, 0]],
                    [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 128, 0]],
                    [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 128, 0]],
                    [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]]
                ], [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
        elif action == "BLINK_RIGHT":
            if self.module_pixels is not None:
                self.module_pixels.notify([
                    [[255, 128, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[255, 128, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[255, 128, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[255, 128, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]]
                ], [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
            self.__last_action = action
        elif action == "LIGHT_BREAK":
            if self.module_pixels is not None:
                self.module_pixels.notify([[[255, 0, 0], [0, 0, 0], [0, 0, 0], [255, 0, 0]]], [1])
            self.__last_action = action
        elif action == "LIGHT_BACKWARD":
            if self.module_pixels is not None:
                if self.__light_backward:
                    self.module_pixels.set_color(0, 0, 0, 0)
                    self.module_pixels.set_color(1, 0, 0, 0)
                    self.module_pixels.set_color(2, 0, 0, 0)
                    self.module_pixels.set_color(3, 0, 0, 0)
                    self.__light_backward = False
                else:
                    self.module_pixels.set_color(0, 0, 0, 0)
                    self.module_pixels.set_color(1, 255, 255, 255)
                    self.module_pixels.set_color(2, 255, 255, 255)
                    self.module_pixels.set_color(3, 0, 0, 0)
                    self.__light_backward = True
            self.__last_action = None
        elif action == "BUZZER":
            if self.module_buzzer is not None:
                self.module_buzzer.beep(0.5)
            self.__last_action = action
        elif action == "REPEAT":
            self.perform(self.__last_action)
        elif action == "NO_INPUT":
            if self.module_wheels is not None:
                self.module_wheels.halt()
            self.__last_action = None

    def cancel(self):
        self.perform("NO_INPUT")

    def looper(self):
        key = self.__get_key()
        if key is not None:
            if self.__timer is not None:
                self.__timer.cancel()
                self.__timer = None
            self.logger.info("Key: " + str(key))
            self.module_mqtt.publish("key", key, module=self)
            if self.__control:
                if key == 69:
                    self.perform("ROLL_LEFT")  # CH-
                elif key == 70:
                    self.perform("PITCH_UP")  # CH
                elif key == 71:
                    self.perform("ROLL_RIGHT")  # CH+
                elif key == 68:
                    self.perform("BLINK_LEFT")  # PREV
                elif key == 64:
                    self.perform("PITCH_DOWN")  # NEXT
                elif key == 67:
                    self.perform("BLINK_RIGHT")  # PLAY/PAUSE
                elif key == 7:
                    self.perform("SPEED_DECREASE")  # VOL-
                elif key == 21:
                    self.perform("SPEED_INCREASE")  # VOL+
                elif key == 9:
                    self.perform("BUZZER")  # EQ
                elif key == 25:
                    self.perform("LIGHT_BREAK")  # 100+
                elif key == 13:
                    self.perform("LIGHT_BACKWARD")  # 200+
                elif key == 12:
                    self.perform("TURN_LEFT")  # 1
                elif key == 24:
                    self.perform("MOVE_FORWARD")  # 2
                elif key == 94:
                    self.perform("TURN_RIGHT")  # 3
                elif key == 8:
                    self.perform("ROTATE_LEFT")  # 4
                elif key == 28:
                    self.perform("STOP")  # 5
                elif key == 90:
                    self.perform("ROTATE_RIGHT")  # 6
                elif key == 66:
                    self.perform("TURN_BACK_LEFT")  # 7
                elif key == 82:
                    self.perform("MOVE_BACKWARD")  # 8
                elif key == 74:
                    self.perform("TURN_BACK_RIGHT")  # 9
                elif key == 255:
                    self.perform("REPEAT")  # Repeat
            self.__timer = threading.Timer(1.0, self.cancel).start()

    def __get_key(self):
        if GPIO.input(self.__pin) == 0:
            count = 0
            while GPIO.input(self.__pin) == 0 and count < 200:  # 9ms
                count += 1
                time.sleep(0.00006)
            if count < 10:
                return
            count = 0
            while GPIO.input(self.__pin) == 1 and count < 80:  # 4.5ms
                count += 1
                time.sleep(0.00006)

            idx = 0
            cnt = 0
            data = [0, 0, 0, 0]
            for i in range(0, 32):
                count = 0
                while GPIO.input(self.__pin) == 0 and count < 15:  # 0.56ms
                    count += 1
                    time.sleep(0.00006)

                count = 0
                while GPIO.input(self.__pin) == 1 and count < 40:  # 0: 0.56mx
                    count += 1  # 1: 1.69ms
                    time.sleep(0.00006)

                if count > 7:
                    data[idx] |= 1 << cnt
                if cnt == 7:
                    cnt = 0
                    idx += 1
                else:
                    cnt += 1
            # self.logger.debug(str(data))
            if data[0] + data[1] == 0xFF and data[2] + data[3] == 0xFF:  # check
                return data[2]
            else:
                return 0xFF  # "repeat"
