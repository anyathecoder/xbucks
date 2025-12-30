# Copyright (c) 2025 Nikola Tesla
# Memory Pool (Mempool) for storing unconfirmed transactions
# It will be a very basic text file for storing all these data
import pickle
import json
import io

class Mempool:
    def __init__(self):
        self.sep = b'\n'
        self.mempool = self.load_mempool()
        
    def load_mempool(self):
        mempool = list()
        import base64
        try:
            file = open('./db/mempool.bin', 'rb')
            content = file.read()
            file.close()
        except OSError:
            return mempool

        tx_list = content.split(self.sep)
        for t in tx_list:
            if len(t) < 1:
                continue
            try:
                # Decode base64 then unpickle
                decoded = base64.b64decode(t)
                t_obj = self.parse_tx(decoded)
                mempool.append(t_obj)
            except Exception:
                continue
        return mempool
    
    def parse_tx(self, tx_data):
        tx = pickle.loads(tx_data)
        # Create an new dictionary for the mc
        mc = {}
        # Seperate the transaction into it's microformat and it's signature
        mcx = tx['mc']
        signature = tx['signature']
        # Then further seperate the mc
        array = mcx.split('|')
        # Add it into the database
        mc['sender'] = array[0]
        mc['recipient'] = array[1]
        mc['money'] = json.loads(array[2]) # Make it an array
        mc['time'] = array[3]
        mc['fees'] = array[4]
        mc['signature'] = signature
        return mc
    
    def store_tx(self, tranx):
        import base64
        file = open('./db/mempool.bin', 'ab')
        ## Serialize the data
        t = pickle.dumps(tranx)
        ## Base64 encode
        t_b64 = base64.b64encode(t)
        ## Write it to the file
        file.write(t_b64)
        file.write(self.sep)
        # Close the file handle
        file.close()
        ## Add the mempool
        tx = self.parse_tx(t)
        self.mempool.append(tx)

