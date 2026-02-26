"""
GreenFlow AI – Events Route
==============================
Accepts incoming green-data events via REST (POST) and
exposes a sink endpoint for the Pathway pipeline to push
enriched results.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import GreenEvent, get_db
from features.extractor import build_features
from ingestion.ingestor import ingest_webhook_payload

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class EventPayload(BaseModel):
    """Shape of a single incoming event."""

    source: str = Field(..., example="sensor_42", description="Event origin identifier")
    text: str | None = Field(None, description="Free-text description or reading")
    co2_ppm: float | None = Field(None, description="CO₂ concentration in ppm")
    temperature_c: float | None = Field(None, description="Temperature in Celsius")
    humidity_pct: float | None = Field(None, description="Relative humidity 0-100")
    energy_kwh: float | None = Field(None, description="Energy consumption in kWh")
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventResponse(BaseModel):
    event_id: str
    message: str
    carbon_score: float | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Background task: persist enriched event to DB
# ─────────────────────────────────────────────────────────────────────────────

async def _persist_event(features: dict, db: AsyncSession) -> None:
    event_id = str(features.get("id", uuid.uuid4()))
    row = GreenEvent(
        event_id=event_id,
        source=str(features.get("source", "unknown")),
        source_type=features.get("source_type"),
        raw_text=features.get("raw_text"),
        carbon_score=features.get("carbon_score"),
    )
    db.add(row)
    await db.commit()
    logger.info("💾 Event persisted | id={}", event_id)


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=EventResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a green-data event",
)
async def create_event(
    payload: EventPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    """
    Accept a single green-data event, run feature extraction, and
    asynchronously persist it to the database.
    """
    raw = ingest_webhook_payload(payload.model_dump())
    features = build_features(raw)

    background_tasks.add_task(_persist_event, features, db)

    # Use dict to avoid potential linter confusion with keyword args on Pydantic models
    response_data = {
        "event_id": str(features.get("id", "unknown")),
        "message": "Event accepted for processing",
        "carbon_score": features.get("carbon_score"),
    }
    return EventResponse(**response_data)


@router.post(
    "/events/sink",
    status_code=status.HTTP_200_OK,
    summary="Pathway pipeline sink (internal)",
    include_in_schema=False,   # hide from public docs
)
async def pipeline_sink(payload: dict[str, Any]) -> dict:
    """
    Internal endpoint – receives enriched rows pushed by the Pathway pipeline.
    Extend to write to a WebSocket broadcast, Kafka topic, etc.
    """
    logger.debug("📬 Pipeline sink received: {}", payload)
    return {"received": True}


@router.get("/", summary="List recent events")
async def list_events(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return the most recent events stored in the database."""
    from sqlalchemy import select, desc

    result = await db.execute(
        select(GreenEvent)
        .order_by(desc(GreenEvent.created_at))
        .offset(offset)
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "event_id": r.event_id,
            "source": r.source,
            "source_type": r.source_type,
            "raw_text": (r.raw_text or "")[:200],
            "carbon_score": r.carbon_score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
