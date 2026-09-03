from typing import Dict
from swarm.state import SwarmNodeState

class RoleManager:
    """
    Manages the dynamic assignment of roles to drones within the swarm.
    Roles: Gateway, Relay, Worker, Backup, Degraded.
    """
    
    def __init__(self):
        pass

    def evaluate_role(self, node: SwarmNodeState) -> str:
        """
        Evaluates the node's state and determines its appropriate role.
        """
        if node.health == "Offline":
            return "Offline"

        if node.health == "Degraded" or node.battery < 15.0:
            return "Degraded"

        # If it's a designated Gateway, it shouldn't change unless failed
        if node.role == "Gateway":
            return "Gateway"

        # Basic role assignment based on battery and link quality, 
        # actual relay selection is driven by SwarmDecisionEngine.
        return node.role

    def transition_role(self, node: SwarmNodeState, new_role: str):
        """
        Transitions the node to a new role.
        """
        old_role = node.role
        if old_role != new_role:
            node.role = new_role
            # Could trigger an event or log here
            print(f"Node {node.node_id} transitioned from {old_role} to {new_role}")
