from mission.planner import MissionPlanner
from mission.objectives import MaintainConnectivityObjective

class Scenario:
    def __init__(self, name: str):
        self.name = name
        self.planner = MissionPlanner()
        
    def setup(self):
        """Reset and initialize the scenario. Safe to call multiple times."""
        self.planner.reset()

class DisasterResponseScenario(Scenario):
    """
    A disaster has disrupted terrestrial communication.
    The swarm is deployed to provide temporary communication coverage.
    """
    def __init__(self):
        super().__init__("Disaster Response Comm Swarm")
        
    def setup(self):
        # Reset planner first to prevent objective accumulation
        super().setup()
        # Goal: maintain >90% PDR despite failures
        obj = MaintainConnectivityObjective(target_pdr=0.90)
        self.planner.add_objective(obj)
