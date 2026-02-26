"""
GreenFlow AI – Enhanced Health Check Endpoints
================================================
Provides liveness, readiness, and deep-health checks that a load balancer,
Kubernetes probe, or uptime monitor can use.

  GET /api/v1/health           → simple liveness (fast, no DB)
  GET /api/v1/health/ready     → readiness (checks DB, disk)
  GET /api/v1/health/deep      → deep-health (DB, disk, model, memory)
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import psutil
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from loguru import logger

from config import settings

router = APIRouter()

# Process start for uptime
_START = time.time()


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:      str
    service:     str
    environment: str
    timestamp:   str
    version:     str = "2.0.0"
    uptime_s:    float = 0.0


class ComponentHealth(BaseModel):
    name:    str
    status:  str   # ok | degraded | failed
    detail:  str = ""
    latency_ms: float = 0.0


class DeepHealthResponse(BaseModel):
    overall:    str
    components: list[ComponentHealth]
    uptime_s:   float
    timestamp:  str


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _check_db() -> ComponentHealth:
    """Ping the database and measure round-trip latency."""
    t0 = time.perf_counter()
    try:
        from database.session import AsyncSessionFactory
        async with AsyncSessionFactory() as sess:
            await sess.execute(text("SELECT 1"))
        latency = (time.perf_counter() - t0) * 1000
        return ComponentHealth( # type: ignore
            name="database", status="ok",
            detail="SQLAlchemy async session OK",
            latency_ms=round(float(latency), 2), # type: ignore
        )
    except Exception as exc:
        return ComponentHealth(
            name="database", status="failed",
            detail=str(exc)[:200],
        )


def _check_disk() -> ComponentHealth:
    """Warn if disk is more than 85% full."""
    usage = psutil.disk_usage("/")
    pct   = usage.percent
    ok    = pct < 85
    return ComponentHealth(
        name    = "disk",
        status  = "ok" if ok else "degraded",
        detail  = f"{usage.free // (1024**3)} GB free ({pct:.1f}% used)",
    )


def _check_memory() -> ComponentHealth:
    """Warn if process memory > 1.5 GB."""
    proc = psutil.Process(os.getpid())
    mb   = proc.memory_info().rss / 1024 / 1024
    ok   = mb < 1500
    return ComponentHealth(
        name   = "memory",
        status = "ok" if ok else "degraded",
        detail = f"Process RSS: {mb:.0f} MB",
    )


def _check_anomaly_engine() -> ComponentHealth:
    """Verify the anomaly detector singleton is responsive."""
    try:
        from features.anomaly_detector import anomaly_detector
        stats = anomaly_detector.get_window_stats()
        return ComponentHealth(
            name   = "anomaly_detector",
            status = "ok",
            detail = f"Tracking {len(stats)} sensors",
        )
    except Exception as exc:
        return ComponentHealth(
            name="anomaly_detector", status="failed", detail=str(exc)[:200]
        )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=HealthResponse, summary="Liveness probe")
async def health_check() -> HealthResponse:
    """
    Ultra-fast liveness check — no DB, no I/O.
    Returns 200 as long as the process is alive.
    """
    return HealthResponse( # type: ignore
        status      = "healthy",
        service     = str(settings.app_name),
        environment = str(settings.app_env),
        timestamp   = datetime.now(timezone.utc).isoformat(),
        uptime_s    = round(time.time() - _START, 1), # type: ignore
    )


@router.get("/ready", summary="Readiness probe")
async def readiness_check() -> JSONResponse:
    """
    Readiness: check DB and disk before accepting traffic.
    Returns 503 if any critical component fails.
    """
    db_health   = await _check_db()
    disk_health = _check_disk()

    ready = (db_health.status == "ok" and disk_health.status != "failed")
    code  = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code = code,
        content = {
            "ready":      ready,
            "database":   db_health.model_dump(),
            "disk":       disk_health.model_dump(),
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get("/deep", response_model=DeepHealthResponse, summary="Deep health diagnostic")
async def deep_health_check() -> DeepHealthResponse:
    """
    Full diagnostic: DB, disk, memory, anomaly engine.
    Intended for monitoring dashboards — NOT for frequent polling.
    """
    components = [
        await _check_db(),
        _check_disk(),
        _check_memory(),
        _check_anomaly_engine(),
    ]

    failed   = [c for c in components if c.status == "failed"]
    degraded = [c for c in components if c.status == "degraded"]
    overall  = "healthy" if not failed and not degraded else \
               "degraded" if not failed else "critical"

    if failed:
        logger.error("Deep health: {} component(s) FAILED: {}",
                     len(failed), [c.name for c in failed])

    return DeepHealthResponse( # type: ignore
        overall    = overall,
        components = components,
        uptime_s   = round(time.time() - _START, 1), # type: ignore
        timestamp  = datetime.now(timezone.utc).isoformat(),
    )
