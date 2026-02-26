# GreenFlow AI — System Architecture 🏗️

This document describes the technical architecture and design decisions behind GreenFlow AI.

---

## 📐 High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        GreenFlow AI                             │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Data     │───▶│ Pathway  │───▶│ FastAPI  │───▶│Dashboard │  │
│  │ Sources  │    │ Pipeline │    │ Backend  │    │(SSE/JS)  │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │                │               │                        │
│       │          ┌─────▼──────┐  ┌────▼─────┐                  │
│       │          │  SQLite /  │  │ OpenAI   │                  │
│       │          │ PostgreSQL │  │ RAG Engine│                  │
│       │          └────────────┘  └──────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Component Architecture

### 1. Data Ingestion Layer (`greenflow/ingestion/`)

Responsible for collecting raw environmental data from multiple sources:

| Source | Format | Description |
|---|---|---|
| JSONL files | `.jsonl` | Drop files into `data/watch/` |
| Kafka | Stream | Real-time broker messages |
| Webhook | HTTP POST | External API push events |
| Simulated Worker | Internal | Background thread generating test data |

```
DataSource → Ingestor → RawEvent → Pipeline
```

The `ingestor.py` normalizes all sources into a unified `RawEvent` schema before passing to the pipeline.

---

### 2. Streaming Pipeline (`greenflow/pipeline/`)

Built on **Pathway** for incremental, real-time computation:

```
RawEvent
    │
    ▼
┌──────────────────────────────────┐
│ Pathway Streaming Graph          │
│                                  │
│  decode_payload()                │
│       ↓                          │
│  classify_source()               │
│       ↓                          │
│  compute_carbon_score()          │
│       ↓                          │
│  enrich_with_metadata()          │
└──────────────────────────────────┘
    │
    ▼
enriched.jsonl  →  SQLite DB  →  SSE stream
```

**Key design choices:**
- Pathway processes events **incrementally** — no full recomputation on new data
- UDFs (User-Defined Functions) are pure Python, easy to extend
- Output written to both file (`enriched.jsonl`) and database for redundancy

---

### 3. Feature Extraction (`greenflow/features/`)

Applies ML-lite scoring to each event:

```python
Features Extracted:
├── carbon_score      # 0.0–1.0 relevance to carbon emissions
├── keyword_hits      # Count of environmental keywords matched
├── source_trust      # Reliability score per data source
└── anomaly_flag      # Boolean: unusual reading detected
```

Uses **keyword-based scoring** + **statistical thresholding** — no heavy ML models required, keeping latency low (<5ms per event).

---

### 4. AI / RAG Engine (`greenflow/rag/`)

Powered by **OpenAI GPT-4o** + **ChromaDB**:

```
User Query
    │
    ▼
┌─────────────────┐
│ ChromaDB Vector │  ← Indexed environmental documents
│ Similarity Search│
└────────┬────────┘
         │ Top-K relevant chunks
         ▼
┌─────────────────┐
│  OpenAI GPT-4o  │  ← Augmented with retrieved context
│  (RAG Prompt)   │
└────────┬────────┘
         │ Generated answer
         ▼
     API Response
```

**Endpoints powered by RAG:**
- `POST /api/v1/chatbot/chat` — Natural language Q&A
- `POST /api/v1/analytics/recommendation` — AI-generated action plan
- `GET /api/v1/analytics/prediction/co2` — 30-min CO₂ forecast

---

### 5. REST API Layer (`greenflow/api/`)

Built with **FastAPI** (async, ASGI):

```
Client Request
    │
    ▼
CORSMiddleware
    │
    ▼
RequestLoggingMiddleware
    │
    ▼
┌──────────────────────────────────┐
│ Routers                          │
│  /api/v1/health     → health.py  │
│  /api/v1/analytics  → analytics.py│
│  /api/v1/stream     → stream.py  │
│  /api/v1/chatbot    → chatbot.py │
│  /api/v1/simulate   → simulate.py│
│  /api/v1/metrics    → metrics.py │
└──────────────────────────────────┘
    │
    ▼
Database Session (AsyncSession)
    │
    ▼
SQLAlchemy → SQLite (dev) / PostgreSQL (prod)
```

**Key patterns:**
- All routes are **async** for maximum concurrency
- Database sessions injected via **FastAPI dependency injection**
- Responses validated with **Pydantic** schemas
- OpenAPI docs auto-generated at `/docs`

---

### 6. Real-Time Streaming (`/api/v1/stream/events`)

Two protocols supported:

#### Server-Sent Events (SSE)
```
Browser ──── GET /api/v1/stream/events ────▶ Server
       ◀─── text/event-stream ─────────────
       ◀─── data: {"aqi": 76, "temp": 29} ─
       ◀─── data: {"aqi": 78, "temp": 29} ─
       ◀─── ... (polling DB every 2s)      ─
```

#### WebSocket
```
Browser ◀──── WS /api/v1/stream/ws ───────▶ Server
        ◀─── Bi-directional messages ──────▶
```

The SSE generator polls `analytics_records` table every 2 seconds and pushes new records to all connected clients.

---

### 7. Database Layer (`greenflow/database/`)

Using **SQLAlchemy async** with two backends:

| Environment | Database | URL |
|---|---|---|
| Development | SQLite | `data/greenflow_dev.db` |
| Production | PostgreSQL | `postgresql+asyncpg://...` |

**Schema:**

```sql
-- analytics_records: Core telemetry table
CREATE TABLE analytics_records (
    id          INTEGER PRIMARY KEY,
    timestamp   FLOAT NOT NULL,
    city        VARCHAR(50),
    temp        FLOAT,
    humidity    FLOAT,
    aqi         INTEGER,
    avg_aqi_10m FLOAT,
    risk_score  FLOAT,
    safety_level VARCHAR(20),
    created_at  DATETIME DEFAULT NOW()
);

-- green_events: Raw ingested events
CREATE TABLE green_events (
    id          INTEGER PRIMARY KEY,
    event_id    VARCHAR(64) UNIQUE,
    source      VARCHAR(128),
    source_type VARCHAR(64),
    raw_text    TEXT,
    carbon_score FLOAT,
    created_at  DATETIME DEFAULT NOW()
);

-- query_logs: RAG audit trail
CREATE TABLE query_logs (
    id          INTEGER PRIMARY KEY,
    query_text  TEXT,
    answer      TEXT,
    latency_ms  FLOAT,
    created_at  DATETIME DEFAULT NOW()
);
```

---

### 8. Frontend (`greenflow/frontend/`)

Pure **Vanilla JS** — no build step, no framework:

```
index.html  ← HTML structure, semantic & accessible
style.css   ← CSS custom properties, glassmorphism UI
script.js   ← API polling + SSE connection + DOM updates
```

**Data flow in browser:**
```
DOMContentLoaded
    │
    ├── connectSSE()        → EventSource → updates KPIs in real-time
    ├── pollAll() every 15s → fetchPrediction(), fetchRisk(), fetchRecommendation()
    ├── updateSimulator()   → POST /simulate → displays what-if results
    └── fetchExecutiveSummary() every 60s → RAG chatbot → typewriter display
```

---

## 🔒 Security Architecture

| Concern | Approach |
|---|---|
| API Keys | Stored in `.env`, never committed to git |
| CORS | Restricted to configured origins |
| Input Validation | Pydantic schemas on all endpoints |
| SQL Injection | SQLAlchemy ORM (parametrized queries) |
| Rate Limiting | Planned via `slowapi` (future) |

---

## 🚀 Scalability Design

### Horizontal Scaling
```bash
# Multiple Uvicorn workers
uvicorn greenflow.main:app --workers 4 --host 0.0.0.0 --port 8000
```

### Vertical Scaling Path
```
SQLite (dev, 1 user)
    ↓
PostgreSQL (production, 100s of users)
    ↓
PostgreSQL + Redis cache (1000s of users)
    ↓
Distributed Pathway + Kafka (enterprise)
```

### Docker Architecture
```
docker-compose.yml
├── db          → PostgreSQL 15
├── engine      → Pathway pipeline worker
├── api         → FastAPI (port 8000)
└── ui          → Streamlit dashboard (port 8501)
```

---

## 📊 Data Flow Diagram

```
[IoT Sensor / File / API]
         │
         ▼
   [Ingestor.py]
   Normalize → RawEvent
         │
         ▼
 [Pathway Pipeline]
 Score → Enrich → Store
         │
    ┌────┴────┐
    ▼         ▼
[SQLite]  [JSONL file]
    │         │
    ▼         ▼
[FastAPI] [SSE Tail]
    │         │
    └────┬────┘
         ▼
  [Browser Dashboard]
  KPIs + Charts + Alerts
```

---

## 🧪 Testing Strategy

| Type | Tool | Coverage |
|---|---|---|
| Unit Tests | `pytest` | Core business logic |
| API Tests | `pytest` + `httpx` | All endpoints |
| Integration Tests | `pytest` + real DB | Full pipeline |
| Load Tests | `locust` (planned) | SSE under load |

---

*Last updated: February 2025 · GreenFlow AI Team*
