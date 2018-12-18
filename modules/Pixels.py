#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import prctl
import time
from threading import Thread

from neopixel import *

from lib.Module import Module

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


class Pixels(Module):
    # Neopixel
    LED_COUNT = 4  # Number of LED pixels.
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA = 5  # DMA channel to use for generating signal (try 5)
    LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
    LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
    LED_CHANNEL = 0
    LED_STRIP = ws.WS2811_STRIP_GRB

    module_mqtt = None

    __pixel_leds = []
    __notify_configs = []
    __notify_delays = []

    def __init__(self, pin=18, count=4, debug=False):
        """
        Constructor

        :param pin: Optional PIO pin connected to the pixels (must support PWM!) - default 18
        :param count: Optional pixel count - default 4
        :param debug: Optional debug mode - default False
        """
        super(Pixels, self).__init__(debug=debug)

        for pixel in range(0, count):
            self.__pixel_leds.append(Color(0, 0, 0))

        # Create NeoPixel object with appropriate configuration.
        self.__strip = Adafruit_NeoPixel(self.LED_COUNT, pin, self.LED_FREQ_HZ, self.LED_DMA, self.LED_INVERT,
                                         self.LED_BRIGHTNESS, self.LED_CHANNEL, self.LED_STRIP)

    def set_color(self, pixel, red, green, blue):
        self.logger.debug("Setting " + str(pixel) + " to " + str(red) + "," + str(green) + "," + str(blue))
        self.__pixel_leds[pixel] = Color(red, green, blue)
        self.__update(self.__pixel_leds)

    def notify(self, configs, delays):
        self.__notify_configs = configs
        self.__notify_delays = delays
        thread = Thread(target=self.__notify_runnable)
        thread.daemon = True
        thread.start()

    def on_mqtt_message(self, path, payload):
        if len(path) > 0:
            rgb = payload.split(",")
            self.set_color(int(path[0]), int(rgb[0]), int(rgb[1]), int(rgb[2]))
        else:
            rgbs = payload.split(" ")
            for pixel in range(0, min(len(rgbs), len(self.__pixel_leds))):
                rgb = rgbs[pixel].split(",")
                self.set_color(pixel, int(rgb[0]), int(rgb[1]), int(rgb[2]))

    def __notify_runnable(self):
        prctl.set_name("Pixels Notify")
        for i in range(len(self.__notify_configs)):
            self.__update(to_colors(self.__notify_configs[i]))
            j = i if (i < len(self.__notify_delays)) else len(self.__notify_delays) - 1
            delay = self.__notify_delays[j] if (j >= 0) else 1
            time.sleep(delay)
        self.__notify_configs = []
        self.__notify_delays = []
        self.__restore()

    def __restore(self):
        self.__update(self.__pixel_leds)

    def __update(self, pixels):
        self.__strip.begin()
        for pixel in range(0, len(pixels)):
            color = pixels[pixel]
            self.__strip.setPixelColor(pixel, color)
            # white = (color & (255 << 24)) >> 24
            red = (color & (255 << 16)) >> 16
            green = (color & (255 << 8)) >> 8
            blue = (color & 255)
            self.logger.debug("Updating " + str(pixel) + " to " + str(red) + "," + str(green) + "," + str(blue))
            if self.module_mqtt is not None:
                self.module_mqtt.publish(str(pixel), str(red) + "," + str(green) + "," + str(blue), module=self)
        self.__strip.show()
