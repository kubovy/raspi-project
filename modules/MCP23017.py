#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import smbus
import time
import math

from lib.ModuleLooper import ModuleLooper


class MCP23017(ModuleLooper):

    IODIRA = 0x00  # Pin Register for direction
    IODIRB = 0x01  # Pin Register for direction
    IODIRS = [IODIRA, IODIRB]

    OLATA = 0x14  # Register for output (GPA)
    OLATB = 0x15  # Register for output (GPB)
    OLATS = [OLATA, OLATB]
    GPIOA = 0x12  # Register for input (GPA)
    GPIOB = 0x13  # Register for input (GPB)
    GPIOS = [GPIOA, GPIOB]

    BUS = None
    DEVICES = [0x20, 0x21]
    INVERSE_OUTPUT = True

    # Binary: 0 = Output, 1 = Input
    # Device 1 GPA: pins as Input (11111111 = 0xFF)
    # Device 1 GBP: pins as Input (11111111 = 0xFF)
    # Device 2 GPA: pins as Input (11111111 = 0xFF)
    # Device 2 GPB: first 3 pins as Input, last 5 pins Output (00000111 = 0x07)
    CONFIG = [
        [0xFF, 0xFF],
        [0xFF, 0x07]
    ]

    state_machine = None

    def __init__(self, client, service_name, debug=False):
        super(MCP23017, self).__init__(client, service_name, "mcp23017", "MCP23017", debug)

        # for _ in self.DEVICES:
        #     bus = smbus.SMBus(0) # Rev 1 Pi
        #     self.BUS.append(smbus.SMBus(1))  # Rev 2 Pi
        self.BUS = smbus.SMBus(1)

        self.input_cache = [0x00, 0x00, 0x00, 0x00]
        self.output_cache = [None, None, None, 0xF8 if self.INVERSE_OUTPUT else 0x00]

        for idx, device in enumerate(self.DEVICES):
            for io, iodir in enumerate(self.IODIRS):
                self.BUS.write_byte_data(self.DEVICES[idx], iodir, self.CONFIG[idx][io])

        for idx, output in enumerate(self.output_cache):
            if self.output_cache[idx] is not None:
                i = int(math.floor(idx / 2.0))
                j = idx % 2
                self.BUS.write_byte_data(self.DEVICES[i], self.OLATS[j], self.output_cache[idx])

    def finalize(self):
        super(MCP23017, self).finalize()
        for device in self.DEVICES:
            for olat in self.OLATS:
                self.BUS.write_byte_data(device, olat, 0xFF if self.INVERSE_OUTPUT else 0x00)

    def on_mqtt_message(self, path, payload):
        if len(path) > 0:   # {service}/control/mcp23017/{bit}
            self.set(int(path[0]), payload.lower() == "true" or payload.lower() == "on")

    def get(self, bit, value=None):
        idx = int(math.floor(bit / 16.0))
        gpio = self.GPIOS[int(math.floor(bit / 8.0)) % 2]
        real_bit = bit % 8

        value = self.BUS.read_byte_data(self.DEVICES[idx], gpio) if value is None else value

        return (value >> real_bit & 1) != 0

    def set(self, bit, value):
        idx = int(math.floor(bit / 8.0))
        # bus = self.BUS[int(math.floor(bit / 16))]
        device = self.DEVICES[int(math.floor(bit / 16))]
        olat = self.OLATS[idx % 2]
        real_bit = bit % 8

        real_value = not value if self.INVERSE_OUTPUT else value
        if real_value:
            self.output_cache[idx] = self.output_cache[idx] | (1 << real_bit)
        else:
            self.output_cache[idx] = self.output_cache[idx] & ~(1 << real_bit)
        # self.logger.debug(">>> " + str(idx) + "," + str(olat) + "," + str(real_bit) + ": " + str(real_value))
        self.logger.debug("Bit " + str(real_bit) + ": " + str(value) + " -> " + str(real_value) +
                          " Output: " + str(self.output_cache[idx]) +
                          " [" + '{0:08b}'.format(self.output_cache[idx]) + "]")
        self.BUS.write_byte_data(device, olat, self.output_cache[idx])

    def looper(self):
        # Status von GPIOA Register auslesen
        current = []
        for device in self.DEVICES:
            for gpio in self.GPIOS:
                current.append(self.BUS.read_byte_data(device, gpio))

        # changed = False
        for idx, buttons in enumerate(current):
            if self.input_cache[idx] != buttons:
                # changed = True
                for bit in range(8):
                    cache = self.get(bit, self.input_cache[idx])
                    current = self.get(idx * 8 + bit)

                    if current != cache:
                        address = "{:02x}".format(self.DEVICES[int(math.floor(idx / 2.0))])
                        part = "AB"[idx % 2]
                        self.logger.debug("" + address + "/" + str(part) + "/" + str(bit) +
                                          " [" + str(idx * 8 + bit) + "]: " + str(cache) + " -> " + str(current))
                        self.publish("state/" + str(idx * 8 + bit), "ON" if current else "OFF")
                        if self.state_machine is not None:
                            self.state_machine.set_state("mcp23017", idx * 8 + bit, current)
                self.input_cache[idx] = buttons
        time.sleep(0.05)
