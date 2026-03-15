import random

class FizzBuzz:
    def __init__(self):
        self.i = 1
        self.output = ""

    def do_step(self):  # TLA+: Step
        if self.i <= 15:
            self.output = "FizzBuzz" if self.i % 15 == 0 else "Fizz" if self.i % 3 == 0 else "Buzz" if self.i % 5 == 0 else self.i
            self.i = self.i + 1
            print(f"output = {self.output}")
            print(f"i = {self.i}")
            return True
        return False

    def step(self):
        actions = []
        if self.i <= 15:
            actions.append(self.do_step)
        if actions:
            random.choice(actions)()

