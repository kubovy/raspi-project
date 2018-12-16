#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Mariam Rady (m@ry.am)
# Author: Jan Kubovy (jan@kubovy.eu)
#
import ast
import time
import traceback
import json
import yaml
import copy

from lib.ModuleMQTT import ModuleMQTT
from jinja2 import Template


class StateMachine(ModuleMQTT):

    MAX_INDEX = 50

    devices = {}
    variables = {}
    current_state = None
    states = {}
    global_state = {}
    interrupted = False

    bluetooth_server = None
    lcd = None
    mcp23017 = None
    ws281x_indicators = None

    def __init__(self, client, service_name, description_file=None, debug=False):
        super(StateMachine, self).__init__(client, service_name, "state-machine", debug)

        self.initial_state = None
        descriptions = yaml.load_all(open(description_file, "r"))
        for description in descriptions:
            self.devices = description['devices']
            self.variables = description['vars']
            for state in description['states']:
                self.logger.debug(" - " + str(state['name']))
                if self.initial_state is None:
                    self.initial_state = state['name']
                self.states[state['name']] = state

        self.logger.debug("Initial: " + str(self.initial_state))
        for k in self.states.keys():
            self.logger.debug(" - " + str(k) + ": " + str(self.states[k]))

    def start(self):
        if self.bluetooth_server is not None:
            self.bluetooth_server.register(self)
        self.transit(self.initial_state)

    def stop(self):
        if self.bluetooth_server is not None:
            self.bluetooth_server.unregister(self)

    def on_bluetooth_message(self, message):
        if message == "BT:CONNECTED":
            self.set_state('bluetooth', 'connected', True)
        elif message == "BT:DISCONNECTED":
            self.set_state('bluetooth', 'connected', False)
            # self.execute({'kind': 'lcd', 'key': None, 'value': "\n         BT\n\n--= DISCONNECTED =--"})
        elif message.startswith("BT:IDD:"):
            if self.lcd is not None:
                btid = message[7:]
                # btid = (btid[:(self.lcd.cols - 2)] + "..") if len(btid) > self.lcd.cols else btid
                # btid = btid.rjust(int(math.floor((self.lcd.cols - len(btid)) / 2)) + len(btid))
                self.set_state('bluetooth', 'device', btid)
                # self.execute({'kind': 'lcd', 'key': None, 'value': "\n" + btid + "\n\n--== CONNECTED ==--"})
        elif message.startswith("TBC:PULL"):
            self.bluetooth_server.send(json.dumps({'devices': self.devices,
                                                   'vars': self.variables,
                                                   'states': self.states.values()}))
        elif message.startswith("TBC:"):
            for msg in message[4:].split(";"):
                parts = msg.split(",", 3)
                self.logger.debug(msg + " -> " + msg[4:] + " -> " + str(parts))
                if len(parts) == 3 and parts[0] == 'action':
                    self.execute({'name': parts[1], 'value': parts[2], 'eval': True})
                elif len(parts) >= 2 and parts[0] == 'transit':
                    self.transit(parts[1])
                elif len(parts) == 3:
                    self.set_state('bluetooth', parts[1], parts[2])

    def on_mqtt_message(self, path, payload):
        if len(path) == 2:
            try:
                self.set_state(path[0], path[1], payload)
            except:
                self.logger.error('Oops!')
                traceback.print_exc()
        elif len(path) == 1 and path[0] == 'restart':
            self.start()
        elif len(path) == 1:
            try:
                self.set_state(path[0], payload)
            except:
                self.logger.error('Oops!')
                traceback.print_exc()
        else:
            self.logger.debug("Current state: " + str(self.current_state['name']))

    def transit(self, new_state):
        self.logger.debug("Transiting " + (self.current_state['name'] if self.current_state is not None else "N/A") +
                          " -> " + new_state)
        self.current_state = self.states[new_state]

        self.logger.debug("Evaluating gate \"enter\"")
        self.evaluate("enter")
        self.logger.debug("Evaluating gate \"initializing\"")
        self.evaluate("initializing")
        self.logger.debug("Evaluating gate \"initialized\"")
        self.evaluate("initialized")
        self.logger.debug("Evaluating gate \"normal\"")

    def get_kind(self, item):
        if 'kind' in item.keys():
            return item['kind']
        elif item['name'] in self.devices.keys() and 'kind' in self.devices[item['name']]:
            return self.devices[item['name']]['kind']
        else:
            return None

    def get_key(self, item):
        key = None
        if 'key' in item.keys():
            key = item['key']
        elif 'name' in item.keys() and item['name'] in self.devices and 'key' in self.devices[item['name']]:
            key = self.devices[item['name']]['key']
        return str(key) if key is not None else None

    def template_variables(self):
        variables = self.variables.copy()  # start with x's keys and values
        variables.update(self.global_state)  # modifies z with y's keys and values & returns None

        device_map = {}
        for device_name, device in self.devices.iteritems():
            if device_name not in device_map:
                device_map[device_name] = [None for _ in range(self.MAX_INDEX)]
            device_map[device_name] = self.get_state(device)

        variables.update(device_map)
        return variables

    def get_value(self, item):
        try:
            if 'eval' in item.keys() and item['eval']:
                try:
                    value = Template(item['value']).render(self.template_variables())
                    if isinstance(value, basestring):
                        try:
                            value = ast.literal_eval(value)
                        except BaseException as e:
                            self.logger.error(e.message)
                except AttributeError:
                    value = item['value']
            elif 'value' in item.keys():
                value = item['value']
            else:
                self.logger.warn("No value in: " + str(item))
                value = None

            return self.variables[value] if value in self.variables.keys() else value
        except:
            self.logger.error("Problem getting value!")
            traceback.print_exc()
            return None

    def evaluate(self, gate="normal", previous_state=None):
        if self.current_state is not None and 'conditions' in self.current_state.keys():
            for condition in self.current_state['conditions']:
                # self.logger.debug("Condition: " + str(condition))
                result = True
                changed = False
                if 'expressions' in condition.keys():
                    for expression in condition['expressions']:
                        if (gate == "normal" or gate == "initializing") and not isinstance(expression, basestring):
                            value = self.get_value(expression) if 'value' in expression.keys() else None
                            current = self.get_state(expression)
                            if current is None:
                                if isinstance(value, str):
                                    current = ""
                                elif isinstance(value, bool):
                                    current = False
                                elif isinstance(value, int):
                                    current = 0

                            previous = self.get_state(expression, state=previous_state) \
                                if previous_state is not None else None
                            if previous is None:
                                if isinstance(value, str):
                                    previous = ""
                                elif isinstance(value, bool):
                                    previous = False
                                elif isinstance(value, int):
                                    previous = 0

                            result = result and (value is None or str(current) == str(value))
                            changed = changed or str(current) != str(previous) or gate != "normal"
                            # self.logger.debug("Expression " + str(expression) + ": " +
                            #                   str(current) + " <> " + str(value) + "[" + str(type(value)) + "] / " +
                            #                   str(current) + " <> " + str(previous) + " => " +
                            #                   str(result) + "/" + str(changed))
                        elif isinstance(expression, basestring):
                            self.logger.debug(expression.lower() + " <> " + gate)
                            result = result and expression.lower() == gate
                            changed = True
                else:
                    result = gate == "enter"
                    changed = True

                if result and changed:
                    self.logger.debug("Condition: " + str(condition) + " FIRED!")
                    if 'actions' in condition.keys():
                        for action in condition['actions']:
                            self.logger.debug("Action " + str(action))
                            if 'only' not in action.keys() or action['only'] == gate:
                                self.execute(action, gate in ['normal', 'initialized'])

    def get_state(self, item, key=None, state=None):
        state = self.global_state if state is None else state
        kind = item if isinstance(item, basestring) else self.get_kind(item)
        key = str(key) if isinstance(item, basestring) else self.get_key(item)

        if kind not in state.keys() or state[kind] is None:
            state[kind] = {}

        return state[kind][key] if key in state[kind] else None

    def set_state(self, item, key=None, value=None):
        item = self.devices[item] if isinstance(item, basestring) and key is None else item
        kind = item if isinstance(item, basestring) else self.get_kind(item)
        key = str(key) if isinstance(item, basestring) else self.get_key(item)

        if kind not in self.global_state.keys() or self.global_state[kind] is None:
            self.global_state[kind] = {}

        previous_state = copy.deepcopy(self.global_state)
        previous_value = self.get_state(kind, key)
        if previous_value != value:
            self.logger.debug(kind + "[" + str(key) + "]: " + str(previous_value) + " -> " + str(value))
            self.global_state[kind][key] = value
            self.evaluate("normal", previous_state)

        return previous_value != value

    def execute(self, action, with_goto=True):
        # self.logger.debug("Action: " + self.get_kind(action) +
        #                   "[" + ("N/A" if self.get_key(action) is None else str(self.get_key(action))) + "]: " +
        #                   str(self.get_value(action)))
        kind = self.get_kind(action)

        if kind == 'GOTO' or kind == 'JUMPTO':
            if with_goto or kind == 'JUMPTO':
                state = self.get_key(action)
                delay = self.get_value(action)
                self.logger.debug("Going to: " + str(state))
                if delay is not None:
                    time.sleep(int(delay) / 1000.0)
                self.transit(state)
        elif kind == 'bluetooth' and self.bluetooth_server is not None:
            key = self.get_key(action)
            if key is None:
                value = self.template_variables()
                # self.bluetooth_server.send(yaml.dump(value, default_flow_style=False, encoding='utf-8'))
                self.bluetooth_server.send(json.dumps(value))
            else:
                value = self.get_value(action)
                value = self.template_variables() if value == 'DUMP' else value
                # self.bluetooth_server.send(yaml.dump({key: value}, default_flow_style=False, encoding='utf-8'))
                self.bluetooth_server.send(json.dumps({key: value}))
        elif kind == 'lcd' and self.lcd is not None:
            key = self.get_key(action)
            if key == "clear":
                self.lcd.clear()
            elif key == "reset":
                self.lcd.setup()
                self.lcd.clear()
            elif key == "backlight":
                self.lcd.backlight(self.get_value(action))
            elif key is not None:
                value = self.get_value(action)
                if value != "IGNORE":
                    self.lcd.set_line(int(key), value)
            else:
                value = self.get_value(action)
                if value != "IGNORE":
                    self.lcd.clear()
                    self.lcd.set(value)
        elif kind == 'mcp23017' and self.mcp23017 is not None:
            self.mcp23017.set(int(self.get_key(action)), self.get_value(action))
        elif kind == 'ws281x-indicators' and self.ws281x_indicators is not None:
            self.ws281x_indicators.set(int(self.get_key(action)), self.get_value(action))
        else:
            self.logger.debug("Unknown " + str(kind) +
                              "[" + str(self.get_key(action)) + "] executed with " + str(self.get_value(action)))
