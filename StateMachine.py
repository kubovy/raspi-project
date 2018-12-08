import traceback
import yaml
import copy
from ModuleMQTT import ModuleMQTT
from jinja2 import Template


class StateMachine(ModuleMQTT):

    MAX_INDEX = 50

    devices = {}
    variables = {}
    current_state = None
    states = {}
    global_state = {}
    interrupted = False

    lcd = None
    mcp23017 = None
    ws281x_indicators = None

    def __init__(self, client, service_name, description_file="state-machine.yml", debug=False):
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
        self.transit(self.initial_state)

    def on_message(self, path, payload):
        if len(path) == 2:
            try:
                self.set_state(path[0], int(path[1]), payload)
            except:
                self.logger.error('Oops!')
                traceback.print_exc()
        elif len(path) == 1 and path[0] == 'restart':
            self.start()
        else:
            self.logger.debug("Current state: " + str(self.current_state['name']))

    def transit(self, new_state):
        self.logger.debug("Transiting to: " + new_state)
        self.current_state = self.states[new_state]

        self.evaluate("enter")
        self.evaluate("initializing")
        self.evaluate("initialized")

    def get_kind(self, item):
        return item['kind'] if 'kind' in item.keys() else self.devices[item['name']]['kind']

    def get_index(self, item):
        if 'index' in item.keys():
            return item['index']
        elif 'name' in item.keys() and item['name'] in self.devices:
            return self.devices[item['name']]['index']
        else:
            return None

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
                except AttributeError:
                    value = item['value']
            else:
                value = item['value']

            return self.variables[value] if value in self.variables.keys() else value
        except:
            self.logger.error("Problem getting value!")
            traceback.print_exc()
            return None

    def evaluate(self, state="normal", previous_state=None):
        self.logger.debug("Current state: " + str(self.current_state['name']) + " evaluating in state " + state)
        if 'conditions' in self.current_state.keys():
            for condition in self.current_state['conditions']:
                # self.logger.debug("Condition: " + str(condition))
                result = True
                changed = False
                if 'expressions' in condition.keys():
                    for expression in condition['expressions']:
                        if (state == "normal" or state == "initializing") and not isinstance(expression, basestring):
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
                            changed = changed or str(current) != str(previous) or state != "normal"
                            # self.logger.debug("Expression " + str(expression) + ": " +
                            #                   str(current) + " <> " + str(value) + "[" + str(type(value)) + "] / " +
                            #                   str(current) + " <> " + str(previous) + " => " +
                            #                   str(result) + "/" + str(changed))
                        elif isinstance(expression, basestring):
                            self.logger.debug(expression.lower() + " <> " + state)
                            result = result and expression.lower() == state
                            changed = True
                else:
                    result = state == "enter"
                    changed = True

                if result and changed:
                    self.logger.debug("Condition: " + str(condition) + " FIRED!")
                    if 'actions' in condition.keys():
                        for action in condition['actions']:
                            self.logger.debug("Action " + str(action))
                            if 'only' not in action.keys() or action['only'] == state:
                                self.execute(action, state in ['normal', 'initialized'])

    def get_state(self, item, index=0, state=None):
        state = self.global_state if state is None else state
        kind = item if isinstance(item, basestring) else self.get_kind(item)
        index = index if isinstance(item, basestring) else self.get_index(item)

        if kind not in state.keys() or state[kind] is None:
            state[kind] = [None for _ in range(self.MAX_INDEX)]

        index = index % self.MAX_INDEX if index >= self.MAX_INDEX else index
        return state[kind][index]

    def set_state(self, item, index=0, value=None):
        kind = item if isinstance(item, basestring) else self.get_kind(item)
        index = index if isinstance(item, basestring) else self.get_index(item)

        if kind not in self.global_state.keys() or self.global_state[kind] is None:
            self.global_state[kind] = [None for _ in range(self.MAX_INDEX)]

        index = index % self.MAX_INDEX if index >= self.MAX_INDEX else index
        previous_state = copy.deepcopy(self.global_state)
        previous_value = self.get_state(kind, index)
        if previous_value != value:
            self.logger.debug(kind + "[" + str(index) + "]: " + str(previous_value) + " -> " + str(value))
            self.global_state[kind][index] = value
            self.evaluate("normal", previous_state)

        return previous_value != value

    def execute(self, action, with_goto=True):
        # self.logger.debug("Action: " + self.get_kind(action) +
        #                   "[" + ("N/A" if self.get_index(action) is None else str(self.get_index(action))) + "]: " +
        #                   str(self.get_value(action)))
        if self.get_kind(action) == 'GOTO' or self.get_kind(action) == 'JUMPTO':
            if with_goto or self.get_kind(action) == 'JUMPTO':
                self.logger.debug("Going to: " + self.get_value(action))
                self.transit(self.get_value(action))
        elif self.get_kind(action) == 'lcd' and self.lcd is not None:
            if self.get_index(action) is not None:
                self.lcd.set_line(self.get_index(action), self.get_value(action))
            else:
                self.lcd.clear()
                self.lcd.set(self.get_value(action))
        elif self.get_kind(action) == 'mcp23017' and self.mcp23017 is not None:
            self.mcp23017.set(self.get_index(action), self.get_value(action))
        elif self.get_kind(action) == 'ws281x-indicators' and self.ws281x_indicators is not None:
            self.ws281x_indicators.set(self.get_index(action), self.get_value(action))
        else:
            self.logger.debug("Unknown " + str(self.get_kind(action)) +
                              "[" + str(self.get_index(action)) + "] executed with " + str(self.get_value(action)))
