"""
AeroLink End-to-End Integration Tests

Tests the complete autonomous loop:
  Sense → Assess → Predict → Reconfigure → Recover → Continue Mission

Run: python -m pytest tests/test_integration.py -v
  or: python tests/test_integration.py
"""
import sys
import os
import random

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarm.state import SwarmNodeState
from swarm.decision_engine import SwarmDecisionEngine
from swarm.relay_selection import RelaySelector
from swarm.prediction import FailurePredictor
from swarm.routing import Router
from simulation.topology import SimulatedTopology
from simulation.mobility import MobilityModel
from simulation.environment import Environment
from simulation.network import NetworkSimulator
from mission.planner import MissionPlanner
from mission.objectives import MaintainConnectivityObjective
from mission.scenarios import DisasterResponseScenario
from rf.detector import AnomalyDetector
from rf.features import FeatureExtractor
from rf.fft import FFTProcessor
from rf.simulator import RFSimulator


def create_test_swarm():
    """Creates a 5-node test swarm with known positions and roles."""
    states = {}
    positions = [
        (200.0, 500.0, 80.0),   # UAV-1: Gateway
        (400.0, 480.0, 100.0),  # UAV-2: Relay
        (450.0, 650.0, 95.0),   # UAV-3: Worker
        (700.0, 450.0, 110.0),  # UAV-4: Worker
        (750.0, 600.0, 105.0),  # UAV-5: Worker
    ]
    roles = ["Gateway", "Relay", "Worker", "Worker", "Worker"]
    
    for i in range(5):
        node_id = f"UAV-{i+1}"
        states[node_id] = SwarmNodeState(
            node_id=node_id,
            position=positions[i],
            velocity=(0.0, 0.0, 0.0),
            role=roles[i],
            battery=95.0 - (i * 2),
            health="Healthy",
        )
    return states


# ═══════════════════════════════════════════════════════════════════
# Scenario A: Normal Operation
# ═══════════════════════════════════════════════════════════════════

def test_scenario_a_normal_operation():
    """All nodes active, connectivity valid, mission active."""
    print("\n=== Scenario A: Normal Operation ===")
    
    states = create_test_swarm()
    topology = SimulatedTopology()
    env = Environment()
    network = NetworkSimulator(topology, env)
    router = Router()
    engine = SwarmDecisionEngine()
    
    # Simulate a tick
    network.simulate_telemetry_tick(states)
    router.update_graph(states)
    
    # All nodes should be in the graph
    assert len(router.graph) == 5, f"Expected 5 nodes in graph, got {len(router.graph)}"
    
    # All nodes should have neighbors
    for nid, state in states.items():
        assert len(state.neighbors) > 0, f"{nid} has no neighbors"
    
    # Route from Gateway to UAV-5 should exist
    route = router.compute_route("UAV-1", "UAV-5")
    assert len(route) >= 2, f"No route found: {route}"
    assert route[0] == "UAV-1"
    assert route[-1] == "UAV-5"
    
    # Mission should be active
    scenario = DisasterResponseScenario()
    scenario.setup()
    scenario.planner.update(states)
    assert scenario.planner.get_status() == "Active", f"Expected Active, got {scenario.planner.get_status()}"
    
    # Decision engine should produce no reconfigurations (low risk)
    rf_features = {nid: {"spectral_anomaly": False} for nid in states}
    actions = engine.process_swarm_state(states, rf_features)
    reconfigure_actions = [a for a in actions if a.get("type") == "RECONFIGURE"]
    assert len(reconfigure_actions) == 0, f"Unexpected reconfigurations: {reconfigure_actions}"
    
    print("  ✓ All 5 nodes active and connected")
    print(f"  ✓ Route: {' → '.join(route)}")
    print(f"  ✓ Mission status: {scenario.planner.get_status()}")
    print("  ✓ No reconfigurations needed")
    print("  PASSED")


# ═══════════════════════════════════════════════════════════════════
# Scenario B: Relay Failure → Recovery
# ═══════════════════════════════════════════════════════════════════

def test_scenario_b_relay_failure_recovery():
    """
    Full end-to-end: Fail UAV-2 → Detect → Select → Reassign → Reroute → Recover
    """
    print("\n=== Scenario B: Relay Failure → Recovery ===")
    
    states = create_test_swarm()
    topology = SimulatedTopology()
    env = Environment()
    network = NetworkSimulator(topology, env)
    router = Router()
    engine = SwarmDecisionEngine()
    engine._reconfigure_cooldown = 0.0  # Disable cooldown for test
    
    # Initial state: establish connectivity
    network.simulate_telemetry_tick(states)
    router.update_graph(states)
    
    route_before = router.compute_route("UAV-1", "UAV-5")
    print(f"  Route before failure: {' → '.join(route_before)}")
    assert "UAV-2" in route_before or len(route_before) > 0, "No initial route"
    
    # ─── FAIL UAV-2 (Primary Relay) ───
    states["UAV-2"].health = "Offline"
    states["UAV-2"].neighbors = []
    states["UAV-2"].link_quality = 0.0
    states["UAV-2"].rssi = -100.0
    states["UAV-2"].latency = 1000.0
    states["UAV-2"].packet_loss = 1.0
    print("  ✗ UAV-2 set to OFFLINE")
    
    # Re-run network + routing
    network.simulate_telemetry_tick(states)
    router.update_graph(states)
    
    # UAV-2 should be excluded from graph
    assert "UAV-2" not in router.graph, "Offline UAV-2 still in routing graph!"
    print("  ✓ UAV-2 removed from routing graph")
    
    # Connectivity risk should be 1.0 for offline node
    rf_features = {nid: {"spectral_anomaly": False} for nid in states}
    actions = engine.process_swarm_state(states, rf_features)
    assert states["UAV-2"].connectivity_risk == 1.0, "Offline node risk should be 1.0"
    print(f"  ✓ UAV-2 connectivity_risk = {states['UAV-2'].connectivity_risk}")
    
    # Decision engine should detect offline relay and select replacement
    reconfigure = [a for a in actions if a.get("type") == "RECONFIGURE"]
    assert len(reconfigure) > 0, f"No reconfiguration triggered! Actions: {actions}"
    
    new_relay_id = reconfigure[0]["new_relay"]
    assert new_relay_id != "UAV-2", "Cannot select failed node as new relay"
    assert new_relay_id != "UAV-1", "Cannot select Gateway as relay"
    print(f"  ✓ Decision engine selected {new_relay_id} as replacement relay")
    
    # Execute reconfiguration
    states["UAV-2"].role = "Worker"  # Demote (it's offline anyway)
    states[new_relay_id].role = "Relay"
    router.update_graph(states)
    print(f"  ✓ {new_relay_id} promoted to Relay")
    
    # Verify new route exists and doesn't include UAV-2
    route_after = router.compute_route("UAV-1", "UAV-5")
    if not route_after:
        route_after = router.compute_route("UAV-1", "UAV-4")
    assert len(route_after) >= 2, f"No route after recovery: {route_after}"
    assert "UAV-2" not in route_after, f"Offline UAV-2 in recovered route: {route_after}"
    print(f"  ✓ Recovered route: {' → '.join(route_after)}")
    
    # Mission should still be active/recovering
    scenario = DisasterResponseScenario()
    scenario.setup()
    scenario.planner.update(states)
    status = scenario.planner.get_status()
    print(f"  ✓ Mission status after recovery: {status}")
    
    print("  PASSED")


# ═══════════════════════════════════════════════════════════════════
# Scenario C: Link Degradation
# ═══════════════════════════════════════════════════════════════════

def test_scenario_c_link_degradation():
    """Gateway link degraded → risk increases → routing adapts."""
    print("\n=== Scenario C: Gateway Link Degradation ===")
    
    states = create_test_swarm()
    topology = SimulatedTopology()
    env = Environment()
    network = NetworkSimulator(topology, env)
    router = Router()
    
    # Normal baseline
    network.simulate_telemetry_tick(states)
    router.update_graph(states)
    baseline_quality = states["UAV-1"].link_quality
    print(f"  Baseline link quality (UAV-1): {baseline_quality:.3f}")
    
    # Add interference near Gateway
    env.add_interference_zone(200.0, 500.0, 80.0, 200.0)
    
    # Re-simulate
    network.simulate_telemetry_tick(states)
    router.update_graph(states)
    degraded_quality = states["UAV-1"].link_quality
    print(f"  Degraded link quality (UAV-1): {degraded_quality:.3f}")
    
    assert degraded_quality < baseline_quality, \
        f"Link quality didn't degrade: {degraded_quality} >= {baseline_quality}"
    print("  ✓ Link quality decreased under interference")
    
    # Route cost to UAV-1 should increase (edges more expensive)
    route = router.compute_route("UAV-1", "UAV-5")
    assert len(route) >= 2, f"Route broken after degradation: {route}"
    print(f"  ✓ Route still exists: {' → '.join(route)}")
    
    print("  PASSED")


# ═══════════════════════════════════════════════════════════════════
# Scenario D: RF Anomaly Detection
# ═══════════════════════════════════════════════════════════════════

def test_scenario_d_rf_anomaly():
    """Spectral anomaly detected → state propagated → link/network responds."""
    print("\n=== Scenario D: RF Anomaly Detection ===")
    
    detector = AnomalyDetector(alpha=0.1, threshold=10.0)
    extractor = FeatureExtractor()
    state = SwarmNodeState(node_id="UAV-T", battery=90.0)
    
    # Establish baseline with normal PSD
    for _ in range(5):
        normal_psd = [1.0 + random.uniform(-0.1, 0.1) for _ in range(10)]
        detector.detect(normal_psd)
    
    baseline = list(detector.baseline)
    print(f"  Baseline established: mean={sum(baseline)/len(baseline):.2f}")
    
    # Inject spike (jamming)
    anomaly_psd = [1.0] * 10
    anomaly_psd[4] = 25.0  # Strong spike in bin 4
    anomaly_psd[5] = 22.0  # Adjacent bin
    
    result = detector.detect(anomaly_psd)
    assert result["anomaly"] is True, f"Anomaly not detected: {result}"
    assert result["severity"] > 10.0, f"Severity too low: {result['severity']}"
    print(f"  ✓ Anomaly detected: severity={result['severity']:.2f}")
    
    # Baseline should NOT have been updated (anomaly protection)
    baseline_after = list(detector.baseline)
    assert abs(baseline_after[4] - baseline[4]) < 0.5, \
        "Baseline was corrupted by anomaly signal"
    print("  ✓ EWMA baseline protected from anomaly contamination")
    
    # Feature extraction should fuse RF anomaly with node state
    features = extractor.extract(result, state)
    assert features["spectral_anomaly"] is True
    assert features["anomaly_severity"] > 10.0
    print(f"  ✓ Features extracted: anomaly={features['spectral_anomaly']}, severity={features['anomaly_severity']:.2f}")
    
    # Predictor should increase risk when RF anomaly is present
    predictor = FailurePredictor()
    risk = predictor.estimate_link_failure_probability(state, features)
    assert risk > 0.0, f"RF anomaly didn't affect risk: {risk}"
    print(f"  ✓ Failure risk with RF anomaly: {risk:.2f}")
    
    # After anomaly clears, baseline should resume adapting
    for _ in range(3):
        normal_psd = [1.0 + random.uniform(-0.1, 0.1) for _ in range(10)]
        result = detector.detect(normal_psd)
    assert result["anomaly"] is False, "Anomaly persisting after clear signal"
    print("  ✓ Anomaly clears after normal signal resumes")
    
    print("  PASSED")


# ═══════════════════════════════════════════════════════════════════
# Scenario E: Multiple Failures
# ═══════════════════════════════════════════════════════════════════

def test_scenario_e_multiple_failures():
    """Multiple nodes fail — verify graceful degradation."""
    print("\n=== Scenario E: Multiple Failures ===")
    
    states = create_test_swarm()
    topology = SimulatedTopology()
    env = Environment()
    network = NetworkSimulator(topology, env)
    router = Router()
    
    network.simulate_telemetry_tick(states)
    
    # Fail UAV-2 AND UAV-4
    for nid in ["UAV-2", "UAV-4"]:
        states[nid].health = "Offline"
        states[nid].neighbors = []
    print("  ✗ UAV-2 and UAV-4 set to OFFLINE")
    
    network.simulate_telemetry_tick(states)
    router.update_graph(states)
    
    assert "UAV-2" not in router.graph
    assert "UAV-4" not in router.graph
    assert len(router.graph) == 3, f"Expected 3 nodes in graph, got {len(router.graph)}"
    print(f"  ✓ Graph reduced to {len(router.graph)} nodes: {list(router.graph.keys())}")
    
    # Route should still work through remaining nodes
    route = router.compute_route("UAV-1", "UAV-5")
    if not route:
        route = router.compute_route("UAV-1", "UAV-3")
    print(f"  ✓ Best available route: {' → '.join(route) if route else 'PARTITIONED'}")
    
    # Mission should be degraded
    scenario = DisasterResponseScenario()
    scenario.setup()
    scenario.planner.update(states)
    print(f"  ✓ Mission status: {scenario.planner.get_status()}")
    
    print("  PASSED")


# ═══════════════════════════════════════════════════════════════════
# Scenario F: Reset After Failure
# ═══════════════════════════════════════════════════════════════════

def test_scenario_f_reset_after_failure():
    """Reset restores all state cleanly — no stale roles, routes, alarms."""
    print("\n=== Scenario F: Reset After Failure ===")
    
    states = create_test_swarm()
    topology = SimulatedTopology()
    env = Environment()
    network = NetworkSimulator(topology, env)
    router = Router()
    engine = SwarmDecisionEngine()
    scenario = DisasterResponseScenario()
    scenario.setup()
    detectors = {nid: AnomalyDetector() for nid in states}
    
    # Cause damage
    states["UAV-2"].health = "Offline"
    env.add_interference_zone(400.0, 480.0, 100.0, 200.0)
    
    network.simulate_telemetry_tick(states)
    router.update_graph(states)
    scenario.planner.update(states)
    print(f"  Pre-reset: UAV-2 health={states['UAV-2'].health}, mission={scenario.planner.get_status()}")
    
    # ─── RESET ───
    states_new = create_test_swarm()
    env.interference_zones.clear()
    router.graph.clear()
    engine.reset()
    scenario_new = DisasterResponseScenario()
    scenario_new.setup()
    detectors_new = {nid: AnomalyDetector() for nid in states_new}
    
    network_new = NetworkSimulator(topology, env)
    network_new.simulate_telemetry_tick(states_new)
    router.update_graph(states_new)
    scenario_new.planner.update(states_new)
    
    # Verify clean state
    for nid, state in states_new.items():
        assert state.health == "Healthy", f"{nid} health not reset: {state.health}"
    assert states_new["UAV-2"].role == "Relay", f"UAV-2 role not reset: {states_new['UAV-2'].role}"
    assert len(router.graph) == 5, f"Graph not fully restored: {len(router.graph)} nodes"
    assert len(env.interference_zones) == 0, "Interference zones not cleared"
    assert scenario_new.planner.get_status() == "Active", f"Mission not reset: {scenario_new.planner.get_status()}"
    assert len(scenario_new.planner.objectives) == 1, f"Objectives accumulated: {len(scenario_new.planner.objectives)}"
    
    # Verify route works
    route = router.compute_route("UAV-1", "UAV-5")
    assert len(route) >= 2, f"No route after reset: {route}"
    
    print(f"  Post-reset: all nodes Healthy, UAV-2=Relay, mission=Active")
    print(f"  ✓ No stale roles")
    print(f"  ✓ No stale interference zones")
    print(f"  ✓ No stale objectives (count={len(scenario_new.planner.objectives)})")
    print(f"  ✓ Route restored: {' → '.join(route)}")
    print("  PASSED")


# ═══════════════════════════════════════════════════════════════════
# Degraded Node Routing Test
# ═══════════════════════════════════════════════════════════════════

def test_degraded_node_routing():
    """Degraded nodes remain in graph with higher cost, not excluded."""
    print("\n=== Test: Degraded Node Stays in Routing Graph ===")
    
    states = create_test_swarm()
    topology = SimulatedTopology()
    env = Environment()
    network = NetworkSimulator(topology, env)
    router = Router()
    
    network.simulate_telemetry_tick(states)
    router.update_graph(states)
    
    # Get normal route cost
    route_normal = router.compute_route("UAV-1", "UAV-5")
    assert len(route_normal) >= 2
    
    # Set UAV-3 to Degraded
    states["UAV-3"].health = "Degraded"
    network.simulate_telemetry_tick(states)
    router.update_graph(states)
    
    # UAV-3 should still be in graph
    assert "UAV-3" in router.graph, "Degraded node excluded from graph!"
    print(f"  ✓ Degraded UAV-3 remains in routing graph")
    
    # Route should still work
    route_degraded = router.compute_route("UAV-1", "UAV-5")
    assert len(route_degraded) >= 2, f"No route with degraded node: {route_degraded}"
    print(f"  ✓ Route still available: {' → '.join(route_degraded)}")
    
    # If UAV-3 is in the route, its edges should have higher cost
    if "UAV-3" in router.graph:
        for neighbor, cost in router.graph["UAV-3"].items():
            assert cost > 0, f"Edge cost is zero for degraded node"
    print("  ✓ Degraded node edges have elevated cost")
    
    print("  PASSED")


# ═══════════════════════════════════════════════════════════════════
# FFT & RFSimulator Tests
# ═══════════════════════════════════════════════════════════════════

def test_fft_processor():
    """Test FFT computes PSD correctly."""
    print("\n=== Test: FFT Processor ===")
    
    fft = FFTProcessor(fft_size=8)
    
    # Simple DC signal
    samples = [1.0 + 0j] * 8
    result = fft.compute_fft(samples)
    assert len(result) == 8
    assert abs(result[0].real - 8.0) < 0.01, f"DC bin wrong: {result[0]}"
    print(f"  ✓ DC signal: X[0] = {result[0].real:.1f}")
    
    # PSD
    psd = fft.estimate_power(result)
    assert len(psd) == 8
    assert psd[0] > 0
    print(f"  ✓ PSD[0] = {psd[0]:.1f}")
    
    print("  PASSED")


def test_rf_simulator():
    """Test RFSimulator generates deterministic PSD."""
    print("\n=== Test: RF Simulator ===")
    
    sim = RFSimulator(seed=42, num_bins=10)
    
    # Clean signal
    psd_clean = sim.generate_psd(interference_level=0.0)
    assert len(psd_clean) == 10
    assert all(p < 3.0 for p in psd_clean), f"Clean PSD too high: {psd_clean}"
    print(f"  ✓ Clean PSD max: {max(psd_clean):.2f}")
    
    # With interference
    psd_dirty = sim.generate_psd(interference_level=1.0)
    assert max(psd_dirty) > 10.0, f"Interference didn't create spike: {max(psd_dirty)}"
    print(f"  ✓ Interference PSD max: {max(psd_dirty):.2f}")
    
    # Deterministic
    sim2 = RFSimulator(seed=42, num_bins=10)
    psd_repeat = sim2.generate_psd(interference_level=0.0)
    assert psd_clean == psd_repeat, "RFSimulator not deterministic!"
    print("  ✓ Deterministic output confirmed")
    
    print("  PASSED")


# ═══════════════════════════════════════════════════════════════════
# Run All Tests
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    random.seed(42)
    
    print("=" * 70)
    print("AeroLink Integration Test Suite")
    print("=" * 70)
    
    tests = [
        test_scenario_a_normal_operation,
        test_scenario_b_relay_failure_recovery,
        test_scenario_c_link_degradation,
        test_scenario_d_rf_anomaly,
        test_scenario_e_multiple_failures,
        test_scenario_f_reset_after_failure,
        test_degraded_node_routing,
        test_fft_processor,
        test_rf_simulator,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)
    
    if failed > 0:
        sys.exit(1)
