# Copyright (c) 2025 Nikola Tesla
# State for recording balances of nodes
import os
import zlib

class State:
    def __init__(self):
        self.state = dict();
        self.load('state')

    def load(self, db):
        # Loads the state from a contemporary database file in the system
        db_path = os.path.join('db/'+db+'.data')
        file_path = open(db_path, 'r')
        # Needs work
        # I'll have to do something about how the FileReader reads the file (it needs to read it as bytes)
        # Even if it reads it as str, I'll have to find a way to convert it into string
        file = file_path.read()
        string = file.split('\n')
        # Needs work
        # Count each entry in the state
        n = 0
        # Iter through the string
        for i in string:
            key_value = i.split('::')
            key = str(key_value[0])
            value = float(key_value[1])
            self.state[key] = value
            n += 1
        file_path.close()
        return str(n)+" values entered."
        

    def parse(self, microformat):
        # Parse a microformat to get the sender and receiver addresses as well as the amount transferred
        pass

    def record(self, sender, receiver, value):
        # Record a transaction
        pass

    def snapshot(self, values):
        # Gives the amount of money in the network
        pass
    
    def get_balance(self, address):
        # Gets the current balance of a user on the network
        pass
    
    def debit(self, sender, amount):
        # Debit a sender of that amount in the state
        if self.state[sender] > amount:
            self.state[sender] -= amount
            self.save()
        else:
            return "Cannot execute transaction: insufficient balance"

    def credit(self, receiver, amount):
        self.state[sender] += amount
        self.save()

    def save(self):
        db_handle = open('./db/state.data', 'w')
        state = ''
        # Convert the state into a string
        for r, s in self.state.items():
            state += r+"::"+str(s)
        db_handle.write(state)
        db_handle.close()


state = State()
print(state.state)
state.debit('MDkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDIgAC7qgOrchBl2L/MflJwHTJCKeDp/PC/mujjBgf/vSLbT4=', 990)
print(state.state)
