#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
from modules.Logger import Logger


class Module(object):
    finalizing = False

    def __init__(self, debug=False):
        self.logger = Logger(type(self).__name__, debug)

    def start(self):
        self.on_start()

    def stop(self):
        self.on_stop()

    def on_start(self):
        self.logger.debug("Starting...")
        pass

    def on_stop(self):
        self.logger.debug("Stopping...")
        pass

    def finalize(self):
        self.logger.debug("Finalizing...")
        self.finalizing = True
