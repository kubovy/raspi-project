# NeoPixel library strandtest example
# Author: Tony DiCola (tony@tonydicola.com)
# Author: Jan Kubovy (jan@kubovy.eu)
#
# Direct port of the Arduino NeoPixel library strandtest example.  Showcases
# various animations on a strip of NeoPixels.
import json
import os

from collections import namedtuple
from neopixel import *
from ModuleLooper import *


def Color(red, green, blue, white = 0):
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.
    """
    return (white << 24) | (red << 8)| (green << 16) | blue


def Color2(color):
        """Color2"""
        return Color(color.red, color.green, color.blue)


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

    data = json.loads(json.dumps([{'pattern': 'fade',
                                   'color1': {'red': 16, 'green': 16, 'blue': 16},
                                   'color2': {'red': 16, 'green': 16, 'blue': 16},
                                   'color3': {'red': 16, 'green': 16, 'blue': 16},
                                   'color4': {'red': 16, 'green': 16, 'blue': 16},
                                   'color5': {'red': 16, 'green': 16, 'blue': 16},
                                   'color6': {'red': 16, 'green': 16, 'blue': 16},
                                   'wait': 10,
                                   'width': 3,
                                   'fading': 0,
                                   'min': 50,
                                   'max': 80}]),
                      object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))

    interrupted = False
    thread = None

    serial_reader = None

    def __init__(self, client, service_name, startup_file=None,
                 led_count=50, row_led_count=12, row_count=2, debug=False):
        super(WS281x, self).__init__(client, service_name, "ws281x", debug)
        # Create NeoPixel object with appropriate configuration.
        self.startup_file = startup_file
        self.led_count = led_count
        self.row_led_count = row_led_count
        self.row_count = row_count
        self.rest_count = int(self.led_count - (self.row_led_count * self.row_count))
        self.strip = Adafruit_NeoPixel(self.led_count, self.LED_PIN, self.LED_FREQ_HZ, self.LED_DMA, self.LED_INVERT,
                                       self.LED_BRIGHTNESS, self.LED_CHANNEL, self.LED_STRIP)
        # Intialize the library (must be called once before other functions).
        self.strip.begin()

    # Define functions which animate LEDs in various ways.
    def color_wipe(self, color, wait_ms=50):
        """Wipe color across display a pixel at a time."""
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, color)
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def theater(self, color1, color2, color5, color6, wait_ms=50, iterations=10):
        """Movie theater light style chaser animation."""
        half = (self.strip.numPixels() - 2) / 2
        self.strip.setPixelColor(self.strip.numPixels() - 1, color5)
        self.strip.setPixelColor(self.strip.numPixels() - 2, color6)
        for j in range(iterations):
            for q in range(3):
                for i in range(0, half, 3):
                    self.strip.setPixelColor(i + q, color1)
                    self.strip.setPixelColor(i + q + half, color2)
                    self.strip.show()
                time.sleep(wait_ms / 1000.0)
                for i in range(0, half, 3):
                    self.strip.setPixelColor(i + q, 0)
                    self.strip.setPixelColor(i + q + half, 0)

    def rainbow(self, wait_ms=20, iterations=1):
        """Draw rainbow that fades across all pixels at once."""
        for j in range(256 * iterations):
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, wheel((i + j) & 255))
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def rainbow_cycle(self, wait_ms=20, iterations=5):
        """Draw rainbow that uniformly distributes itself across all pixels."""
        for j in range(256 * iterations):
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, wheel((int(i * 256 / self.strip.numPixels()) + j) & 255))
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def theater_chase_rainbow(self, wait_ms=50):
        """Rainbow movie theater light style chaser animation."""
        for j in range(256):
            for q in range(3):
                for i in range(0, self.strip.numPixels(), 3):
                    self.strip.setPixelColor(i + q, wheel((i + j) % 255))
                self.strip.show()
                time.sleep(wait_ms / 1000.0)
                for i in range(0, self.strip.numPixels(), 3):
                    self.strip.setPixelColor(i + q, 0)

    # Mine

    def wipe(self, color1, color2, color5, color6, wait_ms=50, sleep=0):
        """Wipe color across display a pixel at a time."""
        half = (self.strip.numPixels() - 2) / 2
        self.strip.setPixelColor(self.strip.numPixels() - 1, color5)
        self.strip.setPixelColor(self.strip.numPixels() - 2, color6)
        for i in range(half):
            self.strip.setPixelColor(i, color1)
            self.strip.setPixelColor(i + half, color2)
            self.strip.show()
            time.sleep(wait_ms / 1000.0)
        if sleep > 0:
            time.sleep(sleep / 1000.0)
            self.wipe(Color(0, 0, 0), Color(0, 0, 0, ), color5, color6, wait_ms, 0)

    def light(self, color1, color2, color5, color6, wait_ms=50):
        half = (self.strip.numPixels() - 2) / 2
        self.strip.setPixelColor(self.strip.numPixels() - 1, color5)
        self.strip.setPixelColor(self.strip.numPixels() - 2, color6)
        for i in range(half):
            self.strip.setPixelColor(i, color1)
            self.strip.setPixelColor(i + half, color2)
        self.strip.show()
        time.sleep(wait_ms / 1000.0)

    def rotation(self, color1, color2, color5, color6, width=3, fade=0, wait_ms=50):
        """Rotation"""
        half = (self.strip.numPixels() - 2) / 2
        self.strip.setPixelColor(self.strip.numPixels() - 1, color5)
        self.strip.setPixelColor(self.strip.numPixels() - 2, color6)
        for i in range(half):
            for j in range(half):
                self.strip.setPixelColor(j, Color(0, 0, 0))
                self.strip.setPixelColor(j + half, Color(0, 0, 0))
            for k in range(width):
                # white1 = (color1 & (255 << 24)) >> 24
                red1 = (color1 & (255 << 8)) >> 8
                green1 = (color1 & (255 << 16)) >> 16
                blue1 = (color1 & 255)
                # white2 = (color2 & (255 << 24)) >> 24
                red2 = (color2 & (255 << 8)) >> 8
                green2 = (color2 & (255 << 16)) >> 16
                blue2 = (color2 & 255)

                percent = 100.0 - float(width - k - 1) * float(fade)
                factor = percent / 100.0

                r1 = int(float(red1) * factor)
                g1 = int(float(green1) * factor)
                b1 = int(float(blue1) * factor)
                r2 = int(float(red2) * factor)
                g2 = int(float(green2) * factor)
                b2 = int(float(blue2) * factor)
                # self.logger.debug(str(percent) + ' -> ' + str(factor) + ': ' + str(r) + ', ' + str(g) + ', ' + str(b))

                c1 = Color(r1, g1, b1)
                c2 = Color(r2, g2, b2)

                p = i + k if (i + k < half) else (i + k) - half
                self.strip.setPixelColor(p, c1)
                self.strip.setPixelColor(p + half, c2)
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def spin(self, color1, color2, color5, color6):
        """Spin"""
        self.strip.setPixelColor(self.strip.numPixels() - 1, color5)
        self.strip.setPixelColor(self.strip.numPixels() - 2, color6)
        for w in range(5):
            self.rotation(color1, color2, 24, 4, 50 - (w * 10))
            self.rotation(color1, color2, 24, 4, 50 - (w * 10))
        for w in range(3):
            self.lighthouse(color1, color2, color1, color2, Color(0, 0, 0), Color(0, 0, 0), 12, 4, 30 - (w * 10))
            self.lighthouse(color1, color2, color1, color2, Color(0, 0, 0), Color(0, 0, 0), 12, 4, 30 - (w * 10))
        self.light(color1, color2, Color(0, 0, 0), Color(0, 0, 0))
        time.sleep(10)

    def chaise(self, color1, color2, color5, color6, width=3, fade=0, wait_ms=50):
        """Rotation"""
        half = (self.strip.numPixels() - 2) / 2
        for i in range(half):
            for j in range(half):
                self.strip.setPixelColor(j, Color(0, 0, 0))
                self.strip.setPixelColor(j + half, Color(0, 0, 0))
            for k in range(width):
                # white1 = (color1 & (255 << 24)) >> 24
                red1 = (color1 & (255 << 8)) >> 8
                green1 = (color1 & (255 << 16)) >> 16
                blue1 = (color1 & 255)
                # white2 = (color2 & (255 << 24)) >> 24
                red2 = (color2 & (255 << 8)) >> 8
                green2 = (color2 & (255 << 16)) >> 16
                blue2 = (color2 & 255)

                percent = 100.0 - float(width - k - 1) * float(fade)
                factor = percent / 100.0

                r1 = int(float(red1) * factor)
                g1 = int(float(green1) * factor)
                b1 = int(float(blue1) * factor)
                r2 = int(float(red2) * factor)
                g2 = int(float(green2) * factor)
                b2 = int(float(blue2) * factor)
                # self.logger.debug(str(percent) + ' -> ' + str(factor) + ': ' + str(r) + ', ' + str(g) + ', ' + str(b))

                c1 = Color(r1, g1, b1)
                c2 = Color(r2, g2, b2)

                p = i + k if (i + k < half) else (i + k) - half
                q = half - (i + k) if (half - (i + k) >= 0) else (half - (i + k)) + half
                self.strip.setPixelColor(p, c1)
                self.strip.setPixelColor(q + half, c2)
            self.strip.setPixelColor(self.strip.numPixels() - 1, color5)
            self.strip.setPixelColor(self.strip.numPixels() - 2, color6)
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def lighthouse(self, color1, color2, color3, color4, color5, color6, width=3, fade=0, wait_ms=50):
        """Lighthouse"""
        half = (self.strip.numPixels() - 2) / 2
        quarter = half / 2
        self.strip.setPixelColor(self.strip.numPixels() - 1, color5)
        self.strip.setPixelColor(self.strip.numPixels() - 2, color6)
        for i in range(half):
            for j in range(half):
                self.strip.setPixelColor(j, Color(0, 0, 0))
                self.strip.setPixelColor(j + half, Color(0, 0, 0))
            for k in range(width):
                # white1 = (color1 & (255 << 24)) >> 24
                red1 = (color1 & (255 << 8)) >> 8
                green1 = (color1 & (255 << 16)) >> 16
                blue1 = (color1 & 255)
                # white2 = (color2 & (255 << 24)) >> 24
                red2 = (color2 & (255 << 8)) >> 8
                green2 = (color2 & (255 << 16)) >> 16
                blue2 = (color2 & 255)
                # white3 = (color3 & (255 << 24)) >> 24
                red3 = (color3 & (255 << 8)) >> 8
                green3 = (color3 & (255 << 16)) >> 16
                blue3 = (color3 & 255)
                # white4 = (color4 & (255 << 24)) >> 24
                red4 = (color4 & (255 << 8)) >> 8
                green4 = (color4 & (255 << 16)) >> 16
                blue4 = (color4 & 255)

                percent = 100.0 - float(width - k - 1) * float(fade)
                factor = percent / 100.0

                r1 = int(float(red1) * factor)
                g1 = int(float(green1) * factor)
                b1 = int(float(blue1) * factor)
                r2 = int(float(red2) * factor)
                g2 = int(float(green2) * factor)
                b2 = int(float(blue2) * factor)
                r3 = int(float(red3) * factor)
                g3 = int(float(green3) * factor)
                b3 = int(float(blue3) * factor)
                r4 = int(float(red4) * factor)
                g4 = int(float(green4) * factor)
                b4 = int(float(blue4) * factor)
                # self.logger.debug(str(percent) + ' -> ' + str(factor) + ': ' + str(r) + ', ' + str(g) + ', ' + str(b))

                c1 = Color(r1, g1, b1)
                c2 = Color(r2, g2, b2)
                c3 = Color(r3, g3, b3)
                c4 = Color(r4, g4, b4)

                p = i + k if (i + k < half) else (i + k) - half
                q = p + quarter if (p + quarter < half) else (p + quarter) - half
                self.strip.setPixelColor(p, c1)
                self.strip.setPixelColor(p + half, c3)
                self.strip.setPixelColor(q, c2)
                self.strip.setPixelColor(q + half, c4)
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def fade(self, color1, color2, color5, color6, wait_ms=50, minimum=0, maximum=100):
        """Fade"""
        half = (self.strip.numPixels() - 2) / 2

        # white1 = (color1 & (255 << 24)) >> 24
        red1 = (color1 & (255 << 8)) >> 8
        green1 = (color1 & (255 << 16)) >> 16
        blue1 = (color1 & 255)
        # white2 = (color2 & (255 << 24)) >> 24
        red2 = (color2 & (255 << 8)) >> 8
        green2 = (color2 & (255 << 16)) >> 16
        blue2 = (color2 & 255)
        # self.logger.debug('Input: ' + str(red) + ', ' + str(green) + ', ' + str(blue))
        self.strip.setPixelColor(self.strip.numPixels() - 1, color5)
        self.strip.setPixelColor(self.strip.numPixels() - 2, color6)
        for pr in range((maximum - minimum + 1) * 2):
            percent = pr + minimum if ((pr + minimum) <= maximum) else maximum - (pr + minimum - maximum)
            factor = float(percent) / 100.0
            # self.logger.debug(str(pr) + ', ' + str(percent) + ', ' + str(factor))
            r1 = int(float(red1) * factor)
            g1 = int(float(green1) * factor)
            b1 = int(float(blue1) * factor)
            r2 = int(float(red2) * factor)
            g2 = int(float(green2) * factor)
            b2 = int(float(blue2) * factor)
            c1 = Color(r1, g1, b1)
            c2 = Color(r2, g2, b2)
            # self.logger.debug('Color: ' + str(r) + ', ' + str(g) + ', ' + str(b))
            for i in range(half):
                self.strip.setPixelColor(i, c1)
                self.strip.setPixelColor(i + half, c2)
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def fade_toggle(self, color1, color2, color5, color6, wait_ms=50, minimum=0, maximum=100):
        """Fade Toggle"""
        half = (self.strip.numPixels() - 2) / 2
        # white1 = (color1 & (255 << 24)) >> 24
        red1 = (color1 & (255 << 8)) >> 8
        green1 = (color1 & (255 << 16)) >> 16
        blue1 = (color1 & 255)
        # white2 = (color2 & (255 << 24)) >> 24
        red2 = (color2 & (255 << 8)) >> 8
        green2 = (color2 & (255 << 16)) >> 16
        blue2 = (color2 & 255)
        # self.logger.debug('Input: ' + str(red) + ', ' + str(green) + ', ' + str(blue))
        self.strip.setPixelColor(self.strip.numPixels() - 1, color5)
        self.strip.setPixelColor(self.strip.numPixels() - 2, color6)
        for pr in range((maximum - minimum + 1) * 2):
            percent = pr + minimum if ((pr + minimum) <= maximum) else maximum - (pr + minimum - maximum)
            factor1 = float(percent) / 100.0
            factor2 = float(maximum - percent + minimum) / 100.0
            r1 = int(float(red1) * factor1)
            g1 = int(float(green1) * factor1)
            b1 = int(float(blue1) * factor1)
            c1 = Color(r1, g1, b1)
            r2 = int(float(red2) * factor2)
            g2 = int(float(green2) * factor2)
            b2 = int(float(blue2) * factor2)
            c2 = Color(r2, g2, b2)
            for i in range(half):
                self.strip.setPixelColor(i, c1)
                self.strip.setPixelColor(i + half, c2)
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def blink(self, color1, color2, color5, color6, wait_ms=50):
        """Blink"""
        half = (self.strip.numPixels() - 2) / 2
        self.strip.setPixelColor(self.strip.numPixels() - 1, color5)
        self.strip.setPixelColor(self.strip.numPixels() - 2, color6)
        for i in range(half):
            self.strip.setPixelColor(i, color1)
            self.strip.setPixelColor(i + half, color2)
        self.strip.show()
        time.sleep(wait_ms / 1000.0)
        for i in range(half):
            self.strip.setPixelColor(i, Color(0, 0, 0))
            self.strip.setPixelColor(i + half, Color(0, 0, 0))
        self.strip.show()
        time.sleep(wait_ms / 1000.0)

    def on_start(self):
        if self.serial_reader is not None:
            self.serial_reader.register(self)

    def on_stop(self):
        if self.serial_reader is not None:
            self.serial_reader.unregister(self)

    def on_serial_message(self, message):
        try:
            self.data = json.loads(message, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
        except ValueError:
            self.logger.error('Oops!  That was no valid JSON.  Try again...')
            traceback.print_exc()

    def looper(self):
        iteration = 0

        try:
            self.data = json.load(open(self.startup_file),
                                  object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
            self.logger.info('Startup: ' + str(len(self.data)) + ' items')
        except ValueError:
            self.logger.error('Oops!  That was no valid JSON.  Try again...')
            traceback.print_exc()

        # lastRestartChange = os.path.getmtime(REBOOT_PATH) if os.path.exists(REBOOT_PATH) else 0
        # (os.path.getmtime(REBOOT_PATH) if os.path.exists(REBOOT_PATH) else 0) == lastRestartChange:
        while not self.interrupted:
            if len(self.data) == 0:
                self.light(Color(0, 0, 0), Color(0, 0, 0), Color(0, 0, 0), Color(0, 0, 0), 50)
                continue

            # index = iteration  # start + (iteration % (len(self.data) - start))
            if iteration > len(self.data): iteration = 0
            conf = self.data[iteration]

            if conf.pattern == 'clear':
                del self.data[:iteration + 1]
                iteration = 0

            # start = index + 1
            # self.logger.info('Cleared index=' + str(index) + ', length=' + str(len(self.data)))
            # + ', start=' + str(start))
            # index = 0  # start + (iteration % (len(self.data) - start))
            conf = self.data[iteration]

            # print ('Index: ' + str(start) + '+(' + str(iteration) + '%(' + str(len(self.data)) + '-' + str(start) + ')='
            #        + str(index) + ': ' + conf.pattern + ' c1=' + str(conf.color1) + ', c2=' + str(conf.color2) + ','
            #        + ' c3=' + str(conf.color3) + ', c4=' + str(conf.color4) + ', c5=' + str(conf.color5) + ','
            #        + ' c6=' + str(conf.color6) + ', wait=' + str(conf.wait) + 'ms, width=' + str(conf.width) + ','
            #        + ' fading=' + str(conf.fading) + ', min=' + str(conf.min) + ', max=' + str(conf.max))
            # self.logger.debug('Index: ' + str(index) + '|' + str(iteration) + ': ' + conf.pattern
            #        + ' c1=' + str(conf.color1) + ', c2=' + str(conf.color2) + ', c3=' + str(conf.color3) + ','
            #        + ' c4=' + str(conf.color4) + ', c5=' + str(conf.color5) + ', c6=' + str(conf.color6) + ','
            #        + ' wait=' + str(conf.wait) + 'ms, width=' + str(conf.width) + ', fading=' + str(conf.fading) + ','
            #        + ' min=' + str(conf.min) + ', max=' + str(conf.max))
            if conf.pattern == 'wipe':
                self.wipe(Color2(conf.color1), Color2(conf.color2), Color2(conf.color5), Color2(conf.color6),
                          conf.wait, conf.fading)
            elif conf.pattern == 'light':
                self.light(Color2(conf.color1), Color2(conf.color2), Color2(conf.color5), Color2(conf.color6),
                           conf.wait)
            elif conf.pattern == 'rotation':
                self.rotation(Color2(conf.color1), Color2(conf.color2), Color2(conf.color5), Color2(conf.color6),
                              conf.width, conf.fading, conf.wait)
            elif conf.pattern == 'spin':
                self.spin(Color2(conf.color1), Color2(conf.color2), Color2(conf.color5), Color2(conf.color6))
            elif conf.pattern == 'chaise':
                self.chaise(Color2(conf.color1), Color2(conf.color2), Color2(conf.color5), Color2(conf.color6),
                            conf.width, conf.fading, conf.wait)
            elif conf.pattern == 'lighthouse':
                self.lighthouse(Color2(conf.color1), Color2(conf.color2), Color2(conf.color3), Color2(conf.color4),
                                Color2(conf.color5), Color2(conf.color6), conf.width, conf.fading, conf.wait)
            elif conf.pattern == 'fade':
                self.fade(Color2(conf.color1), Color2(conf.color2), Color2(conf.color5), Color2(conf.color6),
                          conf.wait, conf.min, conf.max)
            elif conf.pattern == 'fadeToggle':
                self.fade_toggle(Color2(conf.color1), Color2(conf.color2), Color2(conf.color5), Color2(conf.color6),
                                 conf.wait, conf.min, conf.max)
            elif conf.pattern == 'blink':
                self.blink(Color2(conf.color1), Color2(conf.color2), Color2(conf.color5), Color2(conf.color6),
                           conf.wait)
            elif conf.pattern == 'theater':
                self.theater(Color2(conf.color1), Color2(conf.color2), Color2(conf.color5), Color2(conf.color6),
                             conf.wait, conf.fading)
            elif conf.pattern == 'rainbow':
                self.rainbow(conf.wait, conf.fading)
            elif conf.pattern == 'rainbowCycle':
                self.rainbow_cycle(conf.wait, conf.fading)
            elif conf.pattern == 'wait':
                time.sleep(conf.wait / 1000.0)
            else:
                self.fade(Color(16, 16, 16), Color(16, 16, 16), Color(0, 0, 0), Color(0, 0, 0), 10, 50, 80)

            iteration = iteration + 1
            if iteration >= len(self.data): iteration = 0
