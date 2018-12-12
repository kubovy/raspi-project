#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
from subprocess import call
from lib.ModuleMQTT import ModuleMQTT


class Camera(ModuleMQTT):
    """
    Camera switcher
    """

    def __init__(self, client, service_name, state_file="/run/camera.state", debug=False):
        super(Camera, self).__init__(client, service_name, "camera", debug)
        self.state_file = state_file

    def on_mqtt_message(self, path, payload):
        if payload == "ON":
            call(["/usr/local/bin/mjpeg-streamer", "start"])
        else:
            call(["/usr/local/bin/mjpeg-streamer", "stop"])
