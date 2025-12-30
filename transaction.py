# Copyright (c) 2025 Nikola Tesla
import os
import sys
import datetime
import random
from account import Account
from accountmanager import AccountManager
from xdns import DNS
from mempool import Mempool
import json

def serialize(amount, currency, owner):
    money = dict()
    money['amount'] = str(amount) # Amount spent by the user
    money['currency'] = currency # The default owner
    money['owner'] = owner # The original owner of the currencys
    return money

        
class Transaction:
    def __init__(self, passphrase, receiver, amount, fees, currency, sender_account_name="default"):
        self.sender = Account(passphrase, account_name=sender_account_name)
        
        # Resolve receiver using DNS if it doesn't look like a raw key/address (e.g., simplistic check)
        # Assuming "long" strings are keys. Short ones names.
        if len(receiver) < 50:
             dns = DNS()
             resolved = dns.resolve(receiver)
             if resolved:
                 self.receiver = resolved
             else:
                 # Fallback or keep as is if not found (maybe it IS an address or un-registered)
                 self.receiver = receiver
        else:
            self.receiver = receiver

        self.amount = amount
        self.time = datetime.datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
        self.fees = fees # Normally, just a titbit is paid as fees by incentive for the miner
        self.currency = currency # receiver's currency
        self.manager = AccountManager(passphrase)
        self.signature = self.sign();
        # Account management class

    def sign(self):
        # Signs the transaction using the sender's private key
        signature = self.sender.sign(self.get_microformat());
        return signature

    def validate(self):
        # Validates the transaction especially if the transaction inputs do not pass the balance of the user, as well as if the user truely signed the transaction
        txmsg = self.get_microformat()
        if self.sender.verify(txmsg, self.signature) == False:
            return False
        # We will also check if the receiver is a valid xbucks user
        else:
            return True

    def generate_money_format(self):
        # Generate an XBucks Spendable Token
        # Useful for cross - currency transfer
        default_currency = self.manager.get_default() # I will have to know my currency
        money = serialize(self.amount, default_currency, self.sender.ixan())
        return money
        
    def get_microformat(self):
        # Get a streamed - down, interchangeable format of the transaction as a string of bytes
        mc_format = '|'.join([self.sender.ixan(), self.receiver, json.dumps(self.generate_money_format()), self.time, str(self.fees)])
        return mc_format;

    def get_xmif_format(self):
        """
        Generate an XBucks Money Interchange Format
        Used for storing trnasaction details and signature (for clarification)
        """
        xmif = {}
        mc = self.get_microformat()
        sign = self.sign()
        xmif['mc'] = mc
        xmif['signature'] = sign
        return dict(xmif)

    def submit(self):
        """
        Submit the transaction to the Mempool
        """
        mempool = Mempool()
        xmif = self.get_xmif_format()
        mempool.store_tx(xmif)
        print(f"Transaction submitted to Mempool: {xmif}")


