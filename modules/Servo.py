#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import threading

from lib.Module import Module
from lib.PCA9685 import PCA9685


class Servo(Module):
    """Servo module"""

    module_mqtt = None

    def __init__(self, mins=None, mids=None, maxs=None, degree_span=180.0, debug=False):
        super(Servo, self).__init__(debug=debug)

        self.__servo_mins = [1000] if mins is None else mins
        self.__servo_mids = [1500] if mids is None else mids
        self.__servo_maxs = [2000] if maxs is None else maxs
        self.__servo_points_per_degree = float(maxs[0] - mins[0]) / degree_span

        self.__pwm = PCA9685(0x40, debug)
        self.__pwm.setPWMFreq(50)

    def initialize(self):
        super(Servo, self).initialize()
        for servo in range(0, len(self.__servo_mids)):
            self.set_position(servo, self.__servo_mids[servo])

    def on_mqtt_message(self, path, payload):
        if len(path) > 0:
            try:
                servo = int(path[0])
            except ValueError:
                servo = 1 if path[0] == "pitch" else 0

            if len(path) > 1 and path[1] == "deg" or path[1] == "degrees":  # {service}/servo/camera/{servo}/deg
                self.set_position_degrees(servo, -float(payload))
            elif len(path) > 1 and path[1] == "percent":  # {service}/servo/camera/{servo}/percent
                self.set_position_percent(servo, int(payload))
            else:  # {service}/servo/camera/{servo}
                self.set_position(servo, int(payload))

    def servo_count(self):
        min(len(self.__servo_mins), len(self.__servo_mids), len(self.__servo_maxs))

    def set_position(self, servo, position):
        position_min = self.__servo_mins[servo]
        position_max = self.__servo_maxs[servo]
        original = position
        if position > position_max:
            position = position_max
        if position < position_min:
            position = position_min
        self.logger.debug(str(original) + " -> " + str(position))

        if self.module_mqtt is not None:
            self.module_mqtt.publish(str(servo) + "/raw", position, module=self)

        percent = 100 - int(float(position - position_min) * 100.0 / float(position_max - position_min))
        if self.module_mqtt is not None:
            self.module_mqtt.publish(str(servo) + "/percent", percent, module=self)

        self.__pwm.setServoPulse(servo, position)
        threading.Timer(0.5, self.stop_servos).start()

    def set_position_percent(self, servo, percent):
        position_min = self.__servo_mins[servo]
        position_max = self.__servo_maxs[servo]
        if percent > 100:
            percent = 100
        if percent < 0:
            percent = 0
        position = position_min + int((100.0 - float(percent)) * float(position_max - position_min) / 100.0)
        self.logger.debug(str(percent) + "% -> " + str(position))
        self.set_position(servo, position)

    def set_position_degrees(self, servo, degrees):
        position_mid = self.__servo_mids[servo]
        position = int(degrees * self.__servo_points_per_degree + position_mid)
        self.logger.debug(str(degrees) + "deg -> " + str(position))
        self.set_position(servo, position)

    def stop_servos(self):
        self.logger.debug("Stopping")
        self.__pwm.stop(0)
        self.__pwm.stop(1)
