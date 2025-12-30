
import time
import json

from mempool import Mempool
from ledger import Ledger
from account import Account
import hashlib

class Miner:
    def __init__(self, account_passphrase, account_name="default", difficulty=10, pod_k=40, pod_diff=16):
        self.account = Account(account_passphrase, account_name=account_name)
        self.mempool = Mempool()
        self.ledger = Ledger()
        self.difficulty = difficulty # legacy field, ignored
        self.pod_k = pod_k
        self.pod_diff = pod_diff

    def mine_block(self):
        print("Miner: Checking Mempool...")
        from hashcash import get_pod_engine
        pod = get_pod_engine(k_factor=self.pod_k, base_difficulty=self.pod_diff)

        # Reload mempool to get latest
        self.mempool = Mempool() 
        txs = self.mempool.mempool
        
        if not txs:
            print("Miner: No transactions to mine.")
            return None

        # Create Block payload
        last_entry = self.ledger.get_last_entry()
        if last_entry:
            prev_hash = last_entry.get('hash', '0'*64)
            index = last_entry.get('index', 0) + 1
        else:
            prev_hash = '0'*64
            index = 1

        # Calculate Total Amount for N
        total_amount = 0
        try:
            for tx in txs:
                if 'mc' in tx:
                    # Parse MC: owner|receiver|money_json|...
                    parts = tx['mc'].split('|')
                    if len(parts) > 2:
                        # Find the part that looks like json
                        for p in parts:
                            if p.strip().startswith('{') and '"amount":' in p:
                                try:
                                    money = json.loads(p)
                                    total_amount += float(money.get('amount', 0))
                                except: pass
        except Exception as e:
            print(f"Miner warning: could not parse amount: {e}")
            total_amount = 1
        
        if total_amount == 0: total_amount = 1 # Fallback
        print(f"Miner: Total amount in block: {total_amount}")

        # Fingerprint of transactions
        tx_data = json.dumps(txs, sort_keys=True, default=str)
        tx_fingerprint = hashlib.sha256(tx_data.encode('utf-8')).hexdigest()
        block_hash_input = f"{prev_hash}:{tx_fingerprint}:{index}"
        block_hash = hashlib.sha256(block_hash_input.encode('utf-8')).hexdigest()

        # Initialize Block with empty confirmations
        block = {
            'index': index,
            'prev_hash': prev_hash,
            'transactions': txs,
            'confirmations': [],
            'merkle_root': tx_fingerprint,
            'hash': block_hash # The ID of the block we are confirming
        }
        
        print(f"Miner: Starting PoD Mining for Block {index} (Value: {total_amount})...")
        
        # Mine until N reached
        while True:
            is_valid, n_req = pod.check_block_status(block)
            if is_valid:
                print(f"Miner: Block fully confirmed ({len(block['confirmations'])}/{n_req}).")
                break
                
            print(f"Miner: Need confirmation {len(block['confirmations'])+1}/{n_req}...")
            
            # Calculate difficulty for ME (this validator)
            diff = pod.calculate_difficulty(block, self.account.identity())
            
            # Solve
            nonce, conf_hash, ts_ms = pod.solve_puzzle(block['hash'], self.account.identity(), diff)
            
            if nonce is not None:
                print(f"Miner: Solved puzzle (diff {diff})! Nonce: {nonce}")
                conf = {
                    'validator': self.account.identity(),
                    'nonce': nonce,
                    'difficulty': diff,
                    'timestamp': ts_ms,
                    'hash': conf_hash
                }
                block['confirmations'].append(conf)
            else:
                print("Miner: Failed to solve puzzle.")
                return None

        # Save to Ledger
        self.ledger.write(block)
        print("Miner: Block saved to Ledger.")
        
        # Clear Mempool
        self.clear_mempool()
        
        return block

    def clear_mempool(self):
        # Nuke it for now
        print("Miner: Clearing Mempool...")
        try:
             open('./db/mempool.bin', 'wb').close()
             self.mempool.mempool = []
        except:
            pass

if __name__ == "__main__":
    # Test Miner
    miner = Miner(account_passphrase="miner_pass", account_name="miner1", difficulty=12)
    miner.mine_block()
