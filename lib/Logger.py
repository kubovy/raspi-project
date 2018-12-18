#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import os
import time
import traceback
import syslog


class Logger:
    """The Logger"""

    def __init__(self, name, debug=False, use_syslog=True, log_file="/var/log/raspi-project.log"):
        """Constructor

        :param name: label or name of the module
        :param debug: whether debug messages should be shown
        :param use_syslog: whether to log into syslog
        :param log_file: file to log to, if `None` no log file is used
        """
        self.name = name
        self.isDebugging = debug
        self.log_file = log_file
        self.use_syslog = use_syslog
        if self.use_syslog:
            syslog.openlog(self.name + " ", logoption=syslog.LOG_PID, facility=syslog.LOG_LOCAL7)

        if self.log_file is not None and os.path.exists(self.log_file):
            try:
                os.remove(self.log_file)
            except OSError:
                traceback.print_exc()
        
    def debug(self, message):
        """Debug log"""
        if self.isDebugging:
            self.__log__(syslog.LOG_DEBUG, "DEBUG", message)

    def info(self, message):
        """Info log"""
        self.__log__(syslog.LOG_INFO, "INFO", message)

    def warn(self, message):
        """Warning log"""
        self.__log__(syslog.LOG_WARNING, "WARN", message)

    def error(self, message):
        """Error log"""
        self.__log__(syslog.LOG_ERR, "ERROR", message)

    def exception(self, message):
        """Exception log"""
        self.__log__(syslog.LOG_CRIT, "CRITICAL", message)
        raise Exception(message)

    def __log__(self, priority, priority_text, message):
        full_message = time.ctime() + " " + priority_text.ljust(8) + "[" + self.name.ljust(18) + "]: " + message
        print(full_message)
        if self.use_syslog and priority <= syslog.LOG_INFO:
            syslog.syslog(priority, message)
        if self.log_file is not None:
            try:
                with open(self.log_file, "a+") as fp:
                    fp.write(full_message + "\n")
            except:
                traceback.print_exc()
