"""
Discovery Client - Discovers order-service instances from the registry
and calls a random one to demonstrate client-side load balancing.

Usage:
    python client.py                # make 6 calls (default)
    python client.py <n>            # make n calls
"""

import sys
import random
import time
import requests

REGISTRY_URL = "http://localhost:5001"
SERVICE_NAME = "order-service"


def discover_instances(service_name):
    """Ask the registry for all live instances of a service."""
    try:
        r = requests.get(f"{REGISTRY_URL}/discover/{service_name}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("instances", [])
        else:
            print(f"Discovery failed (HTTP {r.status_code}): {r.text}")
    except Exception as e:
        print(f"Cannot reach registry: {e}")
    return []


def call_random_instance(instances):
    """Pick a random instance and call its /order endpoint."""
    inst = random.choice(instances)
    address = inst["address"]
    try:
        r = requests.get(f"{address}/order", timeout=5)
        return r.json(), address
    except Exception as e:
        return {"error": str(e)}, address


def main():
    num_calls = int(sys.argv[1]) if len(sys.argv) > 1 else 6

    print("=" * 70)
    print("  DISCOVERY CLIENT")
    print("=" * 70)

    # ── Step 1: discover ──────────────────────────────────────────────
    print(f"\n→ Discovering '{SERVICE_NAME}' via registry at {REGISTRY_URL} …")
    instances = discover_instances(SERVICE_NAME)

    if not instances:
        print("✗ No instances found. Start the order services first.")
        sys.exit(1)

    print(f"✓ Found {len(instances)} instance(s):")
    for i, inst in enumerate(instances, 1):
        print(f"   [{i}] {inst['address']}  (uptime {inst['uptime_seconds']}s)")

    # ── Step 2: call random instances ─────────────────────────────────
    print(f"\n→ Making {num_calls} requests (random instance each time)…\n")

    call_stats = {}   # address → count

    for n in range(1, num_calls + 1):
        result, addr = call_random_instance(instances)
        call_stats[addr] = call_stats.get(addr, 0) + 1

        if "error" in result:
            print(f"  [{n}] ✗ {addr}  →  ERROR: {result['error']}")
        else:
            print(f"  [{n}] ✓ {addr}  →  "
                  f"order={result['order_id']}  instance={result['instance_id']}  "
                  f"total=${result['total']}  status={result['status']}")

        time.sleep(0.3)   # small delay for readability

    # ── Step 3: summary ───────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  LOAD DISTRIBUTION SUMMARY")
    print(f"{'─' * 70}")
    for addr, count in sorted(call_stats.items()):
        pct = count / num_calls * 100
        bar = "█" * int(pct / 5)
        print(f"   {addr:<30} {count:>3} calls  ({pct:5.1f}%)  {bar}")
    print()


if __name__ == '__main__':
    main()
