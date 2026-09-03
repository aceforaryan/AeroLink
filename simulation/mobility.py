import math
import random
from typing import Tuple

class MobilityModel:
    """
    Simulates UAV movement in 3D space.
    """
    def __init__(self, bounds: Tuple[float, float, float] = (1000.0, 1000.0, 150.0)):
        self.bounds = bounds
        
    def step(self, position: Tuple[float, float, float], velocity: Tuple[float, float, float], dt: float = 1.0) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """
        Updates position based on velocity. Includes random walk factor for drift.
        """
        x, y, z = position
        vx, vy, vz = velocity
        
        # Add slight random drift
        vx += random.uniform(-0.5, 0.5)
        vy += random.uniform(-0.5, 0.5)
        vz += random.uniform(-0.1, 0.1)
        
        # Max velocity clipping
        max_v = 15.0
        v_mag = math.sqrt(vx**2 + vy**2 + vz**2)
        if v_mag > max_v:
            vx = (vx / v_mag) * max_v
            vy = (vy / v_mag) * max_v
            vz = (vz / v_mag) * max_v

        # Update position
        new_x = x + vx * dt
        new_y = y + vy * dt
        new_z = z + vz * dt
        
        # Bounce off bounds
        if new_x < 0 or new_x > self.bounds[0]: vx = -vx; new_x = max(0.0, min(new_x, self.bounds[0]))
        if new_y < 0 or new_y > self.bounds[1]: vy = -vy; new_y = max(0.0, min(new_y, self.bounds[1]))
        if new_z < 10 or new_z > self.bounds[2]: vz = -vz; new_z = max(10.0, min(new_z, self.bounds[2]))
            
        return (new_x, new_y, new_z), (vx, vy, vz)
