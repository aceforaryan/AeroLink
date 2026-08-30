from fastapi import FastAPI, HTTPException
from .models import TelemetryPayload
from .telemetry import TelemetryProcessor

app = FastAPI(
    title="AeroLink C2 API",
    description="Command & Control interface and telemetry aggregation for AeroLink Swarm",
    version="0.1.0"
)

processor = TelemetryProcessor()

@app.post("/api/telemetry")
async def receive_telemetry(payload: TelemetryPayload):
    """
    Endpoint for swarm nodes to report their current state.
    """
    success = processor.process_telemetry(payload)
    if not success:
        raise HTTPException(status_code=400, detail="Telemetry processing failed")
    return {"status": "success", "node_id": payload.node_id}

@app.get("/api/swarm")
async def get_swarm_status():
    """
    Endpoint for the C2 Dashboard to fetch the latest aggregate swarm state.
    """
    return processor.get_swarm_state()
