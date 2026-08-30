class SimulatedNode:
    """
    Represents a digital twin of a physical drone in the swarm.
    Simulates mobility, battery depletion, and component failures.
    """
    
    def __init__(self, node_id: str, start_lat: float, start_lon: float):
        self.node_id = node_id
        self.lat = start_lat
        self.lon = start_lon
        self.battery = 100.0
        self.is_active = True
        
    def update_position(self, delta_time: float):
        """
        Updates the node's position based on a trajectory model.
        """
        pass
        
    def consume_battery(self, delta_time: float, current_role: str):
        """
        Reduces battery based on current role (e.g., RELAY uses more power).
        """
        pass
        
    def trigger_failure(self, failure_type: str):
        """
        Injects a hardware or software failure into the node.
        """
        if failure_type == "power_loss":
            self.is_active = False
            self.battery = 0.0
