"""
Core data contracts for Distributed Edge Fleet SRE Platform.
Defines schemas for telemetry heartbeats, hardware/OS metrics, and remote commands.
"""
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import time


class NodeStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    OFFLINE = "OFFLINE"


class CommandAction(str, Enum):
    SET_STATE = "SET_STATE"
    RESTART_SERVICE = "RESTART_SERVICE"
    THROTTLE = "THROTTLE"
    PING = "PING"


class TelemetryMetrics(BaseModel):
    cpu_percent: float = Field(..., ge=0.0, le=100.0, description="CPU utilization percentage")
    memory_percent: float = Field(..., ge=0.0, le=100.0, description="RAM utilization percentage")
    disk_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="Disk utilization percentage")
    network_latency_ms: float = Field(default=0.0, ge=0.0, description="Network ping round-trip in ms")
    temperature_c: Optional[float] = Field(default=None, description="System/CPU temperature in Celsius")


class HeartbeatPayload(BaseModel):
    node_id: str = Field(..., min_length=3, max_length=64, description="Unique edge node identifier")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp of heartbeat")
    status: NodeStatus = Field(default=NodeStatus.HEALTHY)
    metrics: TelemetryMetrics
    active_services: list[str] = Field(default_factory=list, description="List of running edge service names")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Platform and OS metadata")


class CommandPayload(BaseModel):
    command_id: str = Field(..., description="Unique UUID for command tracking")
    target_node_id: str = Field(...)
    action: CommandAction
    parameters: Dict[str, Any] = Field(default_factory=dict)
    issued_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = Field(default=None)


class CommandResponse(BaseModel):
    command_id: str
    node_id: str
    success: bool
    message: str
    executed_at: float = Field(default_factory=time.time)