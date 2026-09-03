import time
from typing import Dict, List
from swarm.state import SwarmNodeState
from swarm.prediction import FailurePredictor
from swarm.relay_selection import RelaySelector

class SwarmDecisionEngine:
    """
    The central intelligence component for the swarm.
    Performs the closed loop: Sense -> Assess -> Predict -> Reconfigure -> Recover
    
    Handles two distinct failure modes:
    1. OFFLINE relay: Immediate replacement needed (hard failure)
    2. HIGH-RISK relay: Predictive replacement (soft degradation)
    """
    def __init__(self):
        self.predictor = FailurePredictor()
        self.relay_selector = RelaySelector()
        self.failure_threshold = 0.6
        
        # Cooldown: prevent oscillation by tracking recent reconfigurations
        self._last_reconfigure_time: float = 0.0
        self._reconfigure_cooldown: float = 3.0  # seconds
        
    def evaluate_objective_function(self, node: SwarmNodeState, weights: Dict[str, float] = None) -> float:
        """
        J = w1*C - w2*L + w3*B - w4*E - w5*R
        """
        if weights is None:
            weights = {'c': 1.0, 'l': 0.1, 'b': 0.5, 'e': 0.1, 'r': 0.2}
            
        C = node.link_quality
        L = node.latency
        B = node.battery
        E = 10.0  # Energy cost placeholder
        R = 1.0 if node.role == "Relay" else 0.0

        J = (weights['c'] * C - 
             weights['l'] * L + 
             weights['b'] * B - 
             weights['e'] * E - 
             weights['r'] * R)
        return J

    def process_swarm_state(self, states: Dict[str, SwarmNodeState], rf_features_map: Dict[str, Dict]) -> List[Dict]:
        """
        Runs the decision loop across all nodes.
        Returns a list of actions taken.
        
        Decision flow:
        1. SENSE: Read all node states + RF features
        2. ASSESS: Compute connectivity risk for every node
        3. PREDICT: Identify relays that are offline or at high risk
        4. RECONFIGURE: Select alternative relay, execute role swap
        """
        actions = []
        now = time.monotonic()
        
        # 1. SENSE & ASSESS: Compute risk for all nodes
        for node_id, state in states.items():
            rf_features = rf_features_map.get(node_id, {})
            
            if state.health == "Offline":
                state.connectivity_risk = 1.0
            else:
                risk = self.predictor.estimate_link_failure_probability(state, rf_features)
                state.connectivity_risk = risk
        
        # Check cooldown before issuing reconfiguration
        if now - self._last_reconfigure_time < self._reconfigure_cooldown:
            return actions
        
        # 2. PREDICT & RECONFIGURE: Find relays that need replacement
        for node_id, state in states.items():
            needs_replacement = False
            reason = ""
            
            # Case A: Relay is Offline (hard failure — immediate replacement)
            if state.role == "Relay" and state.health == "Offline":
                needs_replacement = True
                reason = f"{node_id} relay OFFLINE — immediate replacement required"
                actions.append({"type": "WARNING", "node": node_id, 
                               "message": f"Relay {node_id} is OFFLINE (hard failure)"})
                
            # Case B: Relay has high predicted failure risk (soft degradation)
            elif state.role == "Relay" and state.connectivity_risk > self.failure_threshold:
                needs_replacement = True
                reason = f"{node_id} relay at high risk ({state.connectivity_risk:.2f})"
                actions.append({"type": "WARNING", "node": node_id,
                               "message": f"Link degradation predicted for {node_id} (risk: {state.connectivity_risk:.2f})"})
            
            if needs_replacement:
                # Evaluate candidates: all nodes except the failing one and the gateway
                candidates = [s for s in states.values() if s.node_id != node_id]
                best_alternative = self.relay_selector.evaluate_candidates(candidates)
                
                if best_alternative:
                    score = self.relay_selector.score_candidate(best_alternative)
                    actions.append({
                        "type": "ACTION",
                        "node": best_alternative.node_id,
                        "message": f"{best_alternative.node_id} selected as alternative relay (score: {score:.2f})"
                    })
                    actions.append({
                        "type": "RECONFIGURE", 
                        "old_relay": node_id, 
                        "new_relay": best_alternative.node_id
                    })
                    self._last_reconfigure_time = now
                    break  # Only one reconfiguration per tick to prevent cascading
                else:
                    actions.append({
                        "type": "WARNING", 
                        "node": "SWARM", 
                        "message": "No viable alternative relays available"
                    })
                    
        return actions
    
    def reset(self):
        """Clears all decision engine state."""
        self._last_reconfigure_time = 0.0
