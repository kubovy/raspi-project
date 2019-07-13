import socket

import time
from prometheus_client import Gauge, start_http_server

from lib.ModuleLooper import ModuleLooper


class Prometheus(ModuleLooper):

    module_mqtt = None
    module_bluetooth = None
    module_camera = None
    module_dht11 = None
    module_motion_detector = None
    module_rgb = None
    module_rpi = None
    module_switch = None
    module_ultrasonic = None
    module_water_detector = None

    def __init__(self, port=11354, interval=15, debug=False):
        super(Prometheus, self).__init__(debug=debug)
        self.__port = port
        self.__interval = interval
        self.__host = socket.gethostname()
        self.__state_metric = Gauge("raspi_project_state", "Raspberry Pi project state", ['host', 'label'])
        self.__bluetooth_message_count_metric = Gauge("bluetooth_message_count", "Incoming Bluetooth messages counter",
                                                      ['host', 'type', 'device'])
        self.__camera_state_metric = Gauge("camera_state", "Camera state", ['host', 'label'])
        self.__temperature_metric = Gauge("temp", "Temperature", ['host', 'label'])
        self.__humidity_metric = Gauge("humidity", "Humidity", ['host', 'label'])
        self.__motion_state_metric = Gauge("motion_detector", "Camera state", ['host', 'label'])
        self.__rgb_state_metric = Gauge("rgb_strip", "RGB Strip", ['host', 'label', 'color'])
        self.__display_state_metric = Gauge("display_state", "Display state", ['host', 'label'])
        self.__switch_state_metric = Gauge("switch", "Switch", ['host', 'label'])
        self.__distance_metric = Gauge("ultrasonic_distance", "Ultrasonic distance", ['host', 'label'])
        self.__water_state_metric = Gauge("water_detector", "Camera state", ['host', 'label'])

    def initialize(self):
        start_http_server(self.__port)
        self.__state_metric.labels(host=self.__host, label="default").set(1)

    def finalize(self):
        self.__state_metric.labels(host=self.__host, label="default").set(0)

    def looper(self):
        self.__state_metric.labels(host=self.__host, label="default").set(1)
        time.sleep(self.__interval)

    def on_bluetooth_message(self, message):
        self.__bluetooth_message_count_metric.labels(host=self.__host, type='incoming', device='default').inc()

    def on_camera_switch(self, state):
        self.__camera_state_metric.labels(host=self.__host, label='default').set(1 if state else 0)

    def on_temperature_changed(self, temperature):
        try:
            self.__temperature_metric.labels(host=self.__host, label='dht11').set(temperature)
        except:
            self.logger.error("Invalid temperature '" + str(temperature) + "'")

    def on_humidity_changed(self, humidity):
        try:
            self.__humidity_metric.labels(host=self.__host, label='dht11').set(humidity)
        except:
            self.logger.error("Invalid humidity '" + str(humidity) + "'")

    def on_motion_change(self, state):
        self.__motion_state_metric.labels(host=self.__host, label='pir').set(1 if state else 0)

    def on_rgb_change(self, red, green, blue):
        self.__rgb_state_metric.labels(host=self.__host, label='default', color='red').set(red)
        self.__rgb_state_metric.labels(host=self.__host, label='default', color='green').set(green)
        self.__rgb_state_metric.labels(host=self.__host, label='default', color='blue').set(blue)

    def on_display_change(self, state):
        self.__display_state_metric.labels(host=self.__host, label='default').set(1 if state else 0)

    def on_switch_change(self, value):
        self.__switch_state_metric.labels(host=self.__host, label='default').set(value)

    def on_distance_change(self, distance):
        self.__distance_metric.labels(host=self.__host, label='default').set(distance)

    def on_water_change(self, state):
        self.__water_state_metric.labels(host=self.__host, label='mh').set(1 if state else 0)