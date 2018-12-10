#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import os
import time
import traceback


class Logger:

    def __init__(self, name, debug=False, log_file="/var/log/raspi-project.log"):
        self.name = name
        self.isDebugging = debug
        self.log_file = log_file
        if os.path.exists(log_file):
            try:
                os.remove(log_file)
            except OSError:
                traceback.print_exc()
        
    def debug(self, message):
        if self.isDebugging: self.__log__(time.ctime() + " DEBUG [" + self.name + "]: " + message)

    def info(self, message):
        self.__log__(time.ctime() + " INFO [" + self.name + "]: " + message)
        
    def error(self, message):
        self.__log__(time.ctime() + " ERROR [" + self.name + "]: " + message)

    def __log__(self, raw_message):
        print(raw_message)
        try:
            with open(self.log_file, "a+") as fp:
                fp.write(raw_message)
        except:
            traceback.print_exc()
