# Copyright (c) 2025 Nikola Tesla
# Ledger class
# Interface to the Ledger database file which is an unbroken chain of transactions
import os
import binascii

class Ledger:
    def __init__(self):
        self.ledger = []
        self.sep = b'\n'
        self.db_path = os.path.join('db/ledger.data')
        self.load_ledger()
   
    def read(self):
        try:
            file = open(self.db_path, 'rb')
            data = file.read()
            file.close()
            return data
        except OSError:
            return b''

    def load_ledger(self):
        import base64
        import pickle
        data = self.read()
        entries = data.split(self.sep)
        for i in entries:
            if len(i) < 1:
                continue
            try:
                decoded = base64.b64decode(i)
                # Assuming entry is pickled transaction/block
                entry = pickle.loads(decoded)
                self.ledger.append(entry)
            except Exception:
                continue
    
    def write(self, entry):
        import base64
        import pickle
        
        # Serialize and encode
        serialized = pickle.dumps(entry)
        encoded = base64.b64encode(serialized)
        
        file = open(self.db_path, 'ab')
        file.write(encoded)
        file.write(self.sep)
        file.close()
        
        self.ledger.append(entry)

    def get_last_entry(self):
        if self.ledger:
            return self.ledger[-1]
        return None

if __name__ == "__main__":
    ledger = Ledger()
    print(f"Ledger loaded with {len(ledger.ledger)} entries")
