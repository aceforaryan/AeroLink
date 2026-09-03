from typing import Tuple, List

class Environment:
    """
    Models external environmental factors like RF interference zones or obstacles.
    """
    def __init__(self):
        self.interference_zones: List[Tuple[float, float, float, float]] = [] # x, y, z, radius
        
    def add_interference_zone(self, x: float, y: float, z: float, radius: float):
        self.interference_zones.append((x, y, z, radius))
        
    def get_interference_penalty(self, position: Tuple[float, float, float]) -> float:
        """
        Returns a penalty factor (0.0 to 1.0) based on proximity to interference zones.
        """
        penalty = 0.0
        px, py, pz = position
        for zx, zy, zz, radius in self.interference_zones:
            dist = ((px - zx)**2 + (py - zy)**2 + (pz - zz)**2)**0.5
            if dist < radius:
                # Closer to center = higher penalty
                severity = 1.0 - (dist / radius)
                penalty = max(penalty, severity)
        return penalty
