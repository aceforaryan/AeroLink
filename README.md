# AeroLink: Autonomous Self-Healing Swarm Resilience Layer

[![Architecture](https://img.shields.io/badge/Architecture-5--Layer%20Swarm%20Intelligence-blue.svg)]()
[![Status](https://img.shields.io/badge/Status-Digital%20Twin%20Active-success.svg)]()
[![Demo](https://img.shields.io/badge/Mission-Disaster%20Response%20Comm-orange.svg)]()
[![Tests](https://img.shields.io/badge/Tests-9%2F9%20Passing-brightgreen.svg)]()

> **Core Engineering Problem:**  
> *How can an autonomous drone swarm maintain mission connectivity and coordination when its communication topology is continuously changing or individual UAVs become unavailable?*

AeroLink is a software-defined resilience and autonomy layer for autonomous UAV swarms. Rather than functioning as a passive RF monitor or generic communications payload, AeroLink transforms individual drones into cooperative, dynamically reconfigurable network nodes that protect mission capability against physical attrition, link degradation, and spectral anomalies.

The central operating principle:
> **A swarm must not lose mission capability merely because one UAV, one relay, or one communication path fails.**

---

## 🔄 Autonomous Closed-Loop Architecture

AeroLink executes a continuous, deterministic control cycle:

```
 Sense ──▶ Assess ──▶ Predict ──▶ Reconfigure ──▶ Recover ──▶ Continue Mission
```

1. **Sense:** Continuously ingests node mobility, battery state, packet loss, RSSI, latency, and per-node spectral deviations.
2. **Assess:** Maintains dynamic mesh topology $G=(V, E)$ and computes pairwise communication health metrics.
3. **Predict:** Quantifies impending failure risk $P(\text{failure within } T)$ via deterministic heuristic scoring. Detects hard failures (Offline nodes) immediately.
4. **Reconfigure:** Evaluates multi-factor relay candidate scores and selects optimal role transitions. Includes hysteresis cooldown to prevent oscillation.
5. **Recover:** Reconstructs routing tables autonomously via Dijkstra-based dynamic path discovery. Degraded nodes remain routable with elevated cost; only Offline nodes are excluded.
6. **Continue Mission:** Ensures high-level objectives (e.g. disaster-zone communication coverage with PDR > 90%) persist without operator intervention.

---

## 🏛️ System Hierarchy

AeroLink enforces strict separation of concerns across 5 modular layers:

```
┌─────────────────────────────────────────────────────────┐
│                     MISSION / C2                        │
│  Mission State Machine • Alerts • Metrics • C2 Controls │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│                  SWARM INTELLIGENCE                     │
│ Dynamic Roles • Failure Prediction • Relay Scoring      │
│ Reconfiguration Cooldown • Offline/Degraded Detection   │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│                   RESILIENT NETWORK                     │
│ Dynamic Mesh Graph G=(V,E) • Pairwise Edge Weights      │
│ Dijkstra Routing • Degraded-Node Cost Penalty           │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│              RF / TELEMETRY INTELLIGENCE                │
│  Per-Node EWMA Spectral Baseline • PSD • Anomaly Detection│
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│                   UAV / DIGITAL TWIN                    │
│ Mobility Physics • Battery Discharge • Interference Zones│
│ Single Authoritative State Store                         │
└─────────────────────────────────────────────────────────┘
```

> **Single Source of Truth:** All layers read from and write to one authoritative state store (`SimulationState.states`). The topology and network layers do not maintain independent copies of node state.

> **Flight/Mission Domain Decoupling:** Flight control (autopilot stabilization, navigation, geofencing) remains segregated from AeroLink's network autonomy stack, preventing high-level communication reconfigurations from affecting low-level flight safety loops.

---

## 🧮 Mathematical Formulations & Decision Engines

### 1. Deterministic RF Anomaly Detection
To ensure explainability without unnecessary black-box compute overhead, spectral analysis uses an Exponentially Weighted Moving Average (EWMA) baseline:

- **Power Spectral Density (PSD):**
  $$X[k] = \text{FFT}\{x[n]\}, \quad P[k] = |X[k]|^2$$
- **EWMA Spectral Baseline (slow-adapting, α = 0.1):**
  $$B[k] = (1 - \alpha) B[k-1] + \alpha P[k]$$
  With α = 0.1, the baseline retains 90% of history and adapts slowly. Sudden spectral spikes stand out as deviations rather than being absorbed into the baseline.
- **Spectral Deviation:**
  $$D[k] = P[k] - B[k]$$

When $D[k] > \text{Threshold}$, an anomaly is flagged. The baseline is **not updated during anomalies** to prevent contamination by jamming signals.

Each node has its own EWMA detector with PSD generated from that node's local RF environment (interference proximity, distance from interference zones).

### 2. Predictive Link Failure
Rather than reacting after a communication path breaks, AeroLink predicts degradation using a deterministic heuristic risk estimator:
$$P(\text{failure within } T) = f(\text{RSSI}, \text{packet loss}, \text{latency}, \text{battery}, D[k])$$

The predictor assigns additive risk contributions from each factor (e.g. battery < 10% → +0.8, spectral anomaly → +0.3, high packet loss → +0.4). The result is clamped to [0.0, 1.0].

Two failure modes are distinguished:
- **Hard failure:** Node health = Offline → connectivity_risk = 1.0, immediate relay replacement
- **Soft degradation:** Predicted risk > threshold → proactive replacement with cooldown

### 3. Dynamic Candidate Relay Scoring
When a relay node fails or is predicted to degrade, candidate replacement nodes $j$ are scored deterministically:
$$S_j = w_1 Q_j + w_2 B_j + w_3 P_j + w_4 R_j$$

| Factor | Description | Weight |
|---|---|---|
| $Q_j$ | Communication / Link Quality | $w_1$ |
| $B_j$ | Battery Availability (normalized to 0–1) | $w_2$ |
| $P_j$ | Positional Suitability (RSSI proxy) | $w_3$ |
| $R_j$ | Historical Reliability (1 − packet_loss) | $w_4$ |

**Candidate filtering:** Gateway nodes, Offline nodes, and Degraded nodes are excluded from candidacy.

### 4. Swarm Global Objective Function
The swarm evaluates its overarching configuration fitness by balancing quality, energy, and stability:
$$J = w_1 C - w_2 L + w_3 B - w_4 E - w_5 R$$
*(where $C$ = connectivity, $L$ = latency, $B$ = battery, $E$ = energy cost, $R$ = route instability penalty)*.

### 5. Pairwise Edge Weights
Routing edge weights use the **worst-of-two-endpoints** for each link metric:

$$\text{cost}(A, B) = \frac{1}{\max(0.01,\; \min(Q_A, Q_B))} + \frac{\max(L_A, L_B)}{100} + 5 \cdot \max(\ell_A, \ell_B)$$

Degraded nodes receive a 3× cost multiplier on their edges, ensuring the routing algorithm penalizes but does not exclude them.

---

## 📦 Repository Structure

```
DroneTech/
├── backend/                  # C2 API & Telemetry Models
│   ├── c2.py                # Deterministic failure injection endpoints
│   ├── models.py            # Pydantic schema for SwarmNodeState payloads
│   └── telemetry.py         # Telemetry aggregation pipeline
│
├── rf/                       # Deterministic RF Subsystem
│   ├── detector.py          # EWMA baseline & anomaly deviation detector
│   ├── features.py          # Fuses RF anomalies with node telemetry
│   ├── fft.py               # DFT implementation & PSD estimation
│   └── simulator.py         # Deterministic RF environment PSD generator
│
├── simulation/               # Digital Twin Simulation Stack
│   ├── environment.py       # Interference zones & propagation impediments
│   ├── mobility.py          # 3D kinematic mobility & drift models
│   ├── network.py           # Packet delivery, latency, loss & battery simulation
│   └── topology.py          # Distance-based link metrics & neighbor model
│
├── swarm/                    # Swarm Autonomy & Resilience Layer
│   ├── decision_engine.py   # Autonomous Sense-Assess-Predict-Reconfigure loop
│   ├── prediction.py        # Deterministic failure risk probability estimator
│   ├── relay_selection.py   # Multi-variable candidate scoring algorithm
│   ├── roles.py             # Dynamic role state definitions
│   ├── routing.py           # Dynamic graph G=(V,E) & Dijkstra rerouting
│   └── state.py             # Unified SwarmNodeState dataclass
│
├── mission/                  # Mission Objective Layer
│   ├── objectives.py        # PDR & connectivity maintenance objectives
│   ├── planner.py           # Mission state machine (Active/Degraded/Recovering)
│   └── scenarios.py         # Disaster-response swarm scenario setup
│
├── dashboard/                # Real-Time C2 Operator Interface
│   ├── app.js               # Reactive polling, dynamic graph rendering & C2 actions
│   ├── index.html           # Tactical layout: Topology, Health, RF, Decision Feed
│   └── style.css            # Dark glassmorphism design system
│
├── tests/                    # Integration & Scenario Test Suite
│   └── test_integration.py  # 9 end-to-end tests covering all failure scenarios
│
├── main.py                   # Integrated Digital Twin simulation loop & FastAPI server
└── README.md
```

---

## 🧪 Testing & Verified Scenarios

Run the integration test suite:
```bash
python tests/test_integration.py
```

| Scenario | Test | Verified |
|---|---|---|
| **A: Normal Operation** | All 5 nodes active, route exists, mission Active | ✅ |
| **B: Relay Failure → Recovery** | Fail UAV-2 → detect → select alternative → promote → reroute → mission continues | ✅ |
| **C: Gateway Link Degradation** | Interference → quality drops → routing adapts | ✅ |
| **D: RF Anomaly Detection** | Spectral spike → EWMA detects → baseline protected → clears after normal signal | ✅ |
| **E: Multiple Failures** | 2 nodes offline → graph reduced → best available route found | ✅ |
| **F: Reset After Failure** | Full reset → no stale roles, routes, objectives, interference, or baselines | ✅ |
| **Degraded Routing** | Degraded node stays in graph with elevated cost | ✅ |
| **FFT Processor** | DFT + PSD computation correct | ✅ |
| **RF Simulator** | Deterministic PSD generation, interference spikes, repeatable output | ✅ |

**End-to-end verified flow:**
```
Fail UAV-2 (Relay)
  → UAV-2 removed from routing graph (connectivity_risk = 1.0)
  → Decision engine selects UAV-4 as replacement (multi-factor score)
  → UAV-4 promoted to Relay
  → Route recomputed: UAV-1 → UAV-3 → UAV-5
  → Mission status: Active (PDR > 90%)
```

---

## 🎯 Validation & Target Benchmarks

| Metric | Baseline (Static/Ad-hoc) | AeroLink Target | Status |
|---|---|---|---|
| **Packet Delivery Ratio (PDR)** | Drops < 50% on failure | $> 90\%$ | Verified |
| **Route Recovery Time** | > 10.0 s (or timeout) | $< 2.0\text{--}3.0\text{ s}$ | Target |
| **RF Anomaly Detection** | N/A (unmonitored) | $< 1.0\text{ s}$ | Verified |
| **Node Failure Recovery** | Network partitioned | $< 3.0\text{ s}$ | Verified |
| **C2 Telemetry Latency** | Variable | $< 250\text{ ms}$ | Target |
| **Mission Continuation Rate** | Degrades to 0% | $> 90\%$ | Verified |

---

## 🔬 Key Architecture Decisions

### Node Health Model
| State | Routing | Relay Candidate | Description |
|---|---|---|---|
| **Healthy** | Full participation | Yes | Normal operation |
| **Degraded** | Included with 3× cost | No | Battery depleted or link marginal |
| **Offline** | Excluded entirely | No | Hard failure — no routes through node |

### Mission State Machine
```
Not Started → Active ⇄ Degraded → Recovering → Active
```
- **Active:** All objectives satisfied (PDR ≥ 90%)
- **Degraded:** One or more objectives not met
- **Recovering:** Was degraded, objectives now being restored

### Reconfiguration Cooldown
To prevent role oscillation, the decision engine enforces a **3-second cooldown** between reconfigurations. Only one reconfiguration is executed per simulation tick.

### Deterministic Reproducibility
The simulation uses `random.seed(42)` for deterministic behavior during competition demos. Reset restores the seed.

---

## 🚀 Quickstart & Demonstration

### 1. Requirements
- Python 3.9+
- `fastapi`
- `uvicorn`

### 2. Setup (Virtual Environment Recommended)
```bash
python -m venv .venv
source .venv/bin/activate        # bash/zsh
# source .venv/bin/activate.fish  # fish shell
pip install fastapi uvicorn
```

### 3. Run the Digital Twin
Launch the integrated simulation loop and backend server:
```bash
python main.py
```

### 4. Access C2 Dashboard
Open your browser to:
```
http://localhost:8000
```
(Automatically redirects to the tactical dashboard)

### 5. Run Tests
```bash
python tests/test_integration.py
```

### 6. Interactive Failure Injection for Judging
Use the dashboard control panel or issue API commands directly:

| Control | Endpoint | Effect |
|---|---|---|
| **Inject Node Failure** | `POST /api/c2/fail_node` | Takes UAV-2 (Relay) offline. Triggers immediate topology rebuild, relay replacement, and route recomputation. |
| **Degrade Link** | `POST /api/c2/degrade_link` | Places RF interference zone near a node. Gradually degrades link quality, triggers predictive rerouting. |
| **RF Anomaly** | `POST /api/c2/degrade_link` (severity=2.0) | High-severity interference spike. Demonstrates EWMA spectral anomaly detection and baseline protection. |
| **Reset Swarm** | `POST /api/c2/reset` | Fully resets all state: nodes, roles, topology, routes, RF baselines, interference, mission, objectives, tick counter. |

**Expected demo sequence:**
1. Observe normal swarm operation (5 nodes, healthy mesh, active route)
2. Press **Inject Node Failure** — watch the event feed:
   - `[PREDICT]` Relay UAV-2 is OFFLINE
   - `[SELECT]` UAV-4 selected as alternative relay (score: X.XX)
   - `[ROLE]` UAV-2 demoted → UAV-4 promoted to RELAY
   - `[ROUTE]` Dynamic mesh route recomputation triggered
3. Mesh topology and route update on the tactical display
4. Mission status remains **ACTIVE** with PDR > 90%
5. Press **Reset** to restore nominal formation

---

## 📡 API Reference

| Method | Endpoint | Body | Description |
|---|---|---|---|
| `GET` | `/api/swarm` | — | Full swarm state snapshot (all nodes, route, PSD, mission, metrics) |
| `POST` | `/api/c2/fail_node` | `{"node_id": "UAV-2"}` | Inject hard node failure |
| `POST` | `/api/c2/degrade_link` | `{"node_id": "UAV-1", "severity": 1.5}` | Place interference zone near node |
| `POST` | `/api/c2/reset` | — | Full system reset to initial formation |

### `/api/swarm` Response Schema
```json
{
  "states": { "UAV-1": { "node_id": "...", "position": [...], "battery": 95.0, "role": "Gateway", "health": "Healthy", ... } },
  "actions": [ { "type": "RECONFIGURE", "old_relay": "UAV-2", "new_relay": "UAV-4" } ],
  "active_route": ["UAV-1", "UAV-3", "UAV-5"],
  "current_psd": [1.2, 1.1, ...],
  "psd_baseline": [1.2, 1.2, ...],
  "mission_status": "Active",
  "mission_pdr": 0.92,
  "avg_latency": 24.5,
  "active_count": 5,
  "total_count": 5,
  "tick": 42
}
```
