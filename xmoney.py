# Copyright (c) 2025 Nikola Tesla
# Money EXCHANGE class
# I wanted all monies moved within this system to be in the Naira denomination and all currencies to be deposited with Naira's exchange rate
# But instead, let there be any currency support as the base currency because people are going to hold funds in different currencies
# "What is money? Well, I think it's VANITY" - Nikola Tesla (c. 1909)
import paystack
from account import Account
import idanalyzer
SUPPORTED_CURRENCIES = ['NGN', 'USD']

class XMoney:
    def __init_(self, amount, currency, output_currency, owner):
        self.amount = amount
        self.uid = self.generate_uid
        self.signature = signature
        self.currency = currency
        self.output_currency = output_currency
        self.owner = owner

   
