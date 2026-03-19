"""
Order Service - A sample microservice that registers with the Service Registry.

Each instance:
  1. Starts a Flask HTTP server on the given port
  2. Registers itself with the registry
  3. Sends heartbeats in the background
  4. Exposes business endpoints:  GET /order, GET /info

Usage:
    python order_service.py <port>      # e.g. python order_service.py 6001
"""

import os
import sys
import time
import uuid
import random
import signal
import logging
import requests
from threading import Thread, Event
from flask import Flask, jsonify

# ── configuration ────────────────────────────────────────────────────
SERVICE_NAME = "order-service"
REGISTRY_URL = os.environ.get("REGISTRY_URL", "http://localhost:5001")
HEARTBEAT_INTERVAL = 10   # seconds

# ── instance identity ────────────────────────────────────────────────
INSTANCE_ID = str(uuid.uuid4())[:8]

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format=f"%(asctime)s [order-{INSTANCE_ID}] %(message)s")
stop_event = Event()


# ── business endpoints ───────────────────────────────────────────────
@app.route('/order', methods=['GET'])
def get_order():
    """Simulate returning an order — proves which instance handled the call."""
    order = {
        "order_id": f"ORD-{random.randint(1000, 9999)}",
        "instance_id": INSTANCE_ID,
        "items": random.sample(["Widget", "Gadget", "Doohickey", "Sprocket", "Gizmo"], k=random.randint(1, 3)),
        "total": round(random.uniform(9.99, 299.99), 2),
        "status": random.choice(["pending", "shipped", "delivered"]),
    }
    app.logger.info(f"Handled /order → {order['order_id']}")
    return jsonify(order)


@app.route('/info', methods=['GET'])
def info():
    return jsonify({"service": SERVICE_NAME, "instance_id": INSTANCE_ID, "status": "running"})


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"healthy": True, "instance": INSTANCE_ID})


# ── registry helpers ─────────────────────────────────────────────────
def register(address):
    try:
        r = requests.post(f"{REGISTRY_URL}/register",
                          json={"service": SERVICE_NAME, "address": address}, timeout=5)
        if r.status_code in (200, 201):
            app.logger.info(f"✓ Registered with registry at {address}")
            return True
        app.logger.warning(f"Registration returned {r.status_code}: {r.text}")
    except Exception as e:
        app.logger.error(f"✗ Cannot reach registry: {e}")
    return False


def deregister(address):
    try:
        requests.post(f"{REGISTRY_URL}/deregister",
                      json={"service": SERVICE_NAME, "address": address}, timeout=5)
        app.logger.info(f"✓ Deregistered {address}")
    except Exception:
        pass


def heartbeat_loop(address):
    while not stop_event.is_set():
        try:
            requests.post(f"{REGISTRY_URL}/heartbeat",
                          json={"service": SERVICE_NAME, "address": address}, timeout=5)
        except Exception:
            pass
        stop_event.wait(HEARTBEAT_INTERVAL)


# ── main ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python order_service.py <port>")
        sys.exit(1)

    port = int(sys.argv[1])
    my_address = f"http://localhost:{port}"

    if not register(my_address):
        print("⚠  Could not register – is the registry running on port 5001?")

    # heartbeat thread
    Thread(target=heartbeat_loop, args=(my_address,), daemon=True).start()

    # graceful shutdown
    original_sigint = signal.getsignal(signal.SIGINT)
    def _shutdown(sig, frame):
        print(f"\n[order-{INSTANCE_ID}] Shutting down…")
        stop_event.set()
        deregister(my_address)
        original_sigint(sig, frame)
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, lambda s, f: (_shutdown(s, f)))

    print(f"{'=' * 60}")
    print(f"  ORDER SERVICE  instance={INSTANCE_ID}  port={port}")
    print(f"{'=' * 60}")
    app.run(host='0.0.0.0', port=port)
