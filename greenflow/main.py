"""
GreenFlow AI – Application Entry Point
========================================
Bootstraps the FastAPI server, configures logging via Loguru,
sets up middleware, mounts routers, and wires up lifespan events.

Run:
    uvicorn greenflow.main:app --reload          # development
    uvicorn greenflow.main:app --workers 4        # production
"""

import sys
from pathlib import Path

# Add current directory to path to allow running from parent dir
curr_dir = Path(__file__).parent.absolute()
if str(curr_dir) not in sys.path:
    sys.path.insert(0, str(curr_dir))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from config import settings

# ── Import routers ────────────────────────────────────────────────────────────
from api.routes import health, events, query, stream, analytics, chatbot, simulate, metrics, ai
from api import risk, prediction, recommendation
from api.middleware.request_logging import RequestLoggingMiddleware
from database.session import init_db


# ─────────────────────────────────────────────────────────────────────────────
# Logging setup (Loguru)
# ─────────────────────────────────────────────────────────────────────────────
def _configure_logging() -> None:
    """Remove default Loguru sink, add console + rotating file sink."""
    logger.remove()

    # Console – human-friendly in dev, JSON-like in prod
    fmt_console = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> – {message}"
    )
    logger.add(sys.stderr, format=fmt_console, level=settings.log_level, colorize=True)

    # Rotating file
    logger.add(
        settings.log_file,
        level=settings.log_level,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        encoding="utf-8",
        enqueue=True,          # thread-safe async write
        backtrace=True,
        diagnose=not settings.is_production,  # hide internals in production
    )

    logger.info(
        "Logging initialised | env={} | level={}",
        settings.app_env,
        settings.log_level,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan – startup / shutdown
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Code before `yield` runs on startup; code after `yield` runs on shutdown.
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("🌿 Starting up {}…", settings.app_name)

    # 1. Configure logging
    _configure_logging()

    # 2. Initialise database (create tables if needed)
    await init_db()
    logger.info("✅ Database ready")

    # 3. (Optional) Start the streaming pipeline
    # from pipeline.streaming import run_pipeline
    # run_pipeline()
    logger.info("✅ Manual Pathway pipeline inactive (standby for production)")

    logger.info("🚀 {} is live on {}:{}", settings.app_name, settings.app_host, settings.app_port)

    yield   # ← application is running

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("🛑 Graceful shutdown initiated…")
    # Close any global async clients here (e.g. Redis, HTTP sessions)
    logger.info("👋 {} stopped.", settings.app_name)


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI application factory
# ─────────────────────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title=settings.app_name,
        description=(
            "Real-time AI streaming system powered by Pathway. "
            "Provides REST, WebSocket, and SSE endpoints for green-data intelligence."
        ),
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Request Logging Middleware (must be added before CORS) ──────────────
    app.add_middleware(RequestLoggingMiddleware)

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routers ───────────────────────────────────────────────────────────
    app.include_router(health.router,  prefix="/api/v1/health", tags=["Health"])
    app.include_router(events.router,  prefix="/api/v1/events", tags=["Events"])
    app.include_router(query.router,   prefix="/api/v1/query", tags=["Query / RAG"])
    app.include_router(stream.router,  prefix="/api/v1/stream", tags=["Streaming"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
    app.include_router(chatbot.router,   prefix="/api/v1/chatbot",   tags=["AI Chat"])
    app.include_router(simulate.router,  prefix="/api/v1/simulate",  tags=["Simulation"])
    app.include_router(metrics.router,   prefix="/api/v1/metrics",   tags=["Metrics"])
    app.include_router(ai.router,        prefix="/api/v1/ai",        tags=["AI Recommendation"])

    # ── Static Frontend ──────────────────────────────────────────────────────
    # Mount Frontend - using absolute path to be robust across different execution directories
    frontend_path = curr_dir / "frontend"
    if frontend_path.exists():
        app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    else:
        logger.error(f"Frontend directory not found at {frontend_path}")

    return app


# ── Create module-level app instance (used by uvicorn) ───────────────────────
app = create_app()


# ─────────────────────────────────────────────────────────────────────────────
# Dev convenience runner
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower(),
    )
