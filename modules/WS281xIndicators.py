# NeoPixel library strandtest example
# Author: Tony DiCola (tony@tonydicola.com)
# Author: Jan Kubovy (jan@kubovy.eu)
#
# Direct port of the Arduino NeoPixel library strandtest example.  Showcases
# various animations on a strip of NeoPixels.
import ast
import json

from lib.ColorGRB import ColorGRB
from lib.ModuleLooper import *
import math
from neopixel import *


def to_color(data):
    if isinstance(data, dict):
        return ColorGRB(data['red'], data['green'], data['blue'])
    elif isinstance(data, int):
        return data
    else:
        return None


def dump_color(color):
    red = (color & (255 << 8)) >> 8
    green = (color & (255 << 16)) >> 16
    blue = (color & 255)
    return str(red) + "," + str(green) + "," + str(blue)


def to_configs(data):
    configs = []
    for item in data:
        if item is not None:
            config = Config()
            config.pattern = item['pattern'] if 'pattern' in item.keys() else 'light'
            config.color = to_color(item['color']) if 'color' in item.keys() else None
            config.wait = item['wait'] if 'wait' in item.keys() else 50
            config.min = item['min'] if 'min' in item.keys() else 0
            config.max = item['max'] if 'max' in item.keys() else 0
            configs.append(config)
    return configs


class Config(object):
    def __init__(self, pattern="light", color=0, wait=50, minimum=0, maximum=100):
        self.pattern = pattern
        self.color = color
        self.wait = wait
        self.min = minimum
        self.max = maximum

    def clone(self):
        return Config(pattern=self.pattern, color=self.color, wait=self.wait, minimum=self.min, maximum=self.max)


class WS281xIndicators(ModuleLooper):
    """WS2811/WS2812 indicator module"""

    # LED strip configuration:
    LED_PIN = 18  # GPIO pin connected to the pixels (18 uses PWM!).
    # LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA = 10  # DMA channel to use for generating signal (try 10)
    LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
    LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
    LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53
    LED_STRIP = ws.WS2811_STRIP_GRB  # Strip type and colour ordering

    LOOP_WAIT = 10  # ms

    module_serial_reader = None

    __iteration = 0

    def __init__(self, led_count=50, debug=False):
        super(WS281xIndicators, self).__init__(debug=debug)
        # Create NeoPixel object with appropriate configuration.
        self.__led_count = led_count
        self.__data = [[] for _ in range(self.__led_count)]
        self.__strip = Adafruit_NeoPixel(led_count, self.LED_PIN, self.LED_FREQ_HZ, self.LED_DMA, self.LED_INVERT,
                                         self.LED_BRIGHTNESS, self.LED_CHANNEL, self.LED_STRIP)
        # Intialize the library (must be called once before other functions).
        self.__strip.begin()
        self.reset()

    def set(self, index, payload):
        self.logger.debug("Setting " + str(index) + " to " + str(payload) + " " + str(type(payload)))
        if isinstance(payload, basestring):
            data = None
            try:
                data = json.loads("[" + payload + "]")
            except ValueError as e:
                self.logger.error(e.message)
            if data is None:
                try:
                    data = [ast.literal_eval(payload)]
                except ValueError as e:
                    self.logger.error(e.message)
        elif payload is not None:
            data = [payload]
        else:
            data = None

        if data is not None:
            self.__data[int(index)] = to_configs(data)

    def finalize(self):
        super(WS281xIndicators, self).finalize()
        self.reset()

    def reset(self):
        self.__data = [None for _ in range(self.__led_count)]
        for led in range(self.__led_count):
            self.__strip.setPixelColor(led, 0)
        self.__strip.show()

    def on_mqtt_message(self, path, payload):
        if len(path) == 1:
            try:
                self.set(int(path[0]), payload)
            except ValueError:
                self.logger.error('Oops!  That was no valid JSON.  Try again...')
                traceback.print_exc()
            except:
                self.logger.error('Oops!')
                traceback.print_exc()
        else:
            # super(WS281xIndicators, self).on_mqtt_message(path, payload)
            all_data = json.loads(payload)
            for led in all_data.keys():
                try:
                    self.logger.debug(str(led) + ": " + str(all_data[led]))
                    self.__data[int(led)] = to_configs([all_data[led]])
                except ValueError:
                    self.logger.error('Oops!  That was no valid JSON.  Try again...')
                    traceback.print_exc()
                except:
                    self.logger.error('Oops!')
                    traceback.print_exc()

    def on_serial_message(self, message):
        try:
            self.__data = to_configs(json.loads(message))
        except ValueError:
            self.logger.error('Oops!  That was no valid JSON.  Try again...')
            traceback.print_exc()

    def looper(self):
        for led, configs in enumerate(self.__data):
            if configs is None or len(configs) == 0:
                self.__strip.setPixelColor(led, 0)
            else:
                config = configs[0]  # TODO JK: also multiple configs should be possible
                if (self.__iteration * self.LOOP_WAIT) % config.wait == 0:
                    if config.pattern == 'fade':
                        step = (self.__iteration * self.LOOP_WAIT / config.wait) % (config.max - config.min)
                        percent = step + config.min if ((step + config.min) < config.max) else \
                            config.max - (step + config.min - config.max)
                        factor = float(percent) / 100.0
                        color = ColorGRB(int(float((config.color & (255 << 8)) >> 8) * factor),
                                         int(float((config.color & (255 << 16)) >> 16) * factor),
                                         int(float((config.color & 255)) * factor))
                        self.__strip.setPixelColor(led, color)
                    elif config.pattern == 'fadeToggle':
                        step = (self.__iteration * self.LOOP_WAIT / config.wait) % ((config.max - config.min) * 2)
                        percent = step + config.min if ((step + config.min) < config.max) else \
                            config.max - (step + config.min - config.max)
                        factor = float(percent) / 100.0
                        color = ColorGRB(int(float((config.color & (255 << 8)) >> 8) * factor),
                                         int(float((config.color & (255 << 16)) >> 16) * factor),
                                         int(float((config.color & 255)) * factor))
                        self.__strip.setPixelColor(led, color)

                    elif config.pattern == 'blink':
                        on = math.floor(self.__iteration * self.LOOP_WAIT / config.wait) % 2 == 0
                        self.__strip.setPixelColor(led, config.color if on else 0)
                    else:
                        self.__strip.setPixelColor(led, config.color)

        self.__strip.show()

        time.sleep(self.LOOP_WAIT / 1000.0)
        self.__iteration = self.__iteration + 1
        # if iteration >= 6000: iteration = 0
