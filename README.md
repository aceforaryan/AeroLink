# AeroLink

Resilient Autonomous Swarm Intelligence & Communication Layer

AeroLink is a software-defined swarm intelligence and communication layer that turns individual UAVs into a fault-tolerant, dynamically reconfigurable network. This project implements the core autonomy sequence for drone swarms, focusing on resilience under communication degradation and node failure.

## Architecture

The system consists of five closed-loop layers:
- **UAV / Digital Twin**: Mobility, position, battery, node failures and link model.
- **RF + Telemetry**: RSSI, latency, packet loss, I/Q acquisition, PSD, anomaly state.
- **Resilient Network**: Neighbor graph, path selection, rerouting and recovery.
- **Swarm Intelligence**: Role assignment, relay selection, failure prediction and adaptation.
- **Mission / C2**: Map, mission state, alerts, logs, metrics and operator controls.

## Components

- `backend/`: API, telemetry aggregation, and Command & Control (C2) bridge.
- `rf/`: Deterministic spectral analysis, failure simulation, and RF feature extraction.
- `simulation/`: Digital twin environment containing node behavior and topology models.
- `swarm/`: Dynamic role assignments and predictive routing intelligence.
- `dashboard/`: Operator interface for live metrics and autonomous event feed.

## Setup
(More details to come as development progresses)
