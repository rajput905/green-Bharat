"""
GreenFlow AI – Database Session & Models
==========================================
SQLAlchemy async engine, session factory, and ORM model definitions.
Supports PostgreSQL in production and SQLite for local development
(switch via DATABASE_URL in .env).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import settings
from loguru import logger


# ─────────────────────────────────────────────────────────────────────────────
# Async engine + session factory
# ─────────────────────────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.app_debug,           # log all SQL in debug mode
    future=True,
)

AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# ─────────────────────────────────────────────────────────────────────────────
# Base declarative model
# ─────────────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """All ORM models inherit from this base."""


# ─────────────────────────────────────────────────────────────────────────────
# ORM Models
# ─────────────────────────────────────────────────────────────────────────────

class GreenEvent(Base):
    """Stores each incoming green-data event after ingestion."""

    __tablename__ = "green_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(64))
    raw_text: Mapped[str | None] = mapped_column(Text)
    carbon_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class QueryLog(Base):
    """Audit log of every RAG query with latency and response."""

    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnalyticsRecord(Base):
    """Unified record of environmental inputs and derived scores."""

    __tablename__ = "analytics_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    city: Mapped[str | None] = mapped_column(String(50))
    temp: Mapped[float | None] = mapped_column(Float)
    humidity: Mapped[float | None] = mapped_column(Float)
    aqi: Mapped[int | None] = mapped_column(Integer)
    avg_aqi_10m: Mapped[float | None] = mapped_column(Float)
    risk_score: Mapped[float | None] = mapped_column(Float)
    safety_level: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PredictionLog(Base):
    """History of AQI predictions vs actuals."""

    __tablename__ = "prediction_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float)
    actual_aqi: Mapped[int | None] = mapped_column(Integer)
    predicted_aqi: Mapped[float | None] = mapped_column(Float)
    delta: Mapped[float | None] = mapped_column(Float)


class CO2PredictionLog(Base):
    """History of CO2 predictions."""

    __tablename__ = "co2_prediction_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float, index=True)
    current_co2: Mapped[float] = mapped_column(Float)
    predicted_co2_30min: Mapped[float] = mapped_column(Float)
    trend: Mapped[str] = mapped_column(String(20))  # increasing/decreasing/stable
    confidence: Mapped[float] = mapped_column(Float)


class SystemAlert(Base):
    """System-level alerts triggered by threshold breaches."""

    __tablename__ = "system_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    city: Mapped[str | None] = mapped_column(String(50))
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)   # e.g. "CO2_CRITICAL"
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)     # LOW / MEDIUM / HIGH / CRITICAL
    resolved: Mapped[bool] = mapped_column(Integer, default=0)            # 0=open, 1=resolved
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EnvironmentalRisk(Base):
    """History of real-time environmental risk assessments."""

    __tablename__ = "environmental_risks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float, index=True)
    risk_score: Mapped[float] = mapped_column(Float)
    level: Mapped[str] = mapped_column(String(20))
    recommendation: Mapped[str] = mapped_column(Text)


# ─────────────────────────────────────────────────────────────────────────────
# Initialise tables
# ─────────────────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create all tables (idempotent – safe to call on every startup)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables initialised")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI dependency
# ─────────────────────────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:  # type: ignore[return]
    """Yield an async DB session; roll back on error, close on exit."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
