# GreenFlow AI — Fault Tolerance Architecture

> **Production-Grade Resilience Strategies for a Real-Time Environmental AI Platform**

---

## 1. Service Layer Fault Tolerance

### 1.1 FastAPI Application

| Mechanism | Implementation | Benefit |
|-----------|---------------|---------|
| **Global exception handler** | FastAPI `@app.exception_handler(Exception)` returns RFC-7807 error envelope | Never leaks stack traces in production |
| **Request timeout** | Starlette `TimeoutMiddleware(timeout=30)` | Prevents thread exhaustion from slow clients |
| **Correlation IDs** | `X-Correlation-ID` header injected by `RequestLoggingMiddleware` | Trace a single request across all log lines |
| **Graceful shutdown** | FastAPI `lifespan` context flushes DB sessions before exit | No torn transactions on SIGTERM |

### 1.2 Database (SQLAlchemy Async + PostgreSQL)

```python
# Pool settings tuned for resilience
engine = create_async_engine(
    DATABASE_URL,
    pool_size        = 10,    # base connections
    max_overflow     = 20,    # burst capacity
    pool_pre_ping    = True,  # reconnect on stale sockets
    pool_recycle     = 1800,  # recycle connections every 30 min
)
```

- **`pool_pre_ping=True`** — SQLAlchemy issues `SELECT 1` before each query. If the DB dropped the connection, it auto-reconnects transparently.
- **Connection recycling** — connections older than 30 minutes are replaced to avoid TCP timeout issues.
- **Async rollback** — the `get_db()` dependency rolls back any failed transaction automatically.

---

## 2. Anomaly & Alert System Resilience

### 2.1 Anomaly Detector
- **Dual-method detection** (Z-score + IQR) — if one method has insufficient data, the other still fires.
- **`MIN_WINDOW = 10`** — detection only starts after 10 readings; avoids false positives during cold start.
- **`COOLDOWN_SECS = 120`** — suppresses duplicate anomaly alerts, preventing alert storms.
- **Sliding deque with `maxlen`** — uses O(1) append; never grows unboundedly.

### 2.2 Alert Engine
- **Per-type cooldown (5 min)** — ensures the same alert type doesn't flood the system.
- **Async DB persistence with try/except** — a DB write failure does NOT block the pipeline.
- **In-memory ring buffer** — alerts remain accessible even if DB is briefly unavailable.

---

## 3. API Resilience Patterns

### 3.1 Graceful Degradation
All API endpoints are designed to return partial responses rather than 500 errors:

```python
# Example: /metrics endpoint with DB fallback
try:
    evt_count = await db.execute(select(func.count())...)
except Exception:
    evt_count = -1          # signals "unavailable" rather than crashing
    db_ok = False
```

### 3.2 Health Check Tiering

| Endpoint | Frequency | Purpose |
|----------|-----------|---------|
| `GET /api/v1/health` | Every 5s | Kubernetes liveness — fast, no I/O |
| `GET /api/v1/health/ready` | Every 10s | Readiness — checks DB + disk, returns **503** if unhealthy |
| `GET /api/v1/health/deep` | Every 60s | Alerting dashboards — full diagnostic |

### 3.3 Simulation Engine Fallback
The `POST /simulate` endpoint falls back to statistical defaults if the DB query for live baselines fails:

```python
live_co2 = fetched_from_db or DEFAULT_CO2   # 420 ppm global average
```

---

## 4. Container Fault Tolerance (Docker)

```yaml
# docker-compose.yml restart policy
restart: unless-stopped

# Health-check driven dependency
depends_on:
  postgres-db:
    condition: service_healthy
```

- **`restart: unless-stopped`** — crashed containers restart automatically.
- **`service_healthy` condition** — FastAPI waits for PostgreSQL's `pg_isready` before starting.
- **Docker `HEALTHCHECK`** in `Dockerfile` — Docker Engine marks the container unhealthy and can restart it.

---

## 5. Data Pipeline Resilience (Pathway Engine)

- **Idempotent ingestion** — events carry a unique `event_id`; duplicates are silently ignored via `INSERT OR IGNORE`.
- **Pipeline restart** — the `analytics_pipeline.py` process is independent of the API; a pipeline crash doesn't affect API availability.
- **Fallback readings** — if live API data (weather, AQI) is unavailable, the pipeline uses the last known value or synthetic baseline data.

---

## 6. Logging & Observability

```
┌──────────────────────────────────────────┐
│  Request → RequestLoggingMiddleware      │
│  ├─ Correlation-ID (X-Correlation-ID)   │
│  ├─ Loguru structured JSON (prod)        │
│  └─ Rotating file + stderr              │
│                                          │
│  Anomaly → logger.warning(...)          │
│  Alert   → logger.error / critical(…)  │
│  DB error→ logger.exception(…)          │
└──────────────────────────────────────────┘
```

Log files rotate at 10 MB, retain 14 days. In production, ship to ELK / Loki via file-beat.

---

## 7. Future Enhancements (Roadmap)

| Feature | Purpose |
|---------|---------|
| **Redis cache layer** | Cache `/metrics`, `/risk` results for 10s to reduce DB pressure |
| **Circuit breaker** (tenacity) | Stop calling OpenAI if it fails 5× in a row; return cached answer |
| **Kafka integration** | Replace in-memory alert queue with durable Kafka topic |
| **Kubernetes HPA** | Auto-scale API replicas based on CPU/request-rate metrics |
| **Distributed tracing** (Jaeger/OTEL) | End-to-end span tracking across services |

---

*Generated for GreenFlow AI v2.0.0 — Green Bharat Hackathon 2025*
