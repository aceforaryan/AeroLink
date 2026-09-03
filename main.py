import uvicorn
import asyncio
import random
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from typing import Dict, List

# Core modules
from swarm.state import SwarmNodeState
from swarm.decision_engine import SwarmDecisionEngine
from swarm.routing import Router
from simulation.topology import SimulatedTopology
from simulation.mobility import MobilityModel
from simulation.environment import Environment
from simulation.network import NetworkSimulator
from mission.scenarios import DisasterResponseScenario
from rf.detector import AnomalyDetector
from rf.features import FeatureExtractor
import backend.c2 as c2

# Deterministic seed for reproducibility during demos
RANDOM_SEED = 42


class SimulationState:
    """
    The single authoritative owner of all simulation state.
    All layers read from and write to self.states.
    """
    def __init__(self):
        # Authoritative state store
        self.states: Dict[str, SwarmNodeState] = {}
        
        # Layer instances
        self.mobility = MobilityModel()
        self.environment = Environment()
        self.topology = SimulatedTopology()
        self.network = NetworkSimulator(self.topology, self.environment)
        self.decision_engine = SwarmDecisionEngine()
        self.router = Router()
        self.scenario = DisasterResponseScenario()
        self.rf_detectors: Dict[str, AnomalyDetector] = {}
        self.feature_extractor = FeatureExtractor()
        
        # Dashboard data
        self.current_psd: Dict[str, List[float]] = {}   # per-node PSD
        self.psd_baseline: Dict[str, List[float]] = {}   # per-node baseline
        self.active_route: List[str] = []
        self.actions_log: List[Dict] = []
        self.tick_count: int = 0
        
    def init_swarm(self, count=5):
        """
        Initializes (or fully resets) the swarm to its initial formation.
        Clears ALL state across all layers to prevent stale data.
        """
        # 1. Clear authoritative state
        self.states.clear()
        self.actions_log.clear()
        self.active_route.clear()
        self.current_psd.clear()
        self.psd_baseline.clear()
        self.tick_count = 0
        
        # 2. Reset all layer state
        self.environment.interference_zones.clear()
        self.router.graph.clear()
        self.decision_engine.reset()
        self.scenario.setup()  # Calls planner.reset() + re-adds objectives
        self.rf_detectors.clear()
        
        # 3. Strategic initial formation for disaster response
        positions = [
            (200.0, 500.0, 80.0),   # UAV-1: Gateway (base station)
            (400.0, 480.0, 100.0),  # UAV-2: Primary Relay
            (450.0, 650.0, 95.0),   # UAV-3: Worker / Best backup candidate
            (700.0, 450.0, 110.0),  # UAV-4: Worker
            (750.0, 600.0, 105.0),  # UAV-5: Worker (furthest)
        ]
        roles = ["Gateway", "Relay", "Worker", "Worker", "Worker"]
        
        for i in range(count):
            node_id = f"UAV-{i+1}"
            pos = positions[i] if i < len(positions) else (float(i * 150), 500.0, 100.0)
            state = SwarmNodeState(
                node_id=node_id,
                position=pos,
                velocity=(0.0, 0.0, 0.0),
                role=roles[i] if i < len(roles) else "Worker",
                battery=98.0 - (i * 2.5),
                health="Healthy",
            )
            self.states[node_id] = state
            self.rf_detectors[node_id] = AnomalyDetector()
            self.current_psd[node_id] = [1.2] * 10
            self.psd_baseline[node_id] = [1.2] * 10
            
    def tick(self):
        """
        One complete iteration of the autonomous loop:
        Sense → Assess → Predict → Reconfigure → Recover → Continue Mission
        """
        self.actions_log.clear()
        self.tick_count += 1
        
        # ── 1. MOBILITY ──────────────────────────────────────────────
        for node_id, state in self.states.items():
            if state.health == "Offline":
                continue
            new_pos, new_vel = self.mobility.step(
                state.position, state.velocity, dt=0.5
            )
            state.position = new_pos
            state.velocity = new_vel
                
        # ── 2. NETWORK SIMULATION (updates telemetry + topology) ──
        self.network.simulate_telemetry_tick(self.states)
        
        # ── 3. ROUTING GRAPH REBUILD ──────────────────────────────
        self.router.update_graph(self.states)
        
        # ── 4. PER-NODE RF ANALYSIS ──────────────────────────────
        rf_features_map = {}
        for node_id, state in self.states.items():
            if state.health == "Offline":
                rf_features_map[node_id] = {
                    "spectral_anomaly": False, "anomaly_severity": 0.0,
                    "link_quality": 0.0, "packet_loss": 1.0, "rssi": -100.0
                }
                continue
                
            # Generate per-node PSD based on that node's local environment
            interference = self.environment.get_interference_penalty(state.position)
            node_psd = [1.2 + random.uniform(-0.1, 0.1) for _ in range(10)]
            if interference > 0.1:
                # Spectral spikes proportional to interference severity
                spike_mag = 10.0 + (interference * 12.0)
                node_psd[4] = spike_mag + random.uniform(-0.5, 0.5)
                node_psd[5] = (spike_mag + 1.5) + random.uniform(-0.5, 0.5)
            
            self.current_psd[node_id] = node_psd
            
            det_out = self.rf_detectors[node_id].detect(node_psd)
            if self.rf_detectors[node_id].baseline:
                self.psd_baseline[node_id] = list(self.rf_detectors[node_id].baseline)
            
            rf_features_map[node_id] = self.feature_extractor.extract(det_out, state)
            
        # ── 5. SWARM DECISION ENGINE ─────────────────────────────
        actions = self.decision_engine.process_swarm_state(self.states, rf_features_map)
        self.actions_log.extend(actions)
        
        # ── 6. EXECUTE RECONFIGURATION ───────────────────────────
        for action in actions:
            if action.get("type") == "RECONFIGURE":
                old_id = action.get("old_relay")
                new_id = action.get("new_relay")
                # Demote old relay (only if not Gateway and not already offline)
                if old_id in self.states:
                    old_node = self.states[old_id]
                    if old_node.role != "Gateway" and old_node.health != "Offline":
                        old_node.role = "Worker"
                # Promote new relay
                if new_id in self.states:
                    self.states[new_id].role = "Relay"
                # Rebuild routing after role change
                self.router.update_graph(self.states)
        
        # ── 7. COMPUTE ACTIVE ROUTE ──────────────────────────────
        # Find route from Gateway to furthest reachable mission node
        self.active_route = self.router.compute_route("UAV-1", "UAV-5")
        if not self.active_route:
            self.active_route = self.router.compute_route("UAV-1", "UAV-4")
        if not self.active_route:
            self.active_route = self.router.compute_route("UAV-1", "UAV-3")
                
        # ── 8. MISSION LAYER ─────────────────────────────────────
        self.scenario.planner.update(self.states)
        
        # ── 9. INTERFERENCE ZONE DECAY ───────────────────────────
        # Interference zones shrink slightly each tick (simulates transient events)
        if self.tick_count % 50 == 0 and self.environment.interference_zones:
            # Remove fully decayed zones
            self.environment.interference_zones = [
                (x, y, z, r * 0.9) for x, y, z, r in self.environment.interference_zones
                if r * 0.9 > 10.0
            ]


# ═══════════════════════════════════════════════════════════════════
# Application Setup
# ═══════════════════════════════════════════════════════════════════

random.seed(RANDOM_SEED)

sim = SimulationState()
sim.init_swarm(5)
c2.set_simulation_ref(sim)


@c2.router.post("/reset")
async def reset_swarm():
    """Fully resets the swarm to its initial formation."""
    random.seed(RANDOM_SEED)
    sim.init_swarm(5)
    return {"status": "success", "message": "Swarm fully reset to initial formation"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop_task = asyncio.create_task(simulation_loop())
    yield
    loop_task.cancel()


app = FastAPI(title="AeroLink Swarm C2", lifespan=lifespan)
app.include_router(c2.router)
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")


@app.get("/")
async def serve_index():
    return RedirectResponse(url="/dashboard/index.html")


@app.get("/api/swarm")
async def get_swarm_state():
    """
    Returns the complete authoritative swarm state for the dashboard.
    All data comes from the single source of truth (sim.states).
    """
    active_nodes = [s for s in sim.states.values() if s.health != "Offline"]
    total_nodes = len(sim.states)
    
    # PDR from mission objective
    pdr = 1.0
    if sim.scenario.planner.objectives:
        pdr = sim.scenario.planner.objectives[0].current_pdr
    
    # Average latency across active nodes
    avg_latency = 0.0
    if active_nodes:
        avg_latency = sum(s.latency for s in active_nodes) / len(active_nodes)
    
    # Aggregate PSD for display (use gateway's PSD or first active node)
    display_psd = [1.2] * 10
    display_baseline = [1.2] * 10
    for nid in ["UAV-1", "UAV-2", "UAV-3"]:
        if nid in sim.current_psd:
            display_psd = sim.current_psd[nid]
            display_baseline = sim.psd_baseline.get(nid, [1.2] * 10)
            break
    
    return {
        "states": {k: v.__dict__ for k, v in sim.states.items()},
        "actions": sim.actions_log,
        "active_route": sim.active_route,
        "current_psd": display_psd,
        "psd_baseline": display_baseline,
        "mission_status": sim.scenario.planner.get_status(),
        "mission_pdr": pdr,
        "avg_latency": avg_latency,
        "active_count": len(active_nodes),
        "total_count": total_nodes,
        "tick": sim.tick_count,
    }


async def simulation_loop():
    """Background task running the autonomous simulation loop."""
    while True:
        try:
            sim.tick()
        except Exception as e:
            import traceback
            print(f"Simulation tick error: {e}")
            traceback.print_exc()
        await asyncio.sleep(0.8)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
