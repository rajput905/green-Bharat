"""
GreenFlow AI – Feature Extraction
===================================
Transforms raw ingested records into rich feature dicts suitable for
LLM prompting, RAG retrieval, and downstream ML models.
"""

import re
import time
from typing import Any

from loguru import logger


# ─────────────────────────────────────────────────────────────────────────────
# Text pre-processing
# ─────────────────────────────────────────────────────────────────────────────

_WHITESPACE_RE = re.compile(r"\s+")
_URL_RE = re.compile(r"https?://\S+")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}")


def clean_text(text: str) -> str:
    """Normalise whitespace, strip URLs and emails from raw text."""
    text = _URL_RE.sub(" <URL> ", text)
    text = _EMAIL_RE.sub(" <EMAIL> ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """
    Lightweight keyword extractor (TF-based, stop-word filtered).
    Swap with KeyBERT or YAKE for production quality.
    """
    STOP_WORDS = {
        "the", "a", "an", "is", "it", "in", "on", "at", "to", "and",
        "of", "for", "with", "this", "that", "are", "was", "be",
    }
    tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
    freq: dict[str, int] = {}
    for tok in tokens:
        if tok not in STOP_WORDS:
            freq[tok] = freq.get(tok, 0) + 1

    return sorted(freq, key=freq.get, reverse=True)[:top_n]  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# Numeric / sensor feature extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_numeric_features(payload: dict[str, Any]) -> dict[str, float | None]:
    """
    Pull known numeric keys from a payload dict.
    Returns a dict of feature_name → value (or None if missing).
    """
    NUMERIC_KEYS = [
        "co2_ppm",
        "temperature_c",
        "humidity_pct",
        "energy_kwh",
        "pm25_ugm3",
        "methane_ppm",
        "solar_irradiance",
    ]
    return {k: float(payload[k]) if k in payload else None for k in NUMERIC_KEYS}


def calculate_carbon_score(numeric_data: dict[str, float | None]) -> float:
    """
    Heuristic to estimate environmental impact (0-100 scale).
    Lower is better (Green).
    """
    score = 50.0  # baseline
    
    co2 = numeric_data.get("co2_ppm")
    if co2:
        # > 1000 ppm is poor air quality
        score += min((co2 - 400) / 20, 30)
        
    energy = numeric_data.get("energy_kwh")
    if energy:
        # Higher energy consumption increases score
        score += min(energy * 5, 20)
        
    # Use float formatting to avoid round() overload confusion
    final_score = float(max(0.0, min(100.0, score)))
    return float(f"{final_score:.2f}")


# ─────────────────────────────────────────────────────────────────────────────
# Main feature builder
# ─────────────────────────────────────────────────────────────────────────────

def build_features(record: dict[str, Any]) -> dict[str, Any]:
    """
    Given a normalised ingestion record, return a feature dict ready for:
      - RAG embedding / indexing
      - LLM prompt construction
      - ML model inference

    Args:
        record: Normalised dict from the ingestion layer
                (must have 'source', 'timestamp', 'payload' keys)

    Returns:
        Feature dict with text, keywords, numeric signals, and metadata.
    """
    payload: dict = record.get("payload", {})

    # ── Text features ─────────────────────────────────────────────────────────
    raw_text: str = (
        payload.get("text")
        or payload.get("message")
        or payload.get("description")
        or str(payload)
    )
    cleaned = clean_text(raw_text)
    keywords = extract_keywords(cleaned)

    # ── Numeric features ──────────────────────────────────────────────────────
    numeric = extract_numeric_features(payload)
    carbon_score = calculate_carbon_score(numeric)

    # ── Metadata ──────────────────────────────────────────────────────────────
    features = {
        "id": payload.get("id", f"auto_{int(time.time() * 1000)}"),
        "source": record.get("source", "unknown"),
        "timestamp": record.get("timestamp", time.time()),
        # Text
        "raw_text": raw_text,
        "clean_text": cleaned,
        "text_length": len(cleaned),
        "keywords": keywords,
        # Numeric signals
        **numeric,
        "carbon_score": carbon_score,
        # Derived
        "has_numeric_data": any(v is not None for v in numeric.values()),
    }

    # Use loop to avoid subscript errors in this environment
    keyword_snip = [k for i, k in enumerate(list(keywords or [])) if i < 5]
    logger.debug("🔬 Features built for record id={} | keywords={}", features["id"], keyword_snip)
    return features
