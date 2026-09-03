from swarm.state import SwarmNodeState
from typing import Dict

class FailurePredictor:
    """
    Estimates whether a link or relay is likely to fail within a defined horizon.
    """
    
    def __init__(self):
        # We could initialize a lightweight ML model here (e.g., Decision Tree)
        # For now, using a heuristic-based probabilistic model
        pass
        
    def estimate_link_failure_probability(self, node: SwarmNodeState, rf_features: Dict[str, float]) -> float:
        """
        Estimates probability of link failure P(failure within T).
        Features: RSSI trend, packet loss, battery, spectral anomalies.
        """
        probability = 0.0
        
        # 1. Battery Risk
        if node.battery < 10.0:
            probability += 0.8
        elif node.battery < 20.0:
            probability += 0.4
            
        # 2. RF / Link Risk
        if rf_features.get('spectral_anomaly', False):
            probability += 0.3
            
        # 3. Packet loss trend
        if node.packet_loss > 0.2:
            probability += 0.4
        elif node.packet_loss > 0.05:
            probability += 0.1
            
        # 4. Latency
        if node.latency > 200.0:
            probability += 0.2

        # 5. RSSI
        if node.rssi < -85.0:
            probability += 0.5
            
        return min(probability, 1.0)
