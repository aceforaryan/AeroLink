from dataclasses import dataclass, field
from typing import List, Dict, Tuple

@dataclass
class SwarmNodeState:
    node_id: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    battery: float = 100.0
    rssi: float = -50.0
    link_quality: float = 1.0
    packet_loss: float = 0.0
    latency: float = 0.0
    neighbors: List[str] = field(default_factory=list)
    role: str = "Worker" # Gateway, Relay, Worker, Degraded
    health: str = "Healthy" # Healthy, Degraded, Offline
    mission_state: str = "Idle"
    connectivity_risk: float = 0.0
