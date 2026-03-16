import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Annotated, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlmodel import Session, select

from database import get_mode, get_session, init_db, set_mode, get_pump, set_pump
from daq import SamplerThread, DatabaseThread, buffers
from models import Measurement, Mode, PumpState

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application lifespan — starts/stops the DAQ thread alongside FastAPI
# ---------------------------------------------------------------------------

_sampler_thread: SamplerThread | None = None
_database_thread: DatabaseThread | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _sampler_thread, _database_thread
    init_db()
    _sampler_thread = SamplerThread(interval=0.1)
    _database_thread = DatabaseThread(interval=1.0)
    _sampler_thread.start()
    _database_thread.start()
    logger.info("DAQ threads launched")
    yield
    if _sampler_thread:
        _sampler_thread.stop()
        _sampler_thread.join(timeout=5)
    if _database_thread:
        _database_thread.stop()
        _database_thread.join(timeout=5)
    logger.info("DAQ threads shut down")


app = FastAPI(title="DAQ & Control", lifespan=lifespan)

# Convenience type alias for injected sessions
DbSession = Annotated[Session, Depends(get_session)]

# ---------------------------------------------------------------------------
# Mode endpoints
# ---------------------------------------------------------------------------

@app.get("/mode", summary="Get current operating mode")
def read_mode(session: DbSession) -> dict:
    return {"mode": get_mode(session).value}


@app.post("/mode/{new_mode}", summary="Change operating mode")
def change_mode(new_mode: Mode, session: DbSession) -> dict:
    set_mode(session, new_mode)
    logger.info("Mode changed to %s", new_mode.value)
    return {"mode": new_mode.value}

# ---------------------------------------------------------------------------
# Pump endpoints
# ---------------------------------------------------------------------------

@app.get("/pump", summary="Get current pump state")
def read_pump(session: DbSession) -> dict:
    return {"pump": get_pump(session).value}


@app.post("/pump/{new_state}", summary="Change pump state")
def change_pump(new_state: PumpState, session: DbSession) -> dict:
    set_pump(session, new_state)
    logger.info("Pump state changed to %s", new_state.value)
    return {"pump": new_state.value}

# ---------------------------------------------------------------------------
# Measurement endpoints
# ---------------------------------------------------------------------------

@app.get("/measurements", summary="Fetch recent measurements")
def get_measurements(
    session: DbSession,
    limit: int = 100,
) -> list[Measurement]:
    return list(
        session.exec(
            select(Measurement).order_by(Measurement.id.desc()).limit(limit)
        ).all()
    )


@app.get("/measurements/latest", summary="Fetch most recent single measurement")
def get_latest(session: DbSession) -> Measurement:
    row = session.exec(
        select(Measurement).order_by(Measurement.id.desc()).limit(1)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="No measurements recorded yet")
    return row


# ---------------------------------------------------------------------------
# Server-Sent Events stream
# ---------------------------------------------------------------------------

@app.get("/stream", summary="Live measurement stream via SSE")
async def stream(session: DbSession) -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        last_id: int | None = None
        while True:
            # Use a fresh session per poll to avoid stale reads
            with Session(session.bind) as s:
                row = s.exec(
                    select(Measurement).order_by(Measurement.id.desc()).limit(1)
                ).first()

            if row and row.id != last_id:
                last_id = row.id
                payload = {
                    "id": row.id,
                    "timestamp": row.timestamp.isoformat(),
                    "ch1": row.ch1,
                    "ch2": row.ch2,
                    "ch3": row.ch3,
                    "pressure": row.pressure,
                    "out1": row.out1,
                    "out2": row.out2,
                    "mode": row.mode.value,
                    "pump": row.pump.value,
                }
                yield f"data: {json.dumps(payload)}\n\n"

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disables buffering in nginx proxies
        },
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, summary="Live dashboard")
def dashboard() -> str:
    with open("templates/index.html") as f:
        return f.read()
    
@app.get("/buffer")
def get_buffer() -> dict[str, list[float]]:
    return {
        "ch1": list(buffers[0]),
        "ch2": list(buffers[1]),
        "ch3": list(buffers[2])
        }
    
@app.get("/buffer/stats")
def get_buffer_stats() -> dict:
    result = {}
    for i, (ch, buf) in enumerate(zip(["ch1", "ch2", "ch3"], buffers)):
        samples = list(buf)
        if len(samples) < 2:
            result[ch] = None
            continue
        
        edges = np.arange(min(samples), max(samples), 0.001)
        
        counts, bin_edges = np.histogram(samples, bins=edges)
        result[ch] = {
            "mean":   round(np.mean(samples), 5),
            "std":    round(np.std(samples), 5),
            "min":    round(min(samples), 5),
            "max":    round(max(samples), 5),
            "counts": counts.tolist(),
            "edges":  bin_edges.tolist(),
        }
    return result