#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import math
import re
from threading import Timer
from time import *

from lib.I2CDevice import I2CDevice
from lib.ModuleLooper import *


class LCD(ModuleLooper):
    # commands
    LCD_CLEARDISPLAY = 0x01
    LCD_RETURNHOME = 0x02
    LCD_ENTRYMODESET = 0x04
    LCD_DISPLAYCONTROL = 0x08
    LCD_CURSORSHIFT = 0x10
    LCD_FUNCTIONSET = 0x20
    LCD_SETCGRAMADDR = 0x40
    LCD_SETDDRAMADDR = 0x80

    # flags for display entry mode
    LCD_ENTRYRIGHT = 0x00
    LCD_ENTRYLEFT = 0x02
    LCD_ENTRYSHIFTINCREMENT = 0x01
    LCD_ENTRYSHIFTDECREMENT = 0x00

    # flags for display on/off control
    LCD_DISPLAYON = 0x04
    LCD_DISPLAYOFF = 0x00
    LCD_CURSORON = 0x02
    LCD_CURSOROFF = 0x00
    LCD_BLINKON = 0x01
    LCD_BLINKOFF = 0x00

    # flags for display/cursor shift
    LCD_DISPLAYMOVE = 0x08
    LCD_CURSORMOVE = 0x00
    LCD_MOVERIGHT = 0x04
    LCD_MOVELEFT = 0x00

    # flags for function set
    LCD_8BITMODE = 0x10
    LCD_4BITMODE = 0x00
    LCD_2LINE = 0x08
    LCD_1LINE = 0x00
    LCD_5x10DOTS = 0x04
    LCD_5x8DOTS = 0x00

    # flags for backlight control
    LCD_BACKLIGHT = 0x08
    LCD_NOBACKLIGHT = 0x00

    En = 0b00000100  # Enable bit
    Rw = 0b00000010  # Read/Write bit
    Rs = 0b00000001  # Register select bit

    module_bluetooth = None
    module_mqtt = None
    module_serial_reader = None

    __message_queue = []

    def __init__(self, cols=20, rows=4, address=0x27, debug=False):
        super(LCD, self).__init__(debug=debug)
        self.__cols = cols
        self.__rows = rows

        self.__device = I2CDevice(address)
        self.__setup()

    def post(self, message, line=-1):
        """Posts a message to a message queue to be displayed on the LCD

        Message can take one of the following values:
            - `None`:  will clear the LCD
            - `True`:  will turn the LCD's backlight on
            - `False`: will turn the LCD's backlight off
            - "ON":    will turn the LCD's backlight on
            - "OFF":   will turn the LCD's backlight off
            - "RESET": will reset the LCD
            - `str` with `line`:
                - in the range between 1 and `rows`: will display the `message` on the `line` (truncated)
                - outside that range: will display the message on the whole display. Line are separated by new line
                  in the `message` string. Multiple messages can be displayed after each other with a pause between them
                  if the `message` takes the following format: "message1{:delay_in_ms:}message2...".

        :param message Message to be displayed
        :param line line which the message should be displayed. If outside the range of 1-`rows` then the whole screen
                    will be used.
        """
        if 1 <= line <= self.__rows and message is not None:
            self.__message_queue.append({'line': line, 'message': message})
        elif message is None:
            self.__message_queue.append(None)
        elif isinstance(message, bool):
            self.__message_queue.append(message)
        elif isinstance(message, str) and message.upper() in ["RESET", "ON", "OFF"]:
            self.__message_queue.append(message)
        elif isinstance(message, list):
            for part in message:
                if isinstance(part, str):
                    for i, s in enumerate(part.splitlines()):
                        if i < self.__rows:
                            self.__message_queue.append({'line': i + 1, 'message': s})
                elif isinstance(part, int):
                    self.__message_queue.append(part)
        elif message is not None:
            self.__message_queue.append(None)
            for m in message.split(":}"):
                parts = m.split("{:", 2)
                for i, s in enumerate(parts[0].splitlines()):
                    if i < self.__rows:
                        self.__message_queue.append({'line': i + 1, 'message': s})
                if len(parts) == 2:
                    self.__message_queue.append(int(parts[1]))

    def clear_queue(self):
        """Clears the messge queue"""
        self.__message_queue = []

    def backlight(self, state):
        """Turn on/off the LCD backlight"""
        if isinstance(state, bool):
            self.__device.write_cmd(self.LCD_BACKLIGHT if state else self.LCD_NOBACKLIGHT)
        elif isinstance(state, str) and str(state).lower() == "on":
            self.__device.write_cmd(self.LCD_BACKLIGHT)
        elif isinstance(state, str) and str(state).lower() == "off":
            self.__device.write_cmd(self.LCD_NOBACKLIGHT)
        else:
            print("Unknown State!")

    def reset(self):
        """Reset the LCD"""
        self.clear()
        self.backlight(False)

    def clear(self):
        """Clear LCD and set to home"""
        self.__write(self.LCD_CLEARDISPLAY)
        self.__write(self.LCD_RETURNHOME)

    def finalize(self):
        super(LCD, self).finalize()
        self.reset()

    def looper(self):
        if len(self.__message_queue) > 0:
            message = self.__message_queue.pop(0)
            if message is None:
                self.clear()
            elif isinstance(message, bool):
                self.backlight(message)
            elif isinstance(message, str) and message.upper() in ["ON", "OFF"]:
                self.backlight(message.upper() == "ON")
            elif isinstance(message, int):
                sleep(message / 1000.0)
            elif isinstance(message, float):
                sleep(message)
            elif isinstance(message, str) and message.upper() == "RESET":
                self.__setup()
                self.clear()
            elif isinstance(message, dict) and 'line' in message.keys() and 'message' in message.keys():
                self.__set_line(message['message'], int(message['line']))
            else:
                self.logger.debug("Unknown message: " + str(message))
            sleep(0.1)
        else:
            sleep(0.5)

    def on_mqtt_message(self, path, payload):
        if len(path) == 1 and path[0] == "clear":
            self.clear()
        elif len(path) == 1 and path[0] == "reset":
            self.logger.debug("Reseting LCD")
            self.__setup()
            self.clear()
        elif len(path) == 1 and path[0] == "backlight":
            self.backlight(payload)
        elif len(path) == 1:
            try:
                self.__set_line(payload, int(path[0]))
            except:
                self.logger.error('Oops!')
                traceback.print_exc()
        else:
            try:
                self.logger.debug("MESSAGE: " + payload)
                self.__set(payload)
            except:
                self.logger.error('Oops!')
                traceback.print_exc()

    def on_bluetooth_message(self, message):
        parts = message.split(":", 2)  # Anybody can reset a display
        if len(parts) == 2 and parts[1] == "LCD_RESET":
            self.logger.debug("Reseting LCD")
            self.__setup()
            self.clear()

    def on_serial_message(self, message):
        try:
            pass  # TODO JK
        except ValueError:
            self.logger.error('Oops!  That was no valid JSON.  Try again...')
            traceback.print_exc()

    def __setup(self):
        self.__write(0x03)
        self.__write(0x03)
        self.__write(0x03)
        self.__write(0x02)

        self.__write(self.LCD_FUNCTIONSET | self.LCD_2LINE | self.LCD_5x8DOTS | self.LCD_4BITMODE)
        self.__write(self.LCD_DISPLAYCONTROL | self.LCD_DISPLAYON)
        self.__write(self.LCD_CLEARDISPLAY)
        self.__write(self.LCD_ENTRYMODESET | self.LCD_ENTRYLEFT)
        sleep(0.2)
        self.backlight(False)

    # clocks EN to latch command
    def __strobe(self, data):
        self.__device.write_cmd(data | self.En | self.LCD_BACKLIGHT)
        sleep(.0005)
        self.__device.write_cmd(((data & ~self.En) | self.LCD_BACKLIGHT))
        sleep(.0001)

    def __write_four_bits(self, data):
        self.__device.write_cmd(data | self.LCD_BACKLIGHT)
        self.__strobe(data)

    # write a command to lcd
    def __write(self, cmd, mode=0):
        self.__write_four_bits(mode | (cmd & 0xF0))
        self.__write_four_bits(mode | ((cmd << 4) & 0xF0))

    def __set(self, string):
        if string is not None:
            messages = string.split(":}")
            message = messages[0].split("{:", 2)
            for i, line in enumerate(message[0].splitlines()):
                if i < self.__rows:
                    self.__set_line(line, i + 1)
            if len(message) == 2 and len(messages) > 1:
                Timer(int(message[1]) / 1000.0, self.__set, args=["".join(messages[1:])]).start()

    def __set_line(self, string, line):
        if line == 1:
            self.__write(0x80)
        if line == 2:
            self.__write(0xC0)
        if line == 3:
            self.__write(0x94)
        if line == 4:
            self.__write(0xD4)

        alignment = re.search(r'^\|c\|(.*)', string, re.I)
        if alignment:
            string = alignment.group(1)
        string = (string[:(self.__cols - 2)] + "..") if len(string) > self.__cols else string
        if alignment:
            string = string.rjust(int(math.floor((self.__cols - len(string)) / 2)) + len(string))
        string = string.ljust(self.__cols)

        for char in string:
            self.__write(ord(char), self.Rs)
