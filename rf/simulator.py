import math
import random
from typing import List

class RFSimulator:
    """
    Simulates RF environments, providing deterministic injection of anomalies
    such as signal degradation, jamming, or node failures.
    
    Generates synthetic I/Q-like power spectral density samples for the
    AnomalyDetector to consume.
    """
    
    def __init__(self, seed: int = 42, num_bins: int = 10):
        self.seed = seed
        self.num_bins = num_bins
        self.rng = random.Random(seed)
        self._anomaly_active = False
        self._anomaly_severity = 0.0
        self._anomaly_bins = []
        
    def generate_psd(self, interference_level: float = 0.0) -> List[float]:
        """
        Generates simulated Power Spectral Density samples.
        
        Args:
            interference_level: 0.0 (clean) to 1.0+ (heavy interference)
            
        Returns:
            List of PSD bin values (power per frequency bin)
        """
        # Base noise floor with slight variation
        psd = [1.0 + self.rng.uniform(-0.15, 0.15) for _ in range(self.num_bins)]
        
        # Apply interference spikes
        if interference_level > 0.1 or self._anomaly_active:
            severity = max(interference_level, self._anomaly_severity)
            spike_mag = 8.0 + (severity * 14.0)
            # Concentrate spikes in mid-band bins
            spike_bins = self._anomaly_bins if self._anomaly_bins else [
                self.num_bins // 3, self.num_bins // 3 + 1
            ]
            for b in spike_bins:
                if 0 <= b < self.num_bins:
                    psd[b] = spike_mag + self.rng.uniform(-0.5, 0.5)
        
        return psd
        
    def inject_anomaly(self, anomaly_type: str, severity: float = 1.0, bins: List[int] = None):
        """
        Inject an RF anomaly into the ongoing simulation.
        
        Args:
            anomaly_type: 'jamming', 'fading', 'narrowband'
            severity: Magnitude of the anomaly (0.0 to 2.0+)
            bins: Which frequency bins to affect (defaults to mid-band)
        """
        self._anomaly_active = True
        self._anomaly_severity = severity
        
        if bins:
            self._anomaly_bins = bins
        elif anomaly_type == "jamming":
            # Broadband: affect multiple bins
            self._anomaly_bins = list(range(self.num_bins // 4, 3 * self.num_bins // 4))
        elif anomaly_type == "narrowband":
            # Single bin spike
            self._anomaly_bins = [self.num_bins // 2]
        else:
            self._anomaly_bins = [self.num_bins // 3, self.num_bins // 3 + 1]
    
    def clear_anomaly(self):
        """Removes any active RF anomaly."""
        self._anomaly_active = False
        self._anomaly_severity = 0.0
        self._anomaly_bins = []
        
    def reset(self):
        """Resets the simulator to its initial state."""
        self.rng = random.Random(self.seed)
        self.clear_anomaly()
