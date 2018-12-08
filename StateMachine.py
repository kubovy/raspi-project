import traceback
import yaml
from ModuleMQTT import ModuleMQTT


class StateMachine(ModuleMQTT):

    MAX_INDEX = 50

    current_state = None
    states = {}
    global_state = {}
    interrupted = False

    def __init__(self, client, service_name, description_file="state-machine.yml", debug=False):
        super(StateMachine, self).__init__(client, service_name, "state-machine", debug)

        initial_state = None
        descriptions = yaml.load_all(open(description_file, "r"))
        for description in descriptions:
            for state in description:
                self.logger.debug(" - " + str(state['name']))
                if initial_state is None:
                    initial_state = state['name']
                self.states[state['name']] = state

        self.logger.debug("Initial: " + str(initial_state))
        for k in self.states.keys():
            self.logger.debug(" - " + str(k) + ": " + str(self.states[k]))

        self.transit(initial_state)

    def on_message(self, path, payload):
        if len(path) == 2:
            try:
                self.set_state(path[0], int(path[1]), payload)
            except:
                self.logger.error('Oops!')
                traceback.print_exc()
        else:
            self.logger.debug("Current state: " + str(self.current_state['name']))

    def transit(self, new_state):
        self.logger.debug("Transiting to: " + new_state)
        self.current_state = self.states[new_state]

        if 'enter' in self.states[new_state].keys():
            for action in self.states[new_state]['enter']:
                self.execute(action)

    def evaluate(self):
        self.logger.debug("Current state: " + str(self.current_state['name']))
        if 'conditions' in self.current_state:
            for condition in self.current_state['conditions']:
                # self.logger.debug("Condition: " + str(condition))
                result = True
                for expression in condition['expressions']:
                    result = result and \
                             str(self.get_state(expression['kind'], expression['index'])) == str(expression['value'])
                if result:
                    self.logger.debug("Condition: " + str(condition) + " FIRED!")
                    self.execute(condition['action'])

    def get_state(self, kind, index=0):
        if kind not in self.global_state.keys() or self.global_state[kind] is None:
            self.global_state[kind] = [None for _ in range(self.MAX_INDEX)]

        index = index % self.MAX_INDEX if index >= self.MAX_INDEX else index
        return self.global_state[kind][index]

    def set_state(self, kind, index=0, value=None):
        if kind not in self.global_state.keys() or self.global_state[kind] is None:
            self.global_state[kind] = [None for _ in range(self.MAX_INDEX)]

        index = index % self.MAX_INDEX if index >= self.MAX_INDEX else index
        previous_value = self.get_state(kind, index)
        if previous_value != value:
            self.global_state[kind][index] = value
            self.evaluate()

        return previous_value != value

    def execute(self, action):
        if action['kind'] == 'GOTO':
            self.logger.debug("Going to: " + action['value'])
            self.transit(action['value'])
        else:
            self.logger.debug("Executing " + str(action['kind']) + "[" + str(action['index']) + "] executed with " + str(action['value']))
