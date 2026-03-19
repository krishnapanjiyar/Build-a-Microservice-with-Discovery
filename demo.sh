#!/usr/bin/env bash
#
# demo.sh  —  End-to-end microservice discovery demo
#
# Starts:
#   1. Service Registry on port 5001
#   2. Order-Service instance A on port 6001
#   3. Order-Service instance B on port 6002
# Then runs the discovery client to make calls to random instances.
#
set -euo pipefail

# ── colours ────────────────────────────────────────────────────────
BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PIDS=()

cleanup() {
    echo -e "\n${YELLOW}→ Cleaning up…${NC}"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null && echo "  stopped PID $pid" || true
    done
    wait 2>/dev/null
    echo -e "${GREEN}✓ All processes stopped.${NC}\n"
}
trap cleanup EXIT

wait_for() {
    local url=$1 label=$2 max=20
    echo -ne "  Waiting for ${label}…"
    for i in $(seq 1 $max); do
        if curl -sf "$url" >/dev/null 2>&1; then
            echo -e " ${GREEN}ready${NC}"
            return 0
        fi
        sleep 0.5
    done
    echo -e " ${RED}TIMEOUT${NC}"
    return 1
}

# ────────────────────────────────────────────────────────────────────
echo -e "${BOLD}${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       MICROSERVICE DISCOVERY  —  LIVE DEMO                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Registry
echo -e "${BOLD}[1/4] Starting Service Registry (port 5001)${NC}"
python3 service_registry.py > /tmp/registry.log 2>&1 &
PIDS+=($!)
wait_for "http://localhost:5001/health" "registry"

# 2. Order-service instance A
echo -e "${BOLD}[2/4] Starting Order Service — Instance A (port 6001)${NC}"
python3 order_service.py 6001 > /tmp/order_a.log 2>&1 &
PIDS+=($!)
wait_for "http://localhost:6001/health" "instance-A"

# 3. Order-service instance B
echo -e "${BOLD}[3/4] Starting Order Service — Instance B (port 6002)${NC}"
python3 order_service.py 6002 > /tmp/order_b.log 2>&1 &
PIDS+=($!)
wait_for "http://localhost:6002/health" "instance-B"

# 4. Verify registry state
echo ""
echo -e "${BOLD}Registry state:${NC}"
curl -s http://localhost:5001/services | python3 -m json.tool
echo ""

# 5. Run the discovery client
echo -e "${BOLD}[4/4] Running Discovery Client (8 calls)${NC}"
echo ""
python3 client.py 8

# 6. Show logs
echo -e "${BOLD}── Registry log (last 12 lines) ──${NC}"
tail -12 /tmp/registry.log || true
echo ""
echo -e "${GREEN}${BOLD}Demo complete!${NC}"
