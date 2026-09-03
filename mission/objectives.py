from abc import ABC, abstractmethod
from typing import Dict
from swarm.state import SwarmNodeState

class MissionObjective(ABC):
    """
    Base class for mission objectives.
    """
    @abstractmethod
    def evaluate(self, states: Dict[str, SwarmNodeState]):
        pass
        
    @abstractmethod
    def is_completed(self) -> bool:
        pass

class MaintainConnectivityObjective(MissionObjective):
    """
    Objective to ensure all active nodes can reach the Gateway.
    """
    def __init__(self, target_pdr: float = 0.9):
        self.target_pdr = target_pdr
        self.current_pdr = 1.0
        
    def evaluate(self, states: Dict[str, SwarmNodeState]):
        # Calculate a simple average PDR across active nodes
        active_nodes = [s for s in states.values() if s.health != "Offline"]
        if not active_nodes:
            self.current_pdr = 0.0
            return
            
        total_loss = sum(s.packet_loss for s in active_nodes)
        avg_loss = total_loss / len(active_nodes)
        self.current_pdr = 1.0 - avg_loss
        
    def is_completed(self) -> bool:
        # This is a continuous objective, so it's "completed" if it's currently satisfying the target
        return self.current_pdr >= self.target_pdr
