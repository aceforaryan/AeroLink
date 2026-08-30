class RFSimulator:
    """
    Simulates RF environments, providing deterministic injection of anomalies
    such as signal degradation, jamming, or node failures.
    """
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        
    def generate_signal(self, time_idx: int):
        """
        Generates simulated complex I/Q samples for a given time index.
        """
        pass
        
    def inject_anomaly(self, anomaly_type: str, severity: float):
        """
        Inject an RF anomaly into the ongoing simulation.
        
        Args:
            anomaly_type (str): E.g., 'jamming', 'fading', 'node_loss'
            severity (float): Magnitude of the anomaly
        """
        pass
