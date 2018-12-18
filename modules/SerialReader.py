#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import binascii
import prctl
import serial
from serial.serialutil import *
import time
from threading import Thread
import traceback

from lib.ModuleLooper import ModuleLooper


STX = "STX"
ETX = "ETX"
ENQ = "ENQ"
ACK = "ACK"


class SerialReader(ModuleLooper):
    """Serial reader module"""

    __port_threads = []
    __receiving_serial_port = None
    __mode = 0
    __fast_success = True
    __content = ""
    __listeners = []
    __serial_ports = []
    __buffers = []

    def __init__(self, identifier="20180214", ports=None, debug=False):
        super(SerialReader, self).__init__(debug=debug)
        self.__identifier = identifier
        self.__ports = [] if ports is None else ports
        for i in range(len(self.__ports)):
            self.__serial_ports.append(None)
            self.__buffers.append(None)

    def register(self, listener):
        if listener not in self.__listeners:
            self.__listeners.append(listener)

    def finalize(self):
        super(SerialReader, self).finalize()
        self.__listeners = []

    def looper(self):
        for i in range(len(self.__ports)):
            thread = Thread(target=self.__port_looper__, args=[i])
            thread.daemon = True
            self.__port_threads.append(thread)
            thread.start()

        while not self.is_interrupted():
            time.sleep(1)

        for thread in self.__port_threads:
            thread.join(5)

        self.logger.info("Exiting looper")

    def __port_init__(self, port):
        self.logger.info("Listening on port " + port)
        serial_port = serial.Serial()
        serial_port.port = port
        # If it breaks try the below
        # self.serConf() # Uncomment lines here till it works
        serial_port.baudrate = 115200  # 9600
        serial_port.bytesize = serial.EIGHTBITS
        serial_port.parity = serial.PARITY_NONE
        serial_port.stopbits = serial.STOPBITS_ONE
        serial_port.timeout = 0  # Non-Block reading
        # serial_port.xonxoff = False  # Disable Software Flow Control
        # serial_port.rtscts = False  # Disable (RTS/CTS) flow Control
        # serial_port.dsrdtr = False  # Disable (DSR/DTR) flow Control
        serial_port.write_timeout = 2

        serial_port.open()
        serial_port.flushInput()
        serial_port.flushOutput()
        return serial_port

    def __readline__(self, index):
        serial_port = self.__serial_ports[index]
        i = self.__buffers[index].find(b"\n")
        if i >= 0:
            line = self.__buffers[index][:i + 1]
            self.__buffers[index] = self.__buffers[index][i + 1:]
            return line.decode("utf-8")
        while not self.is_interrupted():
            try:
                while not self.is_interrupted() and serial_port.in_waiting == 0:
                    time.sleep(1)
            except:
                self.logger.error("Unexpected Error (a)!")
                traceback.print_exc()
            if not self.is_interrupted():
                i = max(1, min(2048, serial_port.in_waiting))
                data = serial_port.read(i)
                if len(data) > 0:
                    i = data.find(b"\n")
                    if i >= 0:
                        line = self.__buffers[index] + data[:i + 1]
                        self.__buffers[index][0:] = data[i + 1:]
                        return line.decode("utf-8")
                    else:
                        self.__buffers[index].extend(data)
                else:
                    time.sleep(0.1)
        return ""

    def __port_looper__(self, index):
        self.logger.debug(">>" + str(self.__ports[index]))
        self.__buffers[index] = bytearray()
        port = self.__ports[index]
        prctl.set_name(self.thread_name + " Port " + str(port))
        serial_port = None

        while not self.is_interrupted():  # Not connected
            try:
                serial_port = self.__port_init__(port)
                self.__serial_ports[index] = serial_port
                try:
                    while not self.is_interrupted():
                        line = self.__readline__(index)
                        # line = serial_port.readline()
                        self.__process_line__(index, line.strip())
                        time.sleep(0.001)
                except serial.SerialException:
                    self.logger.error("Unexpected Error (b)!")
                    traceback.print_exc()
                finally:
                    self.logger.info("(%s) Closing port (a)..." % self.__ports[index])
                    serial_port.close()
                    serial_port = None
            except:
                self.logger.error("Cannot establish connection with " + port)
                # traceback.print_exc()
                time.sleep(2)

        if serial_port is not None:
            self.logger.info("(%s) Closing port (b)..." % self.__ports[index])
            serial_port.close()
        self.logger.info("(%s) Exiting looper" % self.__ports[index])

    def __process_line__(self, index, line):
        port = str(self.__ports[index])
        serial_port = self.__serial_ports[index]
        if line != "":
            if self.__mode == 0 and line == STX:  # and self.__receiving_serial_port is None:
                self.logger.info("[" + port + "] STX: Message start")
                self.__receiving_serial_port = serial_port
                self.__content = ""
                self.__mode = 1
            elif line == ENQ:
                self.logger.info("[" + port + "] ENQ: Identifying...")
                serial_port.reset_output_buffer()
                try:
                    serial_port.write((ACK + ":" + self.__identifier + "\n").encode())
                except SerialTimeoutException:
                    self.logger.error("SerialTimeoutException (b)")
            elif self.__mode == 1 and line == ETX:   # and self.__receiving_serial_port == serial_port:
                if self.__receiving_serial_port == serial_port:
                    checksum = binascii.crc32(self.__content)
                    self.logger.info("[" + port + "] ETX: Message end - Checksum=" + str(checksum)
                                     + (" fast success" if self.__fast_success else " waiting for confirmation"))
                    serial_port.reset_output_buffer()
                    try:
                        serial_port.write(("ACK:" + str(checksum) + "\n").encode())
                    except SerialTimeoutException:
                        self.logger.error("SerialTimeoutException (b)")
                    if self.__fast_success:
                        self.logger.debug("FAST SUCCESS")
                        self.__write_result__()
                        self.__mode = 0
                        self.__receiving_serial_port = None
                        self.__content = ""
                    else:
                        self.logger.debug("WAITING FOR CONFIRMATION...")
                        self.__mode = 2
                else:
                    self.logger.info("[" + port + "] ETX: Starting over")
                    self.__mode = 0
                    self.__receiving_serial_port = None
                    self.__content = ""
            elif self.__mode == 1 and self.__receiving_serial_port == serial_port:
                self.logger.info("[" + port + "] Message part: " + line)
                self.__content = self.__content + line
            elif self.__mode == 2 and line == ACK and self.__receiving_serial_port == serial_port:
                self.logger.info("[" + port + "] ACK: Message received correctly")
                self.__write_result__()
                self.__mode = 0
                self.__receiving_serial_port = None
                self.__content = ""
            elif line == ETX:
                self.logger.info("[" + port + "] ETX: Starting over")
                self.__mode = 0
                self.__receiving_serial_port = None
                self.__content = ""
            else:
                self.logger.debug("[" + port + "] Unknown: " + line)

    def __write_result__(self):
        self.logger.info("Message: " + self.__content)
        for listener in self.__listeners:
            listener.on_serial_message(self.__content)
        self.__content = ""
