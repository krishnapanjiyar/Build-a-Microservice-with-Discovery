# Microservice Discovery Demo

A complete, working demonstration of **service registration, discovery, and client-side load balancing** using a custom service registry.

## What This Demonstrates

| Requirement | How It's Met |
|---|---|
| **2 service instances** | `order_service.py` runs on ports 6001 and 6002 |
| **Register with registry** | Each instance POSTs to `/register` on startup, sends heartbeats |
| **Client discovers service** | `client.py` calls `GET /discover/order-service` |
| **Client calls random instance** | Client picks a random address from discovered list |

## Architecture

```
                    ┌──────────────────────┐
                    │   Service Registry   │
                    │     (port 5001)      │
                    │                      │
                    │  /register           │
                    │  /discover/<name>    │
                    │  /heartbeat          │
                    │  /services           │
                    └──────┬───────┬───────┘
                  register │       │ register
              + heartbeat  │       │  + heartbeat
                           │       │
              ┌────────────┘       └────────────┐
              ▼                                  ▼
   ┌─────────────────────┐          ┌─────────────────────┐
   │  Order Service (A)  │          │  Order Service (B)  │
   │    port 6001        │          │    port 6002        │
   │  instance: a3f2…    │          │  instance: c7b1…    │
   │                     │          │                     │
   │  GET /order         │          │  GET /order         │
   │  GET /info          │          │  GET /info          │
   └─────────────────────┘          └─────────────────────┘
              ▲                                  ▲
              │          ┌───────────┐           │
              └──────────│  Client   │───────────┘
                         │           │
                         │ 1. discover│
                         │ 2. random  │
                         │    pick    │
                         │ 3. call    │
                         └───────────┘
```

## Quick Start (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the full demo (starts everything automatically)
chmod +x demo.sh
./demo.sh
```

### Manual Start (4 terminals)

```bash
# Terminal 1 — Registry
python3 service_registry.py

# Terminal 2 — Order Service instance A
python3 order_service.py 6001

# Terminal 3 — Order Service instance B
python3 order_service.py 6002

# Terminal 4 — Discovery Client
python3 client.py 8
```

## Quick Start (Docker Compose)

```bash
docker compose up --build -d
# Then run the client locally:
python3 client.py 8
```

## API Reference

### Service Registry (port 5001)

| Endpoint | Method | Description |
|---|---|---|
| `/register` | POST | Register `{service, address}` |
| `/discover/<name>` | GET | Returns list of live instances |
| `/heartbeat` | POST | Keep-alive for `{service, address}` |
| `/deregister` | POST | Remove `{service, address}` |
| `/services` | GET | List all services + counts |
| `/health` | GET | Registry health check |

### Order Service (port 6001/6002)

| Endpoint | Method | Description |
|---|---|---|
| `/order` | GET | Returns a random order (proves which instance handled it) |
| `/info` | GET | Instance metadata |
| `/health` | GET | Health check |

## Project Structure

```
MicroserviceDiscovery/
├── service_registry.py    # Central registry with heartbeat & cleanup
├── order_service.py       # Microservice that self-registers
├── client.py              # Discovery client with random load balancing
├── demo.sh                # One-command demo script
├── docker-compose.yml     # Multi-container setup
├── Dockerfile
├── requirements.txt
└── README.md
```

## How It Works

1. **Registry starts** on port 5001 with a background thread that cleans up stale services (no heartbeat for 30s → removed).

2. **Each order-service instance** starts a Flask server, then POSTs `{service: "order-service", address: "http://localhost:<port>"}` to the registry. A background thread sends heartbeats every 10 seconds.

3. **The client** calls `GET /discover/order-service` to get all live instances, then for each request picks one at random and calls its `/order` endpoint. The response includes `instance_id` so you can see which instance handled it.

4. **On shutdown**, each service sends a deregister request so the registry immediately removes it (rather than waiting for heartbeat timeout).


