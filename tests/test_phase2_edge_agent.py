"""
Phase 2 Verification Gate:
Tests metric sampling, heartbeat creation, dynamic degradation, and command routing.
"""
import pytest
from sre_engine.schemas import NodeStatus, CommandPayload, CommandAction, TelemetryMetrics
from edge_agent.python_agent.agent import EdgeAgent
from edge_agent.python_agent.command_handler import EdgeCommandHandler


def test_agent_metrics_sampling():
    agent = EdgeAgent(node_id="edge-worker-01")
    metrics = agent.sample_system_metrics()

    assert 0.0 <= metrics.cpu_percent <= 100.0
    assert 0.0 <= metrics.memory_percent <= 100.0
    assert metrics.network_latency_ms >= 0.0


def test_dynamic_degradation_on_spike():
    agent = EdgeAgent(node_id="edge-worker-01")
    spike_metrics = TelemetryMetrics(
        cpu_percent=95.2,
        memory_percent=60.0,
        disk_percent=30.0,
        network_latency_ms=15.0
    )
    heartbeat = agent.build_heartbeat(injected_metrics=spike_metrics)
    assert heartbeat.status == NodeStatus.DEGRADED


def test_command_execution_lifecycle():
    handler = EdgeCommandHandler(node_id="edge-worker-02")

    # 1. Test ping
    ping_cmd = CommandPayload(
        command_id="cmd-1",
        target_node_id="edge-worker-02",
        action=CommandAction.PING
    )
    res = handler.execute_command(ping_cmd)
    assert res.success is True
    assert res.message == "PONG"

    # 2. Test state change
    state_cmd = CommandPayload(
        command_id="cmd-2",
        target_node_id="edge-worker-02",
        action=CommandAction.SET_STATE,
        parameters={"new_state": "CRITICAL"}
    )
    res_state = handler.execute_command(state_cmd)
    assert res_state.success is True
    assert handler.current_status == NodeStatus.CRITICAL

    # 3. Test node target mismatch rejection
    mismatch_cmd = CommandPayload(
        command_id="cmd-3",
        target_node_id="other-node-99",
        action=CommandAction.PING
    )
    res_mismatch = handler.execute_command(mismatch_cmd)
    assert res_mismatch.success is False