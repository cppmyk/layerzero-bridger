# State interface defining the behavior of different states
class State:
    def handle(self, thread):
        pass


class InitialState(State):
    def handle(self, thread):
        pass
