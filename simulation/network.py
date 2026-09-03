import random
from typing import Dict
from swarm.state import SwarmNodeState
from simulation.topology import SimulatedTopology
from simulation.environment import Environment

class NetworkSimulator:
    """
    Models packet delivery, latency, and packet loss attrition for the digital twin.
    Combines topology distance metrics with environmental interference.
    
    Does NOT own node state. Operates on the authoritative state store passed in.
    """
    
    def __init__(self, topology: SimulatedTopology, environment: Environment):
        self.topology = topology
        self.environment = environment
        
    def simulate_telemetry_tick(self, states: Dict[str, SwarmNodeState]):
        """
        Updates the RSSI, latency, link_quality, and packet loss for all nodes
        in the simulated state. Also depletes battery.
        """
        # Update neighbor lists based on current positions
        self.topology.update_links(states)
        
        for node_id, state in states.items():
            if state.health == "Offline":
                # Offline nodes get worst-case telemetry
                state.link_quality = 0.0
                state.rssi = -100.0
                state.latency = 1000.0
                state.packet_loss = 1.0
                state.neighbors = []
                continue
                
            interference = self.environment.get_interference_penalty(state.position)
            
            if not state.neighbors:
                state.link_quality = 0.0
                state.rssi = -100.0
                state.latency = 1000.0
                state.packet_loss = 1.0
                continue
            
            # Compute per-neighbor link metrics and average
            total_quality = 0.0
            total_rssi = 0.0
            total_latency = 0.0
            total_loss = 0.0
                
            for neighbor_id in state.neighbors:
                neighbor_state = states.get(neighbor_id)
                if not neighbor_state:
                    continue
                metrics = self.topology.get_link_metrics(state, neighbor_state)
                total_quality += metrics['quality']
                total_rssi += metrics['rssi']
                total_latency += metrics['latency']
                total_loss += metrics['loss']
                
            num_neighbors = len(state.neighbors)
            
            # Apply environmental interference
            avg_quality = (total_quality / num_neighbors) * (1.0 - interference * 0.8)
            avg_loss = min(1.0, (total_loss / num_neighbors) + (interference * 0.5))
            
            # Inject small noise for realism
            state.link_quality = max(0.0, min(1.0, avg_quality + random.uniform(-0.02, 0.02)))
            state.rssi = (total_rssi / num_neighbors) - (interference * 20.0)
            state.latency = max(0.0, (total_latency / num_neighbors) + (interference * 100.0))
            state.packet_loss = max(0.0, min(1.0, avg_loss + random.uniform(0.0, 0.03)))
            
            # Battery depletion (relays consume more)
            drain = 0.08 if state.role == "Relay" else 0.04
            state.battery = max(0.0, state.battery - drain)
            
            # Battery floor → health transition
            if state.battery <= 0.0 and state.health != "Offline":
                state.health = "Degraded"
