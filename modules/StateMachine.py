#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Mariam Rady (m@ry.am)
# Author: Jan Kubovy (jan@kubovy.eu)
#
import ast
import copy
import json
import time
import traceback
import yaml
from copy import deepcopy
from jinja2 import Template

from lib.FileWatcherHandler import observe
from lib.ModuleLooper import ModuleLooper


class StateMachine(ModuleLooper):
    MAX_INDEX = 50

    module_bluetooth = None
    module_lcd = None
    module_mcp23017 = None
    module_ws281x_indicators = None

    __initial_state = None
    __current_state = None
    __states = {}
    __global_state = {}
    __devices = {}
    __variables = {}
    __actions = {}
    __under_change = False
    __templates = {}
    __template_variables_cache = None

    __configuration_observer = None

    def __init__(self, description_file=None, transactional=True, debug=False):
        super(StateMachine, self).__init__(debug=debug)

        self.__transactional = transactional
        self.__global_state = {}
        self.__description_file = description_file
        self.__configuration_observer = observe(description_file, self.initialize, self.logger)

    def initialize(self):
        super(StateMachine, self).initialize()
        self.__initial_state = None
        self.__current_state = None
        self.__states = {}
        self.__devices = {}
        self.__variables = {}
        self.__template_variables_cache = None

        if self.module_lcd is not None:
            self.module_lcd.reset()
        if self.module_mcp23017 is not None:
            self.module_mcp23017.reset()
        if self.module_ws281x_indicators is not None:
            self.module_ws281x_indicators.reset()

        descriptions = yaml.load_all(open(self.__description_file, "r"))

        for description in descriptions:
            self.__devices = description['devices']
            self.__variables = description['vars']
            self.logger.info("Description file ...")
            for state in description['states']:
                self.logger.info("Loading " + str(state['name']) + " state ...")
                if self.__initial_state is None:
                    self.__initial_state = state['name']
                self.__states[state['name']] = state
                for condition in state['conditions']:
                    if 'expressions' in condition.keys():
                        for expression in condition['expressions']:
                            if not isinstance(expression, basestring) \
                                    and 'eval' in expression.keys() \
                                    and expression['eval'] \
                                    and 'value' in expression.keys() \
                                    and expression['value'] not in self.__templates.keys():
                                self.__templates[expression['value']] = Template(expression['value'])
                    if 'actions' in condition.keys():
                        for action in condition['actions']:
                            if 'eval' in action.keys() and action['eval']:
                                if action['value'] not in self.__templates.keys():
                                    self.__templates[action['value']] = Template(action['value'])

        if self.module_mcp23017 is not None:
            for bit, value in enumerate(self.module_mcp23017.get_all()):
                self.set_state("mcp23017", bit, value)

        self.logger.info("Transiting to initial state: " + str(self.__initial_state) + " ...")
        self.transit(self.__initial_state)

    def start(self):
        if self.__transactional:
            super(StateMachine, self).start()
        else:
            self.on_start()

    def stop(self):
        if self.__transactional:
            super(StateMachine, self).stop()
        else:
            self.on_stop()

    def transit(self, new_state):
        self.logger.info("Transiting " + (self.__current_state['name'] if self.__current_state is not None else "N/A") +
                         " -> " + new_state)
        self.__current_state = self.__states[new_state]

        self.logger.debug("Evaluating gate \"enter\" in " + str(new_state) + " state")
        self.__evaluate("enter")
        self.logger.debug("Evaluating gate \"initializing\" in " + str(new_state) + " state")
        self.__evaluate("initializing")
        self.logger.debug("Evaluating gate \"initialized\" in " + str(new_state) + " state")
        self.__evaluate("initialized")
        if self.__current_state is not None and new_state == self.__current_state['name']:
            self.logger.debug("Evaluating gate \"normal\" in " + str(new_state) + " state")

    def get_state(self, item, key=None, state=None):
        state = self.__global_state if state is None else state
        kind = item if isinstance(item, basestring) else self.__get_kind(item)
        key = str(key) if isinstance(item, basestring) else self.__get_key(item)

        if kind not in state.keys() or state[kind] is None:
            state[kind] = {}

        return state[kind][key] if key in state[kind] else None

    def set_state(self, item, key=None, value=None):
        item = self.__devices[item] if isinstance(item, basestring) and key is None else item
        kind = item if isinstance(item, basestring) else self.__get_kind(item)
        key = str(key) if isinstance(item, basestring) else self.__get_key(item)

        if kind not in self.__global_state.keys() or self.__global_state[kind] is None:
            self.__global_state[kind] = {}

        previous_state = copy.deepcopy(self.__global_state)
        previous_value = self.get_state(kind, key)
        if previous_value != value:
            self.logger.debug(kind + "[" + str(key) + "]: " + str(previous_value) + " -> " + str(value))
            self.__global_state[kind][key] = value
            self.__evaluate("normal", previous_state)

        if previous_value != value:
            self.__template_variables_cache = None
        return previous_value != value

    def on_bluetooth_message(self, message):
        if message == "BT:CONNECTED":
            self.set_state('bluetooth', 'connected', True)
        elif message == "BT:DISCONNECTED":
            self.set_state('bluetooth', 'connected', False)
            # self.execute({'kind': 'lcd', 'key': None, 'value': "\n         BT\n\n--= DISCONNECTED =--"})
        elif message.startswith("BT:IDD:"):
            btid = message[7:]
            self.set_state('bluetooth', 'device', btid)
        elif message.startswith("TBC:PULL"):
            self.module_bluetooth.send(json.dumps({'devices': self.__devices,
                                                   'vars': self.__variables,
                                                   'states': self.__states.values()}))
        elif message.startswith("TBC:"):
            self.__transaction_start()
            for msg in message[4:].split(";"):
                parts = msg.split(",", 3)
                self.logger.debug(msg + " -> " + msg[4:] + " -> " + str(parts))
                if len(parts) == 3 and parts[0] == 'action':
                    self.__execute({'name': parts[1], 'value': parts[2], 'eval': True})
                elif len(parts) >= 2 and parts[0] == 'transit':
                    self.transit(parts[1])
                elif len(parts) == 3:
                    self.set_state('bluetooth', parts[1], parts[2])
            self.__transaction_end()

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
            self.logger.debug("Current state: " + str(self.__current_state['name']))

    def on_mcp23017_change(self, bit, value):
        self.set_state("mcp23017", bit, value)

    def looper(self):
        self.__transaction_start()
        actions = deepcopy(self.__actions)
        self.__actions = {}
        self.__transaction_end()

        if actions != {}:
            self.logger.debug("Actions: " + str(actions))

        goto_action = None

        for kind, rest in actions.items():
            self.logger.debug(" - " + kind + ": " + str(rest))
            if kind == 'GOTO':
                goto_action = rest
            elif kind == 'bluetooth' and self.module_bluetooth is not None:
                for key, value in rest.items():
                    if key is None:
                        value = self.__template_variables()
                        # self.bluetooth_server.send(yaml.dump(value, default_flow_style=False, encoding='utf-8'))
                        self.module_bluetooth.send(json.dumps(value))
                    else:
                        value = self.__template_variables() if value == 'DUMP' else value
                        self.module_bluetooth.send(json.dumps({key: value}))
            elif kind == 'lcd' and self.module_lcd is not None:
                for key, value in rest.items():
                    if key == "clear":
                        self.module_lcd.post(None)
                    elif key == "reset":
                        self.module_lcd.post("reset")
                    elif key == "backlight":
                        self.module_lcd.post(value)
                    elif key is not None:
                        if value != "IGNORE":
                            self.module_lcd.post(value, int(key))
                    else:
                        if value != "IGNORE":
                            self.module_lcd.clear_queue()
                            self.module_lcd.post(value)
            elif kind == 'mcp23017' and self.module_mcp23017 is not None:
                for key, value in rest.items():
                    self.module_mcp23017.set(int(key), value, False)
                self.module_mcp23017.write_all()
            elif kind == 'ws281x-indicators' and self.module_ws281x_indicators is not None:
                for key, value in rest.items():
                    self.module_ws281x_indicators.set(int(key), value)
            else:
                for key, value in rest.items():
                    self.logger.debug("Unknown " + str(kind) + "[" + str(key) + "] executed with " + str(value))

        if goto_action is not None:
            state = self.__get_key(goto_action)
            delay = self.__get_value(goto_action, False)
            self.logger.debug("Going to: " + str(state))
            if delay is not None:
                time.sleep(int(delay) / 1000.0)
            self.transit(state)

        time.sleep(0.25)

    def __get_kind(self, item):
        if 'kind' in item.keys():
            return item['kind']
        elif 'name' in item.keys() and item['name'] in self.__devices.keys() and 'kind' in self.__devices[item['name']]:
            return self.__devices[item['name']]['kind']
        else:
            return None

    def __get_key(self, item):
        key = None
        if 'key' in item.keys():
            key = item['key']
        elif 'name' in item.keys() and item['name'] in self.__devices and 'key' in self.__devices[item['name']]:
            key = self.__devices[item['name']]['key']
        return str(key) if key is not None else None

    def __get_descriptor(self, item):
        if item is not None:
            value = str(self.__get_kind(item)) + "[" + str(self.__get_key(item)) + "]"
            if 'name' in item.keys():
                value += " (" + item['name'] + ")"
        else:
            value = "N/A"
        return value

    def __template_variables(self):
        while self.__template_variables_cache is None:
            self.__template_variables_cache = self.__variables.copy()
            if self.__template_variables_cache is not None:
                self.__template_variables_cache.update(self.__global_state)

            device_map = {}
            for device_name, device in self.__devices.iteritems():
                if device_name not in device_map:
                    device_map[device_name] = [None for _ in range(self.MAX_INDEX)]
                device_map[device_name] = self.get_state(device)

            if self.__template_variables_cache is not None:
                self.__template_variables_cache.update(device_map)

            if self.__template_variables_cache is None:
                time.sleep(0.5)
        return self.__template_variables_cache

    def __get_value(self, item, evaluate=True):
        try:
            # self.logger.debug("Value: " + str(item) + " eval=" + str(evaluate))
            if evaluate and 'value' in item.keys() and 'eval' in item.keys() and item['eval']:
                try:
                    # self.logger.debug("Template: " + item['value'] + " -> " + str(self.templates[item['value']]))
                    if item['value'] not in self.__templates:
                        self.__templates[item['value']] = Template(item['value'])
                    value = self.__templates[item['value']].render(self.__template_variables())
                    # self.logger.debug("Rendered Value: " + str(value))
                    if isinstance(value, basestring):
                        try:
                            value = ast.literal_eval(value)
                        except BaseException as e:
                            self.logger.error(e.message)
                except AttributeError as e:
                    self.logger.error("Template attribute error: " + str(e.message))
                    traceback.print_exc()
                    value = item['value']
            elif 'value' in item.keys():
                value = item['value']
            else:
                value = None

            return self.__variables[value] if value in self.__variables.keys() else value
        except:
            self.logger.error("Problem getting value!")
            traceback.print_exc()
            return None

    def __evaluate(self, gate="normal", previous_state=None):
        self.__transaction_start()
        current_state = self.__current_state
        if current_state is not None and 'conditions' in current_state.keys():
            for condition in current_state['conditions']:
                if current_state == self.__current_state \
                        and ('only' not in condition.keys() or condition['only'] == gate):
                    # self.logger.debug("Condition: " + str(condition))
                    result = True
                    changed = False
                    if 'expressions' in condition.keys():
                        for expression in condition['expressions']:
                            if isinstance(expression, basestring) \
                                    or 'only' not in expression.keys() \
                                    or expression['only'] == gate:
                                if (gate == "normal" or gate == "initializing" or gate == "initialized") \
                                        and not isinstance(expression, basestring):
                                    value = self.__get_value(expression) if 'value' in expression.keys() else None
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
                                elif isinstance(expression, basestring):
                                    result = result and expression.lower() == gate
                                    changed = True
                    else:
                        result = gate == "enter"
                        changed = True

                    if result and changed and current_state == self.__current_state:
                        # expression = condition['expression'] if 'expression' in condition.keys() else None
                        # self.logger.debug("Condition: " + self.get_descriptor(expression) +
                        #                   " in " + current_state['name'] + "[" + gate + "] state FIRED!")
                        if 'actions' in condition.keys():
                            for action in condition['actions']:
                                # self.logger.debug(" -> action: " + self.get_descriptor(action))
                                if 'only' not in action.keys() or action['only'] == gate:
                                    self.__execute(action, gate in ['normal', 'initialized'])

        self.__transaction_end()

    def __transaction_start(self):
        if self.__transactional:
            while self.__under_change:
                time.sleep(0.05)

            self.__under_change = True

    def __transaction_end(self):
        if self.__transactional:
            self.__under_change = False

    def __execute(self, action, with_goto=True):
        if self.__transactional:
            self.__execute_delayed(action, with_goto)
        else:
            self.__execute_immediately(action, with_goto)

    def __execute_delayed(self, action, with_goto=True):
        kind = self.__get_kind(action)
        key = self.__get_key(action)
        value = self.__get_value(action)

        if kind == 'GOTO' and with_goto:
            self.__actions[kind] = {'key': key, 'value': value}
        else:
            if kind not in self.__actions:
                self.__actions[kind] = {}
            self.__actions[kind][str(key) if key is not None else None] = value

    def __execute_immediately(self, action, with_goto=True):
        kind = self.__get_kind(action)

        if kind == 'GOTO' and with_goto:
            state = self.__get_key(action)
            delay = self.__get_value(action)
            self.logger.debug("Going to: " + str(state))
            if delay is not None:
                time.sleep(int(delay) / 1000.0)
            self.transit(state)
        elif kind == 'bluetooth' and self.module_bluetooth is not None:
            key = self.__get_key(action)
            if key is None:
                value = self.__template_variables()
                # self.bluetooth_server.send(yaml.dump(value, default_flow_style=False, encoding='utf-8'))
                self.module_bluetooth.send(json.dumps(value))
            else:
                value = self.__get_value(action)
                value = self.__template_variables() if value == 'DUMP' else value
                # self.bluetooth_server.send(yaml.dump({key: value}, default_flow_style=False, encoding='utf-8'))
                self.module_bluetooth.send(json.dumps({key: value}))
        elif kind == 'lcd' and self.module_lcd is not None:
            key = self.__get_key(action)
            if key == "clear":
                self.module_lcd.post(None)
            elif key == "reset":
                self.module_lcd.post("reset")
            elif key == "backlight":
                self.module_lcd.post(self.__get_value(action))
            elif key is not None:
                value = self.__get_value(action)
                if value != "IGNORE":
                    self.module_lcd.post(value, int(key))
            else:
                value = self.__get_value(action)
                if value != "IGNORE":
                    self.module_lcd.post(value)
        elif kind == 'mcp23017' and self.module_mcp23017 is not None:
            self.module_mcp23017.set(int(self.__get_key(action)), self.__get_value(action))
        elif kind == 'ws281x-indicators' and self.module_ws281x_indicators is not None:
            self.module_ws281x_indicators.set(int(self.__get_key(action)), self.__get_value(action))
        else:
            self.logger.warn("Unknown " + str(kind) +
                             "[" + str(self.__get_key(action)) + "] executed with " + str(self.__get_value(action)))
