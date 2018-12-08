# NeoPixel library strandtest example
# Author: Tony DiCola (tony@tonydicola.com)
# Author: Jan Kubovy (jan@kubovy.eu)
#
# Direct port of the Arduino NeoPixel library strandtest example.  Showcases
# various animations on a strip of NeoPixels.
import ast
import json
import math
from neopixel import *
from ModuleLooper import *


def Color(red, green, blue, white=0):
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.
    """
    return (white << 24) | (red << 8)| (green << 16) | blue


def to_color(data):
    return Color(data['red'], data['green'], data['blue'])


def dump_color(color):
    red = (color & (255 << 8)) >> 8
    green = (color & (255 << 16)) >> 16
    blue = (color & 255)
    return str(red) + "," + str(green) + "," + str(blue)


def to_configs(data):
    configs = []
    for item in data:
        config = Config()
        config.pattern = item['pattern'] if 'pattern' in item.keys() else 'light'
        config.color = to_color(item['color']) if 'color' in item.keys() else None
        config.wait = item['wait'] if 'wait' in item.keys() else 50
        config.min = item['min'] if 'min' in item.keys() else 0
        config.max = item['max'] if 'max' in item.keys() else 0
        configs.append(config)
    return configs


class Config(object):
    def __init__(self, pattern="light", color=0, wait=50, width=3, fading=0, minimum=0, maximum=100):

        self.pattern = pattern
        self.color = color
        self.wait = wait
        self.min = minimum
        self.max = maximum

    def clone(self):
        return Config(pattern=self.pattern, color=self.color, wait=self.wait, minimum=self.min, maximum=self.max)


class WS281xIndicators(ModuleLooper):
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

    interrupted = False
    thread = None

    serial_reader = None

    def __init__(self, client, service_name, led_count=50, debug=False):
        super(WS281xIndicators, self).__init__(client, service_name, "ws281x-indicators", debug)
        # Create NeoPixel object with appropriate configuration.
        self.led_count = led_count
        self.data = [None for _ in range(self.led_count)]
        self.strip = Adafruit_NeoPixel(self.led_count, self.LED_PIN, self.LED_FREQ_HZ, self.LED_DMA, self.LED_INVERT,
                                       self.LED_BRIGHTNESS, self.LED_CHANNEL, self.LED_STRIP)
        # Intialize the library (must be called once before other functions).
        self.strip.begin()
        for led in range(self.led_count):
            self.strip.setPixelColor(led, Color(0, 0, 0))
            self.strip.show()

    def set(self, index, payload):
        self.logger.debug("Setting " + str(index) + " to " + str(payload) + " " + str(type(payload)))
        if isinstance(payload, basestring):
            try:
                data = json.loads("[" + payload + "]")
            except ValueError:
                data = [ast.literal_eval(payload)]

        else:
            data = [payload]

        self.data[index] = to_configs(data)

    def on_start(self):
        if self.serial_reader is not None:
            self.serial_reader.register(self)

    def on_stop(self):
        if self.serial_reader is not None:
            self.serial_reader.unregister(self)

    def on_message(self, path, payload):
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
            # super(WS281xIndicators, self).on_message(path, payload)
            all_data = json.loads(payload)
            for led in all_data.keys():
                try:
                    self.logger.debug(str(led) + ": " + str(all_data[led]))
                    self.data[int(led)] = to_configs([all_data[led]])
                except ValueError:
                    self.logger.error('Oops!  That was no valid JSON.  Try again...')
                    traceback.print_exc()
                except:
                    self.logger.error('Oops!')
                    traceback.print_exc()

    def on_serial_message(self, message):
        try:
            self.data = to_configs(json.loads(message))
        except ValueError:
            self.logger.error('Oops!  That was no valid JSON.  Try again...')
            traceback.print_exc()

    def looper(self):
        self.logger.debug("Starting looper")
        iteration = 0

        # lastRestartChange = os.path.getmtime(REBOOT_PATH) if os.path.exists(REBOOT_PATH) else 0
        # (os.path.getmtime(REBOOT_PATH) if os.path.exists(REBOOT_PATH) else 0) == lastRestartChange:
        while not self.interrupted:
            # if len(self.data) == 0:
            #     self.light(Config(wait=10, minimum=50, maximum=80))
            #     continue

            # index = iteration  # start + (iteration % (len(self.data) - start))
            # if iteration >= 6000: iteration = 0

            for led, configs in enumerate(self.data):
                if configs is None or configs == []:
                    self.strip.setPixelColor(led, 0)
                else:
                    config = configs[0]  # TODO JK: also multiple configs should be possible
                    if (iteration * self.LOOP_WAIT) % config.wait == 0:
                        if config.pattern == 'fade':
                            step = (iteration * self.LOOP_WAIT / config.wait) % (config.max - config.min)
                            percent = step + config.min if ((step + config.min) < config.max) else \
                                config.max - (step + config.min - config.max)
                            factor = float(percent) / 100.0
                            color = Color(int(float((config.color & (255 << 8)) >> 8) * factor),
                                          int(float((config.color & (255 << 16)) >> 16) * factor),
                                          int(float((config.color & 255)) * factor))
                            self.strip.setPixelColor(led, color)
                        elif config.pattern == 'fadeToggle':
                            step = (iteration * self.LOOP_WAIT / config.wait) % ((config.max - config.min) * 2)
                            percent = step + config.min if ((step + config.min) < config.max) else \
                                config.max - (step + config.min - config.max)
                            factor = float(percent) / 100.0
                            color = Color(int(float((config.color & (255 << 8)) >> 8) * factor),
                                          int(float((config.color & (255 << 16)) >> 16) * factor),
                                          int(float((config.color & 255)) * factor))
                            self.strip.setPixelColor(led, color)

                        elif config.pattern == 'blink':
                            on = math.floor(iteration * self.LOOP_WAIT / config.wait) % 2 == 0
                            self.strip.setPixelColor(led, config.color if on else 0)
                        else:
                            self.strip.setPixelColor(led, config.color)

            self.strip.show()

            time.sleep(self.LOOP_WAIT / 1000.0)
            iteration = iteration + 1
            # if iteration >= 6000: iteration = 0
