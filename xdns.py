
import sqlite3
import os

class DNS:
    def __init__(self):
        self.db_path = './db/dns.db'
        self._init_db()

    def _init_db(self):
        if not os.path.exists('./db'):
            os.makedirs('./db')
        
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    name TEXT PRIMARY KEY,
                    address TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def register_address(self, name, address):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO records (name, address) VALUES (?, ?)", (name, address))
            conn.commit()
            return True
        except Exception as e:
            print(f"DNS Registration Failed: {e}")
            return False
        finally:
            conn.close()

    def resolve(self, name):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT address FROM records WHERE name = ?", (name,))
            result = cursor.fetchone()
            if result:
                return result[0]
            return None
        finally:
            conn.close()

if __name__ == "__main__":
    dns = DNS()
    dns.register_address("alice", "public_key_pem_string_of_alice")
    print(f"alice: {dns.resolve('alice')}")
    print(f"bob: {dns.resolve('bob')}")
