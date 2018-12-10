#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import prctl
import sys
import getopt
import time
from threading import Thread

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from Logger import Logger
from ModuleMQTT import *

debug = False
logger = Logger("MAIN", debug)
mqtt_client = None
mqtt_thread = None
client_id = None
modules = []

# Buzzer
buzzer_pin = 4

# Bluetooth Server
bluetooth_server_start = True
bluetooth_server_inbound_ports = [3]
bluetooth_server_outbound_ports = [4]

# Camera
camera_state_file = "/run/camera.state"

# Commander
commander_checks = None

# DHT11
dht11_pin = 4
dht11_interval = 60

# Infraread Receiver
ir_receiver_pin = 17

# Infrared Sensor
ir_sensor_pins = [19, 16]

# Joystick
joystick_pin_center = 7
joystick_pin_a = 8
joystick_pin_b = 9
joystick_pin_c = 10
joystick_pin_d = 11

# MCP23017
mcp23017_start = False

# Motion Detector
motion_detector_pin = 7

# Pixels
pixels_pin = 18
pixels_count = 4

# Serial Reader
serial_reader_start = False
serial_reader_ports = []

# Servo
servo_roll_min = 750
servo_roll_mid = 1750
servo_roll_max = 2750
# servo_roll_deg = float(servo_roll_max - servo_roll_min) / 180.0
servo_pitch_min = 1150
servo_pitch_mid = 2100
servo_pitch_max = 2800
# servo_pitch_deg = servo_roll_deg

# State Machine
state_machine_start = True
state_machine_description_file = "state-machine.yml"

# Ultrasonic
ultrasonic_pin_trigger = 22
ultrasonic_pin_echo = 27

# Water Detector
water_detector_pin = 23

# Wheels
wheels_pin_right_forward = 13
wheels_pin_right_backward = 12
wheels_pin_right_enabled = 6
wheels_pin_left_forward = 21
wheels_pin_left_backward = 20
wheels_pin_left_enabled = 26

# WS281x
ws281x_start = False
ws281x_startup_file = None
ws281x_led_count = 50
ws281x_reverse = False
ws281x_row_led_count = 24
ws281x_row_count = 2

gpio_modules = ["buzzer", "infrared-receiver", "infrared-sensor",  "joystick",  "motion-detector",  "tracking-sensor",
                "ultrasonic",  "water-detector",  "wheels"]
gpio_loaded = False

interrupted = False


class FileWatcherHandler(FileSystemEventHandler):

    def __init__(self):
        super(FileSystemEventHandler, self).__init__()
        prctl.set_name("File Watcher")

    def on_created(self, event):  # when file is created
        global interrupted
        if event.src_path == '/tmp/raspi-project.stop':
            logger.debug(event.src_path + " created")
            interrupted = True

    def on_modified(self, event):
        global interrupted
        if event.src_path == '/tmp/raspi-project.stop':
            logger.debug(event.src_path + " modified")
            interrupted = True


def initialize(module_names):
    global modules
    global gpio_loaded

    if [i for i in gpio_modules if i in module_names]:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(debug)
        gpio_loaded = True

    logger.info("Loading modules: " + str(module_names))
    for module_name in module_names:
        if module_name == "buzzer":
            from Buzzer import Buzzer
            modules.append(Buzzer(mqtt_client, client_id, pin=buzzer_pin, debug=debug))
        elif module_name == "bluetooth-server":
            from BluetoothServer import BluetoothServer
            modules.append(BluetoothServer(mqtt_client, client_id, bluetooth_server_inbound_ports,
                                           bluetooth_server_outbound_ports, debug=debug))
        elif module_name == "camera":
            from Camera import Camera
            modules.append(Camera(mqtt_client, client_id, state_file=camera_state_file, debug=debug))
        elif module_name == "commander":
            from Commander import Check, Commander
            checks = None if commander_checks is None else map(lambda p: Check(p[0], int(p[1])),
                                                               map(lambda s: s.split(":"), commander_checks.split(",")))
            modules.append(Commander(mqtt_client, client_id, checks=checks, debug=debug))
        elif module_name == "dht11":
            from DHT11 import DHT11
            modules.append(DHT11(mqtt_client, client_id, pin=dht11_pin, interval=dht11_interval, debug=debug))
        elif module_name == "infrared-receiver":
            from InfraredReceiver import InfraredReceiver
            modules.append(InfraredReceiver(mqtt_client, client_id, pin=ir_receiver_pin, debug=debug))
        elif module_name == "infrared-sensor":
            from InfraredSensor import InfraredSensor
            modules.append(InfraredSensor(mqtt_client, client_id, pins=ir_sensor_pins, debug=debug))
        elif module_name == "joystick":
            from Joystick import Joystick
            modules.append(Joystick(mqtt_client, client_id,
                                    pin_center=joystick_pin_center,
                                    pin_a=joystick_pin_a,
                                    pin_b=joystick_pin_b,
                                    pin_c=joystick_pin_c,
                                    pin_d=joystick_pin_d,
                                    debug=debug))
        elif module_name == "lcd":
            from LCD import LCD
            modules.append(LCD(mqtt_client, client_id, debug=debug))
        elif module_name == "mcp23017":
            from MCP23017 import MCP23017
            modules.append(MCP23017(mqtt_client, client_id, debug=debug))
        elif module_name == "monitor":
            from Monitor import Monitor
            modules.append(Monitor(mqtt_client, client_id, debug=debug))
        elif module_name == "motion-detector":
            from MotionDetector import MotionDetector
            modules.append(MotionDetector(mqtt_client, client_id, pin=motion_detector_pin, debug=debug))
        elif module_name == "obstacle-avoidance":
            from ObstacleAvoidance import ObstacleAvoidance
            modules.append(ObstacleAvoidance(mqtt_client, client_id, debug=debug))
        elif module_name == "pantilt":
            from PanTilt import PanTilt
            modules.append(PanTilt(mqtt_client, client_id, debug=debug))
        elif module_name == "pixels":
            from Pixels import Pixels
            modules.append(Pixels(mqtt_client, client_id, led_pin=pixels_pin, pixel_count=pixels_count, debug=debug))
        elif module_name == "rgb":
            from RGB import RGB
            modules.append(RGB(mqtt_client, client_id, debug=debug))
        elif module_name == "rpi":
            from RPI import RPI
            modules.append(RPI(mqtt_client, client_id, debug=debug))
        elif module_name == "serial-reader":
            from SerialReader import SerialReader
            modules.append(SerialReader(mqtt_client, client_id,
                                        ports=serial_reader_ports,
                                        debug=debug))
        elif module_name == "servo":
            from Servo import Servo
            modules.append(Servo(mqtt_client, client_id,
                                 servo_mins=[servo_roll_min, servo_pitch_min],
                                 servo_mids=[servo_roll_mid, servo_pitch_mid],
                                 servo_maxs=[servo_roll_max, servo_pitch_max],
                                 degree_span=180.0,
                                 debug=debug))
        elif module_name == "state-machine":
            from StateMachine import StateMachine
            modules.append(StateMachine(mqtt_client, client_id, state_machine_description_file, debug=debug))
        elif module_name == "tracking-sensor":
            from TrackingSensor import TrackingSensor
            modules.append(TrackingSensor(mqtt_client, client_id, debug=debug))
        elif module_name == "ultrasonic":
            from Ultrasonic import Ultrasonic
            modules.append(Ultrasonic(mqtt_client, client_id,
                                      pin_trigger=ultrasonic_pin_trigger,
                                      pin_echo=ultrasonic_pin_echo,
                                      debug=debug))
        elif module_name == "water-detector":
            from WaterDetector import WaterDetector
            modules.append(WaterDetector(mqtt_client, client_id, pin=water_detector_pin, debug=debug))
        elif module_name == "wheels":
            from Wheels import Wheels
            modules.append(Wheels(mqtt_client, client_id,
                                  pin_right_forward=wheels_pin_right_forward,
                                  pin_right_backward=wheels_pin_right_backward,
                                  pin_right_enabled=wheels_pin_right_enabled,
                                  pin_left_forward=wheels_pin_left_forward,
                                  pin_left_backward=wheels_pin_left_backward,
                                  pin_left_enabled=wheels_pin_left_enabled,
                                  debug=debug))
        elif module_name == "ws281x":
            from WS281x import WS281x
            modules.append(WS281x(mqtt_client, client_id,
                                  startup_file=ws281x_startup_file,
                                  led_count=ws281x_led_count,
                                  row_led_count=ws281x_row_led_count,
                                  row_count=ws281x_row_count,
                                  reverse=ws281x_reverse,
                                  debug=debug))
        elif module_name == 'ws281x-indicators':
            from WS281xIndicators import WS281xIndicators
            modules.append(WS281xIndicators(mqtt_client, client_id, led_count=ws281x_led_count, debug=debug))
        else:
            logger.error("Unknown module " + module_name + "!")

    logger.debug("Loaded modules: " + str(modules))
    for module in modules:

        if hasattr(module, 'buzzer'):
            from Buzzer import Buzzer
            module.buzzer = next((i for i in modules if isinstance(i, Buzzer)), None)
        if hasattr(module, 'bluetooth_server'):
            from BluetoothServer import BluetoothServer
            module.bluetooth_server = next((i for i in modules if isinstance(i, BluetoothServer)), None)
        if hasattr(module, "infrared_receiver"):
            from InfraredReceiver import InfraredReceiver
            module.infrared_receiver = next((i for i in modules if isinstance(i, InfraredReceiver)), None)
        if hasattr(module, "infrared_sensor"):
            from InfraredSensor import InfraredSensor
            module.infrared_sensor = next((i for i in modules if isinstance(i, InfraredSensor)), None)
        if hasattr(module, "joystick"):
            from Joystick import Joystick
            module.joystick = next((i for i in modules if isinstance(i, Joystick)), None)
        if hasattr(module, "lcd"):
            from LCD import LCD
            module.lcd = next((i for i in modules if isinstance(i, LCD)), None)
        if hasattr(module, "mcp23017"):
            from MCP23017 import MCP23017
            module.mcp23017 = next((i for i in modules if isinstance(i, MCP23017)), None)
        if hasattr(module, "motion_detector"):
            from MotionDetector import MotionDetector
            module.motion_detector = next((i for i in modules if isinstance(i, MotionDetector)), None)
        if hasattr(module, "obstacle_avoidance"):
            from ObstacleAvoidance import ObstacleAvoidance
            module.obstacle_avoidance = next((i for i in modules if isinstance(i, ObstacleAvoidance)), None)
        if hasattr(module, "pixels"):
            from Pixels import Pixels
            module.pixels = next((i for i in modules if isinstance(i, Pixels)), None)
        if hasattr(module, "rgb"):
            from RGB import RGB
            module.rgb = next((i for i in modules if isinstance(i, RGB)), None)
        if hasattr(module, "serial_reader"):
            from SerialReader import SerialReader
            module.serial_reader = next((i for i in modules if isinstance(i, SerialReader)), None)
        if hasattr(module, "servo"):
            from Servo import Servo
            module.servo = next((i for i in modules if isinstance(i, Servo)), None)
        if hasattr(module, "state_machine"):
            from StateMachine import StateMachine
            module.state_machine = next((i for i in modules if isinstance(i, StateMachine)), None)
        if hasattr(module, "tracking_sensor"):
            from TrackingSensor import TrackingSensor
            module.tracking_sensor = next((i for i in modules if isinstance(i, TrackingSensor)), None)
        if hasattr(module, "ultrasonic"):
            from Ultrasonic import Ultrasonic
            module.ultrasonic = next((i for i in modules if isinstance(i, Ultrasonic)), None)
        if hasattr(module, "water_detector"):
            from WaterDetector import WaterDetector
            module.wheels = next((i for i in modules if isinstance(i, WaterDetector)), None)
        if hasattr(module, "wheels"):
            from Wheels import Wheels
            module.wheels = next((i for i in modules if isinstance(i, Wheels)), None)
        if hasattr(module, "ws281x"):
            from WS281x import WS281x
            module.ws281x = next((i for i in modules if isinstance(i, WS281x)), None)
        if hasattr(module, "ws281x_indicators"):
            from WS281xIndicators import WS281xIndicators
            module.ws281x_indicators = next((i for i in modules if isinstance(i, WS281xIndicators)), None)

    for module in modules:
        autostart = False

        if bluetooth_server_start:
            from BluetoothServer import BluetoothServer
            if isinstance(module, BluetoothServer):
                autostart = True
        if mcp23017_start:
            from MCP23017 import MCP23017
            if isinstance(module, MCP23017):
                autostart = True
        if serial_reader_start:
            from SerialReader import SerialReader
            if isinstance(module, SerialReader):
                autostart = True
        if state_machine_start:
            from StateMachine import StateMachine
            if isinstance(module, StateMachine):
                autostart = True
        if ws281x_start:
            from WS281x import WS281x
            from WS281xIndicators import WS281xIndicators
            if isinstance(module, WS281x) or isinstance(module, WS281xIndicators):
                autostart = True

        if autostart:
            start_method = getattr(module, "start", None)
            if callable(start_method):
                start_method()


def looper():
    global logger
    global mqtt_client, mqtt_thread

    observer = Observer()
    event_handler = FileWatcherHandler()  # create event handler
    observer.schedule(event_handler, path='/tmp')
    observer.daemon = True
    observer.start()

    logger.info("Press [CTRL+C] to exit")
    try:
        # set observer to use created handler in directory

        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        # Other loop*() functions are available that give a threaded interface and a
        # manual interface.
        # mqtt_client.loop_forever(retry_first_connection=True)
        # mqtt_client.loop_start()
        mqtt_thread = Thread(target=mqtt_looper)
        mqtt_thread.daemon = True
        mqtt_thread.start()

        while not interrupted:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.error("Finishing up...")
    except:
        logger.error("Unexpected Error!")
        traceback.print_exc()
    finally:
        logger.debug("Stopping file observer...")
        observer.stop()
        observer.join(1.0)

        logger.debug("Stopping MQTT loop...")
        # mqtt_client.loop_stop()
        mqtt_client.disconnect()
        mqtt_thread.join(2)

        for module in modules:
            stop_method = getattr(module, "stop", None)
            if callable(stop_method):
                stop_method()

        for module in modules:
            logger.debug("Finalizing module %s..." % type(module))
            module.finalize()

        if gpio_loaded:
            logger.debug("Cleaning up GPIO...")
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        mqtt_client.publish("mutinus/state/status", "CLOSED", 1, True)
        logger.debug("Disconnecting from MQTT broker...")
        mqtt_client.disconnect()
        logger.debug("Exiting looper...")


def mqtt_looper():
    prctl.set_name("MQTT Client")
    mqtt_client.loop_forever(retry_first_connection=True)


def help():
    print """Usage client-id [options]:

Options:
  -h, --help                                 This screen
  -d, --debug                                This screen
  -b, --broker address[:port]                Broker (default: 127.0.0.1, default port: 1883)
  -m, --module name[,name[,...]]             One or more modules to load
      buzzer            : Buzzer
      bluetooth-server  : Bluetooth Server
      camera            : Camera
      commander         : Commander
      dht11             : DHT11 Temperature and Humidity sensor
      infrared-receiver : Infrared remote control receiver
      infrared-sensor   : Infrared distance sensor
      joystick          : Joystick
      lcd               : LCD
      mcp23017          : MCP23017
      monitor           : Target monitoring
      motion-detector   : Motion detector (HC-SR501 PIR)
      obstacle-avoidance: Obstacle avoidance
      pantilt           : PanTilt HAT
      pixels            : WS281x pixels
      rpi               : Raspberry PI
      serial-reader     : Serial port reader
      rgb               : RGB Strip
      servo             : Camera servos
      state-machine     : State machine
      tracking-sensor   : Tracking sensor
      ultrasonic        : Ultrasonic distance sensor
      water-detector    : Water detector (Flying Fish MH Sensor)
      wheels            : Wheels
      ws281x            : WS281x driver
      ws281x-indicators : WS281x driver as indicator LEDs

Bluetooth Server
  --inbound-ports=port1[,port2[,...]]        Bluetooth inbound ports
  --outbound-ports=port1[,port2[,...]]       Bluetooth outbound ports

Commander
  --commander-checks=command1:interval1[,command2:interval2[,...]]

DHT11
  --dht11-pin=pin                            DHT11 pin
  --dht11-interval=interval                  Refresh interval in seconds

MCP23017
  --mcp23017-start                           Start right away

Motion Detector
  --motion-detector-pin=pin                  Motion detector pin

Serial port reader module:
  --serial-reader-ports=port1[,port2[,...]]  Serial ports to read
  --serial-reader-start                      Start listening right away

Water Detector
  --water-detector-pin=pin                   Water detector pin

WS281x Module:
  --ws281x-led-count=count                   Total LED count (default 50)
  --ws281x-reverse                           Reverse LED order
  --ws281x-row-count=count                   Number of rows (default 2)
  --ws281x-row-led-count=count               LED count in one row (default 24)
  --ws281x-start                             Start right away
  --ws281x-startup-file=file                 Startup file

"""


def main(argv):
    global debug
    global logger
    global mqtt_client
    global client_id
    global bluetooth_server_inbound_ports, bluetooth_server_outbound_ports
    global commander_checks
    global dht11_pin, dht11_interval
    global mcp23017_start
    global motion_detector_pin
    global serial_reader_start, serial_reader_ports
    global state_machine_description_file
    global water_detector_pin
    global ws281x_start, ws281x_startup_file, ws281x_led_count, ws281x_row_led_count, ws281x_row_count, ws281x_reverse

    broker_host = "127.0.0.1"
    broker_port = 1883

    try:
        opts, args = getopt.getopt(argv, "hdb:m:", [
            "help", "debug", "broker=", "module=",
            "inbound-ports=", "outbound-ports=",
            "commander-checks=",
            "dht11-pin=", "dht11-interval",
            "mcp23017-start",
            "motion-detector-pin=",
            "water-detector-pin=",
            "serial-reader-start", "serial-reader-ports=",
            "state-machine-description=",
            "ws281x-start", "ws281x-startup-file=", "ws281x-reverse",
            "ws281x-led-count=", "ws281x-row-led-count=", "ws281x-row-count="])
    except getopt.GetoptError:
        traceback.print_exc()
        help()
        sys.exit(1)

    module_names = []
    for opt, arg in opts:
        print opt + " = " + arg
        if opt in ("-h", "--help"):
            help()
            sys.exit()
        elif opt in ("-d", "--debug"):
            debug = True
            logger = Logger("MAIN", debug)
        elif opt in ("-b", "--broker"):
            broker_params = arg.split(":")
            broker_host = broker_params[0]
            broker_port = int(broker_params[1]) if len(broker_params) > 1 else broker_port
        elif opt in ("-m", "--module") and arg not in module_names:
            for module_name in arg.split(","):
                module_names.append(module_name)
        elif opt == "--inbound-ports":
            bluetooth_server_inbound_ports = arg.split(",")
        elif opt == "--outbound-ports":
            bluetooth_server_outbound_ports = arg.split(",")
        elif opt == "--commander-checks":
            commander_checks = arg
        elif opt == "--dht11-pin":
            dht11_pin = int(arg)
        elif opt == "--dht11-interval":
            dht11_interval = float(arg)
        elif opt == "--mcp23017-start":
            mcp23017_start = True
        elif opt == "--motion-detector-pin":
            motion_detector_pin = int(arg)
        elif opt == "--serial-reader-start":
            serial_reader_start = True
        elif opt == "--serial-reader-ports":
            serial_reader_ports = arg.split(",")
        elif opt == "--state-machine-description":
            state_machine_description_file = arg
        elif opt == "--water-detector-pin":
            water_detector_pin = int(arg)
        elif opt == "--ws281x-start":
            ws281x_start = True
        elif opt == "--ws281x-startup-file":
            ws281x_startup_file = arg
        elif opt == "--ws281x-led-count":
            ws281x_led_count = int(arg)
        elif opt == "--ws281x-reverse":
            ws281x_reverse = True
        elif opt == "--ws281x-row-led-count":
            ws281x_row_led_count = arg
        elif opt == "--ws281x-row-count":
            ws281x_row_count = int(arg)

    if client_id is None:
        help()
        sys.exit(2)

    mqtt_client = create_mqtt_client(broker_host, broker_port, client_id,
                                     on_connect=on_connect,
                                     on_disconnect=on_disconnect)
    mqtt_client.on_message = on_message

    initialize(module_names)
    looper()
    logger.debug("Finished")


# The callback for when the client receives a CONNACK response from the server.
# noinspection PyUnusedLocal
def on_connect(client, userdata, flags, rc):
    logger.info("Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # client.subscribe("$SYS/#")
    client.subscribe(client_id + "/control/#")
    client.publish(client_id + "/state/status", "OPEN", 1, True)


# noinspection PyUnusedLocal
def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.error("Unexpected disconnection.")


# The callback for when a PUBLISH message is received from the server.
# noinspection PyUnusedLocal
def on_message(client, userdata, msg):
    global interrupted
    try:
        logger.debug(msg.topic + ": '" + str(msg.payload) + "'")
        path = msg.topic.split("/")
        payload = msg.payload
        if len(path) == 2 and path[0] == client_id and path[1] == "control":
            if payload == "OFF":
                #  mqtt_client.disconnect()
                interrupted = True
#        if len(path) == 2 and path[1] == "last-will-sink":
#            broker=msg.payload.split(":")
#            broker_host = broker[0]
#            broker_port = int(broker[1]) if len(broker) > 1 else 1883
#
#            mqtt_client = create_mqtt_client(broker_host, broker_port, client_id)
    except:
        logger.info("Error!")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Only " + str(len(sys.argv)) + " parameter given")
        help()
        sys.exit(2)

    client_id = sys.argv[1]
    if client_id == "--help" or client_id == "-h":
        help()
        sys.exit(0)

    main(sys.argv[2:])
