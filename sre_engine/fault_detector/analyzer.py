"""
Real-Time SRE Fault Isolation Engine.
Analyzes node telemetry for CPU starvation, memory leaks, and network dropouts.
"""
from typing import Dict, Any, Optional
from sre_engine.schemas import HeartbeatPayload, NodeStatus
from sre_engine.otel.telemetry import trace_span, fault_counter


class FaultAnalyzer:
    def __init__(self, cpu_threshold: float = 90.0, mem_threshold: float = 90.0, latency_threshold_ms: float = 100.0):
        self.cpu_threshold = cpu_threshold
        self.mem_threshold = mem_threshold
        self.latency_threshold = latency_threshold_ms

    @trace_span("sre.analyze_node_health")
    def analyze_heartbeat(self, heartbeat: HeartbeatPayload) -> Dict[str, Any]:
        """
        Inspects metrics and detects system/network faults in real time.
        Returns a fault isolation report.
        """
        detected_faults = []

        if heartbeat.metrics.cpu_percent >= self.cpu_threshold:
            detected_faults.append(f"CPU_SATURATION ({heartbeat.metrics.cpu_percent:.1f}%)")

        if heartbeat.metrics.memory_percent >= self.mem_threshold:
            detected_faults.append(f"MEMORY_LEAK_RISK ({heartbeat.metrics.memory_percent:.1f}%)")

        if heartbeat.metrics.network_latency_ms >= self.latency_threshold:
            detected_faults.append(f"NETWORK_JITTER ({heartbeat.metrics.network_latency_ms:.1f}ms)")

        is_faulty = len(detected_faults) > 0
        suggested_action = None

        if is_faulty:
            fault_counter.add(1, {"node_id": heartbeat.node_id})
            if "MEMORY_LEAK_RISK" in str(detected_faults) or "CPU_SATURATION" in str(detected_faults):
                suggested_action = "RESTART_SERVICE"
            else:
                suggested_action = "THROTTLE"

        return {
            "node_id": heartbeat.node_id,
            "has_fault": is_faulty,
            "faults": detected_faults,
            "recommended_action": suggested_action,
            "isolated": is_faulty
        }