from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

class FailureInjectionCommand(BaseModel):
    node_id: str = None
    target: str = None  # link, rf, etc.
    severity: float = 1.0

router = APIRouter(prefix="/api/c2", tags=["c2"])

# Reference to the running simulation state (set by main.py)
simulation_ref = None

def set_simulation_ref(sim):
    global simulation_ref
    simulation_ref = sim

@router.post("/fail_node")
async def fail_node(cmd: FailureInjectionCommand):
    """
    Deterministically injects a node failure into the simulation.
    Immediately propagates through topology → decision engine → routing.
    """
    if not simulation_ref:
        raise HTTPException(status_code=500, detail="Simulation not linked")
    if not cmd.node_id or cmd.node_id not in simulation_ref.states:
        raise HTTPException(status_code=404, detail=f"Node '{cmd.node_id}' not found")
    
    node = simulation_ref.states[cmd.node_id]
    node.health = "Offline"
    node.neighbors = []
    node.link_quality = 0.0
    node.rssi = -100.0
    node.latency = 1000.0
    node.packet_loss = 1.0
    
    # Immediately propagate: update topology and routing graph
    simulation_ref.network.simulate_telemetry_tick(simulation_ref.states)
    simulation_ref.router.update_graph(simulation_ref.states)
    
    return {"status": "success", "action": f"Node {cmd.node_id} failed and topology updated"}

@router.post("/degrade_link")
async def degrade_link(cmd: FailureInjectionCommand):
    """
    Injects link degradation by placing an interference zone near a node.
    """
    if not simulation_ref:
        raise HTTPException(status_code=500, detail="Simulation not linked")
    
    node = simulation_ref.states.get(cmd.node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{cmd.node_id}' not found")
    
    # Add interference zone centered on the node's position
    radius = 150.0 * max(0.1, cmd.severity)
    simulation_ref.environment.add_interference_zone(
        node.position[0], node.position[1], node.position[2], radius
    )
    
    return {"status": "success", "action": f"Interference zone (r={radius:.0f}m) placed near {cmd.node_id}"}
