from typing import List, Dict
from mission.objectives import MissionObjective
from swarm.state import SwarmNodeState

class MissionPlanner:
    """
    Coordinates overall swarm objectives.
    
    Mission state machine:
      NOT_STARTED → ACTIVE → DEGRADED ⇄ ACTIVE → COMPLETED
                                ↓
                           RECOVERING → ACTIVE
    
    States:
      - Not Started: Before first update
      - Active: All objectives currently satisfied
      - Degraded: One or more objectives not satisfied
      - Recovering: Was degraded, objectives are being restored
      - Completed: All objectives satisfied AND mission explicitly completed
    """
    def __init__(self):
        self.objectives: List[MissionObjective] = []
        self.mission_status = "Not Started"
        self._was_degraded = False
        
    def add_objective(self, objective: MissionObjective):
        self.objectives.append(objective)
        
    def update(self, states: Dict[str, SwarmNodeState]):
        """
        Evaluates mission progress based on current swarm state.
        Transitions mission status based on objective satisfaction.
        """
        if self.mission_status == "Not Started":
            self.mission_status = "Active"
            
        # Evaluate all objectives against current state
        all_satisfied = True
        for obj in self.objectives:
            obj.evaluate(states)
            if not obj.is_completed():
                all_satisfied = False
        
        if not self.objectives:
            return
                
        # State transitions
        if all_satisfied:
            if self._was_degraded:
                self.mission_status = "Recovering"
                self._was_degraded = False
            else:
                self.mission_status = "Active"
        else:
            self.mission_status = "Degraded"
            self._was_degraded = True
            
    def get_status(self) -> str:
        return self.mission_status
    
    def reset(self):
        """Fully resets mission state."""
        self.objectives.clear()
        self.mission_status = "Not Started"
        self._was_degraded = False
