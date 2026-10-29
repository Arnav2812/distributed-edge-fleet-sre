"""
Edge Telemetry Daemon.
Collects OS/system metrics, builds HeartbeatPayloads, and sends them to the backend.
"""
import psutil
import time
from typing import Optional
from sre_engine.schemas import HeartbeatPayload, TelemetryMetrics, NodeStatus
from edge_agent.python_agent.command_handler import EdgeCommandHandler


class EdgeAgent:
    def __init__(self, node_id: str, heartbeat_interval_sec: float = 1.0):
        self.node_id = node_id
        self.interval = heartbeat_interval_sec
        self.command_handler = EdgeCommandHandler(node_id)

    def sample_system_metrics(self) -> TelemetryMetrics:
        """Gathers real-time OS metrics via psutil with safe bounds."""
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent if hasattr(psutil, "disk_usage") else 30.0

        return TelemetryMetrics(
            cpu_percent=max(0.0, min(100.0, float(cpu))),
            memory_percent=max(0.0, min(100.0, float(mem))),
            disk_percent=max(0.0, min(100.0, float(disk))),
            network_latency_ms=10.0,
            temperature_c=45.0
        )

    def build_heartbeat(self, injected_metrics: Optional[TelemetryMetrics] = None) -> HeartbeatPayload:
        """Constructs a validated heartbeat payload ready for transmission."""
        metrics = injected_metrics or self.sample_system_metrics()
        status = self.command_handler.current_status

        # Dynamic SRE degradation logic: mark degraded if RAM or CPU > 90%
        if metrics.cpu_percent > 90.0 or metrics.memory_percent > 90.0:
            status = NodeStatus.DEGRADED

        return HeartbeatPayload(
            node_id=self.node_id,
            timestamp=time.time(),
            status=status,
            metrics=metrics,
            active_services=list(self.command_handler.running_services),
            metadata={"throttled": self.command_handler.throttled}
        )
        
if __name__ == "__main__":
    import os
    import requests

    node_id = os.getenv("NODE_ID", "edge-node-local-01")
    backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    endpoint = f"{backend_url}/api/v1/telemetry/heartbeat"

    agent = EdgeAgent(node_id=node_id, heartbeat_interval_sec=1.0)
    print(f"[EDGE AGENT] Started daemon for '{node_id}', streaming to {endpoint}...")

    try:
        while True:
            payload = agent.build_heartbeat()
            try:
                res = requests.post(endpoint, json=payload.model_dump(), timeout=2.0)
                if res.status_code == 200:
                    data = res.json()
                    dispatched = data.get("dispatched_commands", [])
                    print(f"[{node_id}] Heartbeat ACK | CPU: {payload.metrics.cpu_percent:.1f}% | RAM: {payload.metrics.memory_percent:.1f}% | Queued Commands: {len(dispatched)}")
                    for cmd_dict in dispatched:
                        cmd_obj = CommandPayload(**cmd_dict)
                        recov = agent.command_handler.execute_command(cmd_obj)
                        print(f"[{node_id}] Executed command {cmd_obj.command_id}: {recov.message}")
            except Exception as e:
                print(f"[{node_id}] Connection waiting for backend: {e}")

            time.sleep(agent.interval)
    except KeyboardInterrupt:
        print(f"\n[EDGE AGENT] Stopping '{node_id}' cleanly.")