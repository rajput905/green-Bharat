"""
GreenFlow AI – Main Application Entry Point
==========================================
FastAPI application that integrates:
  - Real-time environmental telemetry (SSE)
  - AI-powered CO2 predictions & risk assessment
  - RAG-based chatbot for environmental advisory
  - "What-if" scenario simulation
"""

import sys
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

# Ensure the backend directory is in the path for internal imports
sys.path.append(str(Path(__file__).parent))

from config import settings
from api.routes import (
    health,
    events,
    query,
    stream,
    analytics,
    chatbot,
    simulate,
    metrics,
    ai
)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Logging Configuration
# ─────────────────────────────────────────────────────────────────────────────

def _configure_logging():
    """Sets up Loguru with clean formatting and file rotation."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level
    )
    # Also log to file for production auditing
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    logger.add(log_dir / "server.log", rotation="10 MB", level="INFO")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Lifecycle Management
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    logger.info("🚀 GreenFlow AI starting up on port {}...", settings.app_port)
    # Ensure data directory exists
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    
    yield
    
    logger.info("🛑 GreenFlow AI shutting down...")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Application Factory
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Initializes and configures the FastAPI application."""
    app = FastAPI(
        title="GreenFlow AI",
        description="Environmental Intelligence Command Center",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request Logging Middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        logger.info(
            "{} {} | Status: {} | Latency: {:.2f}ms",
            request.method, request.url.path, response.status_code, duration * 1000
        )
        return response

    # Include API Routers
    api_prefix = "/api/v1"
    app.include_router(health.router, prefix=f"{api_prefix}/health", tags=["System"])
    app.include_router(analytics.router, prefix=f"{api_prefix}/analytics", tags=["Intelligence"])
    app.include_router(stream.router, prefix=f"{api_prefix}/stream", tags=["Real-time"])
    app.include_router(chatbot.router, prefix=f"{api_prefix}/chatbot", tags=["AI"])
    app.include_router(simulate.router, prefix=f"{api_prefix}/simulate", tags=["Simulator"])
    app.include_router(metrics.router, prefix=f"{api_prefix}/metrics", tags=["System"])

    # ── Static Frontend ──────────────────────────────────────────────────────
    # Mapping to the restructured frontend directory
    frontend_dir = Path(__file__).parent.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
        logger.info("🎨 Frontend mounted from {}", frontend_dir)
    else:
        logger.warning("⚠️ Frontend directory not found at {}", frontend_dir)

    return app

_configure_logging()
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
