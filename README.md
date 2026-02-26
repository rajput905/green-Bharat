<div align="center">

# 🌿 GreenFlow AI

**Real-time Environmental Intelligence Platform**

*Powered by Pathway streaming · FastAPI · OpenAI GPT-4o · ChromaDB RAG*

![Python](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)
![Pathway](https://img.shields.io/badge/Pathway-Streaming-ff6b35)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

</div>

---

## 📸 Dashboard Preview

<div align="center">

![GreenFlow AI Dashboard](docs/dashboard.png)

*Live telemetry · AI risk meter · CO₂ forecasting · Smart recommendations*

</div>

---

## 🏗️ System Architecture

<div align="center">

![System Architecture](docs/architecture.png)

</div>

```
Data Sources → Pathway Pipeline → SQLite/PostgreSQL → FastAPI Backend → JS Dashboard
                                                    ↕
                                              OpenAI GPT-4o + ChromaDB
```

---

## ✨ Features

| Layer | Technology | Description |
|-------|-----------|-------------|
| 🔴 Real-time Streaming | **Pathway** | Incremental computation on live data |
| ⚡ REST API | **FastAPI + Uvicorn** | Async endpoints, auto-generated docs |
| 🤖 AI / RAG | **OpenAI GPT-4o + ChromaDB** | Natural language environmental Q&A |
| 📥 Data Ingestion | **JSONL, Kafka, Webhook** | Multiple source connectors |
| 🧮 Feature Extraction | **Keyword Scoring** | Carbon relevance & anomaly detection |
| 🗄️ Database | **SQLAlchemy async** | PostgreSQL (prod) / SQLite (dev) |
| 🎨 Frontend | **Vanilla JS + SSE** | No build step, instant hot-reload |
| 📋 Logging | **Loguru** | Rotating file + structured console |

---

## 📁 Project Structure

```
GreenFlow-AI/
│
├── greenflow/                  # 🔧 Core application
│   ├── api/
│   │   ├── routes/
│   │   │   ├── analytics.py    # Environmental data endpoints
│   │   │   ├── chatbot.py      # RAG-powered AI chat
│   │   │   ├── health.py       # System health checks
│   │   │   ├── simulate.py     # What-if scenario engine
│   │   │   └── stream.py       # SSE + WebSocket real-time feed
│   │   └── schemas/
│   │       └── analytics.py    # Pydantic response models
│   ├── database/
│   │   └── session.py          # SQLAlchemy models & async session
│   ├── features/
│   │   └── extractor.py        # Carbon scoring & feature extraction
│   ├── frontend/
│   │   ├── index.html          # Dashboard structure (semantic HTML)
│   │   ├── style.css           # Glassmorphism dark theme
│   │   └── script.js           # SSE client + API polling logic
│   ├── ingestion/
│   │   └── ingestor.py         # Data source connectors
│   ├── pipeline/
│   │   └── streaming.py        # Pathway streaming graph
│   ├── rag/
│   │   └── engine.py           # ChromaDB + OpenAI RAG engine
│   ├── config.py               # Pydantic-Settings configuration
│   ├── main.py                 # FastAPI application entry point
│   └── simulated_background_worker.py  # Dev data generator
│
├── scripts/
│   ├── check_db.py             # Database inspection utility
│   └── start_server.bat        # Windows quick-launch script
│
├── docs/                       # Documentation assets
│   ├── architecture.png
│   ├── workflow.png
│   └── dashboard.png
│
├── screenshots/                # UI screenshots
│   ├── dashboard.png
│   ├── ai_panel.png
│   └── risk_meter.png
│
├── architecture/               # Architecture diagrams
│   └── system_design.png
│
├── demo/                       # Demo videos & GIFs
│
├── .github/
│   ├── workflows/ci.yml        # GitHub Actions CI pipeline
│   └── ISSUE_TEMPLATE/         # Bug & feature request templates
│
├── docker-compose.yml          # Full stack Docker deployment
├── Dockerfile                  # Container build instructions
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development & testing tools
├── .env.example                # Environment configuration template
├── README.md
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── ROADMAP.md
└── SECURITY.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### 1 · Clone the repository
```bash
git clone https://github.com/rajput905/green-Bharat.git
cd green-Bharat
```

### 2 · Set up virtual environment
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
copy .env.example .env    # Windows
cp .env.example .env      # macOS / Linux
```
Open `.env` and set:
```env
OPENAI_API_KEY=sk-your-key-here
SECRET_KEY=your-random-secret-key
```

### 5 · Create required directories
```bash
mkdir -p data/watch/output logs
```

### 6 · Run the server
```bash
# Development (auto-reload)
uvicorn greenflow.main:app --reload --host 0.0.0.0 --port 8000

# Windows quick-launch
scripts\start_server.bat
```

🌐 Open **[http://localhost:8000](http://localhost:8000)** in your browser

---

## 📡 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Liveness check |
| `GET` | `/api/v1/analytics/live-data` | Latest telemetry records |
| `GET` | `/api/v1/analytics/risk-score` | Current environmental risk |
| `GET` | `/api/v1/analytics/prediction/co2` | 30-min CO₂ AI forecast |
| `GET` | `/api/v1/analytics/recommendation` | AI action recommendations |
| `POST` | `/api/v1/chatbot/chat` | Natural language AI query |
| `POST` | `/api/v1/simulate` | What-if scenario analysis |
| `GET` | `/api/v1/stream/events` | SSE real-time feed |
| `WS` | `/api/v1/stream/ws` | WebSocket connection |

> 📖 Interactive API docs: **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 📸 Screenshots

<div align="center">

| Dashboard Overview | Risk Meter | AI Panel |
|:---:|:---:|:---:|
| ![Dashboard](screenshots/dashboard.png) | ![Risk](screenshots/risk_meter.png) | ![AI](screenshots/ai_panel.png) |

</div>

---

## 🔁 Pathway Streaming Pipeline

```
data/watch/*.jsonl
       │
       ▼
 Pathway Pipeline
 ├── decode_payload()      → Parse raw JSON
 ├── classify_source()     → Tag sensor/kafka/webhook
 ├── compute_carbon_score()→ 0.0–1.0 relevance score
 └── enrich_metadata()     → Add timestamps & location
       │
       ▼
 data/watch/output/enriched.jsonl  →  SQLite DB
       │
       ▼
 SSE /api/v1/stream/events  →  Browser Dashboard
```

Enable the live pipeline in `main.py`:
```python
from pipeline.streaming import run_pipeline
t = run_pipeline()   # Drop JSONL → instant dashboard update
```

**Example event** (`data/watch/sample.jsonl`):
```json
{"source": "sensor_42", "timestamp": 1700000000.0, "payload": "{\"co2_ppm\": 425.3, \"text\": \"CO2 rising near urban zone\"}"}
```

---

## 🤖 RAG — Ask GreenFlow AI

```python
from rag.engine import rag_engine

# Index environmental knowledge
rag_engine.index_document(
    "AQI above 150 is unhealthy for sensitive groups.",
    metadata={"category": "health_guidelines"}
)

# Natural language query
import asyncio
result = asyncio.run(rag_engine.query("Is it safe to exercise outside today?"))
print(result["answer"])
```

---

## 🐳 Docker Deployment

```bash
# Copy & configure environment
cp .env.example .env
# Add OPENAI_API_KEY to .env

# Start the full stack
docker-compose up --build -d
```

| Service | URL | Description |
|---------|-----|-------------|
| FastAPI Backend | http://localhost:8000 | REST API + Dashboard |
| Streamlit UI | http://localhost:8501 | Alternative UI |
| PostgreSQL DB | localhost:5432 | Persistent storage |

```bash
# View logs
docker-compose logs -f api-backend
```

---

## 🧪 Running Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v --cov=greenflow
```

---

## 🌍 Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `OPENAI_API_KEY` | — | ✅ | GPT-4o access key |
| `SECRET_KEY` | — | ✅ | App signing secret (32+ chars) |
| `DATABASE_URL` | SQLite | ❌ | Use PostgreSQL in production |
| `ALLOWED_ORIGINS` | localhost | ❌ | CORS allowed origins |
| `APP_ENV` | development | ❌ | `development` or `production` |
| `PATHWAY_LICENSE_KEY` | open tier | ❌ | Pathway enterprise license |
| `KAFKA_BROKER` | localhost:9092 | ❌ | Kafka message broker |

See [`.env.example`](.env.example) for full documentation.

---

## 🛠️ Production Deployment

```bash
# Multi-worker Uvicorn
uvicorn greenflow.main:app --workers 4 --host 0.0.0.0 --port 8000

# .env for production
APP_ENV=production
APP_DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/greenflow
```

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup guide
- Coding standards (Black, isort, flake8)
- Commit message conventions
- Pull request checklist

---

## 📋 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full system design & data flow |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [ROADMAP.md](ROADMAP.md) | Planned features |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributor guide |

---

## 📝 License

MIT © 2025 GreenFlow AI Team — see [LICENSE](LICENSE)

---

<div align="center">

*Built with 💚 for Green Bharat Hackathon 2025*

**[⭐ Star this repo](https://github.com/rajput905/green-Bharat) · [🐛 Report Bug](../../issues/new?template=bug_report.md) · [💡 Request Feature](../../issues/new?template=feature_request.md)**

</div>
