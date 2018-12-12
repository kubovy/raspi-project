# NeoPixel library strandtest example
# Author: Tony DiCola (tony@tonydicola.com)
# Author: Jan Kubovy (jan@kubovy.eu)
#
# Direct port of the Arduino NeoPixel library strandtest example.  Showcases
# various animations on a strip of NeoPixels.
import json
from lib.Color import Color
from lib.ModuleLooper import *
from neopixel import *


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
        if 'pattern' in item.keys():
            config.pattern = item['pattern']
        config.color1 = to_color(item['color1']) if 'color1' in item.keys() else None
        config.color2 = to_color(item['color2']) if 'color2' in item.keys() else None
        config.color3 = to_color(item['color3']) if 'color3' in item.keys() else None
        config.color4 = to_color(item['color4']) if 'color4' in item.keys() else None
        config.color5 = to_color(item['color5']) if 'color5' in item.keys() else None
        config.color6 = to_color(item['color6']) if 'color6' in item.keys() else None
        config.color7 = to_color(item['color7']) if 'color7' in item.keys() else None
        config.color8 = to_color(item['color8']) if 'color8' in item.keys() else None
        config.color9 = to_color(item['color9']) if 'color9' in item.keys() else None
        config.color10 = to_color(item['color10']) if 'color10' in item.keys() else None
        config.color11 = to_color(item['color11']) if 'color11' in item.keys() else None
        config.color12 = to_color(item['color12']) if 'color12' in item.keys() else None
        if 'wait' in item.keys():
            config.wait = item['wait']
        if 'width' in item.keys():
            config.width = item['width']
        if 'fading' in item.keys():
            config.fading = item['fading']
        if 'min' in item.keys():
            config.min = item['min']
        if 'max' in item.keys():
            config.max = item['max']
        configs.append(config)
    return configs


class Config(object):
    def __init__(self, pattern="light", color1=0, color2=0, color3=0, color4=0, color5=0, color6=0, color7=0, color8=0,
                 color9=0, color10=0, color11=0, color12=0, wait=50, width=3, fading=0, minimum=0, maximum=100):

        self.pattern = pattern
        self.color1 = color1
        self.color2 = color2
        self.color3 = color3
        self.color4 = color4
        self.color5 = color5
        self.color6 = color6
        self.color7 = color7
        self.color8 = color8
        self.color9 = color9
        self.color10 = color10
        self.color11 = color11
        self.color12 = color12
        self.wait = wait
        self.width = width
        self.fading = fading
        self.min = minimum
        self.max = maximum

    def clone(self):
        return Config(pattern=self.pattern, color1=self.color1, color2=self.color2, color3=self.color3,
                      color4=self.color4, color5=self.color5, color6=self.color6, color7=self.color7,
                      color8=self.color8, color9=self.color9, color10=self.color10, color11=self.color11,
                      color12=self.color12, wait=self.wait, width=self.width, fading=self.fading, minimum=self.min,
                      maximum=self.max)


def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)


class WS281x(ModuleLooper):
    # LED strip configuration:
    LED_PIN = 18  # GPIO pin connected to the pixels (18 uses PWM!).
    # LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA = 10  # DMA channel to use for generating signal (try 10)
    LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
    LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
    LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53
    LED_STRIP = ws.WS2811_STRIP_GRB  # Strip type and colour ordering

    data = to_configs(json.loads(json.dumps([{
        'pattern': 'fade',
        'color1': {'red': 16, 'green': 16, 'blue': 16},
        'color2': {'red': 16, 'green': 16, 'blue': 16},
        'color3': {'red': 16, 'green': 16, 'blue': 16},
        'color4': {'red': 16, 'green': 16, 'blue': 16},
        'color5': {'red': 16, 'green': 16, 'blue': 16},
        'color6': {'red': 16, 'green': 16, 'blue': 16},
        'color7': {'red': 16, 'green': 16, 'blue': 16},
        'color8': {'red': 16, 'green': 16, 'blue': 16},
        'color9': {'red': 16, 'green': 16, 'blue': 16},
        'color10': {'red': 16, 'green': 16, 'blue': 16},
        'color11': {'red': 16, 'green': 16, 'blue': 16},
        'color12': {'red': 16, 'green': 16, 'blue': 16},
        'wait': 10, 'width': 3, 'fading': 0, 'min': 50, 'max': 80}])))

    interrupted = False
    thread = None

    serial_reader = None
    bluetooth_server = None

    def __init__(self, client, service_name, startup_file=None,
                 led_count=50, row_led_count=24, row_count=2, reverse=False, debug=False):
        super(WS281x, self).__init__(client, service_name, "ws281x", "WS281x", debug)
        # Create NeoPixel object with appropriate configuration.
        self.startup_file = startup_file
        self.led_count = led_count
        self.row_led_count = row_led_count
        self.row_count = row_count
        self.rest_count = int(self.led_count - (self.row_led_count * self.row_count))
        self.reverse = reverse
        self.strip = Adafruit_NeoPixel(self.led_count, self.LED_PIN, self.LED_FREQ_HZ, self.LED_DMA, self.LED_INVERT,
                                       self.LED_BRIGHTNESS, self.LED_CHANNEL, self.LED_STRIP)
        # Intialize the library (must be called once before other functions).
        self.strip.begin()

    def __set_pixel_color(self, num, color):
        num_safe = self.led_count - num - 1 if self.reverse else num
        # self.logger.debug("Pixel: " + str(num_safe) + " color: " + dump_color(color))
        self.strip.setPixelColor(num_safe, color)

    def __color_id__(self, config, position):
        color_count = 0
        while hasattr(config, 'color' + str(color_count + 1)) \
                and getattr(config, 'color' + str(color_count + 1), None) is not None:
            color_count = color_count + 1

        if position.startswith('top'):
            num = int(position.split("-")[1]) % self.rest_count
            color_num = color_count - self.rest_count + num
        else:
            num = int(position)
            color_num = num % (color_count - self.rest_count)

            # group = num - (num % 2)
            # group_color_num = group * 2
            # color_num = group_color_num + (num % 2)
            # if variation == "B": color_num = color_num + 2
        color_key = 'color' + str(color_num + 1)
        # self.logger.debug("ColorID: " + position + " -> " + color_key)
        return color_key

    def __color__(self, config, position, value=None):
        if value is not None:
            setattr(config, self.__color_id__(config, position), value)
        return getattr(config, self.__color_id__(config, position))

    # Define functions which animate LEDs in various ways.
    def color_wipe(self, color, wait_ms=50):
        """Wipe color across display a pixel at a time."""
        for i in range(self.led_count):
            self.__set_pixel_color(i, color)
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def theater(self, config):
        """Movie theater light style chaser animation."""
        for i in range(self.rest_count):
            self.__set_pixel_color(self.led_count - i - 1, self.__color__(config, "top-" + str(i)))

        for j in range(config.fading):  # iterations
            for q in range(3):
                for i in range(0, self.row_led_count, 3):
                    for row in range(self.row_count):
                        self.__set_pixel_color(i + q + (row * self.row_led_count), self.__color__(config, str(row)))
                    self.strip.show()
                time.sleep(config.wait / 1000.0)
                for i in range(0, self.row_led_count, 3):
                    for row in range(self.row_count):
                        self.__set_pixel_color(i + q + (row * self.row_led_count), 0)

    def rainbow(self, config):
        """Draw rainbow that fades across all pixels at once."""
        for i in range(self.rest_count):
            self.__set_pixel_color(self.led_count - i - 1, self.__color__(config, "top-" + str(i)))

        for j in range(256 * config.fading):  # iterations
            for i in range(self.row_count * self.row_led_count):
                self.__set_pixel_color(i, wheel((i + j) & 255))
            self.strip.show()
            time.sleep(config.wait / 1000.0)

    def rainbow_cycle(self, config):
        """Draw rainbow that uniformly distributes itself across all pixels."""
        for i in range(self.rest_count):
            self.__set_pixel_color(self.led_count - i - 1, self.__color__(config, "top-" + str(i)))

        for j in range(256 * config.fading):  # iterations
            for i in range(self.row_count * self.row_led_count):
                self.__set_pixel_color(i, wheel((int(i * 256 / self.led_count) + j) & 255))
            self.strip.show()
            time.sleep(config.wait / 1000.0)

    def theater_chase_rainbow(self, config):
        """Rainbow movie theater light style chaser animation."""
        for i in range(self.rest_count):
            self.__set_pixel_color(self.led_count - i - 1, self.__color__(config, "top-" + str(i)))

        for j in range(256):
            for q in range(3):
                for i in range(0, self.row_count * self.row_led_count, 3):
                    self.__set_pixel_color(i + q, wheel((i + j) % 255))
                self.strip.show()
                time.sleep(config.wait / 1000.0)
                for i in range(0, self.row_count * self.row_led_count, 3):
                    self.__set_pixel_color(i + q, 0)

    # Mine

    def wipe(self, config):
        """Wipe color across display a pixel at a time."""
        for i in range(self.rest_count):
            self.__set_pixel_color(self.led_count - i - 1, self.__color__(config, "top-" + str(i)))

        for i in range(self.row_led_count):
            for row in range(self.row_count):
                self.__set_pixel_color(i + (row * self.row_led_count), self.__color__(config, str(row)))
            self.strip.show()
            time.sleep(config.wait / 1000.0)
        if config.fading > 0:
            time.sleep(config.fading / 1000.0)
            copy = config.clone()
            for row in range(self.row_count):
                self.__color__(copy, str(row), 0)
            copy.fading = 0
            self.wipe(copy)

    def light(self, config):
        """Light"""
        for i in range(self.rest_count):
            self.__set_pixel_color(self.led_count - i - 1, self.__color__(config, "top-" + str(i)))
        for row in range(self.row_count):
            for i in range(self.row_led_count):
                self.__set_pixel_color(i + (row * self.row_led_count), self.__color__(config, str(row)))
        self.strip.show()
        time.sleep(config.wait / 1000.0)

    def rotation(self, config):
        """Rotation"""
        for i in range(self.rest_count):
            self.__set_pixel_color(self.led_count - i - 1, self.__color__(config, "top-" + str(i)))

        for i in range(self.row_led_count):
            for j in range(self.row_led_count * self.row_count):
                self.__set_pixel_color(j, 0)
            for row in range(self.row_count):
                # white = (color1 & (255 << 24)) >> 24
                red = (self.__color__(config, str(row)) & (255 << 8)) >> 8
                green = (self.__color__(config, str(row)) & (255 << 16)) >> 16
                blue = (self.__color__(config, str(row)) & 255)

                for w in range(config.width):
                    percent = max(100.0 - float(config.width - w - 1) * float(config.fading), 0.0)
                    factor = percent / 100.0
                    color = Color(int(float(red) * factor), int(float(green) * factor), int(float(blue) * factor))
                    j = i + w if (i + w < self.row_led_count) else (i + w) - self.row_led_count
                    self.__set_pixel_color(j + (row * self.row_led_count), color)

            self.strip.show()
            time.sleep(config.wait / 1000.0)

    def spin(self, config):
        """Spin"""
        use = config.clone()
        for i in range(self.rest_count):
            self.__set_pixel_color(self.led_count - i - 1, self.__color__(use, "top-" + str(i)))
        for w in range(5):
            use.width = self.row_led_count
            use.fading = 100 / self.row_led_count
            use.wait = 50 - (w * 10)
            self.rotation(use)
        for w in range(3):
            use.width = self.row_led_count / 2
            use.fading = 100 / (self.row_led_count / 2)
            use.wait = 30 - (w * 10)
            self.lighthouse(use)
            self.lighthouse(use)
            use.wait = 50
        self.light(use)
        time.sleep(10)

    def chaise(self, config):
        """Chaice"""
        for i in range(self.rest_count):
            self.__set_pixel_color(self.led_count - i - 1, self.__color__(config, "top-" + str(i)))

        for i in range(self.row_led_count):
            for j in range(self.row_led_count * self.row_count):
                self.__set_pixel_color(j, 0)
            for w in range(config.width):
                for row in range(self.row_count):
                    # white = (color1 & (255 << 24)) >> 24
                    red = (self.__color__(config, str(row)) & (255 << 8)) >> 8
                    green = (self.__color__(config, str(row)) & (255 << 16)) >> 16
                    blue = (self.__color__(config, str(row)) & 255)

                    percent = max(100.0 - float(config.width - w - 1) * float(config.fading), 0.0)
                    factor = percent / 100.0

                    color = Color(int(float(red) * factor), int(float(green) * factor), int(float(blue) * factor))
                    if row < self.row_count / 2:
                        j = i + w if (i + w < self.row_led_count) else (i + w) - self.row_led_count
                    else:
                        j = self.row_led_count - (i + w) - 1 if (self.row_led_count > i + w) \
                            else (self.row_led_count - (i + w) - 1) + self.row_led_count
                    self.__set_pixel_color(j + (row * self.row_led_count), color)

            self.strip.show()
            time.sleep(config.wait / 1000.0)

    def lighthouse(self, config):
        """Lighthouse"""
        for i in range(self.rest_count):
            self.__set_pixel_color(self.led_count - i - 1, self.__color__(config, "top-" + str(i)))

        for i in range(self.row_led_count):
            for j in range(self.row_led_count * self.row_count):
                self.__set_pixel_color(j, 0)
            for row in range(self.row_count):
                # white1 = (self.__color__(config, str(row * 2)) & (255 << 24)) >> 24
                red1 = (self.__color__(config, str(row)) & (255 << 8)) >> 8
                green1 = (self.__color__(config, str(row)) & (255 << 16)) >> 16
                blue1 = (self.__color__(config, str(row)) & 255)
                # white2 = (color2 & (255 << 24)) >> 24
                red2 = (self.__color__(config, str(row + self.row_count)) & (255 << 8)) >> 8
                green2 = (self.__color__(config, str(row + self.row_count)) & (255 << 16)) >> 16
                blue2 = (self.__color__(config, str(row + self.row_count)) & 255)

                for w in range(config.width):
                    percent = max(100.0 - float(config.width - w - 1) * float(config.fading), 0.0)
                    factor = percent / 100.0
                    color1 = Color(int(float(red1) * factor), int(float(green1) * factor), int(float(blue1) * factor))
                    color2 = Color(int(float(red2) * factor), int(float(green2) * factor), int(float(blue2) * factor))

                    half = self.row_led_count / 2
                    j = i + w if (i + w < self.row_led_count) else (i + w) - self.row_led_count
                    q = j + half if (j + half < self.row_led_count) else (j + half) - self.row_led_count

                    self.__set_pixel_color(j + (row * self.row_led_count), color1)
                    self.__set_pixel_color(q + (row * self.row_led_count), color2)

            self.strip.show()
            time.sleep(config.wait / 1000.0)

    def fade(self, config):
        """Fade"""
        for i in range(self.rest_count):
            self.__set_pixel_color(self.led_count - i - 1, self.__color__(config, "top-" + str(i)))

        for step in range((config.max - config.min) * 2):
            percent = step + config.min if ((step + config.min) < config.max) else \
                config.max - (step + config.min - config.max)
            factor = float(percent) / 100.0

            for row in range(self.row_count):
                # white1 = (self.__color__(config, str(row)) & (255 << 24)) >> 24
                red = (self.__color__(config, str(row)) & (255 << 8)) >> 8
                green = (self.__color__(config, str(row)) & (255 << 16)) >> 16
                blue = (self.__color__(config, str(row)) & 255)
                color = Color(int(float(red) * factor), int(float(green) * factor), int(float(blue) * factor))
                for i in range(self.row_led_count):
                    self.__set_pixel_color(i + (row * self.row_led_count), color)

            self.strip.show()
            time.sleep(config.wait / 1000.0)

    def fade_toggle(self, config):
        """Fade Toggle"""
        for i in range(self.rest_count):
            self.__set_pixel_color(self.led_count - i - 1, self.__color__(config, "top-" + str(i)))

        for step in range((config.max - config.min) * 2):
            percent = step + config.min if ((step + config.min) < config.max) else \
                config.max - (step + config.min - config.max)

            for row in range(self.row_count):
                if row < self.row_count / 2:
                    factor = float(percent) / 100.0
                else:
                    factor = float(config.max - percent + config.min) / 100.0
                # white1 = (self.__color__(config, str(row)) & (255 << 24)) >> 24
                red = (self.__color__(config, str(row)) & (255 << 8)) >> 8
                green = (self.__color__(config, str(row)) & (255 << 16)) >> 16
                blue = (self.__color__(config, str(row)) & 255)
                color = Color(int(float(red) * factor), int(float(green) * factor), int(float(blue) * factor))
                for i in range(self.row_led_count):
                    self.__set_pixel_color(i + (row * self.row_led_count), color)

            self.strip.show()
            time.sleep(config.wait / 1000.0)

    def blink(self, config):
        """Blink"""
        for i in range(self.rest_count):
            self.__set_pixel_color(self.led_count - i - 1, self.__color__(config, "top-" + str(i)))

        for row in range(self.row_count):
            for i in range(self.row_led_count):
                self.__set_pixel_color(i + (row * self.row_led_count), self.__color__(config, str(row)))
        self.strip.show()
        time.sleep(config.wait / 1000.0)

        for row in range(self.row_count):
            for i in range(self.row_led_count):
                self.__set_pixel_color(i + (row * self.row_led_count), 0)
        self.strip.show()
        time.sleep(config.wait / 1000.0)

    def on_start(self):
        super(WS281x, self).on_start()
        if self.bluetooth_server is not None:
            self.bluetooth_server.register(self)
        if self.serial_reader is not None:
            self.serial_reader.register(self)

    def on_stop(self):
        super(WS281x, self).on_stop()
        if self.bluetooth_server is not None:
            self.bluetooth_server.unregister(self)
        if self.serial_reader is not None:
            self.serial_reader.unregister(self)

    def finalize(self):
        super(WS281x, self).finalize()
        for led in range(self.led_count):
            self.strip.setPixelColor(led, 0)
        self.strip.show()

    def on_mqtt_message(self, path, payload):
        if len(path) == 0:
            if payload == "ON":
                self.data = to_configs(json.loads(json.dumps([{
                    'pattern': 'light',
                    'color1': {'red': 255, 'green': 255, 'blue': 255},
                    'color2': {'red': 255, 'green': 255, 'blue': 255},
                    'color3': {'red': 255, 'green': 255, 'blue': 255},
                    'color4': {'red': 255, 'green': 255, 'blue': 255},
                    'color5': {'red': 255, 'green': 255, 'blue': 255},
                    'color6': {'red': 255, 'green': 255, 'blue': 255},
                    'color7': {'red': 255, 'green': 255, 'blue': 255},
                    'color8': {'red': 255, 'green': 255, 'blue': 255},
                    'color9': {'red': 255, 'green': 255, 'blue': 255},
                    'color10': {'red': 255, 'green': 255, 'blue': 255},
                    'color11': {'red': 255, 'green': 255, 'blue': 255},
                    'color12': {'red': 255, 'green': 255, 'blue': 255},
                    'wait': 50, 'width': 3, 'fading': 0, 'min': 0, 'max': 100}])))
            elif payload == "OFF":
                self.data = to_configs(json.loads(json.dumps([{
                    'pattern': 'light',
                    'color1': {'red': 0, 'green': 0, 'blue': 0},
                    'color2': {'red': 0, 'green': 0, 'blue': 0},
                    'color3': {'red': 0, 'green': 0, 'blue': 0},
                    'color4': {'red': 0, 'green': 0, 'blue': 0},
                    'color5': {'red': 0, 'green': 0, 'blue': 0},
                    'color6': {'red': 0, 'green': 0, 'blue': 0},
                    'color7': {'red': 0, 'green': 0, 'blue': 0},
                    'color8': {'red': 0, 'green': 0, 'blue': 0},
                    'color9': {'red': 0, 'green': 0, 'blue': 0},
                    'color10': {'red': 0, 'green': 0, 'blue': 0},
                    'color11': {'red': 0, 'green': 0, 'blue': 0},
                    'color12': {'red': 0, 'green': 0, 'blue': 0},
                    'wait': 50, 'width': 3, 'fading': 0, 'min': 0, 'max': 100}])))
            elif len(payload.split(",")) == 3:
                rgb = payload.split(",")
                try:
                    red = int(rgb[0])
                    green = int(rgb[1])
                    blue = int(rgb[2])
                    self.data = to_configs(json.loads(json.dumps([{
                        'pattern': 'light',
                        'color1': {'red': red, 'green': green, 'blue': blue},
                        'color2': {'red': red, 'green': green, 'blue': blue},
                        'color3': {'red': red, 'green': green, 'blue': blue},
                        'color4': {'red': red, 'green': green, 'blue': blue},
                        'color5': {'red': red, 'green': green, 'blue': blue},
                        'color6': {'red': red, 'green': green, 'blue': blue},
                        'color7': {'red': red, 'green': green, 'blue': blue},
                        'color8': {'red': red, 'green': green, 'blue': blue},
                        'color9': {'red': red, 'green': green, 'blue': blue},
                        'color10': {'red': red, 'green': green, 'blue': blue},
                        'color11': {'red': red, 'green': green, 'blue': blue},
                        'color12': {'red': red, 'green': green, 'blue': blue},
                        'wait': 50, 'width': 3, 'fading': 0, 'min': 0, 'max': 100}])))
                except:
                    self.logger.error('Oops!  That was no valid RGB color.  Try again...')
                    traceback.print_exc()
            else:
                try:
                    value = int(255.0 * float(payload) / 100)
                    self.data = to_configs(json.loads(json.dumps([{
                        'pattern': 'light',
                        'color1': {'red': value, 'green': value, 'blue': value},
                        'color2': {'red': value, 'green': value, 'blue': value},
                        'color3': {'red': value, 'green': value, 'blue': value},
                        'color4': {'red': value, 'green': value, 'blue': value},
                        'color5': {'red': value, 'green': value, 'blue': value},
                        'color6': {'red': value, 'green': value, 'blue': value},
                        'color7': {'red': value, 'green': value, 'blue': value},
                        'color8': {'red': value, 'green': value, 'blue': value},
                        'color9': {'red': value, 'green': value, 'blue': value},
                        'color10': {'red': value, 'green': value, 'blue': value},
                        'color11': {'red': value, 'green': value, 'blue': value},
                        'color12': {'red': value, 'green': value, 'blue': value},
                        'wait': 50, 'width': 3, 'fading': 0, 'min': 0, 'max': 100}])))
                except:
                    self.logger.error('Oops!  That was no valid number.  Try again...')
                    traceback.print_exc()
        elif len(path) == 1 and path[0] == "set":
            try:
                self.data = to_configs(json.loads(payload))
            except ValueError:
                self.logger.error('Oops!  That was no valid JSON.  Try again...')
                traceback.print_exc()
        elif len(path) == 1 and path[0] == "add":
            try:
                extension = to_configs(json.loads(payload))
                self.data.extend(extension)
            except ValueError:
                self.logger.error('Oops!  That was no valid JSON.  Try again...')
                traceback.print_exc()
        else:
            super(WS281x, self).on_mqtt_message(path, payload)

    def on_bluetooth_message(self, message):
        self.logger.debug("Message: " + message)
        if message == "BT:CONNECTED":
            pass
        elif message == "BT:DISCONNECTED":
            pass
        elif message.startswith("BT:IDD:"):
            pass
        elif message.startswith("WS:"):
            self.data = to_configs(json.loads(message[3:]))

    def on_serial_message(self, message):
        try:
            self.data = to_configs(json.loads(message))
        except ValueError:
            self.logger.error('Oops!  That was no valid JSON.  Try again...')
            traceback.print_exc()

    def looper(self):
        iteration = 0

        if self.startup_file is not None:
            try:
                self.data = to_configs(json.load(open(self.startup_file)))
                self.logger.info('Startup: ' + str(len(self.data)) + ' items')
            except ValueError:
                self.logger.error('Oops!  That was no valid JSON.  Try again...')
                traceback.print_exc()

        # lastRestartChange = os.path.getmtime(REBOOT_PATH) if os.path.exists(REBOOT_PATH) else 0
        # (os.path.getmtime(REBOOT_PATH) if os.path.exists(REBOOT_PATH) else 0) == lastRestartChange:
        while not self.interrupted:
            if len(self.data) == 0:
                self.light(Config(wait=10, minimum=50, maximum=80))
                continue

            # index = iteration  # start + (iteration % (len(self.data) - start))
            if iteration > len(self.data):
                iteration = 0
            config = self.data[iteration]

            if config.pattern == 'clear':
                del self.data[:iteration + 1]
                iteration = 0

            # start = index + 1
            # self.logger.info('Cleared index=' + str(index) + ', length=' + str(len(self.data)))
            # + ', start=' + str(start))
            # index = 0  # start + (iteration % (len(self.data) - start))
            config = self.data[iteration]

            # self.logger.debug(
            #    'Iteration: ' + str(iteration) + ': ' + config.pattern
            #    + ' c1=' + str(config.color1) + ', c2=' + str(config.color2) + ', c3=' + str(config.color3) + ','
            #    + ' c4=' + str(config.color4) + ', c5=' + str(config.color5) + ', c6=' + str(config.color6) + ','
            #    + ' c7=' + str(config.color7) + ', c8=' + str(config.color8) + ', c9=' + str(config.color3) + ','
            #    + ' c10=' + str(config.color10) + ', c11=' + str(config.color11) + ', c12=' + str(config.color12) + ','
            #    + ' wait=' + str(config.wait) + 'ms, width=' + str(config.width) + ','
            #    + ' fading=' + str(config.fading) + ', min=' + str(config.min) + ', max=' + str(config.max))
            if config.pattern == 'wipe':
                self.wipe(config)
            elif config.pattern == 'light':
                self.light(config)
            elif config.pattern == 'rotation':
                self.rotation(config)
            elif config.pattern == 'spin':
                self.spin(config)
            elif config.pattern == 'chaise':
                self.chaise(config)
            elif config.pattern == 'lighthouse':
                self.lighthouse(config)
            elif config.pattern == 'fade':
                self.fade(config)
            elif config.pattern == 'fadeToggle':
                self.fade_toggle(config)
            elif config.pattern == 'blink':
                self.blink(config)
            elif config.pattern == 'theater':
                self.theater(config)
            elif config.pattern == 'theaterChaiseRainbow':
                self.theater_chase_rainbow(config)
            elif config.pattern == 'rainbow':
                self.rainbow(config)
            elif config.pattern == 'rainbowCycle':
                self.rainbow_cycle(config)
            elif config.pattern == 'wait':
                time.sleep(config.wait / 1000.0)
            else:
                self.fade(Config(color1=Color(16, 16, 16),
                                 color2=Color(16, 16, 16),
                                 color3=Color(16, 16, 16),
                                 color4=Color(16, 16, 16),
                                 color5=Color(16, 16, 16),
                                 color6=Color(16, 16, 16),
                                 color7=Color(16, 16, 16),
                                 color8=Color(16, 16, 16),
                                 wait=10,
                                 minimum=50,
                                 maximum=80))

            iteration = iteration + 1
            if iteration >= len(self.data):
                iteration = 0
