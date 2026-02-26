"""
GreenFlow AI – Pathway Real-Time Streaming Pipeline
=====================================================
Defines the core Pathway graph that:
  1. Reads from a directory (or socket) as a streaming table
  2. Applies transformations / enrichments
  3. Writes results to an output connector (HTTP REST / file / DB)

Pathway evaluates incrementally: only changed or new rows are recomputed,
giving sub-second end-to-end latency at scale.

Run standalone (useful for testing):
    python -m pipeline.streaming
"""

import json
import threading
from pathlib import Path

import pathway as pw
from loguru import logger

from config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Input Schema
# ─────────────────────────────────────────────────────────────────────────────

class GreenEventSchema(pw.Schema):
    """Schema for incoming green-data events."""
    source: str
    timestamp: float
    payload: str   # JSON-encoded payload string


# ─────────────────────────────────────────────────────────────────────────────
# UDFs – User-Defined Functions applied inside the Pathway graph
# ─────────────────────────────────────────────────────────────────────────────

@pw.udf
def decode_payload(payload_str: str) -> str:
    """Deserialise payload JSON and extract the 'text' field for downstream NLP."""
    try:
        obj = json.loads(payload_str)
        return str(obj.get("text", obj.get("message", str(obj))))
    except (json.JSONDecodeError, TypeError):
        return payload_str


@pw.udf
def classify_source(source: str) -> str:
    """Simple rule-based source classification (extend with ML as needed)."""
    source_lower = source.lower()
    if "sensor" in source_lower:
        return "IoT_Sensor"
    if "api" in source_lower:
        return "External_API"
    if "upload" in source_lower or "file" in source_lower:
        return "File_Upload"
    return "Webhook"


@pw.udf
def compute_carbon_score(text: str) -> float:
    """
    Placeholder carbon-relevance scorer.
    Returns a mock score in [0, 1] based on keyword presence.
    Replace with a real ML model in production.
    """
    keywords = [
        "carbon", "emission", "co2", "renewable", "solar",
        "wind", "methane", "greenhouse", "deforestation", "biodiversity",
    ]
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw in text_lower)
    return min(hits / max(len(keywords), 1), 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_pipeline() -> None:
    """
    Construct and run the Pathway streaming computation graph.

    Input  → pw.io.fs.read (JSONL files dropped into data_watch_dir)
    Output → pw.io.http.rest_connector (push to FastAPI /api/v1/events/sink)

    This function blocks the calling thread until Pathway is terminated.
    """
    watch_dir = Path(settings.data_watch_dir)
    watch_dir.mkdir(parents=True, exist_ok=True)

    logger.info("🔁 Building Pathway pipeline | watch_dir={}", watch_dir)

    # ── Source connector ──────────────────────────────────────────────────────
    events_table = pw.io.fs.read(
        str(watch_dir),
        format="json",
        schema=GreenEventSchema,
        mode="streaming",          # stream-first: process new rows as they arrive
        autocommit_duration_ms=500,
    )

    # ── Transformation graph ──────────────────────────────────────────────────
    enriched = events_table.select(
        source      = events_table.source,
        timestamp   = events_table.timestamp,
        raw_text    = decode_payload(events_table.payload),
        source_type = classify_source(events_table.source),
    )

    scored = enriched.select(
        *pw.this,
        carbon_score = compute_carbon_score(pw.this.raw_text),
    )

    # ── Sink connector  ───────────────────────────────────────────────────────
    # Option A: write enriched stream back to JSONL (safe default)
    pw.io.fs.write(
        scored,
        filename=str(watch_dir / "output" / "enriched.jsonl"),
        format="json",
    )

    # Option B: push to FastAPI event-sink endpoint (uncomment when ready)
    # pw.io.http.request_response_connector(
    #     url=f"http://localhost:{settings.app_port}/api/v1/events/sink",
    #     method="POST",
    #     format="json",
    # ).write(scored)

    logger.info("▶️  Pathway graph compiled – starting run loop")
    pw.run()


# ─────────────────────────────────────────────────────────────────────────────
# Public API – run inside a daemon thread
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline() -> threading.Thread:
    """
    Spawn Pathway pipeline in a daemon background thread.
    Returns the thread object so the caller can join / monitor it.

    Usage (in main.py lifespan)::

        from pipeline.streaming import run_pipeline
        t = run_pipeline()
    """
    thread = threading.Thread(target=build_pipeline, daemon=True, name="pathway-pipeline")
    thread.start()
    logger.info("🚀 Pathway pipeline thread started (tid={})", thread.ident)
    return thread


# ── Standalone entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    build_pipeline()
