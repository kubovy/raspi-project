#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import time
from threading import Thread
import prctl
from neopixel import *
from lib.ModuleMQTT import ModuleMQTT

COLOR_BLACK = Color(0, 0, 0)
COLOR_WHITE = Color(255, 255, 255)
COLOR_RED = Color(255, 0, 0)
COLOR_GREEN = Color(0, 255, 0)
COLOR_BLUE = Color(0, 0, 255)
COLOR_MAGENTA = Color(255, 0, 255)


def to_color(config):
    return Color(config[0], config[1], config[2])


def to_colors(configs):
    return [to_color(configs[0]), to_color(configs[2]), to_color(configs[3]), to_color(configs[3])]


class Pixels(ModuleMQTT):

    # Neopixel
    LED_COUNT      = 4      # Number of LED pixels.
    LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA        = 5       # DMA channel to use for generating signal (try 5)
    LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
    LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
    LED_CHANNEL    = 0
    LED_STRIP      = ws.WS2811_STRIP_GRB

    pixel_leds = []
    notify_configs = []
    notify_delays = []

    def __init__(self, client, service_name, led_pin=18, pixel_count=4, debug=False):
        """
        Constructor

        :param client: MQTT Client
        :param service_name: Service name (only lower case latin characters and dash)
        :param led_pin: Optional PIO pin connected to the pixels (must support PWM!) - default 18
        :param pixel_count: Optional pixel count - default 4
        :param debug: Optional debug mode - default False
        """
        super(Pixels, self).__init__(client, service_name, "led", debug)

        for pixel in range(0, pixel_count):
            self.pixel_leds.append(Color(0, 0, 0))

        # Create NeoPixel object with appropriate configuration.
        self.strip = Adafruit_NeoPixel(self.LED_COUNT, led_pin, self.LED_FREQ_HZ, self.LED_DMA, self.LED_INVERT,
                                       self.LED_BRIGHTNESS, self.LED_CHANNEL, self.LED_STRIP)

    def on_mqtt_message(self, path, payload):
        if len(path) > 0:
            rgb = payload.split(",")
            self.set_color(int(path[0]), int(rgb[0]), int(rgb[1]), int(rgb[2]))
        else:
            rgbs = payload.split(" ")
            for pixel in range(0, min(len(rgbs), len(self.pixel_leds))):
                rgb = rgbs[pixel].split(",")
                self.set_color(pixel, int(rgb[0]), int(rgb[1]), int(rgb[2]))

    def notify(self, configs, delays):
        self.notify_configs = configs
        self.notify_delays = delays
        thread = Thread(target=self.notify_runnable)
        thread.daemon = True
        thread.start()

    def notify_runnable(self):
        prctl.set_name("Pixels Notify")
        for i in range(len(self.notify_configs)):
            self.update(to_colors(self.notify_configs[i]))
            j = i if (i < len(self.notify_delays)) else len(self.notify_delays) - 1
            delay = self.notify_delays[j] if (j >= 0) else 1
            time.sleep(delay)
        self.notify_configs = []
        self.notify_delays = []
        self.restore()

    def restore(self):
        self.update(self.pixel_leds)

    def update(self, pixels):
        self.strip.begin()
        for pixel in range(0, len(pixels)):
            color = pixels[pixel]
            self.strip.setPixelColor(pixel, color)
            # white = (color & (255 << 24)) >> 24
            red = (color & (255 << 16)) >> 16
            green = (color & (255 << 8)) >> 8
            blue = (color & 255)
            self.logger.debug("Updating " + str(pixel) + " to " + str(red) + "," + str(green) + "," + str(blue))
            self.publish(str(pixel), str(red) + "," + str(green) + "," + str(blue), 1, True)
        self.strip.show()

    def set_color(self, pixel, red, green, blue):
        self.logger.debug("Setting " + str(pixel) + " to " + str(red) + "," + str(green) + "," + str(blue))
        self.pixel_leds[pixel] = Color(red, green, blue)
        self.update(self.pixel_leds)
