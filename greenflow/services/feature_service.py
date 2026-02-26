"""
services/feature_service.py
============================
Business-logic layer for environmental feature extraction.
Wraps the raw extractor in greenflow/features/ with higher-level
service methods that can be consumed by API routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data Transfer Object
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FeatureResult:
    """Structured result returned by the feature service."""
    carbon_score: float         # 0.0–1.0 relevance score
    source_type: str            # sensor | kafka | webhook | simulated
    keyword_hits: int           # Number of environmental keywords matched
    anomaly_flag: bool          # True if reading is statistically unusual
    confidence: float           # Model confidence in the score


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────

class FeatureService:
    """
    Orchestrates feature extraction for incoming environmental events.

    Usage:
        svc = FeatureService()
        result = svc.extract(text="CO2 rising near urban zone", source="sensor_42")
    """

    # Environmental keywords used for carbon relevance scoring
    _KEYWORDS = [
        "co2", "carbon", "emission", "aqi", "pollution", "pm2.5",
        "greenhouse", "methane", "ozone", "nox", "voc", "smog",
    ]

    def extract(self, text: str, source: Optional[str] = None) -> FeatureResult:
        """
        Extract environmental features from raw event text.

        Args:
            text:   The raw text payload from the sensor or data source.
            source: Optional source identifier (e.g., 'sensor_42').

        Returns:
            FeatureResult with carbon score, keyword hits, and anomaly flag.
        """
        text_lower = text.lower()

        # Count keyword matches for relevance scoring
        hits = sum(1 for kw in self._KEYWORDS if kw in text_lower)

        # Simple linear carbon score: more keywords → higher relevance
        score = min(hits / max(len(self._KEYWORDS) * 0.3, 1), 1.0)

        # Detect anomaly if score is unusually high (> 0.8)
        is_anomaly = score > 0.8

        # Classify source type from the source identifier
        source_type = self._classify_source(source or "unknown")

        return FeatureResult(
            carbon_score=round(score, 4),
            source_type=source_type,
            keyword_hits=hits,
            anomaly_flag=is_anomaly,
            confidence=min(0.5 + hits * 0.05, 0.99),
        )

    @staticmethod
    def _classify_source(source: str) -> str:
        """Map a source string to a canonical source type."""
        s = source.lower()
        if "kafka" in s:
            return "kafka"
        if "webhook" in s or "api" in s:
            return "webhook"
        if "simul" in s or "worker" in s:
            return "simulated"
        return "sensor"


# Module-level singleton for convenience
feature_service = FeatureService()
