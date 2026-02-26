# GreenFlow AI 🌿

Real-time environmental intelligence system powered by Pathway, FastAPI, and OpenAI RAG.

---

## ✨ Features

| Layer | Technology |
|---|---|
| Real-time streaming | Pathway – incremental computation |
| REST API | FastAPI + Uvicorn |
| AI / RAG | OpenAI GPT-4o + ChromaDB vector store |
| Data ingestion | JSONL files, Kafka, webhook push |
| Feature extraction | Keyword scoring, carbon relevance |
| Database | SQLAlchemy async (PostgreSQL / SQLite) |
| Frontend | Vanilla JS SSE dashboard (no build step) |
| Logging | Loguru rotating file + structured console |

---

## 📁 Project Structure

```
greenflow/
├── ingestion/          # Data source connectors (file, Kafka, webhook)
│   ├── __init__.py
│   └── ingestor.py
├── pipeline/           # Pathway streaming graph
│   ├── __init__.py
│   └── streaming.py
├── features/           # Feature extraction from raw records
│   ├── __init__.py
│   └── extractor.py
├── rag/                # Retrieval-Augmented Generation engine
│   ├── __init__.py
│   └── engine.py
├── api/                # FastAPI routers
│   ├── __init__.py
│   └── routes/
│       ├── health.py   # GET /health, /ready
│       ├── events.py   # POST/GET /events
│       ├── query.py    # POST /query, /query/index
│       └── stream.py   # SSE + WebSocket
├── database/           # SQLAlchemy models & session
│   ├── __init__.py
│   └── session.py
├── frontend/           # Static HTML/JS dashboard
│   ├── index.html
│   ├── style.css
│   └── script.js
├── config.py           # Pydantic-Settings configuration
├── main.py             # Application entry point
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### 1 · Clone / enter project directory
```bash
cd "e:\green bharat hackthon\greenflow"
```

### 2 · Create virtual environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3 · Install dependencies
```bash
pip install -r requirements.txt
```

### 4 · Configure environment
```bash
copy .env.example .env      # Windows
# cp .env.example .env      # macOS / Linux
```

Open `.env` and fill in at minimum:
```env
OPENAI_API_KEY=sk-your-key-here
SECRET_KEY=some-long-random-string
```
For development, the rest of the defaults work out of the box (SQLite, local Chroma).

### 5 · Create required directories
```bash
mkdir -p data\watch\output logs
```

### 6 · Run the server
```bash
# Development (auto-reload)
uvicorn greenflow.main:app --reload --host 0.0.0.0 --port 8000

# Or via Python
python greenflow/main.py
```

Open your browser at **http://localhost:8000**

---

## 📡 API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Liveness check |
| GET | `/api/v1/ready` | Readiness check |
| POST | `/api/v1/events` | Ingest a green-data event |
| GET | `/api/v1/events` | List recent events |
| POST | `/api/v1/query` | Ask AI (RAG pipeline) |
| POST | `/api/v1/query/index` | Index a document |
| GET | `/api/v1/stream/events` | SSE live feed |
| WS | `/api/v1/stream/ws` | WebSocket connection |

> Interactive docs at **http://localhost:8000/docs** (development mode only).

---

## 🔁 Pathway Streaming Pipeline

The pipeline is in `pipeline/streaming.py`. Enable it in `main.py` by uncommenting:

```python
from pipeline.streaming import run_pipeline
t = run_pipeline()
```

Drop JSONL files into `data/watch/` and Pathway will:

1. Detect them automatically (no restart needed)
2. Apply UDFs: decode payload, classify source, compute carbon score
3. Write enriched rows to `data/watch/output/enriched.jsonl`
4. The SSE endpoint tails that file and pushes to the browser in real time

**Example event file** `data/watch/sample.jsonl`:
```json
{"source": "sensor_42", "timestamp": 1700000000.0, "payload": "{\"text\": \"CO2 levels rising near urban zone\", \"co2_ppm\": 425.3}"}
```

---

## 🤖 RAG Usage

```python
from rag.engine import rag_engine

# Index a document
rag_engine.index_document("Solar irradiance dropped 12% in Q3 2024", metadata={"region": "north"})

# Query
import asyncio
result = asyncio.run(rag_engine.query("What happened to solar irradiance?"))
print(result["answer"])
```

---

## 🐳 Docker Deployment

The fastest way to get the full stack (Database, Engine, API, Dashboard) running is via Docker Compose.

### 1 · Configure Environment
Ensure your `.env` file has the necessary keys:
```env
OPENAI_API_KEY=sk-your-key-here
WEATHER_API_KEY=your-key       # Optional
AQI_API_KEY=your-key           # Optional
```

### 2 · Spin up the stack
```bash
docker-compose up --build -d
```

This will launch:
- **Greenflow DB**: PostgreSQL at port 5432
- **Greenflow Engine**: Pathway processing pipeline
- **Greenflow API**: FastAPI backend at port 8000
- **Greenflow UI**: Streamlit dashboard at port 8501

### 3 · Check logs
```bash
docker-compose logs -f api-backend
```

---

## 🧪 Run Tests

```bash
pytest tests/ -v
```

---

## 🌍 Environment Variables Reference

See `.env.example` for the full list with inline documentation.

| Variable | Default | Required |
|---|---|---|
| `OPENAI_API_KEY` | — | ✅ |
| `SECRET_KEY` | — | ✅ |
| `DATABASE_URL` | SQLite dev | ❌ |
| `PATHWAY_LICENSE_KEY` | (open tier) | ❌ |
| `KAFKA_BROKER` | localhost:9092 | ❌ |

---

## 🛠 Production Deployment

```bash
# 4 Uvicorn workers
uvicorn greenflow.main:app --workers 4 --host 0.0.0.0 --port 8000
```

Set in `.env`:
```env
APP_ENV=production
APP_DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/greenflow
```

---

## 📝 License

MIT © 2025 GreenFlow AI Team
