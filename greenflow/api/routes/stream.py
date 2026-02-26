"""
GreenFlow AI – Streaming Route (SSE + WebSocket)
==================================================
Provides real-time updates to the frontend via:
  - Server-Sent Events (SSE)  → GET /stream/events
  - WebSocket                 → WS  /stream/ws

The SSE endpoint reads enriched JSONL records written by the Pathway pipeline
and pushes them to listening clients in real time.
"""

from __future__ import annotations

import json
import asyncio
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from loguru import logger

from config import settings

router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Connection Manager (WebSocket)
# ─────────────────────────────────────────────────────────────────────────────

class ConnectionManager:
    """Tracks active WebSocket connections and broadcasts messages."""

    def __init__(self) -> None:
        self._active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._active.append(ws)
        logger.info("🔌 WebSocket connected | total={}", len(self._active))

    def disconnect(self, ws: WebSocket) -> None:
        self._active.remove(ws)
        logger.info("🔌 WebSocket disconnected | total={}", len(self._active))

    async def broadcast(self, data: str) -> None:
        """Send *data* string to every connected client."""
        dead: list[WebSocket] = []
        for ws in self._active:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._active.remove(ws)


manager = ConnectionManager()


# ─────────────────────────────────────────────────────────────────────────────
# SSE helper
# ─────────────────────────────────────────────────────────────────────────────

async def _sse_generator():
    """
    Async generator that polls the database for the latest AnalyticsRecord
    and yields SSE frames. This replaces the JSONL tailing for the demo.
    """
    from database.session import AsyncSessionFactory, AnalyticsRecord
    from sqlalchemy import select, desc
    
    last_id = -1
    
    while True:
        try:
            async with AsyncSessionFactory() as session:
                # Fetch latest record
                stmt = select(AnalyticsRecord).order_by(desc(AnalyticsRecord.id)).limit(1)
                result = await session.execute(stmt)
                record = result.scalars().first()
                
                if record and record.id > last_id:
                    last_id = record.id
                    
                    # Map database record to frontend expects
                    # Frontend expects: {source, timestamp, carbon_score, co2_ppm, temperature_c, ...}
                    data = {
                        "source": "simulated_worker",
                        "timestamp": record.timestamp,
                        "carbon_score": round((record.risk_score or 0) / 100.0, 3) if record.risk_score else 0.5,
                        "co2_ppm": record.aqi or 400.0, # AQI used as proxy for CO2 in basic simulation
                        "temperature_c": record.temp or 25.0,
                        "aqi": record.aqi,
                        "risk_score": record.risk_score,
                        "safety_level": record.safety_level,
                        "city": record.city or "New Delhi"
                    }
                    yield f"data: {json.dumps(data)}\n\n"
            
        except Exception as e:
            logger.error(f"SSE Generator Error: {e}")
            
        await asyncio.sleep(2.0)


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/events", summary="Server-Sent Events feed")
async def sse_events():
    """
    Subscribe to real-time green-data events via SSE.
    Connect with: ``EventSource('/api/v1/stream/events')``
    """
    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",    # disable Nginx buffering
        },
    )


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    WebSocket endpoint for bidirectional real-time communication.
    Clients can send queries; the server echoes enriched responses.
    """
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            logger.debug("📨 WS message: {}", data[:200])
            # Echo back with a confirmation wrapper
            reply = json.dumps({"echo": data, "status": "received"})
            await ws.send_text(reply)
    except WebSocketDisconnect:
        manager.disconnect(ws)
