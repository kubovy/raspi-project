#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import subprocess
import traceback
from threading import *
from lib.ModuleMQTT import ModuleMQTT


class Check(object):
    def __init__(self, command, interval=10):
        self.command = command
        self.interval = interval


class Commander(ModuleMQTT):
    timer_map = {}
    last_values = {}

    def __init__(self, client, service_name, checks=None, debug=False):
        super(Commander, self).__init__(client, service_name, "commander", debug)
        self.checks = [] if checks is None else checks
        for check in self.checks:
            self.trigger(check)

    def on_mqtt_message(self, path, payload):
        if len(path) > 0:                                                      # {service}/control/commander
            if len(path) == 1 and path[0] == "shutdown":                       # {service}/control/commander/shutdown
                subprocess.call(["shutdown", "now"])
            elif len(path) == 1 and path[0] == "restart":                      # {service}/control/commander/restart
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

    def trigger(self, check):
        try:
            result = subprocess.Popen('/usr/local/bin/mqtt-cli ' + check.command,
                                      stdout=subprocess.PIPE,
                                      shell=True).communicate()[0].strip()
            self.__process_result(result)
        except:
            self.logger.error("Unexpected Error!")
            traceback.print_exc()
        if not self.finalizing:
            timer = Timer(check.interval, self.trigger, [check])
            self.timer_map[check.command] = timer
            timer.start()

    def __process_result(self, result):
        if result is not None and result != '':
            for line in result.splitlines():
                try:
                    parts = line.split(":", 1)
                    if parts[0] not in self.last_values.keys() or parts[1] != self.last_values[parts[0]]:
                        self.last_values[parts[0]] = parts[1]
                        self.publish(parts[0], parts[1], 1)
                except:
                    self.logger.error("Unexpected Error!")
                    traceback.print_exc()

    def finalize(self):
        super(Commander, self).finalize()
        for key in self.timer_map.keys():
            self.logger.debug("Timer " + key + " = " + str(self.timer_map[key]))
            if self.timer_map[key] is not None: self.timer_map[key].cancel()
