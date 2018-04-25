#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import subprocess
import traceback
from threading import *
from ModuleMQTT import ModuleMQTT


class Check(object):
    def __init__(self, command, interval=10):
        self.command = command
        self.interval = interval


class Commander(ModuleMQTT):
    timer_map = {}

    def __init__(self, client, service_name, checks=None, debug=False):
        super(Commander, self).__init__(client, service_name, "commander", debug)
        self.checks = [] if checks is None else checks
        for check in self.checks:
            self.trigger(check)

    def on_message(self, path, payload):
        if len(path) > 0:                                                      # {service}/control/{module}
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
        timer = Timer(check.interval, self.trigger, [check])
        self.timer_map[check.command] = timer
        timer.start()

    def __process_result(self, result):
        if result is not None and result != '':
            for line in result.splitlines():
                try:
                    parts = line.split(":", 1)
                    self.publish(parts[0], parts[1], 1)
                except:
                    self.logger.error("Unexpected Error!")
                    traceback.print_exc()

    def finalize(self):
        for key in self.timer_map.keys():
            self.logger.debug("Timer " + key + " = " + str(self.timer_map[key]))
            if self.timer_map[key] is not None: self.timer_map[key].cancel()