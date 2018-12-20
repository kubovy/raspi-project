#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
from lib.Logger import Logger


class Module(object):
    """Top module abstraction"""

    finalizing = False
    listeners = []

    def __init__(self, **kwargs):
        self.logger = Logger(type(self).__name__, kwargs['debug'] if 'debug' in kwargs.keys() else False)

    def initialize(self):
        self.logger.debug("Initializing...")

    def register(self, listener):
        """Register a listener."""
        self.logger.debug("Registring: " + str(listener))
        if listener not in self.listeners:
            self.listeners.append(listener)

    def start(self):
        """Module's start trigger.

        This should be overwritten only for changing the start behavior, to add on start behavior override `on_start`
        method.
        """
        self.reset()
        self.on_start()

    def stop(self):
        """Module's stop trigger.

        This should be overwritten only for changing the stop behavior, to add on stop behavior override `on_stop`
        method.
        """
        self.on_stop()

    def reset(self):
        """Resets the modules. This is also called when module is started"""
        self.logger.debug("Resetting...")
        pass

    def on_start(self):
        """Module's on start callback."""
        self.logger.debug("Starting...")
        pass

    def on_stop(self):
        """Module's on stop callback."""
        self.logger.debug("Stopping...")
        pass

    def finalize(self):
        """Final cleanup before unloading the module."""
        self.logger.debug("Finalizing...")
        self.listeners = []
        self.finalizing = True
