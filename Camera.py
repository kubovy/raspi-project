#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import os
import pyinotify
from subprocess import call
from ModuleMQTT import ModuleMQTT


class EventHandler(pyinotify.ProcessEvent):
    def __init__(self, camera):
        super(EventHandler, self).__init__()
        self.camera = camera
        self.process()

    def process(self):
        state = "-1"
        if os.path.exists(self.camera.state_file):
            stream = open(self.camera.state_file, "r")
            state = stream.readline().strip()
        # self.camera.logger.debug(self.camera.state_file + ": " + state)
        if state == "1":
            self.camera.publish("", "ON", 1, True)
        else:
            self.camera.publish("", "OFF", 1, True)

    def process_IN_CREATE(self, event):
        self.camera.logger.info("Created: " + event.pathname)
        self.process()

    def process_IN_MODIFY(self, event):
        self.camera.logger.info("Modified: " + event.pathname)
        self.process()

    def process_IN_DELETE(self, event):
        self.camera.logger.info("Removed: " + event.pathname)
        self.process()


class Camera(ModuleMQTT):
    """
    Camera switcher
    """

    def __init__(self, client, service_name, state_file="/run/camera.state", debug=False):
        super(Camera, self).__init__(client, service_name, "camera", debug)
        self.state_file = state_file
        self.watch_manager = pyinotify.WatchManager()
        watch_mask = pyinotify.IN_CREATE | pyinotify.IN_MODIFY | pyinotify.IN_DELETE  # watched events
        event_handler = EventHandler(self)
        event_handler.process()
        self.notifier = pyinotify.ThreadedNotifier(self.watch_manager, event_handler)
        self.wdd = self.watch_manager.add_watch(state_file, watch_mask)
        self.notifier.start()

    def on_mqtt_message(self, path, payload):
        if payload == "ON":
            call(["/usr/local/bin/mjpeg-streamer", "start"])
        else:
            call(["/usr/local/bin/mjpeg-streamer", "stop"])

    def finalize(self):
        super(Camera, self).finalize()
        self.watch_manager.rm_watch(self.wdd.values())
        self.notifier.stop()
