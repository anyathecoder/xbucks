# Copyright (c) 2025 Nikola Tesla
# Account class
# An account is capable of holding and spending fiat money with XBucks by making signatures with its keys

from Crypto.PublicKey import ECC
from Crypto.PublicKey.ECC import import_key
from util import bytes_to_long, long_to_bytes
import os
import random
import itertools

class Account():
    def __init__(self, passphrase, account_name="default"):
        self.public_key = None
        self.private_key = None
        self.passphrase = passphrase
        self.account_name = account_name
        keydict = self.create_keys()

    def create_keys(self):
        # Create two directories, a, for Private Key and b, Public Key
        if self.account_name == "default":
             a = './keys/privatekey.pem'
             b = './keys/publickey.pem'
        else:
             a = f'./keys/{self.account_name}_privatekey.pem'
             b = f'./keys/{self.account_name}_publickey.pem'
        try:
            privatekey_file = open(a, 'r')
            publickey_file = open(b, 'r')
            
            private_key = privatekey_file.read();
            public_key = publickey_file.read();

            # Just change the key configs
            # Decode the passphrase
            passphrase = self.passphrase
            # Then just change the key configs
            self.private_key = import_key(private_key, passphrase)
            self.public_key = import_key(public_key, passphrase)
        except FileNotFoundError:
            # Define the new keys
            pkey = ECC.generate(curve='secp256r1')
            public_pkey = pkey.public_key()
            #if private_key == None and public_key == None: #FileNotFoundError
            # Now create two file instances that I will use to write to the system
            # Private Key
            private_dir = open(a, 'x')
            private_dir.close()
            # os.makedirs(private_dir)
            # Public
            public_dir = open(b, 'x')
            public_dir.close()
            # os.makedirs(public_dir)
            # Now open the files for modification
            privkey_buffer = open(a, 'w')
            pubkey_buffer = open(b, 'w')
            # I'll write the keys to the files
            # Encode the passphrase
            passphrase = self.passphrase.encode()
            # Write to the files
            privkey_buffer.write(pkey._export_private_pem(passphrase))
            pubkey_buffer.write(public_pkey._export_public_pem(passphrase))
            # Then change the key configs
            self.private_key = pkey
            self.public_key = public_pkey
            # Close the files
            privkey_buffer.close()
            pubkey_buffer.close()
           
    def sign(self, M, randomdigit=None):
        if randomdigit == None:
            randomdigit = random.randint(1, 100)
        # Convert message to bytes
        M = M.encode();
        # Then sign it
        signature = self.private_key._sign(bytes_to_long(M), randomdigit);
        return signature
    
    def verify(self, M, S):
        # Convert message to bytes
        M = M.encode();
        # Then verify the signature
        verification = self.private_key._verify(bytes_to_long(M), S)
        return verification
    
    def identity(self):
        address = self.public_key._export_public_pem(self.passphrase)
        address1 =  str(address).replace('-----BEGIN PUBLIC KEY-----', '')
        address2 =  str(address1).replace('-----END PUBLIC KEY-----', '')
        return address2

    def ixan(self):
        """ 
       Generate an International XBucks Account Number
        """
        file = './keys/ixan.txt'
        try:
            ixan_file = open(file, 'r')
            
            ixan = ixan_file.read();#
        except FileNotFoundError:
            max_length = 12
            ixan = ''
            identity = self.identity()
            # Clean whitespace
            identity = identity.replace('\n', '')
            # Find numbers
            for i in identity:
                if i.isdigit() == True:
                    ixan += i
                else:
                    pass
            # Edit IXAN to be 11 digits
            n = len(ixan)
            if n < max_length:
                char = (max_length - n)
                i = itertools.product(str('1234567890'), repeat=char)
                entry = []
                for r in i:
                    entry.append(r)
                length = len(entry)
                r = random.randint(0, length)
                end_number = ''.join(entry[r])
                ixan = ixan+end_number
            # Create the file
            ixan_dir = open(file, 'x')
            ixan_dir.close()
            # Write to file
            ixan_buffer = open(file, 'w')
            ixan_buffer.write(ixan)
            ixan_buffer.close()
        return ixan

# Remaining work:
# 2. Be able to spend money with the account (Need for a transaction account)
