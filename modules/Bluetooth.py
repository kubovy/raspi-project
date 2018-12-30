#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import time
import prctl
from binascii import crc32
import traceback
from threading import Thread
from bluetooth import *
from lib.ModuleLooper import ModuleLooper

STX = "STX"
ETX = "ETX"
ENQ = "ENQ"
IDD = "IDD"
ACK = "ACK"
NOP = "NOP"

BUFFER = 1024


class Bluetooth(ModuleLooper):
    """Bluetooth server module create two thread each opening one connection, one for inbound and one for outbound
    communication"""

    __buffer_outgoing = []
    __buffer_incoming = ""
    __sockets = []
    __connections = []

    module_mqtt = None

    def __init__(self, client_id, inbound_ports=None, outbound_ports=None, debug=False):
        super(Bluetooth, self).__init__(debug=debug)
        self.__client_id = client_id
        self.__inbound_ports = inbound_ports if inbound_ports is not None else [3]
        self.__outbound_ports = outbound_ports if outbound_ports is not None else [4]

    def send(self, message):
        """Send a message via bluetooth

        :param message: Message to send
        """
        self.__buffer_outgoing.append(message)

    def on_mqtt_message(self, path, payload):
        prefix = ":".join(map(lambda s: s.upper(), path))
        self.send(prefix + (":" if prefix is not None and prefix != '' else "") + payload)

    def looper(self):
        threads = []

        for port in self.__inbound_ports:
            thread = Thread(target=self.__inbound_looper, args=[int(port)])
            thread.daemon = True
            thread.start()
            threads.append(thread)

        for port in self.__outbound_ports:
            thread = Thread(target=self.__outbound_looper, args=[int(port)])
            thread.daemon = True
            thread.start()
            threads.append(thread)

        while not self.is_interrupted():
            time.sleep(5)

        for connection in self.__connections:
            try:
                connection.shutdown(2)
                connection.close()
            except BluetoothError as e:
                self.logger.error(e.message)

        for s in self.__sockets:
            try:
                s.close()
            except:
                traceback.print_exc()

        for thread in threads:
            thread.join(1)

    def __notify(self, message):
        if self.module_mqtt is not None:
            parts = message.split(":", 2)
            if len(parts) > 1:
                self.module_mqtt.publish(parts[0].lower(), parts[1], module=self)
            elif len(parts) > 0:
                self.module_mqtt.publish("", parts[0], module=self)

        for listener in self.listeners:
            if hasattr(listener, 'on_bluetooth_message'):
                listener.on_bluetooth_message(message)

    def __outbound_looper(self, port):
        prctl.set_name(self.thread_name + " Out " + str(port))
        outbound_socket = BluetoothSocket(RFCOMM)
        outbound_socket.bind(('', port))
        outbound_socket.listen(1)
        self.__sockets.append(outbound_socket)

        while not self.is_interrupted():
            self.logger.info("Waiting for outbound connection...")
            connection, address = outbound_socket.accept()
            self.__connections.append(connection)
            self.logger.info("Outbound connection with: " + str(address))
            self.__notify("BT:CONNECTED")
            time.sleep(0.5)

            try:
                while not self.is_interrupted():
                    if len(self.__buffer_outgoing) > 0:
                        message = self.__buffer_outgoing[0]
                        self.logger.info("Outbound message: " + message)
                        correctly_received = False
                        retries = 0
                        while not correctly_received and retries < 3:
                            connection.send(STX + "\n")
                            length = len(message)
                            for chunk in [message[i:i + BUFFER] for i in range(0, length, BUFFER)]:
                                connection.send(chunk)
                            connection.send("\n" + ETX + "\n")

                            crc32_calculated = crc32(message) % (1 << 32)

                            data = connection.recv(BUFFER)[:-1]
                            self.logger.debug("Outbound received: \"" + data + "\"")
                            ack = data.split(":", 2)
                            self.logger.info("Outbound " + ack[0] + ": calculated=" + str(crc32_calculated) +
                                             ", received=" + ack[1] + " => " + str(crc32_calculated == long(ack[1])))
                            correctly_received = crc32_calculated == long(ack[1])
                            retries = retries + 1
                        if correctly_received:
                            self.__buffer_outgoing.pop(0)
                    else:
                        time.sleep(1)
            except BluetoothError as e:
                self.logger.error(e.message)
                # traceback.print_exc()
            finally:
                self.__notify("BT:DISCONNECTED")
                connection.close()

        self.logger.info("Exiting outbound looper")

    def __inbound_looper(self, port):
        prctl.set_name(self.thread_name + " In " + str(port))
        inbound_socket = BluetoothSocket(RFCOMM)
        inbound_socket.bind(('', port))
        inbound_socket.listen(1)
        self.__sockets.append(inbound_socket)

        while not self.is_interrupted():
            self.logger.info("Waiting for inbound connection...")
            connection, address = inbound_socket.accept()
            self.__connections.append(connection)
            self.logger.info("Inbound connection with: " + str(address))
            self.__notify("BT:CONNECTED")
            incomplete = ""

            try:
                while not self.is_interrupted():
                    data = connection.recv(BUFFER)
                    self.logger.debug("Inbound received: \"" + (data[:-1] if data[-1:] == "\n" else data) + "\"")

                    lines = data.split("\n")
                    for idx, line in enumerate(lines):
                        if idx == 0:  # Fist line is prepended with "incomplete" message from last transmission
                            line = incomplete + line
                            incomplete = ""

                        if idx == len(lines) - 1:  # Last is incomplete, may be empty in case of complete transmission
                            incomplete = line
                        elif line == STX:
                            self.buffer_incoming = ""
                        elif line == ETX:
                            self.logger.info("Inbound message: " + self.buffer_incoming)
                            self.__notify(self.buffer_incoming)
                            crc32_calculated = crc32(self.buffer_incoming) % (1 << 32)
                            connection.send("ACK:" + str(crc32_calculated) + "\n")
                            self.buffer_incoming = ""
                        elif line == ENQ:
                            connection.send("IDD:" + self.__client_id + "\n")
                        elif line.startswith(IDD + ":"):
                            self.__notify("BT:" + line)
                        elif line.startswith(ACK + ":"):
                            pass
                        elif line == NOP:
                            pass
                        else:
                            if self.buffer_incoming != "":
                                self.buffer_incoming += "\n"
                            self.buffer_incoming += line

            except BluetoothError as e:
                self.logger.error(e.message)
            finally:
                self.__notify("BT:DISCONNECTED")
                connection.close()

        self.logger.info("Exiting inbound looper")
