#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
from lib.ModuleMQTT import ModuleMQTT
from threading import Timer
import time
import atexit


PWM = 0
WS2812 = 1

RGB = 0
GRB = 1
RGBW = 2
GRBW = 3


class PanTilt(ModuleMQTT):
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

    def __init__(self,
                 client,
                 service_name,
                 enable_lights=True,
                 idle_timeout=2, # Idle timeout in seconds
                 light_mode=WS2812,
                 light_type=RGB,
                 servo1_min=575,
                 servo1_max=2325,
                 servo2_min=575,
                 servo2_max=2325,
                 address=0x15,
                 i2c_bus=None,
                 debug=False):
        super(PanTilt, self).__init__(client, service_name, "pantilt", debug)

        self._is_setup = False

        self._idle_timeout = idle_timeout
        self._servo1_timeout = None
        self._servo2_timeout = None

        self._i2c_retries = 10
        self._i2c_retry_time = 0.01

        self._servo_registry = [self.REG_SERVO1, self.REG_SERVO2]
        self._servo_timeouts = [None, None]
        self._servo_stop = [self._servo1_stop, self._servo2_stop]
        self._enable_servo = [False, False]
        self._enable_lights = enable_lights
        self._light_on = 0

        self._servo_min = [servo1_min, servo2_min]
        self._servo_max = [servo1_max, servo2_max]

        self._light_mode = light_mode
        self._light_type = light_type

        self._i2c_address = address
        self._i2c = i2c_bus

    def on_mqtt_message(self, path, payload):
        if len(path) > 0:
            try:
                servo = int(path[0])
            except ValueError:
                servo = 1 if path[0] == "tilt" else 0

            if len(path) > 1 and path[1] == "deg" or path[1] == "degrees":  # {service}/control/pantilt/{servo}/deg
                self.set_servo(servo, -float(payload), "degrees")
            elif len(path) > 1 and path[1] == "percent":                    # {service}/control/pantilt/{servo}/percent
                self.set_servo(servo, int(payload), "percent")
            elif payload == "ON":                                           # {service}/control/pantilt/{servo}
                self.servo_enable(servo, True)
            elif payload == "OFF":                                          # {service}/control/pantilt/{servo}
                self.servo_enable(servo, False)
            else:                                                           # {service}/control/pantilt/{servo}
                self.set_servo(servo, int(payload), "raw")

    def setup(self):
        if self._is_setup:
            return True

        if self._i2c is None:
            try:
                from smbus import SMBus
                self._i2c = SMBus(1)
            except ImportError:
                if version_info[0] < 3:
                    raise ImportError("This library requires python-smbus\nInstall with: sudo apt-get install python-smbus")
                elif version_info[0] == 3:
                    raise ImportError("This library requires python3-smbus\nInstall with: sudo apt-get install python3-smbus")

        self.clear()
        self._set_config()
        atexit.register(self._atexit)

        self._is_setup = True

    def _atexit(self):
        if self._servo1_timeout is not None:
            self._servo1_timeout.cancel()

        if self._servo2_timeout is not None:
            self._servo2_timeout.cancel()

        self._enable_servo = [False, False]

        self._set_config()

    def idle_timeout(self, value):
        """Set the idle timeout for the servos

        Configure the time, in seconds, after which the servos will be automatically disabled.

        :param value: Timeout in seconds

        """

        self._idle_timeout = value

    def _set_config(self):
        """Generate config value for PanTilt HAT and write to device."""

        config = 0
        config |= self._enable_servo[0]
        config |= self._enable_servo[1] << 1
        config |= self._enable_lights << 2
        config |= self._light_mode    << 3
        config |= self._light_on      << 4

        self._i2c_write_byte(self.REG_CONFIG, config)

    def _check_int_range(self, value, value_min, value_max):
        """Check the type and bounds check an expected int value."""

        if type(value) is not int:
            raise TypeError("Value should be an integer")
        if value < value_min or value > value_max:
            raise ValueError("Value {value} should be between {min} and {max}".format(
                value=value,
                min=value_min,
                max=value_max))

    def _check_range(self, value, value_min, value_max):
        """Check the type and bounds check an expected int value."""

        if value < value_min or value > value_max:
            raise ValueError("Value {value} should be between {min} and {max}".format(
                value=value,
                min=value_min,
                max=value_max))

    def _servo_us_to_degrees(self, us, us_min, us_max):
        """Converts pulse time in microseconds to degrees

        :param us: Pulse time in microseconds
        :param us_min: Minimum possible pulse time in microseconds
        :param us_max: Maximum possible pulse time in microseconds

        """

        self._check_range(us, us_min, us_max)
        servo_range = us_max - us_min
        angle = (float(us - us_min) / float(servo_range)) * 180.0
        return int(round(angle, 0)) - 90

    def _servo_degrees_to_us(self, angle, us_min, us_max):
        """Converts degrees into a servo pulse time in microseconds

        :param angle: Angle in degrees from -90 to 90

        """

        self._check_range(angle, -90, 90)

        angle += 90
        servo_range = us_max - us_min
        us = (servo_range / 180.0) * angle
        return us_min + int(us)

    def _servo_us_to_percent(self, us, us_min, us_max):
        self._check_range(us, us_min, us_max)
        servo_range = us_max - us_min
        percent = (float(us - us_min) / float(servo_range)) * 100.0
        return int(round(percent, 0))

    def _servo_percent_to_us(self, percent, us_min, us_max):
        self._check_range(percent, 0, 100)

        servo_range = us_max - us_min
        us = (servo_range / 100.0) * percent
        return us_min + int(us)

    def _servo_range(self, servo_index):
        """Get the min and max range values for a servo"""

        return self._servo_min[servo_index], self._servo_max[servo_index]

    def _i2c_write_block(self, reg, data):
        if type(data) is list:
            for x in range(self._i2c_retries):
                try:
                    self._i2c.write_i2c_block_data(self._i2c_address, reg, data)
                    return
                except IOError:
                    time.sleep(self._i2c_retry_time)
                    continue

            raise IOError("Failed to write block")
        else:
            raise ValueError("Value must be a list")

    def _i2c_write_word(self, reg, data):
        if type(data) is int:
            for x in range(self._i2c_retries):
                try:
                    self._i2c.write_word_data(self._i2c_address, reg, data)
                    return
                except IOError:
                    time.sleep(self._i2c_retry_time)
                    continue

            raise IOError("Failed to write word")

    def _i2c_write_byte(self, reg, data):
        if type(data) is int:
            for x in range(self._i2c_retries):
                try:
                    self._i2c.write_byte_data(self._i2c_address, reg, data)
                    return
                except IOError:
                    time.sleep(self._i2c_retry_time)
                    continue

            raise IOError("Failed to write byte")

    def _i2c_read_byte(self, reg):
        for x in range(self._i2c_retries):
            try:
                return self._i2c.read_byte_data(self._i2c_address, reg)
            except IOError:
                time.sleep(self._i2c_retry_time)
                continue

        raise IOError("Failed to read byte")

    def _i2c_read_word(self, reg):
        for x in range(self._i2c_retries):
            try:
                return self._i2c.read_word_data(self._i2c_address, reg)
            except IOError:
                time.sleep(self._i2c_retry_time)
                continue

        raise IOError("Failed to read byte")

    def clear(self):
        """Clear the buffer."""

        self._pixels = [0] * self.NUM_LEDS * 3
        self._pixels += [1]

    def light_mode(self, mode):
        """Set the light mode for attached lights.

        PanTiltHAT can drive either WS2812 or SK6812 pixels,
        or provide a PWM dimming signal for regular LEDs.

        * PWM - PWM-dimmable LEDs
        * WS2812 - 24 WS2812 or 18 SK6812 pixels

        """

        self.setup()

        self._light_mode = mode
        self._set_config()

    def light_type(self, set_type):
        """Set the light type for attached lights.

        Set the type of lighting strip connected:

        * RGB - WS2812 pixels with RGB pixel order
        * RGB - WS2812 pixels with GRB pixel order
        * RGBW - SK6812 pixels with RGBW pixel order
        * GRBW - SK6812 pixels with GRBW pixel order

        """

        self._light_type = set_type

    def num_pixels(self):
        """Returns the supported number of pixels depending on light mode.

        RGBW or GRBW support 18 pixels
        RGB supports 24 pixels

        """

        if self._light_type in [RGBW, GRBW]:
            return 18

        return 24

    def brightness(self, brightness):
        """Set the brightness of the connected LED ring.

        This only applies if light_mode has been set to PWM.

        It will be ignored otherwise.

        :param brightness: Brightness from 0 to 255

        """

        self.setup()

        self._check_int_range(brightness, 0, 255)

        if self._light_mode == PWM:
            # The brightness value is taken from the first register of the WS2812 chain
            self._i2c_write_byte(self.REG_WS2812, brightness)

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

        self._check_int_range(index, 0, self.num_pixels() - 1)

        for color in [red, green, blue]:
            self._check_int_range(color, 0, 255)

        if white is not None:
            self._check_int_range(white, 0, 255)

        if self._light_type in [RGBW, GRBW]:
            index *= 4
            if self._light_type == RGBW:
                self._pixels[index] = red
                self._pixels[index+1] = green
                self._pixels[index+2] = blue

            if self._light_type == GRBW:
                self._pixels[index] = green
                self._pixels[index+1] = red
                self._pixels[index+2] = blue

            if white is not None:
                self._pixels[index+3] = white

        else:
            index *= 3
            if self._light_type == RGB:
                self._pixels[index] = red
                self._pixels[index+1] = green
                self._pixels[index+2] = blue

            if self._light_type == GRB:
                self._pixels[index] = green
                self._pixels[index+1] = red
                self._pixels[index+2] = blue

    def show(self):
        """Display the buffer on the connected WS2812 strip."""

        self.setup()

        self._i2c_write_block(self.REG_WS2812, self._pixels[:32])
        self._i2c_write_block(self.REG_WS2812 + 32, self._pixels[32:64])
        self._i2c_write_block(self.REG_WS2812 + 64, self._pixels[64:])
        self._i2c_write_byte(self.REG_UPDATE, 1)

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

        self._enable_servo[index] = state
        self._set_config()

    def servo_pulse_min(self, index, value):
        """Set the minimum high pulse for a servo in microseconds.

        :param index: Servo index 0 or 1
        :param value: Value in microseconds

        """

        if index not in [0, 1]:
            raise ValueError("Servo index must be 0 or 1")

        self._servo_min[index] = value

    def servo_pulse_max(self, index, value):
        """Set the maximum high pulse for a servo in microseconds.

        :param index: Servo index 0 or 1
        :param value: Value in microseconds

        """

        if index not in [0, 1]:
            raise ValueError("Servo index must be 1 or 2")

        self._servo_max[index] = value

    def get_servo(self, index, units="raw"):
        """Get position of servo."""

        if index not in [0, 1]:
            raise ValueError("Servo index must be 0 or 1")

        self.setup()

        us_min, us_max = self._servo_range(index)
        us = self._i2c_read_word(self._servo_registry[index])

        try:
            if units == "percent":
                return self._servo_percent_to_us(us, us_min, us_max)
            elif units == "degrees":
                return self._servo_us_to_degrees(us, us_min, us_max)
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

        if not self._enable_servo[index]:
            self._enable_servo[index] = True
            self._set_config()

        us_min, us_max = self._servo_range(index)
        if units == "percent":
            us = self._servo_percent_to_us(value, us_min, us_max)
        elif units == "degrees":
            us = self._servo_degrees_to_us(value, us_min, us_max)
        else:
            us = value
        self._i2c_write_word(self._servo_registry[index], us)

        if self._idle_timeout > 0:
            if self._servo_timeouts[index] is not None:
                self._servo_timeouts[index].cancel()

            self._servo_timeouts[index] = Timer(self._idle_timeout, self._servo_stop[index])
            self._servo_timeouts[index].daemon = True
            self._servo_timeouts[index].start()

    def _servo1_stop(self):
        self._servo_timeouts[0] = None
        self._enable_servo[0] = False
        self._set_config()

    def _servo2_stop(self):
        self._servo_timeouts[1] = None
        self._enable_servo[1] = False
        self._set_config()
