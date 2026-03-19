"""
Service Registry - Central discovery hub for microservices

Provides:
  POST /register          - Register a service instance
  GET  /discover/<name>   - Discover instances of a service
  POST /heartbeat         - Keep-alive signal
  POST /deregister        - Remove a service instance
  GET  /services          - List all registered services
  GET  /health            - Health check
"""

from flask import Flask, request, jsonify
from datetime import datetime
import threading
import time
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [REGISTRY] %(message)s")

registry = {}
registry_lock = threading.Lock()

HEARTBEAT_TIMEOUT = 30   # seconds before instance considered dead
CLEANUP_INTERVAL = 10    # seconds between cleanup sweeps


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data or 'service' not in data or 'address' not in data:
        return jsonify({"status": "error", "message": "Missing 'service' and 'address'"}), 400

    service = data['service']
    address = data['address']

    with registry_lock:
        registry.setdefault(service, [])
        existing = next((s for s in registry[service] if s['address'] == address), None)

        if existing:
            existing['last_heartbeat'] = datetime.now()
            app.logger.info(f"Heartbeat-update: {service} @ {address}")
            return jsonify({"status": "updated", "message": f"{service} heartbeat updated"})
        else:
            registry[service].append({
                'address': address,
                'registered_at': datetime.now(),
                'last_heartbeat': datetime.now()
            })
            app.logger.info(f"Registered: {service} @ {address}")
            return jsonify({"status": "registered", "message": f"{service} registered at {address}"}), 201


@app.route('/discover/<service>', methods=['GET'])
def discover(service):
    with registry_lock:
        if service not in registry:
            return jsonify({"service": service, "instances": [], "count": 0}), 404

        now = datetime.now()
        active = [
            {"address": s['address'], "uptime_seconds": round((now - s['registered_at']).total_seconds(), 1)}
            for s in registry[service]
            if (now - s['last_heartbeat']).total_seconds() < HEARTBEAT_TIMEOUT
        ]
        return jsonify({"service": service, "instances": active, "count": len(active)})


@app.route('/deregister', methods=['POST'])
def deregister():
    data = request.json
    if not data or 'service' not in data or 'address' not in data:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    service, address = data['service'], data['address']
    with registry_lock:
        if service in registry:
            registry[service] = [s for s in registry[service] if s['address'] != address]
            if not registry[service]:
                del registry[service]
            app.logger.info(f"Deregistered: {service} @ {address}")
            return jsonify({"status": "deregistered"})
        return jsonify({"status": "not_found"}), 404


@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    if not data or 'service' not in data or 'address' not in data:
        return jsonify({"status": "error"}), 400

    service, address = data['service'], data['address']
    with registry_lock:
        if service in registry:
            inst = next((s for s in registry[service] if s['address'] == address), None)
            if inst:
                inst['last_heartbeat'] = datetime.now()
                return jsonify({"status": "ok"})
        return jsonify({"status": "not_found"}), 404


@app.route('/services', methods=['GET'])
def list_services():
    with registry_lock:
        now = datetime.now()
        info = {}
        for svc, instances in registry.items():
            active = sum(1 for s in instances if (now - s['last_heartbeat']).total_seconds() < HEARTBEAT_TIMEOUT)
            info[svc] = {"total_instances": len(instances), "active_instances": active}
        return jsonify({"services": info, "total_services": len(info)})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


def cleanup_stale():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        with registry_lock:
            now = datetime.now()
            to_remove = []
            for svc, instances in registry.items():
                active = [s for s in instances if (now - s['last_heartbeat']).total_seconds() < HEARTBEAT_TIMEOUT]
                if active:
                    registry[svc] = active
                else:
                    to_remove.append(svc)
            for svc in to_remove:
                del registry[svc]
                app.logger.info(f"Cleaned up stale service: {svc}")


if __name__ == '__main__':
    threading.Thread(target=cleanup_stale, daemon=True).start()
    print("=" * 60)
    print("  SERVICE REGISTRY starting on port 5001")
    print(f"  Heartbeat timeout: {HEARTBEAT_TIMEOUT}s | Cleanup interval: {CLEANUP_INTERVAL}s")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5001)
