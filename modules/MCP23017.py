#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import math
import time

import smbus

from lib.ModuleLooper import ModuleLooper


class MCP23017(ModuleLooper):
    IODIRA = 0x00  # Pin Register for direction
    IODIRB = 0x01  # Pin Register for direction

    OLATA = 0x14  # Register for output (GPA)
    OLATB = 0x15  # Register for output (GPB)
    GPIOA = 0x12  # Register for input (GPA)
    GPIOB = 0x13  # Register for input (GPB)

    module_mqtt = None

    __bus = None
    __olats = [OLATA, OLATB]
    __gpios = [GPIOA, GPIOB]
    __devices = [0x20, 0x21]
    __inverse_output = True

    # Binary: 0 = Output, 1 = Input
    # Device 1 GPA: pins as Input (11111111 = 0xFF)
    # Device 1 GBP: pins as Input (11111111 = 0xFF)
    # Device 2 GPA: pins as Input (11111111 = 0xFF)
    # Device 2 GPB: first 3 pins as Input, last 5 pins Output (00000111 = 0x07)
    __config = [
        [0xFF, 0xFF],
        [0xFF, 0x07]
    ]

    def __init__(self, debug=False):
        super(MCP23017, self).__init__(debug=debug)

        # for _ in self.__devices:
        #     bus = smbus.SMBus(0) # Rev 1 Pi
        #     self.__bus.append(smbus.SMBus(1))  # Rev 2 Pi
        self.__bus = smbus.SMBus(1)

        self.__input_cache = [0x00, 0x00, 0x00, 0x00]
        self.__output_cache = [None, None, None, 0xF8 if self.__inverse_output else 0x00]

        for idx, device in enumerate(self.__devices):
            for io, iodir in enumerate([self.IODIRA, self.IODIRB]):
                self.__bus.write_byte_data(self.__devices[idx], iodir, self.__config[idx][io])

        for idx, output in enumerate(self.__output_cache):
            if self.__output_cache[idx] is not None:
                i = int(math.floor(idx / 2.0))
                j = idx % 2
                self.__bus.write_byte_data(self.__devices[i], self.__olats[j], self.__output_cache[idx])

    def initialize(self):
        self.__read_all_registers(notify=False)

    def get(self, bit, value=None):
        idx = int(math.floor(bit / 16.0))
        gpio = self.__gpios[int(math.floor(bit / 8.0)) % 2]
        real_bit = bit % 8

        value = self.__bus.read_byte_data(self.__devices[idx], gpio) if value is None else value

        return (value >> real_bit & 1) != 0

    def get_all(self):
        values = [False] * (len(self.__input_cache) * 8)
        for idx, buttons in enumerate(self.__input_cache):
            for bit in range(8):
                values[idx * 8 + bit] = self.get(bit, buttons)
        return values

    def set(self, bit, value, write=True):
        idx = int(math.floor(bit / 8.0))
        # bus = self.__bus[int(math.floor(bit / 16))]
        device = self.__devices[int(math.floor(bit / 16))]
        olat = self.__olats[idx % 2]
        real_bit = bit % 8

        real_value = not value if self.__inverse_output else value
        if real_value:
            self.__output_cache[idx] = self.__output_cache[idx] | (1 << real_bit)
        else:
            self.__output_cache[idx] = self.__output_cache[idx] & ~(1 << real_bit)
        # self.logger.debug(">>> " + str(idx) + "," + str(olat) + "," + str(real_bit) + ": " + str(real_value))
        self.logger.debug("Bit " + str(real_bit) + ": " + str(value) + " -> " + str(real_value) +
                          " Output: " + str(self.__output_cache[idx]) +
                          " [" + '{0:08b}'.format(self.__output_cache[idx]) + "]")
        if write:
            self.__bus.write_byte_data(device, olat, self.__output_cache[idx])

    def write_all(self):
        for idx, output in enumerate(self.__output_cache):
            if self.__output_cache[idx] is not None:
                device = self.__devices[int(math.floor(idx / 2))]
                olat = self.__olats[idx % 2]
                self.__bus.write_byte_data(device, olat, self.__output_cache[idx])

    def reset(self):
        for device in self.__devices:
            for olat in self.__olats:
                self.__bus.write_byte_data(device, olat, 0xFF if self.__inverse_output else 0x00)

    def finalize(self):
        super(MCP23017, self).finalize()
        self.reset()

    def on_mqtt_message(self, path, payload):
        if len(path) > 0:  # {service}/control/mcp23017/{bit}
            self.set(int(path[0]), payload.lower() == "true" or payload.lower() == "on")
        else:
            super(MCP23017, self).on_mqtt_message(path, payload)

    def looper(self):
        self.__read_all_registers()
        time.sleep(0.05)

    def __read_all_registers(self, notify=True):
        idx = 0
        for device in self.__devices:
            for gpio in self.__gpios:
                buttons = self.__bus.read_byte_data(device, gpio)
                if self.__input_cache[idx] != buttons:
                    # changed = True
                    for bit in range(8):
                        cache = self.get(bit, self.__input_cache[idx])
                        current = self.get(idx * 8 + bit)

                        if current != cache:
                            address = "{:02x}".format(self.__devices[int(math.floor(idx / 2.0))])
                            part = "AB"[idx % 2]
                            self.logger.debug("" + address + "/" + str(part) + "/" + str(bit) +
                                              " [" + str(idx * 8 + bit) + "]: " + str(cache) + " -> " + str(
                                current))
                            if notify:
                                if self.module_mqtt is not None:
                                    self.module_mqtt.publish("state/" + str(idx * 8 + bit), "ON" if current else "OFF",
                                                             module=self)
                                for listener in self.listeners:
                                    if hasattr(listener, 'on_mcp23017_change'):
                                        listener.on_mcp23017_change(idx * 8 + bit, current)
                    self.__input_cache[idx] = buttons
                idx = idx + 1
