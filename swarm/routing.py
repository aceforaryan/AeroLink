import heapq
from typing import Dict, List, Tuple
from swarm.state import SwarmNodeState

class Router:
    """
    Implements resilient network routing for the swarm.
    Maintains the dynamic network graph G=(V,E).
    
    Edge weights are computed from pairwise link metrics between neighbors,
    not from node-level averages.
    """
    
    def __init__(self):
        # adjacency list: node_id -> {neighbor_id: weight}
        self.graph: Dict[str, Dict[str, float]] = {}
        
    def update_graph(self, states: Dict[str, SwarmNodeState]):
        """
        Rebuilds the graph from the latest node states.
        
        - Offline nodes are EXCLUDED (no vertex, no edges).
        - Degraded nodes are INCLUDED with higher edge cost.
        - Edge weight reflects the quality of the specific link between two nodes.
        """
        self.graph.clear()
        
        for node_id, state in states.items():
            # Offline nodes are completely removed from the graph
            if state.health == "Offline":
                continue
                
            self.graph[node_id] = {}
            for neighbor_id in state.neighbors:
                neighbor = states.get(neighbor_id)
                if not neighbor or neighbor.health == "Offline":
                    continue
                
                # Pairwise edge cost based on the link between these two specific nodes.
                # Lower link_quality → higher cost. Higher latency → higher cost.
                # Use the worse of the two endpoints' metrics for the edge.
                lq = min(state.link_quality, neighbor.link_quality)
                lat = max(state.latency, neighbor.latency)
                pl = max(state.packet_loss, neighbor.packet_loss)
                
                cost = (1.0 / max(0.01, lq)) + (lat / 100.0) + (pl * 5.0)
                
                # Additional penalty for degraded endpoints
                if state.health == "Degraded":
                    cost *= 3.0
                if neighbor.health == "Degraded":
                    cost *= 3.0
                    
                self.graph[node_id][neighbor_id] = cost

    def compute_route(self, source: str, destination: str) -> List[str]:
        """
        Calculates the optimal path using Dijkstra's algorithm.
        Returns empty list if no path exists.
        """
        if source not in self.graph or destination not in self.graph:
            return []

        distances = {node: float('infinity') for node in self.graph}
        distances[source] = 0
        pq = [(0, source)]
        previous_nodes = {node: None for node in self.graph}

        while pq:
            current_distance, current_node = heapq.heappop(pq)

            if current_node == destination:
                path = []
                while current_node is not None:
                    path.append(current_node)
                    current_node = previous_nodes[current_node]
                return path[::-1]

            if current_distance > distances[current_node]:
                continue

            for neighbor, weight in self.graph.get(current_node, {}).items():
                distance = current_distance + weight
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous_nodes[neighbor] = current_node
                    heapq.heappush(pq, (distance, neighbor))

        return []  # No path found
        
    def trigger_recovery(self, failed_node: str, states: Dict[str, SwarmNodeState]):
        """
        Initiates autonomous healing by marking a node as Offline and rebuilding the graph.
        """
        if failed_node in states:
            states[failed_node].health = "Offline"
            states[failed_node].neighbors = []
        self.update_graph(states)
