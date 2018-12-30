#!/usr/bin/python2
# -*- coding:utf-8 -*-
#
# Author: Mariam Rady (m@ry.am)
# Author: Jan Kubovy (jan@kubovy.eu)
#
import ast
import json
import os
import time
import traceback
import yaml
from copy import deepcopy
from itertools import product
from jinja2 import Template, StrictUndefined, TemplateError

from lib.ColorGRB import ColorGRB
from lib.FileWatcherHandler import observe
from lib.ModuleLooper import ModuleLooper


def _reference_based_value(value, reference):
    if value is None:
        if isinstance(reference, str):
            return ""
        elif isinstance(reference, bool):
            return False
        elif isinstance(reference, int):
            return 0
        elif isinstance(reference, float):
            return 0.0
        else:
            return None
    else:
        return value


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

    def __init__(self, description_file=None, transactional=True, optimize=True, debug=False):
        super(StateMachine, self).__init__(debug=debug)

        self.__transactional = transactional
        self.__optimize = optimize
        self.__global_state = {}
        self.__description_file = description_file
        self.__optimized_description_file = os.path.splitext(description_file)[0] + '.optimized.yml'
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

        reload_file = not self.__optimize or not os.path.isfile(self.__optimized_description_file) \
            or os.stat(self.__description_file).st_mtime > os.stat(self.__optimized_description_file).st_mtime

        description_file = self.__description_file if reload_file else self.__optimized_description_file

        self.logger.info("Description file: " + description_file + "...")
        descriptions = yaml.load_all(open(description_file, "r"))

        for description in descriptions:
            self.__devices = description['devices']
            self.__variables = description['vars']
            self.__initial_state = description['initial_state'] if 'initial_state' in description.keys() else None
            for state in description['states']:
                self.logger.info("Loading " + str(state['name']) + " state ...")
                if self.__initial_state is None:
                    self.__initial_state = state['name']
                self.__states[state['name']] = state
                conditions = []
                for condition in state['conditions']:
                    action_to_evaluate = False
                    if reload_file and 'expressions' in condition.keys():
                        for expression in condition['expressions']:
                            if isinstance(expression, dict) and 'name' in expression.keys():
                                name = expression.pop('name', None)
                                expression['kind'] = self.__devices[name]['kind']
                                expression['key'] = self.__devices[name]['key']

                    if 'actions' in condition.keys():
                        for action in condition['actions']:
                            if reload_file and 'name' in action.keys():
                                name = action.pop('name', None)
                                action['kind'] = self.__devices[name]['kind']
                                action['key'] = self.__devices[name]['key']

                            if 'eval' in action.keys() and action['eval']:
                                action_to_evaluate = True
                                if action['value'] not in self.__templates.keys():
                                    self.__templates[action['value']] = Template(action['value'],
                                                                                 undefined=StrictUndefined)

                            elif reload_file:
                                value = self.__get_value(action)
                                if value is None:
                                    raise ValueError('NULL action value on "' + str(action) + '"!')
                                action['value'] = value

                    if reload_file and action_to_evaluate:
                        self.__global_state = {}
                        combinations = {}
                        if 'expressions' in condition.keys():
                            for expression in condition['expressions']:
                                if isinstance(expression, dict) and 'value' in expression.keys():
                                    self.set_state(expression, value=expression['value'], evaluate=False)
                                else:
                                    possible_values = self.__get_possible_values(expression)
                                    composite = self.__get_kind(expression) + '|' + self.__get_key(expression)
                                    if len(possible_values) > 0:
                                        combinations[composite] = possible_values
                                        self.set_state(expression, value=possible_values[0], evaluate=False)

                        if len(combinations.keys()) > 0:
                            self.logger.debug("Expanding " + str(combinations) + ": " +
                                              str(list(product(*combinations.values()))))
                            for combination in product(*combinations.values()):
                                combined_expressions = deepcopy(condition['expressions'])
                                for idx, value in enumerate(combination):
                                    composite = combinations.keys()[idx]
                                    (kind, key) = composite.split('|', 2)
                                    self.set_state(kind, key, value, evaluate=False)
                                    for e in combined_expressions:
                                        if isinstance(e, dict) and e['kind'] == kind and str(e['key']) == key:
                                            e['value'] = value

                                evaluated_actions = deepcopy(condition['actions'])
                                for action in evaluated_actions:
                                    value = self.__get_value(action, remove_evaluation_tag=True)
                                    if value is None:
                                        raise ValueError('NULL action value on "' + str(action) + '"!')
                                    action['value'] = value

                                conditions.append({'expressions': combined_expressions, 'actions': evaluated_actions})
                        else:
                            adapted_condition = {}
                            if 'expressions' in condition.keys():
                                adapted_condition['expressions'] = deepcopy(condition['expressions'])

                            adapted_condition['actions'] = deepcopy(condition['actions'])
                            for action in adapted_condition['actions']:
                                value = self.__get_value(action, remove_evaluation_tag=True)
                                if value is None:
                                    raise ValueError('NULL action value on "' + str(action) + '"!')
                                action['value'] = value

                            conditions.append(adapted_condition)
                    else:
                        conditions.append(condition)

                state['conditions'] = conditions

        if reload_file:
            yaml.dump(
                {
                    'devices': self.__devices,
                    'vars': self.__variables,
                    'initial_state': self.__initial_state,
                    'states': self.__states.values()
                },
                file(self.__optimized_description_file, 'w'))

        self.__global_state = {}

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

    def transit(self, new_state_name):
        self.logger.info("Transiting " + (self.__current_state['name'] if self.__current_state is not None else "N/A") +
                         " -> " + new_state_name)
        self.__current_state = self.__states[new_state_name]

        self.logger.debug("Evaluating gate \"ENTER\" in \"" + str(new_state_name) + "\" state")
        self.__evaluate("ENTER")
        self.logger.debug("Evaluating gate \"INITIALIZED\" in \"" + str(new_state_name) + "\" state")
        self.__evaluate("INITIALIZED")
        if self.__current_state is not None and new_state_name == self.__current_state['name']:
            self.logger.debug("Evaluating gate \"NORMAL\" in \"" + str(new_state_name) + "\" state")

    def get_state(self, item, key=None, state=None):
        state = self.__global_state if state is None else state
        kind = item if isinstance(item, basestring) else self.__get_kind(item)
        key = str(key) if isinstance(item, basestring) else self.__get_key(item)

        if kind not in state.keys() or state[kind] is None:
            state[kind] = {}

        return state[kind][key] if key in state[kind] else None

    def set_state(self, item, key=None, value=None, evaluate=True):
        item = self.__devices[item] if isinstance(item, basestring) and key is None else item
        kind = item if isinstance(item, basestring) else self.__get_kind(item)
        key = str(key) if isinstance(item, basestring) else self.__get_key(item)

        if kind not in self.__global_state.keys() or self.__global_state[kind] is None:
            self.__global_state[kind] = {}

        previous_state = deepcopy(self.__global_state) if evaluate else None
        previous_value = self.get_state(kind, key) if evaluate else None
        if not evaluate or previous_value != value:
            self.logger.debug(kind + "[" + str(key) + "]: " + str(previous_value) + " -> " + str(value))
            self.__global_state[kind][key] = value
            if evaluate:
                self.__evaluate("NORMAL", previous_state)
            self.__template_variables_cache = None
        return previous_value != value

    def on_bluetooth_message(self, message):
        if message == "BT:CONNECTED":
            self.set_state('bluetooth', 'connected', True)
        elif message == "BT:DISCONNECTED":
            self.set_state('bluetooth', 'connected', False)
            # self.execute({'kind': 'lcd', 'key': None, 'value': "\n         BT\n\n--= DISCONNECTED =--"})
        elif message.startswith("BT:IDD:"):
            bt_id = message[7:]
            self.set_state('bluetooth', 'device', bt_id)
        elif message.startswith("TBC:PULL"):
            self.module_bluetooth.send(json.dumps({'devices': self.__devices,
                                                   'vars': self.__variables,
                                                   'states': self.__states.values()}))
        elif message.startswith("TBC:"):
            for msg in message[4:].split(";"):
                parts = msg.split(",", 3)
                self.logger.debug(msg + " -> " + str(parts))
                if len(parts) == 3 and parts[0] == 'action':
                    self.__execute({'name': parts[1], 'value': parts[2], 'eval': True})
                elif len(parts) >= 2 and parts[0] == 'transit':
                    self.transit(parts[1])
                elif len(parts) == 3 and parts[0] == 'state':
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
            super(StateMachine, self).on_mqtt_message(path, payload)
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
                        value = self.__template_variables(with_vars=False)
                        # self.bluetooth_server.send(yaml.dump(value, default_flow_style=False, encoding='utf-8'))
                        self.module_bluetooth.send(json.dumps(value))
                    else:
                        self.set_state(kind, key, value, evaluate=False)
                        value = self.__template_variables(with_vars=False) if value == 'DUMP' else value
                        self.module_bluetooth.send(json.dumps({key: value}))
            elif kind == 'lcd' and self.module_lcd is not None:
                for key, value in rest.items():
                    if key == "clear":
                        self.module_lcd.post(None)
                    elif key == "reset":
                        self.module_lcd.post("reset")
                    elif key == "backlight":
                        self.module_lcd.post(value)
                    elif isinstance(key, int) and value != "IGNORE":
                        self.module_lcd.post(value, int(key))
                    elif value != "IGNORE":
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
            if delay is not None and delay > 0:
                time.sleep(int(delay) / 1000.0)
            self.transit(state)

        time.sleep(0.4)

    def __get_kind(self, item):
        if isinstance(item, basestring):
            return "STR"
        elif 'kind' in item.keys():
            return item['kind']
        elif 'name' in item.keys() and item['name'] in self.__devices.keys() and 'kind' in self.__devices[item['name']]:
            return self.__devices[item['name']]['kind']
        else:
            return None

    def __get_key(self, item):
        key = None
        if isinstance(item, basestring):
            key = item
        elif 'key' in item.keys():
            key = item['key']
        elif 'name' in item.keys() and item['name'] in self.__devices and 'key' in self.__devices[item['name']]:
            key = self.__devices[item['name']]['key']
        return str(key) if key is not None else None

    def __get_descriptor(self, item):
        if item is not None:
            value = str(self.__get_kind(item)) + "[" + str(self.__get_key(item)) + "]"
            if not isinstance(item, basestring) and 'name' in item.keys():
                value += " (" + item['name'] + ")"
        else:
            value = "N/A"
        return value

    def __get_possible_values(self, item):
        if isinstance(item, dict) and 'values' in item.keys():
            possible_values = item['values']
        elif isinstance(item, dict) and 'name' in item.keys() and item['name'] in self.__devices \
                and 'values' in self.__devices[item['name']]:
            possible_values = self.__devices[item['name']]['values']
        elif isinstance(item, dict) and 'kind' in item.keys() and 'key' in item.keys():
            var = next((v for n, v in self.__devices.iteritems()
                        if v['kind'] == item['kind'] and v['key'] == item['key']), None)
            possible_values = var['values'] if var is not None and 'values' in var.keys() else None
        else:
            possible_values = None

        if isinstance(possible_values, basestring):
            possible_values = self.__variables[possible_values]

        if possible_values is None and isinstance(item, dict) and \
                ('kind' in item.keys() and item['kind'] == 'mcp23017' or
                 'name' in item.keys() and item['name'] in self.__devices and self.__devices[item['name']]['kind']):
            possible_values = [False, True]

        self.logger.debug("Possible value of " + self.__get_descriptor(item) + ": " + str(possible_values))
        return possible_values

    def __template_variables(self, with_vars=True):
        while self.__template_variables_cache is None:
            self.__template_variables_cache = self.__variables.copy()
            if self.__template_variables_cache is not None:
                self.__template_variables_cache.update(self.__global_state)

            device_map = {}
            for device_name, device in self.__devices.iteritems():
                value = self.get_state(device)
                if value is not None:
                    device_map[device_name] = value

            if self.__template_variables_cache is not None:
                self.__template_variables_cache.update(device_map)

            if self.__template_variables_cache is not None and with_vars:
                self.__template_variables_cache.update({'vars': self.__template_variables_cache})

            if self.__template_variables_cache is None:
                time.sleep(0.5)
        return self.__template_variables_cache

    def __get_value(self, item, evaluate=True, remove_evaluation_tag=False):
        try:
            # self.logger.debug("Value: " + str(item) + " eval=" + str(evaluate))
            if evaluate and isinstance(item, dict) and \
                    'value' in item.keys() and 'eval' in item.keys() and item['eval']:
                try:
                    # self.logger.debug("Template: " + item['value'] + " -> " + str(self.templates[item['value']]))
                    # self.logger.debug("Template: " + item['value'])
                    if item['value'] not in self.__templates:
                        self.__templates[item['value']] = Template(item['value'], undefined=StrictUndefined)
                    value = self.__templates[item['value']].render(self.__template_variables())
                    if remove_evaluation_tag:
                        item.pop('eval', None)

                    # self.logger.debug("Rendered Value: " + str(value))
                    if isinstance(value, basestring):
                        try:
                            value = ast.literal_eval(value)
                        except BaseException as e:
                            self.logger.debug(str(e) + ' in "' + str(value).replace("\n", "\\n") + '"')
                            # traceback.print_exc()
                except AttributeError as e:
                    self.logger.error("Template attribute error: " + str(e.message))
                    traceback.print_exc()
                    value = item['value']
                except TemplateError as e:
                    self.logger.info(str(e.message) + " in " + str(item['value']))
                    value = item['value']
            elif isinstance(item, dict) and 'value' in item.keys():
                value = item['value']
            elif isinstance(item, dict) and 'kind' in item.keys() and item['kind'] == 'GOTO':
                value = 0
            else:
                value = None

            value = self.__variables[value] if value in self.__variables.keys() else value

            if isinstance(value, dict) and 'color' in value.keys() and isinstance(value['color'], dict) \
                    and 'red' in value['color'].keys() \
                    and 'green' in value['color'].keys() \
                    and 'blue' in value['color'].keys():
                color = value['color']
                value['color'] = ColorGRB(color['red'], color['green'], color['blue'])

            return value
        except:
            self.logger.error("Problem getting value!")
            traceback.print_exc()
            return None

    def __evaluate(self, gate="NORMAL", previous_state=None):
        """Evaluation

        :param gate: one of: ENTER, INITIALIZED, NORMAL
        """
        self.__transaction_start()
        current_state = deepcopy(self.__current_state)
        if current_state is not None and 'conditions' in current_state.keys():
            for condition in current_state['conditions']:
                if 'name' in current_state.keys() and 'name' in self.__current_state.keys() \
                        and current_state['name'] == self.__current_state['name'] \
                        and ('only' not in condition.keys() or condition['only'].upper() == gate):
                    # self.logger.debug("Condition: " + str(condition))
                    result = True
                    changed = False
                    if 'expressions' in condition.keys():
                        for expression in condition['expressions']:
                            additional_info = ""
                            if isinstance(expression, basestring):
                                result = result and expression.upper() == gate
                                changed = True
                            elif ('only' not in expression.keys() or expression['only'].upper() == gate) \
                                    and gate in ['INITIALIZED', 'NORMAL']:
                                value = self.__get_value(expression) if 'value' in expression.keys() else None
                                current = _reference_based_value(self.get_state(expression), value)
                                previous = _reference_based_value(self.get_state(expression, state=previous_state)
                                                                  if previous_state is not None else None, value)

                                result = result and (value is None or str(current) == str(value))
                                changed = changed or str(current) != str(previous) or gate != "NORMAL"
                                additional_info = str(previous) + " -> " + str(current) + " ?= " + str(value)
                            self.logger.debug("Expression: " + self.__get_descriptor(expression) +
                                              " in state " + current_state['name'] + "[" + gate + "] " +
                                              additional_info + " => " + str(result) +
                                              (" CHANGED " if changed else " UNCHANGED "))
                    else:
                        result = gate == "ENTER"
                        changed = True

                    if 'name' in current_state.keys() and 'name' in self.__current_state.keys() \
                            and current_state['name'] == self.__current_state['name'] \
                            and result and changed:
                        # expression = condition['expressions'] if 'expressions' in condition.keys() else None
                        self.logger.debug("Condition in " + current_state['name'] + "[" + gate + "] state FIRED!")
                        if 'actions' in condition.keys():
                            for action in condition['actions']:
                                self.logger.debug(" -> action: " + self.__get_descriptor(action) + " = " +
                                                  str(self.__get_value(action)))
                                if 'only' not in action.keys() or action['only'].upper() == gate:
                                    self.__execute(action, gate in ['INITIALIZED', 'NORMAL'])

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
            if delay is not None and delay > 0:
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
                self.set_state(action, value=value, evaluate=False)
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
