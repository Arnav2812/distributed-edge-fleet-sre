"""
High-Concurrency SRE Telemetry & Ingestion Backend.
Processes real-time node heartbeats and provides REST APIs for fleet management.
"""
from fastapi import FastAPI, HTTPException, status
from typing import Dict, List, Any
import time

from sre_engine.schemas import (
    HeartbeatPayload,
    CommandPayload,
    CommandResponse,
    NodeStatus
)
from sre_engine.cache.aerospike_client import AerospikeFleetCache

app = FastAPI(
    title="Distributed Edge Fleet SRE Platform API",
    version="1.0.0",
    description="High-frequency telemetry ingestion & fleet orchestration backend"
)

# Global Aerospike cache instance
cache = AerospikeFleetCache(ttl_sec=5)
# In-memory command queue per node
pending_commands: Dict[str, List[CommandPayload]] = {}


@app.post("/api/v1/telemetry/heartbeat", status_code=status.HTTP_200_OK)
async def ingest_heartbeat(heartbeat: HeartbeatPayload) -> Dict[str, Any]:
    """
    Ingests high-frequency edge node heartbeats and persists state to Aerospike NoSQL cache.
    Returns any pending commands awaiting delivery to the node.
    """
    success = cache.put_node_state(heartbeat)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to persist heartbeat in cache")

    # Fetch queued commands for this node, if any
    queued = pending_commands.pop(heartbeat.node_id, [])

    return {
        "status": "ACK",
        "node_id": heartbeat.node_id,
        "server_time": time.time(),
        "dispatched_commands": queued
    }


@app.get("/api/v1/fleet/nodes/{node_id}")
async def get_node_status(node_id: str) -> Dict[str, Any]:
    """Retrieves live state for a specific edge node."""
    state = cache.get_node_state(node_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"Node '{node_id}' not found or heartbeat expired (TTL offline)"
        )
    return state


@app.get("/api/v1/fleet/nodes")
async def list_fleet_status() -> Dict[str, Any]:
    """Returns an aggregated snapshot of all active edge nodes across the fleet."""
    nodes = cache.get_all_active_nodes()
    return {
        "total_active_nodes": len(nodes),
        "nodes": nodes
    }


@app.post("/api/v1/fleet/commands", status_code=status.HTTP_202_ACCEPTED)
async def dispatch_command(cmd: CommandPayload) -> Dict[str, Any]:
    """Queues a remote state-change or recovery command for an edge node."""
    if cmd.target_node_id not in pending_commands:
        pending_commands[cmd.target_node_id] = []

    pending_commands[cmd.target_node_id].append(cmd)
    return {
        "status": "QUEUED",
        "command_id": cmd.command_id,
        "target_node_id": cmd.target_node_id
    }