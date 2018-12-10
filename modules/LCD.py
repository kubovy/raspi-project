# Author: Jan Kubovy (jan@kubovy.eu)
from ModuleLooper import *
from lib.I2CDevice import I2CDevice
from time import *


class LCD(ModuleMQTT):
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

    interrupted = False

    serial_reader = None

    def __init__(self, client, service_name, cols=20, rows=4, address=0x27, debug=False):
        super(LCD, self).__init__(client, service_name, "lcd", debug)
        self.cols = cols
        self.rows = rows

        self.device = I2CDevice(address)

        self.write(0x03)
        self.write(0x03)
        self.write(0x03)
        self.write(0x02)

        self.write(self.LCD_FUNCTIONSET | self.LCD_2LINE | self.LCD_5x8DOTS | self.LCD_4BITMODE)
        self.write(self.LCD_DISPLAYCONTROL | self.LCD_DISPLAYON)
        self.write(self.LCD_CLEARDISPLAY)
        self.write(self.LCD_ENTRYMODESET | self.LCD_ENTRYLEFT)
        sleep(0.2)

    def on_start(self):
        if self.serial_reader is not None:
            self.serial_reader.register(self)

    def on_stop(self):
        if self.serial_reader is not None:
            self.serial_reader.unregister(self)

    def on_mqtt_message(self, path, payload):
        if len(path) == 1 and path[0] == "clear":
            self.clear()
        elif len(path) == 1 and path[0] == "backlight":
            self.backlight(payload)
        elif len(path) == 1:
            try:
                self.set_line(payload, int(path[0]))
            except:
                self.logger.error('Oops!')
                traceback.print_exc()
        else:
            try:
                self.logger.debug("MESSAGE: " + payload)
                self.set(payload)
            except:
                self.logger.error('Oops!')
                traceback.print_exc()

    def on_serial_message(self, message):
        try:
            pass  # TODO JK
        except ValueError:
            self.logger.error('Oops!  That was no valid JSON.  Try again...')
            traceback.print_exc()

        # clocks EN to latch command

    def strobe(self, data):
        self.device.write_cmd(data | self.En | self.LCD_BACKLIGHT)
        sleep(.0005)
        self.device.write_cmd(((data & ~self.En) | self.LCD_BACKLIGHT))
        sleep(.0001)

    def write_four_bits(self, data):
        self.device.write_cmd(data | self.LCD_BACKLIGHT)
        self.strobe(data)

    # write a command to lcd
    def write(self, cmd, mode=0):
        self.write_four_bits(mode | (cmd & 0xF0))
        self.write_four_bits(mode | ((cmd << 4) & 0xF0))

    # turn on/off the lcd backlight
    def backlight(self, state):
        if state.lower() == "on":
            self.device.write_cmd(self.LCD_BACKLIGHT)
        elif state.lower() == "off":
            self.device.write_cmd(self.LCD_NOBACKLIGHT)
        else:
            print("Unknown State!")

    def set(self, string):
        if string is not None:
            for i, line in enumerate(string.splitlines()):
                if i < self.rows:
                    self.set_line(line, i + 1)

    def set_line(self, string, line):
        if line == 1:
            self.write(0x80)
        if line == 2:
            self.write(0xC0)
        if line == 3:
            self.write(0x94)
        if line == 4:
            self.write(0xD4)

        string = ((string[:(self.cols - 2)] + "..") if len(string) > self.cols else string).ljust(self.cols)
        for char in string:
            self.write(ord(char), self.Rs)

    # clear lcd and set to home
    def clear(self):
        self.write(self.LCD_CLEARDISPLAY)
        self.write(self.LCD_RETURNHOME)
