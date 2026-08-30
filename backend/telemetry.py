from .models import TelemetryPayload

class TelemetryProcessor:
    """
    Handles ingestion and basic validation of incoming telemetry data.
    Aggregates swarm state for the C2 bridge.
    """
    
    def __init__(self):
        self.swarm_state = {}

    def process_telemetry(self, payload: TelemetryPayload):
        """
        Ingest a new telemetry payload and update the global swarm state.
        
        Args:
            payload (TelemetryPayload): The structured telemetry data from a node.
        """
        self.swarm_state[payload.node_id] = payload
        # Additional processing (e.g., logging, alerting) can be hooked here.
        return True

    def get_swarm_state(self):
        """
        Retrieve the latest known state of all nodes in the swarm.
        
        Returns:
            dict: Mapping of node_id to TelemetryPayload.
        """
        return self.swarm_state
