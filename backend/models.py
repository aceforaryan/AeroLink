from typing import Optional
from pydantic import BaseModel, Field

class TelemetryPayload(BaseModel):
    """
    Compact state record for each swarm node.
    Kept sparse and versioned to support deterministic relay selection.
    """
    node_id: str = Field(..., description="Unique identifier for the drone node")
    timestamp: float = Field(..., description="UNIX timestamp of the telemetry reading")
    lat: float = Field(..., description="Latitude coordinate")
    lon: float = Field(..., description="Longitude coordinate")
    battery: float = Field(..., description="Battery level percentage (0.0 to 100.0)")
    rssi: float = Field(..., description="Received Signal Strength Indicator")
    link_quality: float = Field(..., description="Calculated link quality metric (0.0 to 1.0)")
    role: str = Field(..., description="Current role: GATEWAY, RELAY, WORKER, BACKUP RELAY, or DEGRADED")
    health: float = Field(..., description="Overall hardware/software health score")
    anomaly_flags: int = Field(0, description="Bitmask of active RF or system anomalies")
    mission_state: str = Field("active", description="Current state of the assigned mission task")
