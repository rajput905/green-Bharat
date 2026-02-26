# ─────────────────────────────────────────────────────────────────────────────
# GreenFlow AI – Production Dockerfile
# Multi-stage, non-root, health-check enabled
# ─────────────────────────────────────────────────────────────────────────────

# Stage 1: Dependency builder
FROM python:3.11-slim AS builder

LABEL maintainer="GreenFlow AI Team"
LABEL version="2.0.0"

WORKDIR /build

# System build tools (only in builder stage – not copied to final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Lean runtime image
FROM python:3.11-slim AS runtime

LABEL maintainer="GreenFlow AI Team"
LABEL version="2.0.0"
LABEL description="GreenFlow AI – Real-time environmental intelligence platform"

# Security: run as non-root
RUN groupadd -r greenflow && useradd -r -g greenflow -d /app greenflow

WORKDIR /app

# Runtime system libs only (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY --chown=greenflow:greenflow . .

# Create writable directories
RUN mkdir -p /app/logs /app/data /app/knowledge_base \
    && chown -R greenflow:greenflow /app

# Runtime environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    PYTHONPATH=/app

# Expose ports
EXPOSE 8000

# Healthcheck using the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Switch to non-root user
USER greenflow

# Default: run the FastAPI server with production settings
CMD ["uvicorn", "main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--workers", "2", \
    "--loop", "uvloop", \
    "--access-log"]
