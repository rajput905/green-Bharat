# Changelog

All notable changes to GreenFlow AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Mobile-responsive dashboard improvements
- Kafka consumer integration
- Real-time alerts via email/Slack webhook
- Multi-city support

---

## [1.2.0] - 2025-02-26

### Added
- **What-If Simulator** — POST `/api/v1/simulate` endpoint for scenario modeling
- **Executive Summary** — AI-generated 3-sentence briefing refreshed every 60s
- **Countdown ring** animation in Executive Summary card
- `style.css` and `script.js` extracted from monolithic `index.html`
- `scripts/` directory for utility scripts (`check_db.py`, `start_server.bat`)
- `docs/`, `screenshots/`, `architecture/`, `demo/` project folders
- `ARCHITECTURE.md` with full system design documentation
- `CONTRIBUTING.md` with contributor guidelines
- `LICENSE` (MIT)

### Changed
- SSE generator now polls `analytics_records` table instead of tailing JSONL file
- CORS origins expanded to include `http://localhost:8000` and `http://127.0.0.1:8000`
- `start_server.bat` updated to use `uvicorn greenflow.main:app` module path

### Fixed
- Route mismatch: `/analytics/recommendation-ai` → `/analytics/recommendation`
- Database path corrected in `check_db.py`
- Port 8000 conflict resolution in startup script

---

## [1.1.0] - 2025-02-25

### Added
- **Risk Score** endpoint with circular gauge visualization
- **CO₂ 30-minute forecast** with confidence bar
- **AI Recommendation** panel with emergency pulse animation
- ChromaDB-backed RAG engine for natural language queries
- Async SQLAlchemy database layer
- Loguru structured logging with file rotation
- Docker Compose stack (PostgreSQL, Pathway, FastAPI, Streamlit)
- `simulated_background_worker.py` for development data generation

### Changed
- Migrated from synchronous to async FastAPI endpoints
- Database schema updated: added `analytics_records` table
- Frontend rebuilt with glassmorphism dark theme

---

## [1.0.0] - 2025-02-21

### Added
- Initial project structure
- Basic FastAPI backend with health check endpoint
- Pathway streaming pipeline skeleton
- SQLite database integration
- Minimal SSE endpoint
- Vanilla JS frontend dashboard
- Environmental data ingestion pipeline

---

[Unreleased]: https://github.com/greenflow-ai/greenflow/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/greenflow-ai/greenflow/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/greenflow-ai/greenflow/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/greenflow-ai/greenflow/releases/tag/v1.0.0
