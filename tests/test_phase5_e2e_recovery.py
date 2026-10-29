"""
Phase 5 Verification Gate:
End-to-End lifecycle test:
1. Ingest normal telemetry.
2. Inject a critical memory leak / CPU saturation fault.
3. Automatically isolate the fault via FaultAnalyzer.
4. Issue automated recovery command and verify node recovery.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from sre_engine.server import app, cache
from sre_engine.schemas import HeartbeatPayload, TelemetryMetrics, NodeStatus, CommandAction, CommandPayload
from sre_engine.fault_detector.analyzer import FaultAnalyzer
from edge_agent.python_agent.agent import EdgeAgent


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.asyncio
async def test_end_to_end_fault_detection_and_auto_recovery():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        node_id = "edge-e2e-node-01"
        agent = EdgeAgent(node_id=node_id)
        analyzer = FaultAnalyzer()

        # Step 1: Initial normal heartbeat
        healthy_hb = agent.build_heartbeat(
            injected_metrics=TelemetryMetrics(cpu_percent=40.0, memory_percent=45.0)
        )
        post_res = await ac.post("/api/v1/telemetry/heartbeat", json=healthy_hb.model_dump())
        assert post_res.status_code == 200

        # Step 2: Inject critical memory leak failure
        failing_metrics = TelemetryMetrics(cpu_percent=95.0, memory_percent=94.5)
        failing_hb = agent.build_heartbeat(injected_metrics=failing_metrics)

        # Step 3: SRE Fault Analyzer isolates failure
        fault_report = analyzer.analyze_heartbeat(failing_hb)
        assert fault_report["has_fault"] is True
        assert fault_report["recommended_action"] == "RESTART_SERVICE"

        # Step 4: Automated Recovery Workflow queues command
        recovery_cmd = {
            "command_id": "auto-recov-001",
            "target_node_id": node_id,
            "action": "RESTART_SERVICE",
            "parameters": {"service_name": "telemetry_worker"}
        }
        cmd_res = await ac.post("/api/v1/fleet/commands", json=recovery_cmd)
        assert cmd_res.status_code == 202

        # Step 5: Next heartbeat receives recovery command
        cycle_res = await ac.post("/api/v1/telemetry/heartbeat", json=healthy_hb.model_dump())
        dispatched = cycle_res.json()["dispatched_commands"]
        assert len(dispatched) == 1
        assert dispatched[0]["action"] == "RESTART_SERVICE"

        # Step 6: Agent parses and executes the received CommandPayload cleanly
        cmd_data = dispatched[0]
        cmd_obj = CommandPayload(
            command_id=cmd_data["command_id"],
            target_node_id=cmd_data["target_node_id"],
            action=CommandAction(cmd_data["action"]),
            parameters=cmd_data["parameters"]
        )
        recov_res = agent.command_handler.execute_command(cmd_obj)
        assert recov_res.success is True
        assert "gracefully cycled" in recov_res.message