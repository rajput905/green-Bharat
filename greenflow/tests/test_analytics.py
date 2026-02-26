"""
tests/test_analytics.py
========================
Unit tests for the analytics API routes.

Run with:
    pytest greenflow/tests/ -v
"""

import pytest
from httpx import AsyncClient, ASGITransport


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
async def client():
    """Async test client for the FastAPI app."""
    from greenflow.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# Health Check Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Health endpoint should return 200 OK."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Analytics Route Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_risk_score_returns_valid_structure(client):
    """Risk score endpoint must return current_score, safety_level, timestamp."""
    response = await client.get("/api/v1/analytics/risk-score")
    assert response.status_code == 200
    data = response.json()
    assert "current_score" in data
    assert "safety_level" in data
    assert isinstance(data["current_score"], (int, float))


@pytest.mark.asyncio
async def test_co2_prediction_returns_valid_structure(client):
    """CO2 prediction endpoint must return required forecast fields."""
    response = await client.get("/api/v1/analytics/prediction/co2")
    assert response.status_code == 200
    data = response.json()
    assert "current_co2" in data
    assert "predicted_co2_30min" in data
    assert "confidence" in data
    assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_recommendation_returns_action_level(client):
    """Recommendation endpoint must include an action_level field."""
    response = await client.get("/api/v1/analytics/recommendation")
    assert response.status_code == 200
    data = response.json()
    assert "action_level" in data
    assert data["action_level"].upper() in ["SAFE", "MODERATE", "HIGH", "CRITICAL"]


# ─────────────────────────────────────────────────────────────────────────────
# Services Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_feature_service_scores_co2_text():
    """FeatureService should give a higher score to CO2-related text."""
    from greenflow.services.feature_service import feature_service
    result = feature_service.extract("CO2 levels rising, carbon emission high, ozone depletion")
    assert result.carbon_score > 0.3
    assert result.keyword_hits >= 3


def test_feature_service_scores_unrelated_text():
    """Unrelated text should produce a near-zero carbon score."""
    from greenflow.services.feature_service import feature_service
    result = feature_service.extract("The stock market closed higher today.")
    assert result.carbon_score == 0.0
    assert result.keyword_hits == 0


def test_feature_service_classifies_source():
    """FeatureService should correctly classify source types."""
    from greenflow.services.feature_service import feature_service
    assert feature_service._classify_source("kafka_topic") == "kafka"
    assert feature_service._classify_source("webhook_push") == "webhook"
    assert feature_service._classify_source("simulated_worker") == "simulated"
    assert feature_service._classify_source("sensor_42") == "sensor"
