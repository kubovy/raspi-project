import sys
import time
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO


def Color(red, green, blue, white = 0):
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.
    """
    return (white << 24) | (red << 8)| (green << 16) | blue


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # client.subscribe("$SYS/#")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unexpected disconnection.")


def pin_flip(pin):
    if GPIO.input(pin):
        print "PIN " + str(pin) + " = TRUE"
    else:
        print "PIN " + str(pin) + " = FALSE"


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

    if "pins" in modules:
        GPIO.setmode(GPIO.BCM)
        for pin in [5, 6, 7, 8, 9, 10, 20, 21, 22, 23, 24, 25]:
            GPIO.setup(pin, GPIO.IN)
            GPIO.add_event_detect(pin, GPIO.BOTH, callback=pin_flip)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Interrupting")

    if "ws281x" in modules:
        from neopixel import *

        # LED strip configuration:
        LED_PIN = 18  # GPIO pin connected to the pixels (18 uses PWM!).
        # LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
        LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
        LED_DMA = 10  # DMA channel to use for generating signal (try 10)
        LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
        LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
        LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53
        LED_STRIP = ws.WS2811_STRIP_GRB  # Strip type and colour ordering
        strip = Adafruit_NeoPixel(100, 18, 800000, 10, False, 255, 0, ws.WS2811_STRIP_GRB)
        strip.setPixelColor(0, Color(64, 0, 0))
        strip.setPixelColor(1, Color(0, 64, 0))
        strip.setPixelColor(2, Color(0, 0, 64))
        strip.setPixelColor(3, Color(64, 64, 0))
        strip.show()
    mqtt_client.disconnect()
