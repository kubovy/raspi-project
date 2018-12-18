#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import prctl
import subprocess
import traceback
from threading import *

from lib.Module import Module


class Check(object):
    def __init__(self, command, interval=10):
        self.command = command
        self.interval = interval


class Commander(Module):
    """Commander module"""

    module_mqtt = None

    __timer_map = {}
    __last_values = {}

    def __init__(self, checks=None, debug=False):
        super(Commander, self).__init__(debug=debug)
        for check in [] if checks is None else checks:
            self.__enqueue(check)

    def on_mqtt_message(self, path, payload):
        if len(path) > 0:  # {service}/control/commander
            if len(path) == 1 and path[0] == "shutdown":  # {service}/control/commander/shutdown
                subprocess.call(["shutdown", "now"])
            elif len(path) == 1 and path[0] == "restart":  # {service}/control/commander/restart
                subprocess.call(["reboot"])
            else:
                try:
                    result = subprocess.Popen('/usr/local/bin/mqtt-cli ' + path.join(" ") + ' ' + payload,
                                              stdout=subprocess.PIPE,
                                              shell=True).communicate()[0].strip()
                    self.__process_result(result)
                except:
                    self.logger.error("Unexpected Error!")
                    traceback.print_exc()

    def finalize(self):
        super(Commander, self).finalize()
        for key in self.__timer_map.keys():
            self.logger.debug("Timer " + key + " = " + str(self.__timer_map[key]))
            if self.__timer_map[key] is not None:
                self.__timer_map[key].cancel()

    def __enqueue(self, check):
        timer = Timer(check.interval, self.__trigger, [check])
        self.__timer_map[check.command] = timer
        timer.daemon = True
        timer.start()

    def __trigger(self, check):
        prctl.set_name(Commander.__name__)
        try:
            result = subprocess.Popen('/usr/local/bin/mqtt-cli ' + check.command,
                                      stdout=subprocess.PIPE,
                                      shell=True).communicate()[0].strip()
            self.__process_result(result)
        except:
            self.logger.error("Unexpected Error!")
            traceback.print_exc()
        if not self.finalizing:
            self.__enqueue(check)

    def __process_result(self, result):
        if result is not None and result != '':
            for line in result.splitlines():
                try:
                    parts = line.split(":", 1)
                    if parts[0] not in self.__last_values.keys() or parts[1] != self.__last_values[parts[0]]:
                        self.__last_values[parts[0]] = parts[1]
                        if self.module_mqtt is not None:
                            self.module_mqtt.publish(parts[0], parts[1], module=self)
                except:
                    self.logger.error("Unexpected Error!")
                    traceback.print_exc()
