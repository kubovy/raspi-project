import smbus
import time
import math
import os

from ModuleLooper import ModuleLooper


class MCP23017(ModuleLooper):

    IODIRA = 0x00  # Pin Register fuer die Richtung
    IODIRB = 0x01  # Pin Register fuer die Richtung
    IODIRS = [IODIRA, IODIRB]

    OLATA = 0x14
    OLATB = 0x15  # Register fuer Ausgabe (GPB)
    OLATS = [OLATA, OLATB]
    GPIOA = 0x12  # Register fuer Eingabe (GPA)
    GPIOB = 0x13
    GPIOS = [GPIOA, GPIOB]

    BUS = []
    DEVICES = [0x20, 0x21]
    INVERSE_OUTPUT = True

    CONFIG = [
        [0xFF, 0xFF],
        [0xFF, 0x07]
    ]

    state_machine = None

    def __init__(self, client, service_name, debug=False):
        super(MCP23017, self).__init__(client, service_name, "mcp23017", "MCP23017", debug)

        for _ in self.DEVICES:
            # bus = smbus.SMBus(0) # Rev 1 Pi
            self.BUS.append(smbus.SMBus(1))  # Rev 2 Pi

        self.input_cache = [0x00, 0x00, 0x00, 0x00]
        self.output_cache = [None, None, None, 0xF8 if self.INVERSE_OUTPUT else 0x00]

        # Definiere GPA Pin 7 als Input (10000000 = 0x80)
        # Binaer: 0 bedeutet Output, 1 bedeutet Input
        # Definiere alle GPB Pins als Output (00000000 = 0x00)

        for idx, bus in enumerate(self.BUS):
            for io, iodir in enumerate(self.IODIRS):
                bus.write_byte_data(self.DEVICES[idx], iodir, self.CONFIG[idx][io])

        for idx, output in enumerate(self.output_cache):
            if self.output_cache[idx] is not None:
                i = int(math.floor(idx / 2.0))
                j = idx % 2
                self.BUS[i].write_byte_data(self.DEVICES[i], self.OLATS[j], self.output_cache[idx])

    def on_message(self, path, payload):
        if len(path) > 0:   # {service}/control/mcp23017/{bit}
            self.set(int(path[0]), payload.lower() == "true" or payload.lower() == "on")

    def get(self, bit, value=None):
        idx = int(math.floor(bit / 16.0))
        gpio = self.GPIOS[int(math.floor(bit / 8.0)) % 2]
        real_bit = bit % 8

        value = self.BUS[idx].read_byte_data(self.DEVICES[idx], gpio) if value is None else value

        return (value >> real_bit & 1) != 0

    def set(self, bit, value):
        idx = int(math.floor(bit / 8.0))
        bus = self.BUS[int(math.floor(bit / 16))]
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
        bus.write_byte_data(device, olat, self.output_cache[idx])

    def looper(self):
        # Status von GPIOA Register auslesen
        current = []
        for idx, bus in enumerate(self.BUS):
            for gpio in self.GPIOS:
                current.append(bus.read_byte_data(self.DEVICES[idx], gpio))

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
