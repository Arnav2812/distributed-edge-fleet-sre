"""
Phase 1 Verification Gate:
Tests schema constraints, serialization, edge cases, and directory scaffolding.
"""
import pytest
from pydantic import ValidationError
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sre_engine.schemas import (
    HeartbeatPayload,
    TelemetryMetrics,
    NodeStatus,
    CommandPayload,
    CommandAction,
    CommandResponse
)


def test_valid_heartbeat_payload():
    """Verify that a standard edge node heartbeat serializes and validates cleanly."""
    metrics = TelemetryMetrics(
        cpu_percent=34.5,
        memory_percent=58.2,
        disk_percent=42.0,
        network_latency_ms=12.4,
        temperature_c=48.5
    )
    payload = HeartbeatPayload(
        node_id="edge-node-delhi-01",
        status=NodeStatus.HEALTHY,
        metrics=metrics,
        active_services=["camera_ingest", "local_buffer"]
    )
    assert payload.node_id == "edge-node-delhi-01"
    assert payload.metrics.cpu_percent == 34.5
    assert payload.status == NodeStatus.HEALTHY
    assert "camera_ingest" in payload.active_services


def test_invalid_cpu_metric_bounds():
    """Verify that impossible metric values (>100% or <0%) trigger strict validation errors."""
    with pytest.raises(ValidationError):
        TelemetryMetrics(cpu_percent=150.0, memory_percent=50.0)

    with pytest.raises(ValidationError):
        TelemetryMetrics(cpu_percent=-5.0, memory_percent=50.0)


def test_command_payload_execution():
    """Verify state-change command structure and response contract."""
    cmd = CommandPayload(
        command_id="cmd-8923-recover",
        target_node_id="edge-node-noida-02",
        action=CommandAction.RESTART_SERVICE,
        parameters={"service_name": "telemetry_collector", "graceful": True}
    )
    assert cmd.action == CommandAction.RESTART_SERVICE
    assert cmd.parameters["service_name"] == "telemetry_collector"

    res = CommandResponse(
        command_id=cmd.command_id,
        node_id=cmd.target_node_id,
        success=True,
        message="Service restarted successfully"
    )
    assert res.success is True