import sys
import time
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # client.subscribe("$SYS/#")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unexpected disconnection.")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Only " + str(len(sys.argv)) + " parameter given")
        sys.exit(2)

    broker = sys.argv[1].split(":")
    client_id = sys.argv[2]
    modules = sys.argv[3].split(",")

    broker_host = broker[0]
    broker_port = int(broker[1]) if len(broker) > 1 else 1883

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.reconnect_delay_set(min_delay=1, max_delay=60)
    mqtt_client.connect(broker_host, broker_port)  # connect to broker

    if "rgb" in modules:
        print "RGB white"
        mqtt_client.publish(client_id + "/control/rgb", "255,255,255")
        time.sleep(1)
        print "RGB red"
        mqtt_client.publish(client_id + "/control/rgb", "255,0,0")
        time.sleep(1)
        print "RGB green"
        mqtt_client.publish(client_id + "/control/rgb", "0,255,0")
        time.sleep(1)
        print "RGB blue"
        mqtt_client.publish(client_id + "/control/rgb", "0,0,255")
        time.sleep(1)
        print "RGB off"
        mqtt_client.publish(client_id + "/control/rgb", "0,0,0")
        time.sleep(1)

    if "motion-detector" in modules:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(7, GPIO.IN)
        try:
            while True:
                if GPIO.input(7):
                    print("Motion Detected...")
                else:
                    print("No Motion")
                time.sleep(1)
        except KeyboardInterrupt:
            print("Interrupting")

    if "water-detector" in modules:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(23, GPIO.IN)
        try:
            while True:
                if GPIO.input(23):
                    print("Dry")
                else:
                    print("Water Detected...")
                time.sleep(1)
        except KeyboardInterrupt:
            print("Interrupting")

    mqtt_client.disconnect()