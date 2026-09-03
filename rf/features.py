from typing import List, Dict
from swarm.state import SwarmNodeState

class FeatureExtractor:
    """
    Extracts relevant RF spectral features and fuses them with standard 
    telemetry metrics for swarm state interpretation.
    """
    
    def __init__(self):
        pass
        
    def extract(self, rf_detector_output: dict, node_state: SwarmNodeState) -> Dict:
        """
        Fuses RF anomaly state with standard node metrics to produce a 
        comprehensive link degradation state.
        """
        return {
            "spectral_anomaly": rf_detector_output.get("anomaly", False),
            "anomaly_severity": rf_detector_output.get("severity", 0.0),
            "link_quality": node_state.link_quality,
            "packet_loss": node_state.packet_loss,
            "rssi": node_state.rssi
        }
