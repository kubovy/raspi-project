#!/usr/bin/python
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

    interrupted = False
    thread = None
    port_threads = []
    receiving_serial_port = None
    mode = 0
    fast_success = True
    content = ""
    listeners = []
    serial_ports = []
    buffers = []

    def __init__(self, client, service_name, identifier="20180214", ports=None, debug=False):
        super(SerialReader, self).__init__(client, service_name, "serial-reader", "Serial", debug)
        self.identifier = identifier
        self.ports = [] if ports is None else ports
        for i in range(len(self.ports)):
            self.serial_ports.append(None)
            self.buffers.append(None)

    def register(self, listener):
        if listener not in self.listeners:
            self.listeners.append(listener)

    def unregister(self, listener):
        self.listeners.remove(listener)

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
        serial_port = self.serial_ports[index]
        i = self.buffers[index].find(b"\n")
        if i >= 0:
            line = self.buffers[index][:i + 1]
            self.buffers[index] = self.buffers[index][i + 1:]
            return line.decode("utf-8")
        while not self.interrupted:
            try:
                while not self.interrupted and serial_port.in_waiting == 0:
                    time.sleep(1)
            except:
                self.logger.error("Unexpected Error (a)!")
                traceback.print_exc()
            if not self.interrupted:
                i = max(1, min(2048, serial_port.in_waiting))
                data = serial_port.read(i)
                if len(data) > 0:
                    i = data.find(b"\n")
                    if i >= 0:
                        line = self.buffers[index] + data[:i + 1]
                        self.buffers[index][0:] = data[i + 1:]
                        return line.decode("utf-8")
                    else:
                        self.buffers[index].extend(data)
                else:
                    time.sleep(0.1)
        return ""

    def __port_looper__(self, index):
        self.logger.debug(">>" + str(self.ports[index]))
        self.buffers[index] = bytearray()
        port = self.ports[index]
        prctl.set_name(self.thread_name + " Port " + str(port))
        serial_port = None

        while not self.interrupted:  # Not connected
            try:
                serial_port = self.__port_init__(port)
                self.serial_ports[index] = serial_port
                try:
                    while not self.interrupted:
                        line = self.__readline__(index)
                        # line = serial_port.readline()
                        self.__process_line__(index, line.strip())
                        time.sleep(0.001)
                except serial.SerialException:
                    self.logger.error("Unexpected Error (b)!")
                    traceback.print_exc()
                finally:
                    self.logger.info("(%s) Closing port (a)..." % self.ports[index])
                    serial_port.close()
                    serial_port = None
            except:
                self.logger.error("Cannot establish connection with " + port)
                # traceback.print_exc()
                time.sleep(2)

        if serial_port is not None:
            self.logger.info("(%s) Closing port (b)..." % self.ports[index])
            serial_port.close()
        self.logger.info("(%s) Exiting looper" % self.ports[index])

    def __process_line__(self, index, line):
        port = str(self.ports[index])
        serial_port = self.serial_ports[index]
        if line != "":
            if self.mode == 0 and line == STX:  # and self.receiving_serial_port is None:
                self.logger.info("[" + port + "] STX: Message start")
                self.receiving_serial_port = serial_port
                self.content = ""
                self.mode = 1
            elif line == ENQ:
                self.logger.info("[" + port + "] ENQ: Identifying...")
                serial_port.reset_output_buffer()
                try:
                    serial_port.write((ACK + ":" + self.identifier + "\n").encode())
                except SerialTimeoutException:
                    self.logger.error("SerialTimeoutException (b)")
            elif self.mode == 1 and line == ETX:   # and self.receiving_serial_port == serial_port:
                if self.receiving_serial_port == serial_port:
                    checksum = binascii.crc32(self.content)
                    self.logger.info("[" + port + "] ETX: Message end - Checksum=" + str(checksum)
                                     + (" fast success" if self.fast_success else " waiting for confirmation"))
                    serial_port.reset_output_buffer()
                    try:
                        serial_port.write(("ACK:" + str(checksum) + "\n").encode())
                    except SerialTimeoutException:
                        self.logger.error("SerialTimeoutException (b)")
                    if self.fast_success:
                        self.logger.debug("FAST SUCCESS")
                        self.__write_result__()
                        self.mode = 0
                        self.receiving_serial_port = None
                        self.content = ""
                    else:
                        self.logger.debug("WAITING FOR CONFIRMATION...")
                        self.mode = 2
                else:
                    self.logger.info("[" + port + "] ETX: Starting over")
                    self.mode = 0
                    self.receiving_serial_port = None
                    self.content = ""
            elif self.mode == 1 and self.receiving_serial_port == serial_port:
                self.logger.info("[" + port + "] Message part: " + line)
                self.content = self.content + line
            elif self.mode == 2 and line == ACK and self.receiving_serial_port == serial_port:
                self.logger.info("[" + port + "] ACK: Message received correctly")
                self.__write_result__()
                self.mode = 0
                self.receiving_serial_port = None
                self.content = ""
            elif line == ETX:
                self.logger.info("[" + port + "] ETX: Starting over")
                self.mode = 0
                self.receiving_serial_port = None
                self.content = ""
            else:
                self.logger.debug("[" + port + "] Unknown: " + line)

    def __write_result__(self):
        self.logger.info("Message: " + self.content)
        for listener in self.listeners:
            listener.on_serial_message(self.content)
        self.content = ""

    def looper(self):
        for i in range(len(self.ports)):
            thread = Thread(target=self.__port_looper__, args=[i])
            thread.daemon = True
            self.port_threads.append(thread)
            thread.start()

        while not self.interrupted:
            time.sleep(1)

        for thread in self.port_threads:
            thread.join(5)

        self.logger.info("Exiting looper")