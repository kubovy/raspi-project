#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import binascii
import serial
import time
import threading
import traceback
from ModuleLooper import ModuleLooper


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

    def __init__(self, client, service_name, identifier="20180214", ports=None, debug=False):
        super(SerialReader, self).__init__(client, service_name, "serial-reader", debug)
        self.identifier = identifier
        self.ports = [] if ports is None else ports

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
        # serial_port.writeTimeout = 2

        serial_port.open()
        serial_port.flushInput()
        serial_port.flushOutput()
        return serial_port

    def __port_looper__(self, port):
        self.logger.debug(">>" + str(port))
        while not self.interrupted:  # Not connected
            try:
                serial_port = self.__port_init__(port)

                try:
                    while not self.interrupted:
                        line = serial_port.readline()
                        self.__process_line__(port, serial_port, line.strip())
                        time.sleep(0.001)
                except serial.SerialException:
                    self.logger.error("Unexpected Error!")
                    traceback.print_exc()
                finally:
                    serial_port.close()
            except:
                self.logger.error("Cannot establish connection with "+ port)
                time.sleep(2)

    def __process_line__(self, port, serial_port, line):
        if line != "":
            if self.mode == 0 and line == STX:  # and self.receiving_serial_port is None:
                self.logger.info("[" + port + "] STX: Message start")
                self.receiving_serial_port = serial_port
                self.content = ""
                self.mode = 1
            elif line == ENQ:
                self.logger.info("[" + port + "] ENQ: Identifying...")
                serial_port.write((ACK + ":" + self.identifier + "\n").encode())
            elif self.mode == 1 and line == ETX:   # and self.receiving_serial_port == serial_port:
                if self.receiving_serial_port == serial_port:
                    checksum = binascii.crc32(self.content)
                    self.logger.info("[" + port + "] ETX: Message end - Checksum=" + str(checksum))
                    serial_port.write(("ACK:" + str(checksum) + "\n").encode())
                    if self.fast_success:
                        self.__write_result__()
                        self.mode = 0
                        self.receiving_serial_port = None
                        self.content = ""
                    else:
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
        for port in self.ports:
            thread = threading.Thread(target=self.__port_looper__, args=[port])
            self.port_threads.append(thread)
            thread.start()

        while not self.interrupted:
            time.sleep(1)

        for thread in self.port_threads:
            thread.join(5)

        self.logger.info("Exiting looper")