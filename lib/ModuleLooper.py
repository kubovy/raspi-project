#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import prctl
import threading
import time
import traceback

from lib.Module import Module
from lib.Util import to_snake_case


class ModuleLooper(Module):
    """Looper module providing a simple thread management"""

    __interrupted = False
    __thread = None

    module_mqtt = None

    def __init__(self, **kwargs):
        super(ModuleLooper, self).__init__(**kwargs)
        self.thread_name = to_snake_case(type(self).__name__, " ", None)

    def start(self):
        """Starts the looper.

        Only starts a looper if not already running.

        This should be overwritten only for changing the start behavior, to add on start behavior override `on_start`
        method.
        """
        if self.module_mqtt is not None:
            self.module_mqtt.publish("state", "OFF", module=self)

        if self.__thread is None:
            self.on_start()
            if self.module_mqtt is not None:
                self.module_mqtt.publish("state", "ON", module=self)
            self.__interrupted = False
            self.__thread = threading.Thread(target=self.__looper__)
            self.__thread.daemon = True
            self.__thread.start()
        return self.__thread

    def stop(self):
        """Stops the looper.

        Tries to do so gracefully by setting `interrupted` to `True`.
        """
        self.__interrupted = True
        if self.__thread is not None:
            self.on_stop()
            if self.module_mqtt is not None:
                self.module_mqtt.publish("state", "OFF", module=self)
            self.__thread.join(5)

        self.__thread = None

    def finalize(self):
        super(ModuleLooper, self).finalize()
        self.__interrupted = True

    def on_mqtt_message(self, path, payload):
        if len(path) > 0 and path[0] == "state":  # {service}/control/{module}/state
            if payload == "ON":
                self.start()
            else:
                self.stop()

    def is_interrupted(self):
        """Checks if looper was interrupted"""
        return self.__interrupted

    def is_running(self):
        """Checks if looper is still running"""
        return self.__thread is not None

    def looper(self):
        """Looper method to be overwritten by modules.

        The loop condition and rough exception handling is already done. This method will be periodically triggered
        until `interrupted` is set to `True`.
        """
        self.logger.info("Looper not implemented!")
        time.sleep(5)

    def __looper__(self):
        prctl.set_name(self.thread_name)
        while not self.__interrupted:
            try:
                self.looper()
            except:
                self.logger.error("Unexpected Error!")
                traceback.print_exc()
        self.__thread = None
        self.logger.info("Exiting looper")
