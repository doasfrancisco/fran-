import random

class HelloWorld:
    def __init__(self):
        self.printed = False

    def print(self):  # TLA+: Print
        if self.printed == False:
            self.printed = True
            print(f"printed = {self.printed}")
            return True
        return False

    def step(self):
        actions = []
        if self.printed == False:
            actions.append(self.print)
        if actions:
            random.choice(actions)()

    def check(self):
        assert self.printed in {True, False}, "TypeInvariant violated"

