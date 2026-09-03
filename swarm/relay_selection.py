from typing import List, Dict
from swarm.state import SwarmNodeState

class RelaySelector:
    """
    Evaluates candidate nodes for relay roles based on a multi-variable scoring function.
    """

    def __init__(self, weights: Dict[str, float] = None):
        if weights is None:
            self.weights = {
                'q': 1.0, # Communication/Link Quality
                'b': 1.0, # Battery Availability
                'p': 1.0, # Positional Suitability
                'r': 1.0  # Recent Reliability
            }
        else:
            self.weights = weights

    def score_candidate(self, node: SwarmNodeState) -> float:
        """
        Calculates score: Sj = w1*Qj + w2*Bj + w3*Pj + w4*Rj
        """
        # Normalize inputs where possible. Assuming inputs 0-100 or 0-1
        q_j = node.link_quality
        b_j = node.battery / 100.0
        # Positional suitability: simplified for now, assuming higher RSSI correlates loosely to better positional links, or distance to centroid
        p_j = 1.0 if node.rssi > -60 else 0.5
        r_j = 1.0 - node.packet_loss

        score = (self.weights['q'] * q_j +
                 self.weights['b'] * b_j +
                 self.weights['p'] * p_j +
                 self.weights['r'] * r_j)
        return score

    def evaluate_candidates(self, candidates: List[SwarmNodeState]) -> SwarmNodeState:
        """
        Evaluates a list of candidates and returns the best node to act as a relay.
        Returns None if list is empty or no valid candidates.
        """
        if not candidates:
            return None

        best_node = None
        best_score = -1.0

        for node in candidates:
            # Do not select degraded or offline nodes
            if node.health in ["Degraded", "Offline"] or node.role == "Gateway":
                continue
                
            score = self.score_candidate(node)
            if score > best_score:
                best_score = score
                best_node = node
                
        return best_node
