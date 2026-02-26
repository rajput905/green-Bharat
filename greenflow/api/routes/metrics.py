"""
GreenFlow AI – System Metrics Endpoint
========================================
Exposes a real-time JSON snapshot of operational KPIs.
Feeds Prometheus, Grafana (via JSON source), or your custom dashboard.

GET /api/v1/metrics        → full JSON metrics object
GET /api/v1/metrics/live   → lightweight subset for polling dashboards
"""

from __future__ import annotations

import os
import time
import platform
import psutil
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func, select
from loguru import logger

from database.session import get_db, GreenEvent, QueryLog, AnalyticsRecord
from features.anomaly_detector import anomaly_detector
from features.alert_engine import alert_engine

router = APIRouter()

# ── Process start time for uptime calculation ────────────────────────────────
_START_TIME = time.time()

# ── Rolling request counter (updated by middleware) ──────────────────────────
_REQUEST_STATS: dict = {
    "total":    0,
    "per_route": {},
    "errors":   0,
    "last_reset": time.time(),
}

def increment_requests(route: str, is_error: bool = False) -> None:
    _REQUEST_STATS["total"] += 1
    _REQUEST_STATS["per_route"][route] = _REQUEST_STATS["per_route"].get(route, 0) + 1
    if is_error:
        _REQUEST_STATS["errors"] += 1


# ─────────────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────────────

class SystemInfo(BaseModel):
    hostname:    str
    platform:    str
    python:      str
    cpu_count:   int

class ProcessMetrics(BaseModel):
    uptime_seconds:  float
    cpu_percent:     float
    memory_mb:       float
    memory_percent:  float
    open_files:      Optional[int] = None
    threads:         int

class DiskMetrics(BaseModel):
    total_gb:  float
    used_gb:   float
    free_gb:   float
    percent:   float

class DatabaseMetrics(BaseModel):
    total_events:       int
    total_queries:      int
    total_analytics:    int
    db_reachable:       bool

class RequestMetrics(BaseModel):
    total_requests:   int
    error_count:      int
    uptime_seconds:   float
    requests_per_min: float

class FullMetrics(BaseModel):
    generated_at:     str
    system:           SystemInfo
    process:          ProcessMetrics
    disk:             DiskMetrics
    database:         DatabaseMetrics
    requests:         RequestMetrics
    anomalies_recent: int
    alerts_total:     int
    alerts_recent:    list


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _process_metrics() -> ProcessMetrics:
    proc = psutil.Process(os.getpid())
    mem  = proc.memory_info()
    try:
        open_files = len(proc.open_files())
    except (psutil.AccessDenied, AttributeError):
        open_files = None

    return ProcessMetrics( # type: ignore
        uptime_seconds = round(time.time() - _START_TIME, 1), # type: ignore
        cpu_percent    = float(proc.cpu_percent(interval=0.1)),
        memory_mb      = round(mem.rss / 1024 / 1024, 2), # type: ignore
        memory_percent = round(proc.memory_percent(), 2), # type: ignore
        open_files     = open_files,
        threads        = int(proc.num_threads()),
    )


def _disk_metrics() -> DiskMetrics:
    usage = psutil.disk_usage("/")
    return DiskMetrics( # type: ignore
        total_gb = round(usage.total / 1e9, 2), # type: ignore
        used_gb  = round(usage.used  / 1e9, 2), # type: ignore
        free_gb  = round(usage.free  / 1e9, 2), # type: ignore
        percent  = float(usage.percent),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=FullMetrics, summary="Full system metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)) -> FullMetrics:
    """
    Returns a comprehensive JSON snapshot of:
    - Process / OS / disk usage
    - Database record counts
    - Request stats
    - Recent anomaly and alert counts
    """
    uptime = time.time() - _START_TIME

    # ── System info ───────────────────────────────────────────────────────────
    sys_info = SystemInfo( # type: ignore
        hostname  = platform.node(),
        platform  = f"{platform.system()} {platform.release()}",
        python    = platform.python_version(),
        cpu_count = os.cpu_count() or 1,
    )

    # ── Database queries ──────────────────────────────────────────────────────
    db_ok       = True
    evt_count   = 0
    qlog_count  = 0
    ana_count   = 0
    try:
        await db.execute(text("SELECT 1"))  # ping
        evt_count  = (await db.execute(select(func.count()).select_from(GreenEvent))).scalar_one()
        qlog_count = (await db.execute(select(func.count()).select_from(QueryLog))).scalar_one()
        ana_count  = (await db.execute(select(func.count()).select_from(AnalyticsRecord))).scalar_one()
    except Exception as exc:
        logger.warning("Metrics DB query failed: {}", exc)
        db_ok = False

    # ── Request stats ─────────────────────────────────────────────────────────
    mins_up = uptime / 60 or 1
    req_metrics = RequestMetrics( # type: ignore
        total_requests   = int(_REQUEST_STATS["total"]),
        error_count      = int(_REQUEST_STATS["errors"]),
        uptime_seconds   = round(float(uptime), 1), # type: ignore
        requests_per_min = round(float(_REQUEST_STATS["total"] / mins_up), 2), # type: ignore
    )

    return FullMetrics( # type: ignore
        generated_at   = datetime.now(timezone.utc).isoformat(),
        system         = sys_info,
        process        = _process_metrics(),
        disk           = _disk_metrics(),
        database       = DatabaseMetrics( # type: ignore
            total_events    = evt_count,
            total_queries   = qlog_count,
            total_analytics = ana_count,
            db_reachable    = db_ok,
        ),
        requests       = req_metrics,
        anomalies_recent = len(anomaly_detector.get_recent(50)),
        alerts_total   = alert_engine.total_fired,
        alerts_recent  = alert_engine.get_recent(10),
    )


@router.get("/live", summary="Lightweight live metrics for dashboard polling")
async def get_live_metrics() -> dict:
    """Minimal CPU/memory/uptime snapshot — fast (no DB query)."""
    proc = _process_metrics()
    return {
        "uptime_s":      proc.uptime_seconds,
        "cpu_pct":       proc.cpu_percent,
        "memory_mb":     proc.memory_mb,
        "requests":      _REQUEST_STATS["total"],
        "errors":        _REQUEST_STATS["errors"],
        "anomalies":     len(anomaly_detector.get_recent(50)),
        "alerts_fired":  alert_engine.total_fired,
        "timestamp":     datetime.now(timezone.utc).isoformat(),
    }
