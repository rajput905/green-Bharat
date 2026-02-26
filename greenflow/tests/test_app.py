"""
GreenFlow AI – Sample Test Suite
==================================
Run with: pytest tests/ -v
"""

import pytest
from httpx import AsyncClient, ASGITransport

# ── Guards ────────────────────────────────────────────────────────────────────
# The imports below may fail if dependencies are not installed.
# Install with: pip install -r requirements.txt
try:
    from main import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────────────────
# Health checks
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not APP_AVAILABLE, reason="app not importable")
async def test_health_check():
    """GET /api/v1/health → 200 with expected fields."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "timestamp" in data


@pytest.mark.skipif(not APP_AVAILABLE, reason="app not importable")
async def test_readiness_check():
    """GET /api/v1/ready → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Events
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not APP_AVAILABLE, reason="app not importable")
async def test_create_event():
    """POST /api/v1/events → 202 with event_id."""
    payload = {
        "source": "test_sensor",
        "text": "Carbon dioxide levels elevated in zone 3.",
        "co2_ppm": 430.5,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/events", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "event_id" in data
    assert "message" in data


# ─────────────────────────────────────────────────────────────────────────────
# Feature extraction unit tests
# ─────────────────────────────────────────────────────────────────────────────

def test_build_features_basic():
    """Feature extraction returns expected keys."""
    from features.extractor import build_features

    record = {
        "source": "unit_test",
        "timestamp": 1700000000.0,
        "payload": {"text": "Renewable solar energy captured today.", "co2_ppm": 410.0},
    }
    features = build_features(record)
    assert features["source"] == "unit_test"
    assert isinstance(features["keywords"], list)
    assert features["text_length"] > 0
    assert features["co2_ppm"] == 410.0


def test_clean_text_removes_urls():
    from features.extractor import clean_text

    cleaned = clean_text("Visit https://example.com for more info")
    assert "https://" not in cleaned
    assert "<URL>" in cleaned


def test_extract_keywords_returns_list():
    from features.extractor import extract_keywords

    kws = extract_keywords("Carbon emissions are rising due to deforestation and fossil fuels")
    assert isinstance(kws, list)
    assert len(kws) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Config validation
# ─────────────────────────────────────────────────────────────────────────────

def test_settings_singleton():
    """get_settings() must always return the same object."""
    from config import get_settings

    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_cors_origins_parsed():
    from config import settings

    assert isinstance(settings.cors_origins, list)
    assert len(settings.cors_origins) >= 1
