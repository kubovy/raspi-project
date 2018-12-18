#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import subprocess
import time
import traceback
from subprocess import call

from lib.ModuleLooper import ModuleLooper


class Camera(ModuleLooper):
    """Camera switcher module"""

    module_mqtt = None

    __last_state = None

    def __init__(self, state_file="/run/camera.state", debug=False):
        super(Camera, self).__init__(debug=debug)
        self.__state_file = state_file

    def looper(self):
        try:
            result = subprocess.Popen('/usr/local/bin/mjpeg-streamer status',
                                      stdout=subprocess.PIPE,
                                      shell=True).communicate()[0].strip()
            state = result.endswith("running")
            if self.__last_state != state:
                if self.module_mqtt is not None:
                    self.module_mqtt.publish("", "ON" if state else "OFF", module=self)
        except:
            self.logger.error("Unexpected Error!")
            traceback.print_exc()
        time.sleep(5.0)

    def on_mqtt_message(self, path, payload):
        if payload == "ON":
            call(["/usr/local/bin/mjpeg-streamer", "start"])
        else:
            call(["/usr/local/bin/mjpeg-streamer", "stop"])
