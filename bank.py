
# Copyright (c) 2025 Nikola Tesla
# Decentralized Banking & DEX Module

import time
import json
import random
import sqlite3
import hashlib
from accountmanager import AccountManager
from transaction import Transaction

class Bank:
    def __init__(self, account_manager):
        self.am = account_manager
        self.db = self.am.db # Reuse AccountManager DB connection
        self.cursor = self.db.cursor()
        
        # Ensure tables exist for Savings
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS savings(
            account_id TEXT, 
            currency TEXT, 
            balance REAL, 
            interest_rate REAL, 
            locked_until REAL)""")
        
        # Ensure USDT wallet tracking (if separate from main currency table)
        # We use the main 'currency' table for USDT balance, but 'addresses' table for external wallet addresses.
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS usdt_wallets(
            account_id TEXT PRIMARY KEY,
            wallet_address TEXT,
            private_key_enc TEXT
        )""")
        self.db.commit()

    def create_usdt_wallet(self, account_id):
        # Generate a unique USDT deposit address for the customer
        # In a real app, this would generate an actual TRC20/ERC20 address.
        # Here we mock it deterministically or randomly.
        addr = "0x" + hashlib.sha256(f"{account_id}-usdt-{time.time()}".encode()).hexdigest()[:40]
        try:
             self.cursor.execute("INSERT INTO usdt_wallets (account_id, wallet_address) VALUES (?, ?)", (account_id, addr))
             self.db.commit()
             return addr
        except sqlite3.IntegrityError:
             # Already exists
             return self.get_usdt_wallet(account_id)

    def get_usdt_wallet(self, account_id):
        res = self.cursor.execute("SELECT wallet_address FROM usdt_wallets WHERE account_id=?", (account_id,)).fetchone()
        if res:
            return res[0]
        return self.create_usdt_wallet(account_id)

    def deposit_fiat(self, amount, currency, card_details):
        # Process card payment (Mock)
        # Verify card...
        print(f"Processing deposit of {amount} {currency} via Card ends {card_details.get('number', '')[-4:]}...")
        time.sleep(1) # Simulate network
        
        # Credit user balance
        self.am.update_balance(currency, amount)
        print(f"Deposited {amount} {currency}.")
        return True

    def withdraw(self, amount, currency, target_account):
        # Check balance
        bal = self.am.get_balance(currency)
        current_bal = float(bal[0]) if bal else 0.0
        
        if current_bal < amount:
            raise ValueError("Insufficient funds")
            
        # Debit
        self.am.update_balance(currency, -amount)
        print(f"Withdrew {amount} {currency} to {target_account}.")
        return True

    def convert_fiat_to_usdt(self, fiat_currency, fiat_amount):
        # 1. Get Rate
        rate = DEX.get_rate(fiat_currency, "USDT")
        usdt_amount = fiat_amount * rate
        
        # 2. Debit Fiat
        self.withdraw(fiat_amount, fiat_currency, "INTERNAL_CONVERSION")
        
        # 3. Credit USDT
        # Ensure USDT exists in currency table (AccountManager might need 'add_currency' logic if dynamic? 
        # But 'update_balance' usually fails if row missing. AccountManager Init creates NGN,USD,ZAR.)
        # We need to ensure USDT row exists.
        self._ensure_currency("USDT")
        self.am.update_balance("USDT", usdt_amount)
        
        print(f"Converted {fiat_amount} {fiat_currency} -> {usdt_amount} USDT")
        return usdt_amount

    def _ensure_currency(self, symbol):
        # Internal helper to add currency row if missing
        res = self.cursor.execute("SELECT * FROM currency WHERE currency_symbol=?", (symbol,)).fetchone()
        if not res:
            self.cursor.execute("INSERT INTO currency VALUES (?, ?, ?, ?, ?)", ("Tether", symbol, "No", "No", "0"))
            self.db.commit()

    # --- Savings ---
    def deposit_savings(self, amount, currency, lock_days=30):
        # Interest rate logic
        rate = 0.05 # 5% APY fixed for demo
        
        # Debit main balance
        self.withdraw(amount, currency, "SAVINGS_DEPOSIT")
        
        # Add to savings
        lock_until = time.time() + (lock_days * 86400)
        account = self.am.account_key # Assuming single user per AccountManager instance
        
        self.cursor.execute("INSERT INTO savings VALUES (?, ?, ?, ?, ?)", 
                            (account, currency, amount, rate, lock_until))
        self.db.commit()
        return True

    def get_savings_balance(self):
        account = self.am.account_key
        res = self.cursor.execute("SELECT currency, balance, interest_rate, locked_until FROM savings WHERE account_id=?", (account,)).fetchall()
        return res


class DEX:
    # Production level decentralized exchange logic (AMM conceptual)
    
    POOLS = {
        ("USD", "USDT"): 1.0,   # Stable
        ("NGN", "USDT"): 0.001, # 1 NGN ~ 0.001 USDT (Mock)
        ("NGN", "USD"): 0.001,
        ("USDT", "NGN"): 1000.0,
        ("USD", "NGN"): 1000.0
    }
    
    @staticmethod
    def get_rate(from_curr, to_curr):
        if from_curr == to_curr: return 1.0
        
        pair = (from_curr, to_curr)
        if pair in DEX.POOLS:
            # Add some volatility or slippage simulation?
            base_rate = DEX.POOLS[pair]
            fluctuation = random.uniform(0.99, 1.01)
            return base_rate * fluctuation
            
        # Recursive / Inverse path check?
        inverse = (to_curr, from_curr)
        if inverse in DEX.POOLS:
            return (1.0 / DEX.POOLS[inverse])
            
        return 0.0 # No pool

    @staticmethod
    def swap(account_manager, from_curr, to_curr, amount):
        rate = DEX.get_rate(from_curr, to_curr)
        if rate == 0.0:
            raise ValueError(f"No liquidity pair for {from_curr}/{to_curr}")
            
        receive_amount = amount * rate
        
        # Execute Swap
        # Debit
        bal = account_manager.get_balance(from_curr)[0]
        if float(bal) < amount:
             raise ValueError("Insufficient balance")
             
        account_manager.update_balance(from_curr, -amount)
        
        # Credit
        # Ensure dest currency exists
        cursor = account_manager.db.cursor()
        res = cursor.execute("SELECT * FROM currency WHERE currency_symbol=?", (to_curr,)).fetchone()
        if not res:
             cursor.execute("INSERT INTO currency VALUES (?, ?, ?, ?, ?)", (to_curr, to_curr, "No", "No", "0"))
             
        account_manager.update_balance(to_curr, receive_amount)
        
        return receive_amount, rate

