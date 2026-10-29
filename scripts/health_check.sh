#!/usr/bin/env bash
# Real-time health-check script for edge nodes
# Usage: ./scripts/health_check.sh [NODE_ID] [API_BASE_URL]

set -euo pipefail

NODE_ID="${1:-edge-node-01}"
API_URL="${2:-http://127.0.0.1:8000}"

echo "[INFO] Running SRE health check for node: ${NODE_ID}"

HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/api/v1/fleet/nodes/${NODE_ID}" || true)
BODY=$(echo "${HTTP_RESPONSE}" | head -n -1)
STATUS_CODE=$(echo "${HTTP_RESPONSE}" | tail -n 1)

if [ "${STATUS_CODE}" -eq 200 ]; then
    echo "[OK] Node ${NODE_ID} is LIVE and transmitting telemetry."
    echo "${BODY}"
    exit 0
else
    echo "[WARN] Node ${NODE_ID} is UNREACHABLE or heartbeat expired (HTTP ${STATUS_CODE})."
    exit 1
fi