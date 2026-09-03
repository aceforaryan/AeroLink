import math
from typing import Dict
from swarm.state import SwarmNodeState

class SimulatedTopology:
    """
    Manages the communication graph of the simulated swarm.
    Models packet attrition, latency, and link availability based on distance.
    
    IMPORTANT: Does not own node state. Receives a reference to the 
    authoritative state store (sim.states) via update_links().
    """
    
    def __init__(self):
        self.max_range = 500.0  # meters
        
    def _calculate_distance(self, pos1, pos2) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))

    def update_links(self, states: Dict[str, SwarmNodeState]):
        """
        Recalculates neighbor lists for all nodes based on their current 
        positions. Offline nodes are excluded entirely. Degraded nodes
        remain reachable but with reduced quality (handled by get_link_metrics).
        """
        for node_id, state in states.items():
            if state.health == "Offline":
                state.neighbors = []
                continue
                
            neighbors = []
            for other_id, other_state in states.items():
                if node_id == other_id or other_state.health == "Offline":
                    continue
                    
                dist = self._calculate_distance(state.position, other_state.position)
                if dist <= self.max_range:
                    neighbors.append(other_id)
            
            state.neighbors = neighbors
            
    def get_link_metrics(self, node_a_state: SwarmNodeState, node_b_state: SwarmNodeState) -> dict:
        """
        Returns simulated link quality, RSSI, and latency based on distance
        between two specific nodes. Accounts for degraded node penalty.
        """
        if not node_a_state or not node_b_state:
            return {"rssi": -100.0, "quality": 0.0, "latency": 1000.0, "loss": 1.0}
            
        dist = self._calculate_distance(node_a_state.position, node_b_state.position)
        
        if dist > self.max_range:
            return {"rssi": -100.0, "quality": 0.0, "latency": 1000.0, "loss": 1.0}
            
        # Simplified free-space path loss model approximation
        rssi = -30 - (20 * math.log10(max(1.0, dist)))
        quality = max(0.0, 1.0 - (dist / self.max_range))
        latency = 10.0 + (dist / 10.0)  # base 10ms + dist factor
        loss = 0.01 + (0.1 * (dist / self.max_range))
        
        # Degraded node penalty: if either endpoint is degraded, reduce quality
        if node_a_state.health == "Degraded" or node_b_state.health == "Degraded":
            quality *= 0.4
            latency *= 2.5
            loss = min(1.0, loss + 0.3)
            rssi -= 15.0
        
        return {"rssi": rssi, "quality": quality, "latency": latency, "loss": loss}
