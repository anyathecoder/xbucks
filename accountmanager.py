# Copyright (c) 2025 Nikola Tesla
# Account Manager Daemon (for management and creation of new accounts)
import account
import hashlib
import time
import sqlite3
import nowpayments

class AccountManager():
    def __init__(self, account_key, default='NGN'):
        self.account_key = account_key
        self.default_currency = ''
        self.db = sqlite3.connect('./db/account.db')

        self.cursor = self.db.cursor()
        ## I have to enter the currencies into the table
        data = [
            ('United States Dollar', 'USD', 'No', 'No', '0'),
            ('Nigerian Naira', 'NGN', 'Yes', 'Yes', '0'),
            ('South African Rand', 'ZAR', 'No', 'Yes', '0')
            ]
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS currency(currency_name,
                            currency_symbol, default_currency, kyc_auth, balance)""")
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS addresses(currency_symbol, address)""")

        # We will have a list of currencies that our user will be holding
        if self.get_snapshot() < 1:
             self.cursor.executemany("""INSERT INTO currency VALUES(?, ?, ?, ?, ?)""", data)

    def add_address(self, currency, address):
        cursor = self.db.cursor()
        cursor.execute("INSERT OR REPLACE INTO addresses (currency_symbol, address) VALUES (?, ?)", (currency, address))
        self.db.commit()

    def get_address(self, currency):
        cursor = self.db.cursor()
        res = cursor.execute("SELECT address FROM addresses WHERE currency_symbol = ?", (currency,))
        return res.fetchone()
        
    def get_default(self):
        cursor = self.db.cursor()
        res = cursor.execute('SELECT currency_symbol FROM currency WHERE default_currency="Yes"')
        return res.fetchone()

    def get_balance(self, cns):
        cursor = self.db.cursor()
        res = cursor.execute('SELECT balance FROM currency WHERE currency_symbol="'+cns+'"')
        return res.fetchone()
    
    def get_snapshot(self):
        cursor = self.db.cursor()
        res = cursor.execute("SELECT count(*) FROM currency")
        return res.fetchone()[0]

    def get_full_snapshot(self):
        cursor = self.db.cursor()
        res = cursor.execute("SELECT * FROM currency ORDER BY currency_symbol")
        return res.fetchall()

    def get_snapshot_hash(self):
        import json
        data = self.get_full_snapshot()
        # Serialize to canonical JSON string
        dump = json.dumps(data, sort_keys=True)
        return hashlib.sha256(dump.encode('utf-8')).hexdigest()
    
    def update_balance(self, currency, amount):
        # I create this so that accounts can be invoked
        cursor = self.db.cursor()
        cursor.execute("UPDATE currency SET balance = balance+"+str(amount)+" WHERE currency_symbol = '"+currency+"'")

    def connect(self):
        # Connect to wallet for transfer of funds and viewing balance
        return f"Connected to wallet for account {self.account_key}"


if __name__ == "__main__":
    acct = AccountManager('m2r4t8i7')
    cur = acct.get_default()
    print(cur[0])
    x = acct.get_balance('NGN')
    acct.update_balance('NGN', 500)
    y = acct.get_balance('NGN')
    print(x)
    print(y)
