#!/usr/bin/env bash
# Automated recovery workflow script
# Dispatches service restarts when an edge node is flagged as faulty

set -euo pipefail

NODE_ID="${1:-edge-node-01}"
SERVICE_NAME="${2:-telemetry_worker}"
API_URL="${3:-http://127.0.0.1:8000}"

echo "[RECOVERY] Triggering automated recovery workflow for node '${NODE_ID}'..."

COMMAND_ID="recov-$(date +%s)"
PAYLOAD=$(cat <<EOF
{
  "command_id": "${COMMAND_ID}",
  "target_node_id": "${NODE_ID}",
  "action": "RESTART_SERVICE",
  "parameters": {
    "service_name": "${SERVICE_NAME}",
    "automated": true
  }
}
EOF
)

RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/fleet/commands" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")

echo "[SUCCESS] Recovery command queued: ${RESPONSE}"