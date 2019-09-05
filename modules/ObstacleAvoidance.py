#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import time
from threading import Timer

from lib.Module import Module

MODE_RUNNING = "RUNNING"
MODE_TURNING_LEFT = "TURNING_LEFT"
MODE_TURNING_RIGHT = "TURNING_RIGHT"
MODE_CHECK_SPACE = "CHECK_SPACE"

RUNNING_SPEEDS = [10, 30, 50, 75, 85, 100]
RUNNING_DISTANCES = [200, 500, 1000, 2000, 2500]
TURNING_DISTANCE_MIN = 800.0  # mm
TURNING_SPEED = 30

CHECK_SPEED = 30
CHECK_INTERVAL = 0.09
CHECK_ROUND_ITERATIONS = 26


class ObstacleAvoidance(Module):
    """
    Obstacle avoidance
    """

    module_ir_sensor = None
    module_mqtt = None
    module_ultrasonic = None
    module_wheels = None

    __distance = -1
    __left = -1
    __right = -1
    __left_timestamp = -1
    __right_timestamp = -1

    __left_speed = 30
    __right_speed = 30
    __interval = 0
    __mode = MODE_RUNNING
    __iterations = -1
    __distances = []
    __last_distance = -1

    def initialize(self):
        super(ObstacleAvoidance, self).initialize()
        if self.module_mqtt is not None:
            self.module_mqtt.publish("obstacle-avoidance", "OFF", module=self)

    def on_mqtt_message(self, path, payload):
        if len(path) == 0:
            if payload == "ON":
                self.__start_obstacle_avoidance()
            else:
                self.__stop_obstacle_avoidance()

    def __start_obstacle_avoidance(self):
        # if self.thread is None:
        #    self.interrupted = False
        #    self.thread = threading.Thread(target=self.looper)
        #    self.thread.start()
        if self.module_mqtt is not None:
            self.module_mqtt.publish("obstacle-avoidance", "ON", module=self)
        if self.module_ir_sensor is not None:
            self.module_ir_sensor.subscribe(self.__on_infrared_distance)
        if self.module_ultrasonic is not None:
            self.module_ultrasonic.subscribe(self.__on_ultrasonic_distance)
        # return self.thread
        # self.update_wheels()

    def __stop_obstacle_avoidance(self):
        # self.interrupted = True
        # if self.thread is not None:
        #    self.thread.join(5)
        # self.thread = None
        if self.module_mqtt is not None:
            self.module_mqtt.publish("obstacle-avoidance", "OFF", module=self)

        if self.module_ir_sensor is not None:
            self.module_ir_sensor.unsubscribe(self.__on_infrared_distance)
        if self.module_ultrasonic is not None:
            self.module_ultrasonic.unsubscribe(self.__on_ultrasonic_distance)
        if self.module_wheels is not None:
            self.module_wheels.halt()

    def __on_infrared_distance(self, state):
        left = state[0]
        right = state[1]
        if self.__left != left or self.__right != right:
            self.logger.info("Left: " + str(left) + ", Right: " + str(right))
        if self.__left != left:
            self.__left_timestamp = time.time() if left == 0 else -1
            self.__left = left
        if self.__right != right:
            self.__right_timestamp = time.time() if right == 0 else -1
            self.__right = right
        if not self.__mode.startswith("CHECK_"):
            self.__update_wheels()

    def __on_ultrasonic_distance(self, distance):
        if self.__distance != distance:
            self.logger.info("Distance: " + str(distance))
            self.__distance = distance
        if not self.__mode.startswith("CHECK_"):
            self.__update_wheels()

    def __update_wheels(self):
        if self.__mode == MODE_RUNNING and (self.__left == 0 or self.__right == 0):
            self.__left_speed = self.__right_speed = 0
            self.__interval = 0
            self.__mode = MODE_TURNING_RIGHT if self.__left_timestamp > self.__right_timestamp else MODE_TURNING_LEFT
            self.logger.info("Mode: " + self.__mode + ", "
                             + "Left time:" + str(self.__left_timestamp) + ", "
                             + "Right time: " + str(self.__right_timestamp))
        elif self.__mode == MODE_RUNNING:
            speed = RUNNING_SPEEDS[-1]
            for i in range(0, len(RUNNING_DISTANCES)):
                if self.__distance < RUNNING_DISTANCES[i]:
                    speed = RUNNING_SPEEDS[i]
                    break
            self.__left_speed = self.__right_speed = speed
            self.__interval = 0
        elif self.__mode == MODE_TURNING_LEFT \
                and self.__left == 1 \
                and self.__right == 1 \
                and self.__distance > TURNING_DISTANCE_MIN:
            self.__left_speed = self.__right_speed = 10
            self.__interval = 0
            self.__mode = MODE_RUNNING
            self.logger.info("Mode: " + self.__mode + ", Left: " + str(self.__left) + ", Right: " + str(self.__right))
        elif self.__mode == MODE_TURNING_LEFT:
            self.__left_speed = -TURNING_SPEED
            self.__right_speed = TURNING_SPEED
            self.__interval = 0.5
        elif self.__mode == MODE_TURNING_RIGHT \
                and self.__left == 1 \
                and self.__right == 1 \
                and self.__distance > TURNING_DISTANCE_MIN:
            self.__left_speed = self.__right_speed = 10
            self.__interval = 0
            self.__mode = MODE_RUNNING
            self.logger.info("Mode: " + self.__mode + ", Left: " + str(self.__left) + ", Right: " + str(self.__right))
        elif self.__mode == MODE_TURNING_RIGHT:
            self.__left_speed = TURNING_SPEED
            self.__right_speed = -TURNING_SPEED
            self.__interval = 0.5
        elif self.__mode == MODE_CHECK_SPACE:
            if self.__iterations < 0:
                self.__distances = []
                self.__iterations = 0
            self.logger.info("Mode: " + self.__mode + ", Iterations: " + str(self.__iterations))
            distance = self.__distance
            if self.__iterations > CHECK_ROUND_ITERATIONS * 2:  # Rounds finished
                self.__iterations = -1
                self.__left_speed = self.__right_speed = 0
                self.__interval = 0
                self.__mode = "STOP"
            elif self.__last_distance != distance:  # Distance acquired
                self.__left_speed = CHECK_SPEED
                self.__right_speed = -CHECK_SPEED
                self.__interval = CHECK_INTERVAL
                self.__iterations += 1
                self.__last_distance = distance
                self.__distances.append(distance)
                Timer(1.0, self.__update_wheels).start()
            else:  # Distance not acquired, try again
                self.__left_speed = self.__right_speed = 0
                self.__interval = 0
                Timer(1.0, self.__update_wheels).start()
        else:
            self.logger.info("Mode: " + self.__mode + ", "
                             + "Left speed: " + str(self.__left_speed) + ", "
                             + "Right speed: " + str(self.__right_speed))

        # self.logger.info("Updating: " + self.mode + ", "
        #                  + "Left: " + str(self.left) + ", "
        #                  + "Right: " + str(self.right) + ", "
        #                  + "Distance: " + str(self.distance))
        if self.module_wheels is not None:
            self.module_wheels.move(self.__left_speed, self.__right_speed, self.__interval)
