#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import os
import subprocess

from lib.Module import Module


class RPI(Module):
    """Raspberry Pi essentials module"""

    module_mqtt = None

    def __init__(self, debug=False):
        super(RPI, self).__init__(debug=debug)

    def on_mqtt_message(self, path, payload):
        if len(path) == 1 and path[0] == "display":  # {service}/control/rpi/display
            self.__display(payload == "ON")

    def __display(self, state):
        if state:
            subprocess.call(["vcgencmd", "display_power", "1"])
            my_env = os.environ.copy()
            my_env["DISPLAY"] = ":0.0"
            subprocess.Popen(["sudo", "-u", "pi", "xset", "s", "activate"], env=my_env)
        else:
            subprocess.call(["vcgencmd", "display_power", "0"])

        if self.module_mqtt is not None:
            self.module_mqtt.publish("display", "ON" if state else "OFF", module=self)

        for listener in self.listeners:
            if hasattr(listener, 'on_display_change'):
                listener.on_display_change(state)
