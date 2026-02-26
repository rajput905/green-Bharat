# GreenFlow AI — Roadmap 🗺️

This document outlines the planned development roadmap for GreenFlow AI.

---

## ✅ Completed (v1.0 – v1.2)

- [x] Core FastAPI backend with async endpoints
- [x] Pathway streaming pipeline
- [x] SQLAlchemy database layer (SQLite + PostgreSQL)
- [x] Real-time SSE dashboard
- [x] OpenAI GPT-4o RAG chatbot
- [x] CO₂ 30-minute prediction engine
- [x] Environmental Risk Score meter
- [x] AI Recommendation engine
- [x] What-If Scenario Simulator
- [x] Executive Summary with typewriter animation
- [x] Docker Compose deployment
- [x] Structured Loguru logging

---

## 🔄 In Progress (v1.3)

- [ ] **Multi-city support** — configure multiple monitoring locations
- [ ] **Historical trend charts** — 24h/7d AQI & CO₂ graphs using Chart.js
- [ ] **Email/Slack alerts** — webhook notifications when risk > CRITICAL
- [ ] **Prometheus metrics** — expose `/metrics` endpoint for Grafana

---

## 🔮 Planned (v2.0)

### Data Sources
- [ ] Live AQI API integration (IQAir, WAQI)
- [ ] Weather data from OpenWeatherMap
- [ ] Kafka consumer for enterprise data pipelines
- [ ] IoT MQTT sensor support

### AI & ML
- [ ] Time-series ML model (LSTM) for CO₂ forecasting
- [ ] Anomaly detection using Isolation Forest
- [ ] Multi-modal RAG with image support
- [ ] Fine-tuned environmental language model

### Infrastructure
- [ ] Kubernetes deployment manifests (Helm chart)
- [ ] Redis cache layer for high-traffic SSE
- [ ] Rate limiting via `slowapi`
- [ ] JWT authentication for dashboard
- [ ] CI/CD pipeline (GitHub Actions)

### Frontend
- [ ] Mobile-responsive design
- [ ] Dark/light theme toggle
- [ ] Exportable PDF reports
- [ ] Map view with city-level risk heatmap

---

## 💡 Community Ideas

Have a feature idea? [Open an issue](../../issues/new) with the **Feature Request** template!

---

*Last updated: February 2025*
