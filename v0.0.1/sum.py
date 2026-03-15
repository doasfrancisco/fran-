import random

class Sum:
    def __init__(self):
        self.i = 1
        self.sum = 0

    def add(self):  # TLA+: Add
        if self.i <= 3:
            self.sum = self.sum + self.i
            self.i = self.i + 1
            print(f"sum = {self.sum}")
            print(f"i = {self.i}")
            return True
        return False

    def step(self):
        actions = []
        if self.i <= 3:
            actions.append(self.add)
        if actions:
            random.choice(actions)()

    def check(self):
        assert self.sum >= 0, "SumInvariant violated"

