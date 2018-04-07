#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import sys
import getopt
import RPi.GPIO as GPIO
from neopixel import *

from Logger import Logger
from ModuleMQTT import *

from Buzzer import Buzzer
from InfraredReceiver import InfraredReceiver
from InfraredSensor import InfraredSensor
from Joystick import Joystick
from MotionDetector import MotionDetector
from ObstacleAvoidance import ObstacleAvoidance
from Pixels import Pixels
from RGB import RGB
from SerialReader import SerialReader
from Servo import Servo
from TrackingSensor import TrackingSensor
from Ultrasonic import Ultrasonic
from WaterDetector import WaterDetector
from Wheels import Wheels
from WS281x import WS281x


debug          = False
logger         = Logger("MAIN", debug)
mqtt_client    = None
client_id      = None
modules        = []

# Buzzer
buzzer_pin = 4

# Camera Servo
servo_roll_min = 750
servo_roll_mid = 1750
servo_roll_max = 2750
# servo_roll_deg = float(servo_roll_max - servo_roll_min) / 180.0
servo_pitch_min = 1150
servo_pitch_mid = 2100
servo_pitch_max = 2800
# servo_pitch_deg = servo_roll_deg

# Infraread Receiver
ir_receiver_pin = 17

# Infrared Sensor
ir_sensor_pins = [19, 16]

# Joystick
joystick_pin_center = 7
joystick_pin_a      = 8
joystick_pin_b      = 9
joystick_pin_c      = 10
joystick_pin_d      = 11

# Motion Detector
motion_detector_pin = 7

# Pixels
pixels_pin   = 18
pixels_count = 4

# Serial Reader
serial_reader_start = False
serial_reader_ports = []

# Ultrasonic
ultrasonic_pin_trigger = 22
ultrasonic_pin_echo    = 27

# Water Detector
water_detector_pin = 23

# Wheels
wheels_pin_right_forward  = 13
wheels_pin_right_backward = 12
wheels_pin_right_enabled  = 6
wheels_pin_left_forward   = 21
wheels_pin_left_backward  = 20
wheels_pin_left_enabled   = 26

# WS281x
ws281x_start = False
ws281x_startup_file = None


def initialize(module_names):
    global modules

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(debug)

    logger.info("Loading modules: " + str(module_names))
    for module_name in module_names:
        if module_name == "buzzer":
            modules.append(Buzzer(mqtt_client, client_id, pin=buzzer_pin, debug=debug))
        elif module_name == "camera-servo":
            modules.append(Servo(mqtt_client, client_id,
                                 servo_mins=[servo_roll_min, servo_pitch_min],
                                 servo_mids=[servo_roll_mid, servo_pitch_mid],
                                 servo_maxs=[servo_roll_max, servo_pitch_max],
                                 degree_span=180.0,
                                 debug=debug))
        elif module_name == "infrared-receiver":
            modules.append(InfraredReceiver(mqtt_client, client_id, pin=ir_receiver_pin, debug=debug))
        elif module_name == "infrared-sensor":
            modules.append(InfraredSensor(mqtt_client, client_id, pins=ir_sensor_pins, debug=debug))
        elif module_name == "joystick":
            modules.append(Joystick(mqtt_client, client_id,
                                    pin_center=joystick_pin_center,
                                    pin_a=joystick_pin_a,
                                    pin_b=joystick_pin_b,
                                    pin_c=joystick_pin_c,
                                    pin_d=joystick_pin_d,
                                    debug=debug))
        elif module_name == "motion-detector":
            modules.append(MotionDetector(mqtt_client, client_id, pin=motion_detector_pin, debug=debug))
        elif module_name == "obstacle-avoidance":
            modules.append(ObstacleAvoidance(mqtt_client, client_id, debug=debug))
        elif module_name == "pixels":
            modules.append(Pixels(mqtt_client, client_id, led_pin=pixels_pin, pixel_count=pixels_count, debug=debug))
        elif module_name == "rgb":
            modules.append(RGB(mqtt_client, client_id, debug=debug))
        elif module_name == "serial-reader":
            modules.append(SerialReader(mqtt_client, client_id,
                                        ports=serial_reader_ports,
                                        debug=debug))
        elif module_name == "tracking-sensor":
            modules.append(TrackingSensor(mqtt_client, client_id, debug=debug))
        elif module_name == "ultrasonic":
            modules.append(Ultrasonic(mqtt_client, client_id,
                                      pin_trigger=ultrasonic_pin_trigger,
                                      pin_echo=ultrasonic_pin_echo,
                                      debug=debug))
        elif module_name == "water-detector":
            modules.append(WaterDetector(mqtt_client, client_id, pin=water_detector_pin, debug=debug))
        elif module_name == "wheels":
            modules.append(Wheels(mqtt_client, client_id,
                                  pin_right_forward=wheels_pin_right_forward,
                                  pin_right_backward=wheels_pin_right_backward,
                                  pin_right_enabled=wheels_pin_right_enabled,
                                  pin_left_forward=wheels_pin_left_forward,
                                  pin_left_backward=wheels_pin_left_backward,
                                  pin_left_enabled=wheels_pin_left_enabled,
                                  debug=debug))
        elif module_name == "ws281x":
            modules.append(WS281x(mqtt_client, client_id, startup_file=ws281x_startup_file, debug=debug))
        else:
            logger.error("Unknown module " + module_name + "!")

    logger.debug("Loaded modules: " + str(modules))
    for module in modules:

        if hasattr(module, 'buzzer'):
            module.buzzer = next(i for i in modules if isinstance(i, Buzzer))
        if hasattr(module, "infrared_receiver"):
            module.infrared_receiver = next(i for i in modules if isinstance(i, InfraredReceiver))
        if hasattr(module, "infrared_sensor"):
            module.infrared_sensor = next(i for i in modules if isinstance(i, InfraredSensor))
        if hasattr(module, "joystick"):
            module.joystick = next(i for i in modules if isinstance(i, Joystick))
        if hasattr(module, "motion_detector"):
            modules.motion_detector = next(i for i in modules if isinstance(i, MotionDetector))
        if hasattr(module, "obstacle_avoidance"):
            module.obstacle_avoidance = next(i for i in modules if isinstance(i, ObstacleAvoidance))
        if hasattr(module, "pixels"):
            module.pixels = next(i for i in modules if isinstance(i, Pixels))
        if hasattr(module, "rgb"):
            module.rgb = next(i for i in modules if isinstance(i, RGB))
        if hasattr(module, "serial_reader"):
            module.serial_reader = next(i for i in modules if isinstance(i, SerialReader))
        if hasattr(module, "servo"):
            module.servo = next(i for i in modules if isinstance(i, Servo))
        if hasattr(module, "tracking_sensor"):
            module.tracking_sensor = next(i for i in modules if isinstance(i, TrackingSensor))
        if hasattr(module, "ultrasonic"):
            module.ultrasonic = next(i for i in modules if isinstance(i, Ultrasonic))
        if hasattr(module, "water_detector"):
            module.wheels = next(i for i in modules if isinstance(i, WaterDetector))
        if hasattr(module, "wheels"):
            module.wheels = next(i for i in modules if isinstance(i, Wheels))
        if hasattr(module, "ws281x"):
            module.ws281x = next(i for i in modules if isinstance(i, WS281x))

    for module in modules:
        if serial_reader_start and isinstance(module, SerialReader) \
                or ws281x_start and isinstance(module, WS281x):
            start_method = getattr(module, "start", None)
            if callable(start_method):
                start_method()


def looper():
    global logger
    global mqtt_client

    logger.info("Press [CTRL+C] to exit")
    try:
        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        # Other loop*() functions are available that give a threaded interface and a
        # manual interface.
        mqtt_client.loop_forever(retry_first_connection=True)
    except KeyboardInterrupt:
        logger.error("Finishing up...")
    except:
        logger.error("Unexpected Error!")
        traceback.print_exc()
    finally:
        for module in modules:
            stop_method = getattr(module, "stop", None)
            if callable(stop_method):
                stop_method()

        for module in modules:
            module.finalize()

        GPIO.cleanup()
        mqtt_client.publish("mutinus/state/status", "CLOSED", 1, True)


def help():
    print """Usage client-id [options]:

Options:
  -h, --help                                 This screen
  -d, --debug                                This screen
  -b, --broker address[:port]                Broker (default: 127.0.0.1, default port: 1883)
  -m, --module name[,name[,...]]             One or more modules to load
      buzzer            : Buzzer
      camera-servo      : Camera servos
      infrared-receiver : Infrared remote control receiver
      infrared-sensor   : Infrared distance sensor
      joystick          : Joystick
      motion-detector   : Motion detector (HC-SR501 PIR)
      obstacle-avoidance: Obstacle avoidance
      pixels            : WS281x pixels
      serial-reader     : Serial port reader
      rgb               : RGB Strip
      tracking-sensor   : Tracking sensor
      ultrasonic        : Ultrasonic distance sensor
      water-detector    : Water detector (Flying Fish MH Sensor)
      wheels            : Wheels
      ws281x            : WS281x driver

Serial port reader module:
  --serial-reader-ports port1[,port2[,...]]  Serial ports to read.
  --serial-reader-start                      Start listening right away

WS281x Module:
  --ws281x-start                             Start right away
  --ws281x-startup-file file                 Startup file
"""


def main(argv):
    global debug
    global logger
    global mqtt_client
    global client_id
    global serial_reader_start
    global serial_reader_ports
    global ws281x_start
    global ws281x_startup_file

    broker_address = "127.0.0.1"
    broker_port = 1883

    try:
        opts, args = getopt.getopt(argv, "hdb:m:", ["help", "debug", "broker=", "module=",
                                                    "serial-reader-start", "serial-reader-ports=",
                                                    "ws281x-start", "ws281x-startup-file="])
    except getopt.GetoptError:
        traceback.print_exc()
        help()
        sys.exit(1)

    module_names = []
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            help()
            sys.exit()
        elif opt in ("-d", "--debug"):
            debug = True
            logger = Logger("MAIN", debug)
        elif opt in ("-b", "--broker"):
            broker_params = arg.split(":")
            broker_address = broker_params[0]
            broker_port = int(broker_params[1]) if len(broker_params) > 1 else broker_port
        elif opt in ("-m", "--module") and arg not in module_names:
            for module_name in arg.split(","):
                module_names.append(module_name)
        elif opt == "--serial-reader-start":
            serial_reader_start = True
        elif opt == "--serial-reader-ports":
            serial_reader_ports = arg.split(",")
        elif opt == "--ws281x-start":
            ws281x_start = True
        elif opt == "--ws281x-startup-file":
            ws281x_startup_file = arg

    if client_id is None:
        help()
        sys.exit(2)

    mqtt_client = create_mqtt_client(broker_address, broker_port, client_id,
                                     on_connect=on_connect,
                                     on_disconnect=on_disconnect)
    mqtt_client.on_message = on_message

    initialize(module_names)
    looper()


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logger.info("Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # client.subscribe("$SYS/#")
    client.subscribe(client_id + "/control/#")
    client.publish(client_id + "/state/status", "OPEN", 1, True)


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.error("Unexpected disconnection.")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    try:
        logger.debug(msg.topic + ": '" + str(msg.payload) + "'")
#        path = msg.topic.split("/")
#        if len(path) == 2 and path[1] == "last-will-sink":
#            broker=msg.payload.split(":")
#            broker_address = broker[0]
#            broker_port = int(broker[1]) if len(broker) > 1 else 1883
#
#            mqtt_client = create_mqtt_client(broker_address, broker_port, client_id)
    except:
        logger.info("Error!")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Only " + str(len(sys.argv)) + " parameter given")
        help()
        sys.exit(2)

    client_id = sys.argv[1]
    main(sys.argv[2:])
