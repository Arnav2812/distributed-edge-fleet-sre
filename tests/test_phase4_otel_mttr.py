"""
Phase 4 Verification Gate:
Tests OpenTelemetry tracing, real-time fault isolation, and validates the 45% MTTR reduction claim.
"""
import pytest
from sre_engine.schemas import HeartbeatPayload, TelemetryMetrics, NodeStatus
from sre_engine.fault_detector.analyzer import FaultAnalyzer
from sre_engine.fault_detector.mttr_benchmark import run_mttr_benchmark
from sre_engine.otel.telemetry import trace_span


def test_opentelemetry_span_execution():
    """Verifies that OpenTelemetry decorator starts and ends spans cleanly."""
    @trace_span("test.sre_execution")
    def sample_monitored_task():
        return 42

    result = sample_monitored_task()
    assert result == 42


def test_fault_isolation_healthy_node():
    analyzer = FaultAnalyzer()
    healthy_hb = HeartbeatPayload(
        node_id="node-health-01",
        metrics=TelemetryMetrics(cpu_percent=45.0, memory_percent=50.0, network_latency_ms=15.0)
    )
    report = analyzer.analyze_heartbeat(healthy_hb)
    assert report["has_fault"] is False
    assert len(report["faults"]) == 0
    assert report["recommended_action"] is None


def test_fault_isolation_memory_and_cpu_saturation():
    analyzer = FaultAnalyzer()
    failing_hb = HeartbeatPayload(
        node_id="node-failing-02",
        metrics=TelemetryMetrics(cpu_percent=96.4, memory_percent=92.1, network_latency_ms=12.0)
    )
    report = analyzer.analyze_heartbeat(failing_hb)
    assert report["has_fault"] is True
    assert "CPU_SATURATION" in report["faults"][0]
    assert "MEMORY_LEAK_RISK" in report["faults"][1]
    assert report["recommended_action"] == "RESTART_SERVICE"


def test_mttr_reduction_benchmark_exceeds_45_percent():
    """Mathematically validates the 45% MTTR reduction stated on the resume."""
    benchmark = run_mttr_benchmark(trials=50)
    assert benchmark["manual_mttr_sec"] > benchmark["automated_mttr_sec"]
    assert benchmark["mttr_reduction_percent"] >= 45.0
    assert benchmark["claim_verified"] is True