from typing import List

class AnomalyDetector:
    """
    Implements EWMA (Exponentially Weighted Moving Average) baseline for RF environments.
    Isolates deviations from normal operating profiles.
    
    The baseline adapts SLOWLY so that sudden spikes are detected as anomalies.
    B[k] = (1 - alpha) * B[k-1] + alpha * P[k]
    
    With alpha = 0.1, the baseline gives 90% weight to history and 10% to the 
    new sample — meaning it adapts slowly and sudden deviations stand out.
    """
    
    def __init__(self, alpha: float = 0.1, threshold: float = 10.0):
        self.alpha = alpha
        self.threshold = threshold
        self.baseline: List[float] = None
        
    def update_baseline(self, current_power: List[float]):
        """
        Updates the EWMA baseline using the latest spectral power estimate.
        B[k] = (1 - alpha) * B[k-1] + alpha * P[k]
        """
        if self.baseline is None:
            self.baseline = list(current_power)
            return

        for k in range(min(len(current_power), len(self.baseline))):
            self.baseline[k] = (1.0 - self.alpha) * self.baseline[k] + self.alpha * current_power[k]
        
    def detect(self, current_power: List[float]) -> dict:
        """
        Calculates deviation D[k] = P[k] - B[k].
        Returns dict with anomaly boolean, deviation severity, and per-bin deviations.
        """
        if self.baseline is None:
            self.update_baseline(current_power)
            return {"anomaly": False, "severity": 0.0, "deviations": [0.0] * len(current_power)}

        deviations = []
        max_deviation = 0.0
        for k in range(min(len(current_power), len(self.baseline))):
            deviation = current_power[k] - self.baseline[k]
            deviations.append(deviation)
            if deviation > max_deviation:
                max_deviation = deviation
                
        is_anomaly = max_deviation > self.threshold
        
        # Update baseline slowly — only when NOT anomalous, so the baseline
        # doesn't get corrupted by jamming signals
        if not is_anomaly:
            self.update_baseline(current_power)
            
        return {"anomaly": is_anomaly, "severity": max_deviation, "deviations": deviations}
    
    def reset(self):
        """Clears baseline state."""
        self.baseline = None
