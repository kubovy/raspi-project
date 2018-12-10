#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import os
import time
import traceback
import syslog


class Logger:

    def __init__(self, name, debug=False, log_file="/var/log/raspi-project.log"):
        self.name = name
        self.isDebugging = debug
        self.log_file = log_file
        syslog.openlog(self.name + " ", logoption=syslog.LOG_PID, facility=syslog.LOG_LOCAL7)
        if os.path.exists(log_file):
            try:
                os.remove(log_file)
            except OSError:
                traceback.print_exc()
        
    def debug(self, message):
        if self.isDebugging: self.__log__(time.ctime() + " DEBUG [" + self.name + "]: " + message)
        # syslog.syslog(syslog.LOG_DEBUG, message)

    def info(self, message):
        self.__log__(time.ctime() + " INFO [" + self.name + "]: " + message)
        syslog.syslog(syslog.LOG_INFO, message)

    def warn(self, message):
        self.__log__(time.ctime() + " WARN [" + self.name + "]: " + message)
        syslog.syslog(syslog.LOG_WARNING, message)

    def error(self, message):
        self.__log__(time.ctime() + " ERROR [" + self.name + "]: " + message)
        syslog.syslog(syslog.LOG_ERR, message)

    def __log__(self, raw_message):
        print(raw_message)
        try:
            with open(self.log_file, "a+") as fp:
                fp.write(raw_message)
        except:
            traceback.print_exc()
