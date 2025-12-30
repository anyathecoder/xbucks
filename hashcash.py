
# Proof - Of - Diplomacy anti - spam system
# A proof - of - originality system used to time - check, vote and confirm blocks
import hashlib
import json
import time
import math

# ----------------- Utilities -----------------
def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def leading_zero_bits(hex_digest: str) -> int:
    # Count leading zero bits
    b = bin(int(hex_digest, 16))[2:].zfill(256)
    return len(b) - len(b.lstrip('0'))

# ----------------- PoD Consensus Engine -----------------

class ProofOfDiplomacy:
    def __init__(self, k_factor=40, base_difficulty=16):
        self.k = k_factor
        self.base_difficulty = base_difficulty # Bits

    def calculate_n(self, block_size_bytes, total_amount_titan):
        # The number ,n , varies with directly with the speed of confirmation (bytes/sec) 
        # and inversely with the amount issued out (titan).
        # This formula is an interpretation of the requirement.
        # Assuming a target 'speed' of network? or block density?
        # Let's use a simpler heuristic for now: 
        # n = max(3, k * (size / amount)) 
        # This ensures larger blocks with small value have high n (anti-spam).
        if total_amount_titan <= 0: total_amount_titan = 1 # Avoid div by zero
        
        # Heuristic: n scales with size/value ratio
        n = int(self.k * (block_size_bytes / total_amount_titan))
        return max(3, n) # Minimum 3 confirmations

    def calculate_difficulty(self, block, validator_id):
        # The Hashcash puzzle will be increased if the same user tries to confirm it again.
        # It increases (with an additional zero collision = +4 bits usually, or +1 bit?)
        # "additional zero collision" usually means hex digit -> 4 bits.
        
        count = 0
        if 'confirmations' in block:
            for conf in block['confirmations']:
                if conf.get('validator') == validator_id:
                    count += 1
        
        # Increase difficulty for same user
        # Base difficulty + (count * 4 bits)
        return self.base_difficulty + (count * 4)

    def solve_puzzle(self, block_hash, validator_id, difficulty, max_tries=10_000_000):
        """
        Solve PoD puzzle for a block.
        Returns: (nonce, conf_hash, timestamp_ms)
        """
        nonce = 0
        start_time = time.time()
        
        while nonce < max_tries:
            ts_ms = int(time.time() * 1000)
            # Payload: BlockHash + Validator + Nonce + Diff + TS
            payload = f"{block_hash}:{validator_id}:{nonce}:{difficulty}:{ts_ms}"
            h = sha256_hex(payload)
            
            if leading_zero_bits(h) >= difficulty:
                return nonce, h, ts_ms
            
            nonce += 1
        return None, None, None

    def verify_confirmation(self, block_hash, conf):
        # Verify a single confirmation entry
        validator = conf['validator']
        nonce = conf['nonce']
        difficulty = conf['difficulty']
        ts_ms = conf['timestamp']
        conf_hash = conf['hash']
        
        payload = f"{block_hash}:{validator}:{nonce}:{difficulty}:{ts_ms}"
        h = sha256_hex(payload)
        
        if h != conf_hash:
            return False
        if leading_zero_bits(h) < difficulty:
            return False
        return True

    def check_block_status(self, block):
        # Check if block has enough confirmations
        # 1. Calc N
        txs = block.get('transactions', [])
        size = len(json.dumps(txs, default=str))
        amount = sum(float(tx.get('mc', '').split('|')[2].split('"amount": "')[1].split('"')[0]) for tx in txs if 'mc' in tx) # Rough parsing
        if amount == 0: amount = 1
        
        n_required = self.calculate_n(size, amount)
        
        confirmations = block.get('confirmations', [])
        if len(confirmations) >= n_required:
            return True, n_required
        return False, n_required

# Helper func for existing code compatibility
def get_pod_engine(k_factor=40, base_difficulty=16):
    return ProofOfDiplomacy(k_factor, base_difficulty)
