#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import subprocess
from threading import *
from ModuleMQTT import ModuleMQTT


class Check(object):
    def __init__(self, topic, command, interval=10):
        self.topic = topic
        self.command = command
        self.interval = interval


class Commander(ModuleMQTT):
    def __init__(self, client, service_name, checks=None, debug=False):
        super(Commander, self).__init__(client, service_name, "commander", debug)
        self.checks = [] if checks is None else checks
        for check in self.checks:
            Timer(check.interval, self.trigger, [check]).start()

    def on_message(self, path, payload):
        if len(path) > 0:               # {service}/control/{module}
            result = subprocess.Popen('/usr/local/bin/' + path + ' ' + payload,
                                      stdout=subprocess.PIPE,
                                      shell=True).communicate()[0].strip()
            if result is not None and result != '':
                self.publish(path, result, 1)

    def trigger(self, check):
        result = subprocess.Popen('/usr/local/bin/' + check.command,
                                  stdout=subprocess.PIPE,
                                  shell=True).communicate()[0].strip()
        if result is not None and result != '':
            self.publish(check.topic, result, 1)
        Timer(check.interval, self.trigger, [check]).start()
