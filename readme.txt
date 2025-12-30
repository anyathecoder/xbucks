XBucks
---------
XBucks is a experimental serverless digital bank that operates on the premises of anonymity, security and trust.
It is meant to convert fiat money (e.g. Naira, Dollars) into a spendable data packet.

Such spendable data packets can be routed around the network to send to the receiver. 

It also allows for IOUs(borrowing of money) and buying and selling digital files.

It does not rely on a central server for keeping record of transactions and is very fast with validating, and verifying data.

Programming Languages: Python
- Kivy (GUI)
- pycryptodome (Cryptography)
- MySQL / LevelDB (data management and storage)
- Flutterwave/Rapyd - Fiat money handling
- NowPayments/Block.io - Crypto - to - Fiat gateway


Deposit and withdrawal:
	XBucks maintains off-shore accounts for holding different currencies. it uses their APIs to make calls and requests.
	Examples: Paystack(Naira), Braintree(Dollar/Euro/Pound)

Transaction:
	A user spends a certain amount of money by creating a data entry consisting of the receiver's address, amount to be sent, and optional fees (for spurring miners)
	A gas fee of ₦10 will be collected (or a random pick from a tenth to a hundredth of that amount).
	The user has to sign that entry and commit it to the mempool
	When the transaction is confirmed, the receiving address' default currency is taken into consideration
	When it is ascertained, the amount will be converted and transferred to the necessary third - party payment service provider while the amounts are debited from the sender and credited to the user
ToDo:
----
2. Modify the transaction class to be able to use the DNS to get the receiving address, and to sign, validate and store transactions in the mempool
3. Enhance the accountmanager that it would be able to keep track of the different currencies (using MySQLdb) that an account is qualifed to hold, and able 
   to present all the data in the currencies table so that a snapshot (hash) of the table can be taken
4. Ensure that the account manager can also hold crypto addresses of the users for easy accessibility
5. Finally, round up the microformat compression method which will be used instead of hashes 
6. The money format of the XBucks ledger should be made compatible with the Mempool and the Transaction format and can be validated
7. Repair `six` in urllib3(I should request for urllib3==1.4.2) 
---------------------------------------------------------------------
8. Build the XBucks Ledger, and method to keep the transactions.
9. Make the XBucks ledger also have support for fiat transactions (into the chain) and crypto - to - fiat transactions (into the customer's account as well)
10. Repair the hashcash puzzle system, and use it to build the PoD consensus system.
11. Create a mining system were validators use PoD to confirm and store transactions(native, in-coming fiat and in-coming crypto - to - fiat transfers), as well as
    for them to receive payment
12. Build and integrate the rails for fiat and crypto support (Paystack[I might find an alternative that supports payments], Braintree, Xoom, NowPayments)
---------------------------------------------------------------------
13. Build an app for XBucks users to "Send Money", "Request for Money", "Deposit", "Withdraw", "About", "Settings"
14. Compile for Desktop(Windows, macOS and Linux)
15. Then create a lightweight client for iOs and Android

How to make it grow:
--------------------
1. Publish the whitepaper (probably the same place where Satoshi published his)
2. Relese early compilations to my developer group on Discord
3. Create a fan group on Discord that will be committed to growing the product by talking about it on Medium, Facebook and Twitter
4. Crowdfund on Crowdcube.com or crowdfundr.com to get money to register the business and pay upfront costs
5. When that is done, I will launch a beta test on my Selar page [I might have to register my business Anya Digital Services]
6. Introduce an API that can be used to process payments (and deliver it to my fan group for people to be talking about it)s
7. Create an online workspace for 2 developers to be making changes, correcting bugs and enhancing the performance of the product

Queries to run:
---------------
pip install pillow
pip install pyinstaller
pip install python-android
pip install rapyd (for international payments)
pip install flutterwave (for African payments)

Applicaion deployment:
      1. We will deploy a full client on Desktop (Windows, macOS, Linux) and;
      2. A lightweight client for Android and iOS users. (these users only have a Hash of the Entire ledger and can use it to confirm authenticity of ledgers)