#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import threading
from PCA9685 import PCA9685
from ModuleMQTT import ModuleMQTT


class Servo(ModuleMQTT):

    def __init__(self, client, service_name, servo_mins=None, servo_mids=None, servo_maxs=None, degree_span=180.0,
                 debug=False):
        super(Servo, self).__init__(client, service_name, "servo", debug)

        self.servo_mins = [1000] if servo_mins is None else servo_mins
        self.servo_mids = [1500] if servo_mids is None else servo_mids
        self.servo_maxs = [2000] if servo_maxs is None else servo_maxs
        self.servo_points_per_degree = float(servo_maxs[0] - servo_mins[0]) / degree_span

        self.pwm = PCA9685(0x40, debug)
        self.pwm.setPWMFreq(50)

        for servo in range(0, len(self.servo_mids)):
            self.set_position(servo, servo_mids[servo])

    def on_mqtt_message(self, path, payload):
        if len(path) > 0:
            try:
                servo = int(path[0])
            except ValueError:
                servo = 1 if path[0] == "pitch" else 0

            if len(path) > 1 and path[1] == "deg" or path[1] == "degrees":  # {service}/servo/camera/{servo}/deg
                self.set_position_degrees(servo, -float(payload))
            elif len(path) > 1 and path[1] == "percent":                    # {service}/servo/camera/{servo}/percent
                self.set_position_percent(servo, int(payload))
            else:                                                           # {service}/servo/camera/{servo}
                self.set_position(servo, int(payload))

    def servo_count(self):
        min(len(self.servo_mins), len(self.servo_mids), len(self.servo_maxs))

    def set_position(self, servo, position):
        position_min = self.servo_mins[servo]
        position_max = self.servo_maxs[servo]
        original = position
        if position > position_max: position = position_max
        if position < position_min: position = position_min
        self.logger.debug(str(original) + " -> " + str(position))

        self.publish(str(servo) + "/raw", position, 0, True)

        percent = 100 - int(float(position - position_min) * 100.0 / float(position_max - position_min))
        self.publish(str(servo) + "/percent", percent, 1, True)
        
        self.pwm.setServoPulse(servo, position)
        threading.Timer(0.5, self.stop).start()

    def set_position_percent(self, servo, percent):
        position_min = self.servo_mins[servo]
        position_max = self.servo_maxs[servo]
        if percent > 100: percent = 100
        if percent < 0: percent = 0
        position = position_min + int((100.0 - float(percent)) * float(position_max - position_min) / 100.0)
        self.logger.debug(str(percent) + "% -> " + str(position))
        self.set_position(servo, position)

    def set_position_degrees(self, servo, degrees):
        position_mid = self.servo_mids[servo]
        position = int(degrees * self.servo_points_per_degree + position_mid)
        self.logger.debug(str(degrees) + "deg -> " + str(position))
        self.set_position(servo, position)

    def stop(self):
        self.logger.debug("Stopping")
        self.pwm.stop(0)
        self.pwm.stop(1)
