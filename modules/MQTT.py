#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import paho.mqtt.client as mqtt

from lib.ModuleLooper import ModuleLooper
from lib.Util import to_snake_case


class MQTT(ModuleLooper):
    """MQTT Module"""

    __listeners = {}

    def __init__(self, client_id, host, port=1883, debug=False):
        super(MQTT, self).__init__(debug=debug)

        self.logger.debug("Client ID: " + client_id)
        self.client_id = client_id
        self.client = mqtt.Client(self.client_id)
        self.client.on_connect = self.__on_connect
        self.client.on_disconnect = self.__on_disconnect
        self.client.will_set(self.client_id + "/state/status", "CLOSED", 1, True)
        self.client.reconnect_delay_set(min_delay=1, max_delay=60)
        self.client.connect(host, port, 60)  # connect to broker
        self.client.publish("status", "OPEN", 1, True)
        self.client.on_message = self.__on_message

    def register(self, listener):
        module_id = to_snake_case(type(listener).__name__, "-")
        if module_id not in self.__listeners.keys():
            subscription = self.client_id + "/control/" + module_id + "/#"
            self.logger.debug("Subscribing " + module_id + " to MQTT topic: " + subscription)
            # self.client.message_callback_add(subscription, self.__on_message__)
            self.__listeners[module_id] = {'module': listener, 'subscription': subscription}
            # listener.__class__.publish = self.get_publish_method(module_name)

    def publish(self, topic, payload=None, qos=0, retrain=False, module=None):
        path = [self.client_id, 'state']
        if module is not None:
            path.append(module if isinstance(module, basestring) else to_snake_case(type(module).__name__))
        if topic is not None and topic != "":
            path.append(topic)
        self.logger.debug("Publishing: " + "/".join(path) + " qos=" + str(qos) + ", retain=" + str(retrain) + ": " +
                          payload)
        self.client.publish("/".join(path), payload, qos, retrain)

    def looper(self):
        self.client.loop_forever(retry_first_connection=True)

    def finalize(self):
        super(MQTT, self).finalize()
        for module_id in self.__listeners.keys():
            subscription = self.__listeners[module_id]['subscription']
            self.client.message_callback_remove(subscription)
            self.__listeners.pop(module_id, None)
        self.client.publish("status", "CLOSED", 1, True)
        self.logger.debug("Disconnecting from MQTT broker...")
        self.client.disconnect()

    def __on_connect(self, client, userdata, flags, rc):
        """The callback for when the client receives a CONNACK response from the server."""

        self.logger.info("Connected with result code " + str(rc))

        # Subscribing in __on_connect() means that if we lose the connection and reconnect then subscriptions will be
        # renewed.
        # client.subscribe("$SYS/#")
        client.subscribe(self.client_id + "/control/#")
        self.publish("status", "OPEN", 1, True)

    def __on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.logger.error("Unexpected disconnection with code " + str(rc) + ": " + str(userdata))

    def __on_message(self, client, userdata, msg):
        """The callback for when a PUBLISH message is received from the server."""
        try:
            self.logger.debug("Received " + msg.topic + ": '" + str(msg.payload) + "'")
            path = msg.topic.split("/")
            # payload = msg.payload
            # if len(path) == 2 and path[0] == self.client_id and path[1] == "control":
            #     if payload == "OFF":
            #         #  mqtt_client.disconnect()
            #         if hasattr(self, 'interrupted'):
            #             self.interrupted = True

            for module_name, listener in self.__listeners.items():
                if len(path) > 2 and path[0] == self.client_id and path[1] == "control" and path[2] == module_name:
                    if hasattr(listener['module'], 'on_mqtt_message'):
                        listener['module'].on_mqtt_message(path[3:], msg.payload)  # {service}/control/{module}/#
        except Exception as e:
            self.logger.error("Unexpected error: " + e.message)
