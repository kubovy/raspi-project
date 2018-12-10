#!/usr/bin/python
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
from ModuleLooper import ModuleLooper

STX = "STX"
ETX = "ETX"
ENQ = "ENQ"
IDD = "IDD"
ACK = "ACK"
NOP = "NOP"

BUFFER = 1024


class BluetoothServer(ModuleLooper):

    listeners = []
    buffer_outgoing = []
    buffer_incoming = ""
    sockets = []
    connections = []
    # mode = 0  # 0 - idle, 1 - receiving, 2 - waiting for confirmation

    def __init__(self, client, service_name, inbound_ports=None, outbound_ports=None, debug=False):
        super(BluetoothServer, self).__init__(client, service_name, "bluetooth-server", "Bluetooth", debug)
        self.inbound_ports = inbound_ports if inbound_ports is not None else [3]
        self.outbound_ports = outbound_ports if outbound_ports is not None else [4]

    def register(self, listener):
        if listener not in self.listeners:
            self.listeners.append(listener)

    def unregister(self, listener):
        self.listeners.remove(listener)

    def notify(self, message):
        for listener in self.listeners:
            listener.on_bluetooth_message(message)

    def send(self, message):
        self.buffer_outgoing.append(message)

    def outbound_looper(self, port):
        prctl.set_name(self.thread_name + " Out " + str(port))
        outbound_socket = BluetoothSocket(RFCOMM)
        outbound_socket.bind(('', port))
        outbound_socket.listen(1)
        self.sockets.append(outbound_socket)

        while not self.interrupted:
            self.logger.info("Waiting for outbound connection...")
            connection, address = outbound_socket.accept()
            self.connections.append(connection)
            self.logger.info("Outbound connection with: " + str(address))
            self.notify("BT:CONNECTED")

            try:
                while not self.interrupted:
                    if len(self.buffer_outgoing) > 0:
                        message = self.buffer_outgoing.pop(0)
                        self.logger.debug("Outbound message: >>>" + message + "<<<")
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
                            self.logger.debug("Outbound " + ack[0] + ": calculated=" + str(crc32_calculated) +
                                              ", received=" + ack[1] + " => " + str(crc32_calculated == long(ack[1])))
                            correctly_received = crc32_calculated == long(ack[1])
                            retries = retries + 1
                    else:
                        time.sleep(1)
            except BluetoothError as e:
                self.logger.error(e.message)
                # traceback.print_exc()
            finally:
                self.notify("BT:DISCONNECTED")
                connection.close()

        self.logger.info("Exiting outbound looper")

    def inbound_looper(self, port):
        prctl.set_name(self.thread_name + " In " + str(port))
        inbound_socket = BluetoothSocket(RFCOMM)
        inbound_socket.bind(('', port))
        inbound_socket.listen(1)
        self.sockets.append(inbound_socket)

        while not self.interrupted:
            self.logger.info("Waiting for inbound connection...")
            connection, address = inbound_socket.accept()
            self.connections.append(connection)
            self.logger.info("Inbound connection with: " + str(address))
            self.notify("BT:CONNECTED")
            incomplete = ""

            try:
                while not self.interrupted:
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
                            self.logger.debug("Inbound message: " + self.buffer_incoming)
                            self.notify(self.buffer_incoming)
                            crc32_calculated = crc32(self.buffer_incoming) % (1 << 32)
                            connection.send("ACK:" + str(crc32_calculated) + "\n")
                            self.buffer_incoming = ""
                        elif line == ENQ:
                            connection.send("IDD:" + self.service_name + "\n")
                        elif line.startswith(IDD + ":"):
                            self.notify("BT:" + line)
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
                # traceback.print_exc()
            finally:
                self.notify("BT:DISCONNECTED")
                connection.close()

        self.logger.info("Exiting inbound looper")

    def looper(self):
        threads = []

        for port in self.inbound_ports:
            thread = Thread(target=self.inbound_looper, args=[int(port)])
            thread.daemon = True
            thread.start()
            threads.append(thread)

        for port in self.outbound_ports:
            thread = Thread(target=self.outbound_looper, args=[int(port)])
            thread.daemon = True
            thread.start()
            threads.append(thread)

        try:
            while not self.interrupted:
                time.sleep(5)
        except:
            traceback.print_exc()
        finally:
            self.interrupted = True
            for connection in self.connections:
                try:
                    connection.shutdown(2)
                    connection.close()
                except BluetoothError as e:
                    self.logger.error(e.message)

            for s in self.sockets:
                try:
                    s.close()
                except:
                    traceback.print_exc()

            for thread in threads:
                thread.join(1)
