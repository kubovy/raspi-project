#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import traceback
import paho.mqtt.client as mqtt

from Module import Module


class ModuleMQTT(Module):

    def __init__(self, client, service_name, module_name, debug=False):
        super(ModuleMQTT, self).__init__(debug)
        self.client = client
        self.service_name = service_name
        self.module_name = module_name
        self.subscription = self.service_name + "/control/" + module_name + "/#"
        self.logger.debug("Subcribing to MQTT topic: " + self.subscription)

        self.client.message_callback_add(self.subscription, self.__on_message__)

    def on_stop(self):
        super(ModuleMQTT, self).on_stop()
        self.client.message_callback_remove(self.subscription)

    def publish(self, topic, payload=None, qos=0, retrain=False):
        if topic != "": topic = "/" + topic
        # self.logger.debug(self.service_name + "/state/" + self.module_name + topic
        #                  + " qos=" + str(qos) + ", retain="  + str(retrain) + ": " + payload)
        self.client.publish(self.service_name + "/state/" + self.module_name + topic, payload, qos, retrain)

    def on_mqtt_message(self, path, payload):
        self.logger.info("Message: " + "/".join(path) + ": " + payload)

    def __on_message__(self, client, userdata, msg):
        self.logger.info(msg.topic + ": " + msg.payload)
        try:
            path = msg.topic.split("/")
            if len(path) > 2 and path[0] == self.service_name and path[1] == "control" and path[2] == self.module_name:
                    self.on_mqtt_message(path[3:], msg.payload)  # {service}/control/{module}/#
        except:
            self.logger.error("Unexpected Error!")
            traceback.print_exc()


def create_mqtt_client(broker_address, broker_port, client_id, clean_session=True, userdata=None, protocol=mqtt.MQTTv311,
                       transport="tcp", on_connect=None, on_disconnect=None):
    mqtt_client = mqtt.Client(client_id, clean_session, userdata, protocol, transport)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.will_set(client_id + "/state/status", "CLOSED", 1, True)
    mqtt_client.reconnect_delay_set(min_delay=1, max_delay=60)
    mqtt_client.connect(broker_address, broker_port, 60)  # connect to broker
    mqtt_client.publish(client_id + "/state/status", "OPEN", 1, True)
    return mqtt_client
