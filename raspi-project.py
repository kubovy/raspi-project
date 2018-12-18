#!/usr/bin/env python2
# -*- coding:utf-8 -*-
#
# Author: Jan Kubovy (jan@kubovy.eu)
#
import getopt
import os
import sys
import time
import traceback
from copy import deepcopy

from lib.FileWatcherHandler import observe
from lib.Logger import Logger
from lib.Util import to_snake_case

REQUIRED_STRING = "REQUIRED"
REQUIRED_INT = -1

debug = False
logger = Logger("MAIN", debug)

module_parameters = {
    'Bluetooth': {
        'client-id': [REQUIRED_STRING, "", ""],
        'inbound-ports': [[REQUIRED_INT], "port1[,port2[,...]]", "Bluetooth inbound ports"],
        'outbound-ports': [[REQUIRED_INT], "port1[,port2[,...]]", "Bluetooth outbound ports"],
        'start': [True, "", "Starts bluetooth server"]
    },
    'Buzzer': {
        'pin': [4, "pin", "Buzzer pin (default: 7)"]
    },
    'Camera': {
        'state-file': ["/run/camera.state", "file", "State file (default: /run/camera.state)"]
    },
    'Commander': {
        'checks': [[], "command1:interval1[,command2:interval2[,...]]", "Checks to perform in defined intervals"]
    },
    'DHT11': {
        'pin': [7, "pin", "DHT11 pin (default: 7)"],
        'interval': [60, "interval", "Refresh interval in seconds (default: 60)"]
    },
    'IRReceiver': {
        'pin': [17, "pin", "IR Receiver pin (default: 17)"]
    },
    'IRSensor': {
        'pins': [[19, 16], "pin1,pin2", "IR sensor pins (default: 19,16)"]
    },
    'Joystick': {
        'pin-center': [7, "pin", "Center pin (default: 7)"],
        'pin-a': [8, "pin", "Up pin (default: 8)"],
        'pin-b': [9, "pin", "Right pin (default: 9)"],
        'pin-c': [10, "pin", "Left pin (default: 10)"],
        'pin-d': [11, "pin", "Down pin (default: 11)"]
    },
    'LCD': {
        'cols': [20, 'cols', "Number of columns (default: 20)"],
        'rows': [4, 'rows', "Number of rows (default: 4)"],
        'address': [0x27, "address", "I2C address (default: 0x27)"],
        'start': [True, "", "Starts LCD"]
    },
    'MotionDetector': {
        'pin': [7, "pin", "Motion detector pin (default: 7)"]
    },
    'MCP23017': {
        'start': [False, "", "Starts MPC23017"]
    },
    'MQTT': {
        'client-id': [REQUIRED_STRING, "", ""],
        'start': [True, "", "Starts MQTT"],
        'host': [REQUIRED_STRING, "host", "MQTT host"],
        'port': [1883, "port", "MQTT port (default: 1883)"]
    },
    'PanTilt': {
        'enable-lights': [True, "", "Enable lights"],
        'idle-timeout': [2, "timeout", "Idle timeout in seconds (default: 2)"],
        'servo1-min': [575, "value", "Servo 1 min (default: 575)"],
        'servo1-max': [2325, "value", "Servo 1 max (default: 2325)"],
        'servo2-min': [575, "value", "Servo 2 min (default: 575)"],
        'servo2-max': [2325, "value", "Servo 2 max (default: 2325)"],
        'address': [0x15, "address", "I2C address (default: 0x15)"],
    },
    'Pixels': {
        'pin': [18, "pin", "Pixels pin (default: 18)"],
        'count': [4, "count", "Count of LEDs (default: 4)"]
    },
    'SerialReader': {
        'identifier': ['20180214', "identifier", "Serial reader idenfifier (default: 20180214)"],
        'ports': [[], "port1[,port2[,...]]", "Serial reader ports (default: None)"],
        'start': [False, "", "Starts serial reader"]
    },
    'Servo': {
        'servo-mins': [[1000], "min1[,min2[,...]", ""],
        'servo-mids': [[1500], "mid1[,mid2[,...]", ""],
        'servo-maxs': [[2000], "max2[,max2[,...]", ""],
        'degree-span': [180.0, "degrees", ""]
    },
    'StateMachine': {
        'description-file': ["REQUIRED", "file", "State machine's description file"],
        'transactional': [True, "", "Transactional transitions between states (default: absent)"],
        'start': [False, "", "Starts state machine"]
    },
    'Tracking': {
        'num-sensors': [5, 'num', "Number of sensor (default: 5)"]
    },
    'Ultrasonic': {
        'pin-trigger': [22, "pin", "Trigger pin (default: 22)"],
        'pin-echo': [27, "pin", "Echo pin (default: 27)"]
    },
    'WaterDetector': {
        'pin': [23, "pin", "Water detector pin (default: 23)"]
    },
    'Wheels': {
        'pin-right-forward': [13, "pin", "Right forward pin (default: 13)"],
        'pin-right-backward': [12, "pin", "Right backward pin (default: 12)"],
        'pin-right-enabled': [6, "pin", "Right enable pin (default: 6)"],
        'pin-left-forward': [21, "pin", "Left forward pin (default: 21)"],
        'pin-left-backward': [20, "pin", "Left backward pin (default: 20)"],
        'pin-left-enabled': [26, "pin", "Left enable pin (default: 26)"]
    },
    'WS281x': {
        'startup-file': ["", "file", "Startup file"],
        'led-count': [50, "count", "Total LED count (default 50)"],
        'row-led-count': [24, "count", "LED count in one row (default 24)"],
        'row-count': [2, "count", "Number of rows (default 2)"],
        'reverse': [False, "", "Reverse LED order"],
        'start': [False, "", "Starts WS281x"]
    },
    'WS281xIndicators': {
        'led-count': [50, "count", "Total LED count (default 50)"],
        'start': [False, "", "Starts WS281x indicators"]
    }
}

parameter_values = {}

client_id = None
modules = []

gpio_modules = ["Buzzer", "InfraredReceiver", "InfraredSensor", "Joystick", "MotionDetector", "TrackingSensor",
                "Ultrasonic", "WaterDetector", "Wheels"]
gpio_loaded = False

interrupted = False


def initialize(module_names):
    global modules, debug, gpio_loaded

    if [i for i in gpio_modules if i in module_names]:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(debug)
        gpio_loaded = True

    logger.info("Loading modules: " + str(module_names))

    for module_file in sorted(os.listdir('modules')):
        if module_file.endswith(".py") and module_file != "__init__.py":
            module_name = module_file[:-3]

            if module_name in module_names:
                module = __import__("modules." + module_name, fromlist=[module_name])
                clazz = getattr(module, module_name)
                attributes = deepcopy(parameter_values[module_name]) if module_name in parameter_values.keys() else {}
                attributes['debug'] = debug
                attributes.pop('start', None)
                logger.debug("Instantiating " + str(clazz.__name__) + "(" + str(attributes) + ")")
                instance = clazz(**attributes)
                modules.append(instance)

    logger.debug("Loaded modules: " + str(modules))
    for module in modules:
        for module_name in module_names:
            if module_name != type(module).__name__:
                module_property = "module_" + to_snake_case(module_name)
                if hasattr(module, module_property):
                    import_module = __import__("modules." + module_name, fromlist=[module_name])
                    clazz = getattr(import_module, module_name)
                    injectee = next((i for i in modules if isinstance(i, clazz)), None)
                    if injectee is not None:
                        logger.debug("Injecting " + type(injectee).__name__ + " into " + type(module).__name__ + "." +
                                     module_property)
                        setattr(module, module_property, injectee)
                        if hasattr(injectee, 'register'):
                            getattr(injectee, 'register')(module)

    for module in modules:
        module.initialize()

    for module in modules:
        if type(module).__name__ in parameter_values \
                and 'start' in parameter_values[type(module).__name__] \
                and parameter_values[type(module).__name__]['start']:
            module.start()


def looper():
    global logger

    observer = observe('/tmp/raspi-project.stop', on_stop_file_touched, logger)

    logger.info("Press [CTRL+C] to exit")
    try:
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

        for module in modules:
            module.stop()

        for module in modules:
            logger.debug("Finalizing module %s..." % type(module))
            module.finalize()

        if gpio_loaded:
            logger.debug("Cleaning up GPIO...")
            import RPi.GPIO as GPIO
            GPIO.cleanup()


def help():
    print """Usage client-id [options]:

Options:
  -h, --help                                 This screen
  -d, --debug                                This screen
  -m, --module name[,name[,...]]             One or more modules to load"""
    for module_file in sorted(os.listdir('modules')):
        if module_file.endswith(".py") and module_file != "__init__.py":
            module_name = module_file[:-3]
            print "      ", to_snake_case(module_name, separator="-").ljust(20), ": ", \
                to_snake_case(module_name, separator=" ", case=None)

    for module_name, parameters in sorted(module_parameters.items(), key=lambda tupple: tupple[0]):
        print ""
        print to_snake_case(module_name, separator=" ", case=None)
        for option_name, definition in sorted(parameters.items(), key=lambda tupple: tupple[0]):
            if option_name != "client-id" and (not isinstance(definition[0], bool) or not definition[0]):
                option = "  --" + to_snake_case(module_name, separator="-") + "-" + option_name
                value = "=" + definition[1] if len(definition) > 1 and not isinstance(definition[0], bool) else ""
                print (option + value).ljust(50), " ", definition[2] if len(definition) > 2 else ""


def main(argv):
    global debug, logger, client_id, module_parameters, parameter_values

    try:
        options = ["help", "debug", "module="]
        for module_name, parameters in module_parameters.items():
            module_id = to_snake_case(module_name, "-")
            for option_name, definition in parameters.items():
                options.append(module_id + "-" + option_name + ("" if isinstance(definition[0], bool) else "="))

        opts, args = getopt.getopt(argv, "hd:m:", options)
    except getopt.GetoptError as e:
        help()
        print "\nError: ", e.msg
        sys.exit(1)

    module_names = []
    for opt, arg in opts:
        print opt + " = " + arg
        if opt in ("-h", "--help"):
            help()
            sys.exit()
        elif opt in ("-d", "--debug"):
            debug = True
        elif opt in ("-m", "--module") and arg not in module_names:
            for module_id in arg.split(","):
                found = False
                for module_file in sorted(os.listdir('modules')):
                    if module_file.endswith(".py") and module_file != "__init__.py":
                        module_name = module_file[:-3]
                        if to_snake_case(module_name, "-") == module_id:
                            module_names.append(module_name)
                            found = True
                if not found:
                    logger.exception("Module " + module_id + " not found!")

            for module_name, parameters in module_parameters.items():
                if module_name in module_names:
                    for option_name, definition in parameters.items():
                        parameter_name = option_name.replace("-", "_")
                        if module_name not in parameter_values.keys():
                            parameter_values[module_name] = {}
                        parameter_values[module_name][parameter_name] = client_id if parameter_name == "client_id" \
                            else definition[0]
        else:
            for module_name, parameters in module_parameters.items():
                for option_name, definition in parameters.items():
                    parameter_name = option_name.replace("-", "_")
                    option = "--" + to_snake_case(module_name, separator="-") + "-" + option_name

                    if module_name not in parameter_values.keys():
                        parameter_values[module_name] = {}

                    if opt == option:
                        if option == "--client-id":
                            parameter_values[module_name][parameter_name] = client_id
                        elif isinstance(definition[0], bool):
                            parameter_values[module_name][parameter_name] = True
                        elif isinstance(definition[0], int):
                            parameter_values[module_name][parameter_name] = int(arg)
                        elif isinstance(definition[0], float):
                            parameter_values[module_name][parameter_name] = float(arg)
                        elif isinstance(definition[0], list) and len(definition[0]) > 0 \
                                and isinstance(definition[0][0], int):
                            values = []
                            for value in arg.split(","):
                                values.append(int(value))
                            parameter_values[module_name][parameter_name] = values
                        elif isinstance(definition[0], list):
                            parameter_values[module_name][parameter_name] = arg.split(",")
                        elif isinstance(definition[0], basestring):
                            parameter_values[module_name][parameter_name] = arg

    for module_name, parameters in parameter_values.items():
        for parameter_name, parameter_value in parameters.items():
            if parameter_name != "client_id":
                required_values = parameter_value[0] if isinstance(parameter_value, list) and len(parameter_value) == 1 \
                    else parameter_value
                if required_values in [REQUIRED_STRING, REQUIRED_INT]:
                    option = "--" + to_snake_case(module_name, separator="-") + "-" + parameter_name.replace("_", "-")
                    help()
                    print "Parameter: ", option, " is required!"
                    exit(2)

    initialize(module_names)
    looper()
    logger.debug("Finished")


def on_stop_file_touched():
    global interrupted
    interrupted = True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Only " + str(len(sys.argv)) + " parameter given")
        help()
        sys.exit(2)

    client_id = sys.argv[1]
    if client_id == "--help" or client_id == "-h":
        help()
        sys.exit(0)

    if client_id is None:
        help()
        sys.exit(2)

    main(sys.argv[2:])
