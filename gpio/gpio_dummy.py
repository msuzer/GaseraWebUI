# Define your known mapping here
PIN_MAP = {
    "PC1": 65, "PC5": 69, "PC6": 70, "PC7": 71, "PC8": 72, "PC9": 73, "PC10": 74, "PC11": 75, "PC14": 78, "PC15": 79,
    "PH2": 226, "PH3": 227, "PH4": 228, "PH5": 229, "PH6": 230, "PH7": 231, "PH8": 232, "PH9": 233,
    "PI6": 262, "PI16": 272
}

print("GPIOController running in dummy mode (non-Linux platform)")

class GPIOController:
    def __init__(self, chip_name='gpiochip1'):
        self.pin_states = {}

    def read(self, pin_name):
        self.pin_states[PIN_MAP[pin_name]] = 1
        return 1

    def set(self, pin_name):
        self.pin_states[PIN_MAP[pin_name]] = 1
        return 1

    def reset(self, pin_name):
        self.pin_states[PIN_MAP[pin_name]] = 0
        return 0

    def dispatch(self, pin_name, action):
        if action == "read":
            return self.read(pin_name)
        elif action == "set":
            return self.set(pin_name)
        elif action == "reset":
            return self.reset(pin_name)
        elif action == "state":
            return self.pin_states.get(PIN_MAP[pin_name])
        else:
            raise ValueError(f"Unknown action: {action}")
