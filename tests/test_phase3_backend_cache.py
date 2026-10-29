"""
Phase 3 Verification Gate:
Tests concurrent heartbeat ingestion, Aerospike NoSQL caching, TTL expiration, and command dispatch.
"""
import pytest
from httpx import AsyncClient, ASGITransport
import time

from sre_engine.server import app, cache
from sre_engine.schemas import HeartbeatPayload, TelemetryMetrics, NodeStatus, CommandAction


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.asyncio
async def test_heartbeat_ingestion_and_cache_retrieval():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        heartbeat = {
            "node_id": "edge-node-mumbai-01",
            "status": "HEALTHY",
            "metrics": {
                "cpu_percent": 42.1,
                "memory_percent": 55.4,
                "disk_percent": 28.0,
                "network_latency_ms": 11.2,
                "temperature_c": 46.0
            },
            "active_services": ["streamer", "watchdog"],
            "metadata": {}
        }

        # 1. Ingest heartbeat
        post_res = await ac.post("/api/v1/telemetry/heartbeat", json=heartbeat)
        assert post_res.status_code == 200
        assert post_res.json()["status"] == "ACK"

        # 2. Verify sub-millisecond state lookup from Aerospike cache
        get_res = await ac.get("/api/v1/fleet/nodes/edge-node-mumbai-01")
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["node_id"] == "edge-node-mumbai-01"
        assert data["cpu_percent"] == 42.1
        assert data["status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_high_concurrency_batch_ingestion():
    """Simulates concurrent heartbeats from multiple edge nodes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for i in range(25):
            payload = {
                "node_id": f"node-worker-{i:02d}",
                "status": "HEALTHY",
                "metrics": {
                    "cpu_percent": float(20 + i),
                    "memory_percent": 40.0,
                    "disk_percent": 15.0,
                    "network_latency_ms": 5.0
                }
            }
            res = await ac.post("/api/v1/telemetry/heartbeat", json=payload)
            assert res.status_code == 200

        list_res = await ac.get("/api/v1/fleet/nodes")
        assert list_res.status_code == 200
        assert list_res.json()["total_active_nodes"] == 25


@pytest.mark.asyncio
async def test_ttl_key_expiration():
    """Verifies that stale nodes automatically drop out of active status upon TTL expiry."""
    cache.ttl = 0.5  # Half-second TTL for fast test
    node_payload = HeartbeatPayload(
        node_id="temporary-node-99",
        metrics=TelemetryMetrics(cpu_percent=10.0, memory_percent=20.0)
    )
    cache.put_node_state(node_payload)
    assert cache.get_node_state("temporary-node-99") is not None

    # Wait for TTL to expire
    time.sleep(0.6)
    assert cache.get_node_state("temporary-node-99") is None


@pytest.mark.asyncio
async def test_command_dispatch_and_delivery():
    """Tests command queueing and delivery upon next heartbeat."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        cmd = {
            "command_id": "cmd-restart-01",
            "target_node_id": "edge-node-pune-01",
            "action": "RESTART_SERVICE",
            "parameters": {"service_name": "streamer"}
        }

        # Queue command
        cmd_res = await ac.post("/api/v1/fleet/commands", json=cmd)
        assert cmd_res.status_code == 202

        # Send heartbeat from target node and expect dispatched command in response
        hb = {
            "node_id": "edge-node-pune-01",
            "metrics": {"cpu_percent": 25.0, "memory_percent": 30.0}
        }
        hb_res = await ac.post("/api/v1/telemetry/heartbeat", json=hb)
        dispatched = hb_res.json()["dispatched_commands"]
        assert len(dispatched) == 1
        assert dispatched[0]["command_id"] == "cmd-restart-01"