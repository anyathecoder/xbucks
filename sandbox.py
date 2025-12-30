# Sandbox for testing code
# Copyright (c) 2025 The Tesla Brothers (Nikola, Mikhail, and Zeev)
from transaction import Transaction
from account import Account
from mempool import Mempool
import pickle
import json
import sqlite3

tx = Transaction('m2r4t8i7', '007234586798', 1000, 0.0001, 'NGN')
xmif = tx.get_xmif_format()

src = sqlite3.connect('./db/account.db')
