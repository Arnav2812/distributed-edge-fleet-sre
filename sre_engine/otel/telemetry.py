"""
OpenTelemetry Tracing & Metrics Instrumentation for Edge Fleet SRE Platform.
Generates spans for heartbeat ingestion, fault detection, and telemetry throughput.
"""
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from functools import wraps
import time

# Initialize OpenTelemetry Tracing Provider
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer("sre.fleet.engine", "1.0.0")

# Initialize OpenTelemetry Metrics Provider
meter = metrics.get_meter("sre.fleet.engine", "1.0.0")

# Custom SRE Metrics
ingest_counter = meter.create_counter(
    name="fleet_heartbeats_total",
    description="Total count of edge node heartbeats processed",
    unit="1"
)

fault_counter = meter.create_counter(
    name="fleet_faults_isolated_total",
    description="Total system and network faults isolated in real time",
    unit="1"
)

latency_histogram = meter.create_histogram(
    name="telemetry_ingest_duration_ms",
    description="Latency distribution for processing edge node heartbeats",
    unit="ms"
)


def trace_span(span_name: str):
    """Decorator to wrap execution inside an active OpenTelemetry trace span."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("sre.status", "OK")
                    return result
                except Exception as exc:
                    span.set_attribute("sre.status", "ERROR")
                    span.record_exception(exc)
                    raise exc
                finally:
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    latency_histogram.record(duration_ms)
        return wrapper
    return decorator