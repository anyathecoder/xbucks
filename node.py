# Copyright (c) 2025 Nikola Tesla
# Node for on - XBucks connections
# This functions both as a node and as a server

"""
Extended node using XML-RPC + HMAC authentication + configurable roaming discovery.

Key features (added / modified):
- XML-RPC server (threaded) as the main RPC endpoint.
- RPC methods:
    - announce(host, port, timestamp, nonce, signature): announce peer
    - get_state(timestamp, nonce, signature): request node state (returns xml string)
    - get_ledger(timestamp, nonce, signature): request ledger xml string
    - send_state(xml_payload, timestamp, nonce, signature): push state to this node
    - send_ledger(xml_payload, timestamp, nonce, signature): push ledger to this node
- HMAC-SHA256 signature verification for RPC calls (shared secret).
- Configurable roaming discovery with a subnet base and explicit list/range of ports.
- SQLite peer DB, and saving STATE/LEDGER to files under ./db/.
- Graceful shutdown on SIGINT.
"""

import os
import sys
import signal
import sqlite3
import threading
import time
import random
import xml.etree.ElementTree as ET
import hmac
import hashlib
from datetime import datetime
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
from xmlrpc.client import ServerProxy, Transport, Fault, ProtocolError
from socketserver import ThreadingMixIn

# ----------------------------
# Configuration (edit as needed)
# ----------------------------
CONFIG = {
    # Node listening address
    "host": "127.0.0.1",
    "port": 9999,  # XML-RPC server port

    # Discovery/roaming
    "roam_subnet_base": "192.168.1.",  # change to "192.168.1." for LAN scanning (be careful)
    # ports can be explicitly listed or a range tuple (start, end)
    "roam_ports": list(range(9900, 9910)),  # example explicit list
    "roam_interval_seconds": 3.0,  # average delay between probes

    # Security
    "hmac_secret": "supersecret_shared_key",  # Change to a secure secret on all nodes
    "hmac_tolerance_seconds": 120,  # acceptable clock skew for timestamp

    # Files / DB
    "db_dir": "./db",
    "state_file": "./db/state.data",
    "ledger_file": "./db/ledger.data",
    "db_file": "./db/peers.db",
}

# Ensure db dir exists
os.makedirs(CONFIG["db_dir"], exist_ok=True)

# ----------------------------
# Utility: HMAC helpers
# ----------------------------
def make_signature(secret: str, message: str) -> str:
    """Return hex digest of HMAC-SHA256 over message using secret."""
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_signature(secret: str, message: str, signature: str) -> bool:
    """Constant-time comparison of HMAC signature."""
    try:
        expected = make_signature(secret, message)
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


def make_message_for_rpc(*parts) -> str:
    """Create canonical message string for signing (simple ':' join)."""
    # Convert all to strings and join. Be consistent between clients and server.
    return ":".join(str(p) for p in parts)


# ----------------------------
# Simple SQLite-backed peer DB
# ----------------------------
class PeerDB:
    def __init__(self, db_path=CONFIG["db_file"]):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS peers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    last_seen TEXT,
                    UNIQUE(host, port)
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def add_or_update(self, host, port):
        now = datetime.utcnow().isoformat()
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                c = conn.cursor()
                # insert or update last_seen
                c.execute(
                    "INSERT INTO peers (host, port, last_seen) VALUES (?, ?, ?) "
                    "ON CONFLICT(host, port) DO UPDATE SET last_seen=excluded.last_seen",
                    (host, int(port), now),
                )
                conn.commit()
            finally:
                conn.close()

    def list_peers(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                c = conn.cursor()
                c.execute("SELECT host, port, last_seen FROM peers")
                return c.fetchall()
            finally:
                conn.close()

    def pick_random_peer(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                c = conn.cursor()
                c.execute("SELECT host, port FROM peers ORDER BY RANDOM() LIMIT 1")
                r = c.fetchone()
                return (r[0], r[1]) if r else None
            finally:
                conn.close()


# ----------------------------
# File saving helpers
# ----------------------------
from ledger import Ledger
import base64
import json

# ... (keep config) ...

# ----------------------------
# File saving helpers
# ----------------------------
def save_state(xml_payload: str):
    if not xml_payload or not xml_payload.strip():
        return
    with open(CONFIG["state_file"], "ab") as f:
        f.write((f"---{datetime.utcnow().isoformat()}---\n").encode("utf-8"))
        f.write(xml_payload.encode("utf-8"))
        f.write(b"\n")
    print("Saved STATE to", CONFIG["state_file"])

# ----------------------------
# Threaded XML-RPC server
# ----------------------------
class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass


class NodeRPCHandler:
    """Instance with RPC-callable methods. An instance of this class is registered with the XMLRPC server."""

    def __init__(self, node_host, node_port, peer_db: PeerDB, secret: str):
        self.node_host = node_host
        self.node_port = node_port
        self.peer_db = peer_db
        self.secret = secret
        self.ledger = Ledger()

    # Helper: check timestamp + signature tolerance
    def _check_time_and_signature(self, signature: str, timestamp: float, nonce: str, payload: str = ""):
        # timestamp validation
        try:
            ts = float(timestamp)
        except Exception:
            return False, "invalid_timestamp"

        if abs(time.time() - ts) > CONFIG["hmac_tolerance_seconds"]:
            return False, "timestamp_out_of_range"

        # canonical message
        message = make_message_for_rpc(timestamp, nonce, payload)
        if not verify_signature(self.secret, message, signature):
            return False, "bad_signature"

        return True, "ok"

    # RPC methods
    def announce(self, host: str, port: int, timestamp: float, nonce: str, signature: str):
        """
        Peer announces itself. Must be signed.
        Returns: dict(success: bool, reason: str)
        """
        payload = f"{host}:{port}"
        ok, reason = self._check_time_and_signature(signature, timestamp, nonce, payload)
        if not ok:
            return {"success": False, "reason": reason}
        # store peer
        self.peer_db.add_or_update(host, int(port))
        print(f"Peer announced: {host}:{port}")
        return {"success": True, "reason": "added"}

    def get_state(self, timestamp: float, nonce: str, signature: str):
        """Return the node state (xml string) if signature valid."""
        ok, reason = self._check_time_and_signature(signature, timestamp, nonce)
        if not ok:
            raise Fault(1, f"auth_failed:{reason}")
        # Build simple xml state
        root = ET.Element("state")
        ET.SubElement(root, "host").text = str(self.node_host)
        ET.SubElement(root, "port").text = str(self.node_port)
        ET.SubElement(root, "time").text = datetime.utcnow().isoformat()
        peers_el = ET.SubElement(root, "known_peers")
        for h, p, _ in self.peer_db.list_peers():
            p_el = ET.SubElement(peers_el, "peer")
            ET.SubElement(p_el, "host").text = h
            ET.SubElement(p_el, "port").text = str(p)
        xml = ET.tostring(root, encoding="utf-8").decode("utf-8")
        return xml

    def get_ledger(self, timestamp: float, nonce: str, signature: str):
        """Return the raw ledger file content (base64 encoded) if authorized."""
        ok, reason = self._check_time_and_signature(signature, timestamp, nonce)
        if not ok:
            raise Fault(1, f"auth_failed:{reason}")
        
        # Read raw ledger
        raw_data = self.ledger.read()
        # Encode to base64 to transport safely via XML-RPC
        b64_data = base64.b64encode(raw_data).decode('utf-8')
        return b64_data

    def send_state(self, xml_payload: str, timestamp: float, nonce: str, signature: str):
        """Receive a state payload (append to file) if signature valid."""
        ok, reason = self._check_time_and_signature(signature, timestamp, nonce, xml_payload)
        if not ok:
            return {"success": False, "reason": reason}
        save_state(xml_payload)
        # Optionally extract announcing peer info from xml (if present)
        try:
            root = ET.fromstring(xml_payload)
            h = root.findtext("host")
            p = root.findtext("port")
            if h and p:
                self.peer_db.add_or_update(h, int(p))
        except ET.ParseError:
            pass
        return {"success": True, "reason": "saved"}

    def receive_block(self, block_json: str, timestamp: float, nonce: str, signature: str):
        """Receive a mined block and append to ledger if valid."""
        ok, reason = self._check_time_and_signature(signature, timestamp, nonce, block_json)
        if not ok:
            return {"success": False, "reason": reason}
        
        try:
            block = json.loads(block_json)
            # In a real system, we would validate the block proof-of-work here
            # For now, we trust the miner (if they have the hmac secret)
            # Check if block is already present? 
            # self.ledger.write handles appending.
            self.ledger.write(block)
            print("Received and saved block via RPC.")
            return {"success": True, "reason": "saved"}
        except Exception as e:
            print(f"Failed to save block: {e}")
            return {"success": False, "reason": str(e)}

    # Simple ping to check node alive + optional auth
    def ping(self, timestamp: float, nonce: str, signature: str):
        ok, reason = self._check_time_and_signature(signature, timestamp, nonce)
        if not ok:
            return {"success": False, "reason": reason}
        return {"success": True, "time": datetime.utcnow().isoformat()}


# ----------------------------
# Client helpers: XML-RPC calls with HMAC signing
# ----------------------------
class HMACTransport(Transport):
    """Transport helper to set a short timeout (optional)."""
    timeout = 5.0


def rpc_call(host: str, port: int, method: str, secret: str, payload: str = "", timeout: float = 5.0):
    """
    Generic RPC caller that performs HMAC signing and calls remote XML-RPC method.
    Returns the result or raises.
    """
    timestamp = str(time.time())
    nonce = str(random.getrandbits(64))
    message = make_message_for_rpc(timestamp, nonce, payload)
    signature = make_signature(secret, message)
    url = f"http://{host}:{port}/"
    proxy = ServerProxy(url, transport=HMACTransport(), allow_none=True)
    try:
        func = getattr(proxy, method)
        # All RPC methods follow signature: (..., timestamp, nonce, signature) or (payload, timestamp, nonce, signature)
        if payload:
            return func(payload, timestamp, nonce, signature)
        else:
            return func(timestamp, nonce, signature)
    finally:
        try:
            proxy("close")  # not a real call — just attempt to cleanly close underlying transport (best-effort)
        except Exception:
            pass


# ----------------------------
# Node Manager: starts server, roaming, announce threads and controls shutdown
# ----------------------------
class NodeManager:
    def __init__(self, host: str, port: int, secret: str):
        self.host = host
        self.port = port
        self.secret = secret
        self.peer_db = PeerDB()
        self.server = None
        self.server_thread = None
        self.stop_event = threading.Event()
        self.threads = []

    def start_server(self):
        # Bind XML-RPC server in a threaded way
        class RequestHandler(SimpleXMLRPCRequestHandler):
            rpc_paths = ("/",)

        self.server = ThreadedXMLRPCServer((self.host, self.port), requestHandler=RequestHandler, allow_none=True, logRequests=False)
        handler_instance = NodeRPCHandler(self.host, self.port, self.peer_db, self.secret)
        # Register functions from the handler instance
        self.server.register_instance(handler_instance)

        print(f"XML-RPC server listening on {self.host}:{self.port}")
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.threads.append(self.server_thread)

    def stop_server(self):
        if self.server:
            print("Shutting down XML-RPC server...")
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
            self.server = None

    def roam_discovery(self, subnet_base: str, ports, interval_sec: float):
        """Continuously probe `subnet_baseX` and ports list to attempt announce/ping/GET_STATE.
        We call remote 'announce' RPC to introduce ourselves (if available).
        """
        print("Roaming discovery thread started (subnet:", subnet_base, "ports:", ports, ")")
        while not self.stop_event.is_set():
            try:
                target_last = random.randint(1, 254)
                target_host = subnet_base + str(target_last)
                target_port = random.choice(ports)
                # Try ping first to see if server responds
                try:
                    result = rpc_call(target_host, target_port, "ping", self.secret, payload="")
                    if isinstance(result, dict) and result.get("success"):
                        # contact succeeded; announce ourselves also
                        announce_payload = f"{self.host}:{self.port}"
                        # call announce(host, port, timestamp, nonce, signature)
                        # We need to call the raw announce signature; construct call differently:
                        timestamp = str(time.time())
                        nonce = str(random.getrandbits(64))
                        message = make_message_for_rpc(timestamp, nonce, announce_payload)
                        signature = make_signature(self.secret, message)
                        url = f"http://{target_host}:{target_port}/"
                        proxy = ServerProxy(url, transport=HMACTransport(), allow_none=True)
                        try:
                            res = proxy.announce(self.host, int(self.port), timestamp, nonce, signature)
                            if isinstance(res, dict) and res.get("success"):
                                print(f"Roaming: announced to {target_host}:{target_port}")
                                self.peer_db.add_or_update(target_host, target_port)
                        except Exception:
                            pass
                        finally:
                            try:
                                proxy("close")
                            except Exception:
                                pass
                except Exception:
                    # unreachable or not XML-RPC
                    pass
                # Sleep a bit (randomized)
                time.sleep(max(0.5, random.random() * interval_sec))
            except Exception as e:
                # Fail-safe and keep running
                time.sleep(1.0)
        print("Roaming discovery thread exiting.")

    def periodic_announce(self, interval_seconds=30):
        """Periodically announce to peers in the DB to keep them alive/known."""
        while not self.stop_event.is_set():
            peers = self.peer_db.list_peers()
            announce_payload = f"{self.host}:{self.port}"
            # sign message once per loop
            timestamp = str(time.time())
            nonce = str(random.getrandbits(64))
            message = make_message_for_rpc(timestamp, nonce, announce_payload)
            signature = make_signature(self.secret, message)
            for h, p, _ in peers:
                try:
                    url = f"http://{h}:{p}/"
                    proxy = ServerProxy(url, transport=HMACTransport(), allow_none=True)
                    try:
                        res = proxy.announce(self.host, int(self.port), timestamp, nonce, signature)
                        if isinstance(res, dict) and res.get("success"):
                            self.peer_db.add_or_update(h, p)
                    except Exception:
                        pass
                    finally:
                        try:
                            proxy("close")
                        except Exception:
                            pass
                except Exception:
                    pass
            # Sleep in small increments to allow quick shutdown
            for _ in range(int(interval_seconds)):
                if self.stop_event.is_set():
                    break
                time.sleep(1)

    def start(self):
        # Start XML-RPC server
        self.start_server()

        # Start roaming discovery thread
        roam_thread = threading.Thread(
            target=self.roam_discovery,
            args=(CONFIG["roam_subnet_base"], CONFIG["roam_ports"], CONFIG["roam_interval_seconds"]),
            daemon=True,
        )
        roam_thread.start()
        self.threads.append(roam_thread)

        # Start periodic announce thread
        ann_thread = threading.Thread(target=self.periodic_announce, args=(30,), daemon=True)
        ann_thread.start()
        self.threads.append(ann_thread)

    def stop(self):
        print("Stopping NodeManager...")
        self.stop_event.set()
        self.stop_server()
        # Wait briefly for threads to finish
        time.sleep(0.5)

    # Convenience methods for local test/usage:
    def call_get_state(self, host, port):
        try:
            return rpc_call(host, port, "get_state", self.secret)
        except Exception as e:
            return None

    def call_send_state(self, host, port, xml_payload):
        return rpc_call(host, port, "send_state", self.secret, payload=xml_payload)


# ----------------------------
# Signal handler and main
# ----------------------------
node_manager = None


def signal_handler(sig, frame):
    global node_manager
    print("Shutting down node...")
    if node_manager:
        node_manager.stop()
    sys.exit(0)


if __name__ == "__main__":
    # Setup
    host = CONFIG["host"]
    port = CONFIG["port"]
    secret = CONFIG["hmac_secret"]

    node_manager = NodeManager(host, port, secret)
    signal.signal(signal.SIGINT, signal_handler)
    node_manager.start()

    # Example: create a small startup state and announce self to any known peers file
    # (save local state file too)
    starter_state = f"<state><host>{host}</host><port>{port}</port><time>{datetime.utcnow().isoformat()}</time></state>"
    save_state(starter_state)

    print("NodeManager started. Press Ctrl+C to stop.")

    # Keep main thread alive
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        node_manager.stop()
