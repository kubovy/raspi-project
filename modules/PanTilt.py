#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Pimoroni (https://github.com/pimoroni/pantilt-hat)
# Author: Jan Kubovy (jan@kubovy.eu)
#
import atexit
import time
from threading import Timer

from lib.Module import Module

PWM = 0
WS2812 = 1

RGB = 0
GRB = 1
RGBW = 2
GRBW = 3


class PanTilt(Module):
    """PanTilt HAT Driver

    Communicates with PanTilt HAT over i2c
    to control pan, tilt and light functions

    """
    REG_CONFIG = 0x00
    REG_SERVO1 = 0x01
    REG_SERVO2 = 0x03
    REG_WS2812 = 0x05
    REG_UPDATE = 0x4E
    UPDATE_WAIT = 0.03
    NUM_LEDS = 24

    module_mqtt = None

    def __init__(self,
                 enable_lights=True,
                 idle_timeout=2,  # Idle timeout in seconds
                 # light_mode=WS2812,
                 # light_type=RGB,
                 servo1_min=575,
                 servo1_max=2325,
                 servo2_min=575,
                 servo2_max=2325,
                 address=0x15,
                 debug=False):
        super(PanTilt, self).__init__(debug=debug)

        self.__is_setup = False

        self.__idle_timeout = idle_timeout
        self.__servo1_timeout = None
        self.__servo2_timeout = None

        self.__i2c_retries = 10
        self.__i2c_retry_time = 0.01

        self.__servo_registry = [self.REG_SERVO1, self.REG_SERVO2]
        self.__servo_timeouts = [None, None]
        self.__servo_stop = [self.__servo1_stop, self.__servo2_stop]
        self.__enable_servo = [False, False]
        self.__enable_lights = enable_lights
        self.__light_on = 0

        self.__servo_min = [servo1_min, servo2_min]
        self.__servo_max = [servo1_max, servo2_max]

        self.__light_mode = WS2812
        self.__light_type = RGB

        self.__i2c_address = address
        self.__i2c = None

    def on_mqtt_message(self, path, payload):
        if len(path) > 0:
            try:
                servo = int(path[0])
            except ValueError:
                servo = 1 if path[0] == "tilt" else 0

            if len(path) > 1 and path[1] == "deg" or path[1] == "degrees":  # {service}/control/pan-tilt/{servo}/deg
                self.set_servo(servo, -float(payload), "degrees")
            elif len(path) > 1 and path[1] == "percent":  # {service}/control/pan-tilt/{servo}/percent
                self.set_servo(servo, int(payload), "percent")
            elif payload == "ON":  # {service}/control/pan-tilt/{servo}
                self.servo_enable(servo, True)
            elif payload == "OFF":  # {service}/control/pan-tilt/{servo}
                self.servo_enable(servo, False)
            else:  # {service}/control/pan-tilt/{servo}
                self.set_servo(servo, int(payload), "raw")

    def setup(self):
        if self.__is_setup:
            return True

        if self.__i2c is None:
            try:
                from smbus import SMBus
                self.__i2c = SMBus(1)
            except ImportError:
                if version_info[0] < 3:
                    raise ImportError("This library requires python-smbus\n" +
                                      "Install with: sudo apt-get install python-smbus")
                elif version_info[0] == 3:
                    raise ImportError("This library requires python3-smbus\n" +
                                      "Install with: sudo apt-get install python3-smbus")

        self.clear()
        self.__set_config()
        atexit.register(self.__atexit)

        self.__is_setup = True

    def idle_timeout(self, value):
        """Set the idle timeout for the servos

        Configure the time, in seconds, after which the servos will be automatically disabled.

        :param value: Timeout in seconds

        """

        self.__idle_timeout = value

    def clear(self):
        """Clear the buffer."""
        self.__pixels = [0] * self.NUM_LEDS * 3
        self.__pixels += [1]

    def light_mode(self, mode):
        """Set the light mode for attached lights.

        PanTiltHAT can drive either WS2812 or SK6812 pixels,
        or provide a PWM dimming signal for regular LEDs.

        * PWM - PWM-dimmable LEDs
        * WS2812 - 24 WS2812 or 18 SK6812 pixels

        """

        self.setup()

        self.__light_mode = mode
        self.__set_config()

    def light_type(self, set_type):
        """Set the light type for attached lights.

        Set the type of lighting strip connected:

        * RGB - WS2812 pixels with RGB pixel order
        * RGB - WS2812 pixels with GRB pixel order
        * RGBW - SK6812 pixels with RGBW pixel order
        * GRBW - SK6812 pixels with GRBW pixel order

        """

        self.__light_type = set_type

    def num_pixels(self):
        """Returns the supported number of pixels depending on light mode.

        RGBW or GRBW support 18 pixels
        RGB supports 24 pixels

        """

        if self.__light_type in [RGBW, GRBW]:
            return 18

        return 24

    def brightness(self, brightness):
        """Set the brightness of the connected LED ring.

        This only applies if light_mode has been set to PWM.

        It will be ignored otherwise.

        :param brightness: Brightness from 0 to 255

        """

        self.setup()

        self.__check_int_range(brightness, 0, 255)

        if self.__light_mode == PWM:
            # The brightness value is taken from the first register of the WS2812 chain
            self.__i2c_write_byte(self.REG_WS2812, brightness)

    def set_all(self, red, green, blue, white=None):
        """Set all pixels in the buffer.

        :param red: Amount of red, from 0 to 255
        :param green: Amount of green, from 0 to 255
        :param blue: Amount of blue, from 0 to 255
        :param white: Optional amount of white for RGBW and GRBW strips

        """

        for index in range(self.num_pixels()):
            self.set_pixel(index, red, green, blue, white)

    def set_pixel_rgbw(self, index, red, green, blue, white):
        """Set a single pixel in the buffer for GRBW lighting stick

        :param index: Index of pixel from 0 to 17
        :param red: Amount of red, from 0 to 255
        :param green: Amount of green, from 0 to 255
        :param blue: Amount of blue, from 0 to 255
        :param white: Amount of white, from 0 to 255

        """

        self.set_pixel(index, red, green, blue, white)

    def set_pixel(self, index, red, green, blue, white=None):
        """Set a single pixel in the buffer.

        :param index: Index of pixel from 0 to 23
        :param red: Amount of red, from 0 to 255
        :param green: Amount of green, from 0 to 255
        :param blue: Amount of blue, from 0 to 255
        :param white: Optional amount of white for RGBW and GRBW strips

        """

        self.__check_int_range(index, 0, self.num_pixels() - 1)

        for color in [red, green, blue]:
            self.__check_int_range(color, 0, 255)

        if white is not None:
            self.__check_int_range(white, 0, 255)

        if self.__light_type in [RGBW, GRBW]:
            index *= 4
            if self.__light_type == RGBW:
                self.__pixels[index] = red
                self.__pixels[index + 1] = green
                self.__pixels[index + 2] = blue

            if self.__light_type == GRBW:
                self.__pixels[index] = green
                self.__pixels[index + 1] = red
                self.__pixels[index + 2] = blue

            if white is not None:
                self.__pixels[index + 3] = white

        else:
            index *= 3
            if self.__light_type == RGB:
                self.__pixels[index] = red
                self.__pixels[index + 1] = green
                self.__pixels[index + 2] = blue

            if self.__light_type == GRB:
                self.__pixels[index] = green
                self.__pixels[index + 1] = red
                self.__pixels[index + 2] = blue

    def show(self):
        """Display the buffer on the connected WS2812 strip."""

        self.setup()

        self.__i2c_write_block(self.REG_WS2812, self.__pixels[:32])
        self.__i2c_write_block(self.REG_WS2812 + 32, self.__pixels[32:64])
        self.__i2c_write_block(self.REG_WS2812 + 64, self.__pixels[64:])
        self.__i2c_write_byte(self.REG_UPDATE, 1)

    def servo_enable(self, index, state):
        """Enable or disable a servo.

        Disabling a servo turns off the drive signal.

        It's good practise to do this if you don't want
        the Pan/Tilt to point in a certain direction and
        instead want to save power.

        :param index: Servo index: either 0 or 1
        :param state: Servo state: True = on, False = off

        """

        self.setup()

        if index not in [0, 1]:
            raise ValueError("Servo index must be 0 or 1")

        if state not in [True, False]:
            raise ValueError("State must be True/False")

        self.__enable_servo[index] = state
        self.__set_config()

    def servo_pulse_min(self, index, value):
        """Set the minimum high pulse for a servo in microseconds.

        :param index: Servo index 0 or 1
        :param value: Value in microseconds

        """

        if index not in [0, 1]:
            raise ValueError("Servo index must be 0 or 1")

        self.__servo_min[index] = value

    def servo_pulse_max(self, index, value):
        """Set the maximum high pulse for a servo in microseconds.

        :param index: Servo index 0 or 1
        :param value: Value in microseconds

        """

        if index not in [0, 1]:
            raise ValueError("Servo index must be 1 or 2")

        self.__servo_max[index] = value

    def get_servo(self, index, units="raw"):
        """Get position of servo."""

        if index not in [0, 1]:
            raise ValueError("Servo index must be 0 or 1")

        self.setup()

        us_min, us_max = self.__servo_range(index)
        us = self.__i2c_read_word(self.__servo_registry[index])

        try:
            if units == "percent":
                return self.__servo_percent_to_us(us, us_min, us_max)
            elif units == "degrees":
                return self.__servo_us_to_degrees(us, us_min, us_max)
            else:
                return us
        except ValueError:
            return 0

    def set_servo(self, index, value, units="raw"):
        """Set position of servo.

        :param index: :param index: Servo index 0 or 1
        :param value: Angle in degrees from -90 to 90
        :param units: "percent", "degrees" or "raw"

        """
        if index not in [0, 1]:
            raise ValueError("Servo index must be 0 or 1")

        self.setup()

        if not self.__enable_servo[index]:
            self.__enable_servo[index] = True
            self.__set_config()

        us_min, us_max = self.__servo_range(index)
        if units == "percent":
            us = self.__servo_percent_to_us(value, us_min, us_max)
        elif units == "degrees":
            us = self.__servo_degrees_to_us(value, us_min, us_max)
        else:
            us = value
        self.__i2c_write_word(self.__servo_registry[index], us)

        if self.__idle_timeout > 0:
            if self.__servo_timeouts[index] is not None:
                self.__servo_timeouts[index].cancel()

            self.__servo_timeouts[index] = Timer(self.__idle_timeout, self.__servo_stop[index])
            self.__servo_timeouts[index].daemon = True
            self.__servo_timeouts[index].start()

    def __atexit(self):
        if self.__servo1_timeout is not None:
            self.__servo1_timeout.cancel()

        if self.__servo2_timeout is not None:
            self.__servo2_timeout.cancel()

        self.__enable_servo = [False, False]

        self.__set_config()

    def __set_config(self):
        """Generate config value for PanTilt HAT and write to device."""

        config = 0
        config |= self.__enable_servo[0]
        config |= self.__enable_servo[1] << 1
        config |= self.__enable_lights << 2
        config |= self.__light_mode << 3
        config |= self.__light_on << 4

        self.__i2c_write_byte(self.REG_CONFIG, config)

    def __check_int_range(self, value, value_min, value_max):
        """Check the type and bounds check an expected int value."""

        if type(value) is not int:
            raise TypeError("Value should be an integer")
        if value < value_min or value > value_max:
            raise ValueError("Value {value} should be between {min} and {max}".format(
                value=value,
                min=value_min,
                max=value_max))

    def __check_range(self, value, value_min, value_max):
        """Check the type and bounds check an expected int value."""

        if value < value_min or value > value_max:
            raise ValueError("Value {value} should be between {min} and {max}".format(
                value=value,
                min=value_min,
                max=value_max))

    def __servo_us_to_degrees(self, us, us_min, us_max):
        """Converts pulse time in microseconds to degrees

        :param us: Pulse time in microseconds
        :param us_min: Minimum possible pulse time in microseconds
        :param us_max: Maximum possible pulse time in microseconds

        """

        self.__check_range(us, us_min, us_max)
        servo_range = us_max - us_min
        angle = (float(us - us_min) / float(servo_range)) * 180.0
        return int(round(angle, 0)) - 90

    def __servo_degrees_to_us(self, angle, us_min, us_max):
        """Converts degrees into a servo pulse time in microseconds

        :param angle: Angle in degrees from -90 to 90

        """

        self.__check_range(angle, -90, 90)

        angle += 90
        servo_range = us_max - us_min
        us = (servo_range / 180.0) * angle
        return us_min + int(us)

    def __servo_us_to_percent(self, us, us_min, us_max):
        self.__check_range(us, us_min, us_max)
        servo_range = us_max - us_min
        percent = (float(us - us_min) / float(servo_range)) * 100.0
        return int(round(percent, 0))

    def __servo_percent_to_us(self, percent, us_min, us_max):
        self.__check_range(percent, 0, 100)

        servo_range = us_max - us_min
        us = (servo_range / 100.0) * percent
        return us_min + int(us)

    def __servo_range(self, servo_index):
        """Get the min and max range values for a servo"""

        return self.__servo_min[servo_index], self.__servo_max[servo_index]

    def __i2c_write_block(self, reg, data):
        if type(data) is list:
            for x in range(self.__i2c_retries):
                try:
                    self.__i2c.write_i2c_block_data(self.__i2c_address, reg, data)
                    return
                except IOError:
                    time.sleep(self.__i2c_retry_time)
                    continue

            raise IOError("Failed to write block")
        else:
            raise ValueError("Value must be a list")

    def __i2c_write_word(self, reg, data):
        if type(data) is int:
            for x in range(self.__i2c_retries):
                try:
                    self.__i2c.write_word_data(self.__i2c_address, reg, data)
                    return
                except IOError:
                    time.sleep(self.__i2c_retry_time)
                    continue

            raise IOError("Failed to write word")

    def __i2c_write_byte(self, reg, data):
        if type(data) is int:
            for x in range(self.__i2c_retries):
                try:
                    self.__i2c.write_byte_data(self.__i2c_address, reg, data)
                    return
                except IOError:
                    time.sleep(self.__i2c_retry_time)
                    continue

            raise IOError("Failed to write byte")

    def __i2c_read_byte(self, reg):
        for x in range(self.__i2c_retries):
            try:
                return self.__i2c.read_byte_data(self.__i2c_address, reg)
            except IOError:
                time.sleep(self.__i2c_retry_time)
                continue

        raise IOError("Failed to read byte")

    def __i2c_read_word(self, reg):
        for x in range(self.__i2c_retries):
            try:
                return self.__i2c.read_word_data(self.__i2c_address, reg)
            except IOError:
                time.sleep(self.__i2c_retry_time)
                continue

        raise IOError("Failed to read byte")

    def __servo1_stop(self):
        self.__servo_timeouts[0] = None
        self.__enable_servo[0] = False
        self.__set_config()

    def __servo2_stop(self):
        self.__servo_timeouts[1] = None
        self.__enable_servo[1] = False
        self.__set_config()
