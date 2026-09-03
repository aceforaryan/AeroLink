from typing import Optional, List
from pydantic import BaseModel, Field

class TelemetryPayload(BaseModel):
    """
    Compact state record for each swarm node, matching SwarmNodeState.
    """
    node_id: str = Field(..., description="Unique identifier for the drone node")
    timestamp: float = Field(..., description="UNIX timestamp of the telemetry reading")
    lat: float = Field(..., description="Latitude coordinate or X position")
    lon: float = Field(..., description="Longitude coordinate or Y position")
    alt: float = Field(..., description="Altitude coordinate or Z position")
    battery: float = Field(..., description="Battery level percentage (0.0 to 100.0)")
    rssi: float = Field(..., description="Received Signal Strength Indicator")
    link_quality: float = Field(..., description="Calculated link quality metric (0.0 to 1.0)")
    packet_loss: float = Field(0.0, description="Packet loss ratio")
    latency: float = Field(0.0, description="Latency in ms")
    neighbors: List[str] = Field(default_factory=list, description="IDs of connected neighbors")
    role: str = Field(..., description="Current role: Gateway, Relay, Worker, or Degraded")
    health: str = Field("Healthy", description="Overall node health state")
    mission_state: str = Field("Idle", description="Current state of the assigned mission task")
    connectivity_risk: float = Field(0.0, description="Predicted risk of link failure")
