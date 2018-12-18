#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import time

import RPi.GPIO as GPIO

from lib.ModuleLooper import ModuleLooper

CS = 5
Clock = 25
Address = 24
DataOut = 23
Button = 7


class Tracking(ModuleLooper):
    """Tracking module"""

    __delay = -1
    __last = -1

    def __init__(self, num_sensors=5, debug=False):
        super(Tracking, self).__init__(debug=debug)
        self.__num_sensors = num_sensors
        self.__calibrated_min = [0] * self.__num_sensors
        self.__calibrated_max = [1023] * self.__num_sensors
        self.__last_value = 0

        GPIO.setup(Clock, GPIO.OUT)
        GPIO.setup(Address, GPIO.OUT)
        GPIO.setup(CS, GPIO.OUT)
        GPIO.setup(DataOut, GPIO.IN, GPIO.PUD_UP)
        GPIO.setup(Button, GPIO.IN, GPIO.PUD_UP)

    def initialize(self):
        super(Tracking, self).initialize()
        if self.module_mqtt is not None:
            self.module_mqtt.publish("delay", str(self.__delay), module=self)

    def on_mqtt_message(self, path, payload):
        if payload == "" or payload == "MEASURE":
            data = self.analog_read()
            self.logger.info("Measuring TR: " + str(data))
            if self.module_mqtt is not None:
                self.module_mqtt.publish("", str(data), module=self)
        else:
            self.__delay = 0 if (payload == "OFF") else float(payload)
            if self.__delay <= 0:
                self.__delay = 0
            if self.module_mqtt is not None:
                self.module_mqtt.publish("delay", str(self.__delay), module=self)
            self.__last = -1 if (self.__delay <= 0) else time.time() * 1000.0
            self.logger.info("Measuring track each " + str(self.__delay) + "ms")
            if self.__delay > 0:
                self.start()
            else:
                self.stop()

    def looper(self):
        if self.__last > 0 and 0 < self.__delay < time.time() - self.__last:
            data = self.analog_read()
            self.logger.info(str(data))
            if self.module_mqtt is not None:
                self.module_mqtt.client.publish("", str(data), module=self)
            self.__last = time.time()
        time.sleep(0.2)

    def analog_read(self):
        """
        Reads the sensor values into an array. There *MUST* be space for as many values as there were sensors
        specified in the constructor.

        Example usage:

        unsigned int sensor_values[8];

        sensors.read(sensor_values);

        The values returned are a measure of the reflectance in abstract units, with higher values corresponding to
        lower reflectance (e.g. a black surface or a void).
        """
        value = [0] * (self.__num_sensors + 1)
        # Read Channel0~channel6 AD value
        for j in range(0, self.__num_sensors + 1):
            GPIO.output(CS, GPIO.LOW)
            for i in range(0, 4):
                # sent 4-bit Address
                if (j >> (3 - i)) & 0x01:
                    GPIO.output(Address, GPIO.HIGH)
                else:
                    GPIO.output(Address, GPIO.LOW)
                # read MSB 4-bit data
                value[j] <<= 1
                if GPIO.input(DataOut):
                    value[j] |= 0x01
                GPIO.output(Clock, GPIO.HIGH)
                GPIO.output(Clock, GPIO.LOW)
            for i in range(0, 6):
                # read LSB 8-bit data
                value[j] <<= 1
                if GPIO.input(DataOut):
                    value[j] |= 0x01
                GPIO.output(Clock, GPIO.HIGH)
                GPIO.output(Clock, GPIO.LOW)
            # no mean ,just delay
            #            for i in range(0,6):
            #                GPIO.output(Clock, GPIO.HIGH)
            #                GPIO.output(Clock, GPIO.LOW)
            time.sleep(0.0001)
            GPIO.output(CS, GPIO.HIGH)
        #        print value[1:]
        return value[1:]

    def calibrate(self):
        """
        Reads the sensors 10 times and uses the results for
        calibration.  The sensor values are not returned; instead, the
        maximum and minimum values found over time are stored internally
        and used for the readCalibrated() method.
        """
        max_sensor_values = [0] * self.__num_sensors
        min_sensor_values = [0] * self.__num_sensors
        for j in range(0, 10):

            sensor_values = self.analog_read()

            for i in range(0, self.__num_sensors):

                # set the max we found THIS time
                if (j == 0) or max_sensor_values[i] < sensor_values[i]:
                    max_sensor_values[i] = sensor_values[i]

                # set the min we found THIS time
                if (j == 0) or min_sensor_values[i] > sensor_values[i]:
                    min_sensor_values[i] = sensor_values[i]

        # record the min and max calibration values
        for i in range(0, self.__num_sensors):
            if min_sensor_values[i] > self.__calibrated_min[i]:
                self.__calibrated_min[i] = min_sensor_values[i]
            if max_sensor_values[i] < self.__calibrated_max[i]:
                self.__calibrated_max[i] = max_sensor_values[i]

    def read_calibrated(self):
        """
        Returns values calibrated to a value between 0 and 1000, where
        0 corresponds to the minimum value read by calibrate() and 1000
        corresponds to the maximum value.  Calibration values are
        stored separately for each sensor, so that differences in the
        sensors are accounted for automatically.
        """
        value = 0
        # read the needed values
        sensor_values = self.analog_read()

        for i in range(0, self.__num_sensors):

            denominator = self.__calibrated_max[i] - self.__calibrated_min[i]

            if denominator != 0:
                value = (sensor_values[i] - self.__calibrated_min[i]) * 1000 / denominator

            if value < 0:
                value = 0
            elif value > 1000:
                value = 1000

            sensor_values[i] = value

        # print("readCalibrated",sensor_values)
        return sensor_values

    def read_line(self, white_line=0):
        """
        Operates the same as read calibrated, but also returns an
        estimated position of the robot with respect to a line. The
        estimate is made using a weighted average of the sensor indices
        multiplied by 1000, so that a return value of 0 indicates that
        the line is directly below sensor 0, a return value of 1000
        indicates that the line is directly below sensor 1, 2000
        indicates that it's below sensor 2000, etc.  Intermediate
        values indicate that the line is between two sensors.  The
        formula is:

           0*value0 + 1000*value1 + 2000*value2 + ...
           --------------------------------------------
                 value0  +  value1  +  value2 + ...

        By default, this function assumes a dark line (high values)
        surrounded by white (low values).  If your line is light on
        black, set the optional second argument white_line to true.  In
        this case, each sensor value will be replaced by (1000-value)
        before the averaging.
        """
        sensor_values = self.read_calibrated()
        avg = 0
        sum = 0
        on_line = 0
        for i in range(0, self.__num_sensors):
            value = sensor_values[i]
            if white_line:
                value = 1000 - value
            # keep track of whether we see the line at all
            if value > 200:
                on_line = 1

            # only average in values that are above a noise threshold
            if value > 50:
                avg += value * (i * 1000)  # this is for the weighted total,
                sum += value  # this is for the denominator

        if on_line != 1:
            # If it last read to the left of center, return 0.
            if self.__last_value < (self.__num_sensors - 1) * 1000 / 2:
                # print("left")
                self.__last_value = 0

            # If it last read to the right of center, return the max.
            else:
                # print("right")
                self.__last_value = (self.__num_sensors - 1) * 1000
        else:
            self.__last_value = avg / sum

        return self.__last_value, sensor_values
