#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import os
import subprocess
from lib.ModuleMQTT import ModuleMQTT


class RPI(ModuleMQTT):

    def __init__(self, client, service_name, debug=False):
        super(RPI, self).__init__(client, service_name, "rpi", debug)

    def on_mqtt_message(self, path, payload):
        if len(path) == 1 and path[0] == "display":                              # {service}/control/commander/display
            if payload == "ON":
                subprocess.call(["vcgencmd", "display_power", "1"])
                my_env = os.environ.copy()
                my_env["DISPLAY"] = ":0.0"
                subprocess.Popen(["sudo", "-u", "pi", "xset", "s", "activate"], env=my_env)
                self.publish("display", "ON", 1)
            else:
                subprocess.call(["vcgencmd", "display_power", "0"])
                self.publish("display", "OFF", 1)
