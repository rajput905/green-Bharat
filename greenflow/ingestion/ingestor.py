"""
GreenFlow AI – Data Ingestion Layer
=====================================
Handles ingestion of data from multiple sources:
  - Local filesystem (CSV, JSON, JSONL)
  - Kafka topics
  - REST/Webhook push

Each source yields normalised Python dicts that the pipeline layer consumes.
"""

import json
import asyncio
from pathlib import Path
from typing import AsyncIterator, Any

import aiofiles
from loguru import logger

from config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Schema helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_record(raw: dict) -> dict:
    """Add metadata fields to every incoming record."""
    import time
    return {
        "source": raw.get("source", "unknown"),
        "timestamp": raw.get("timestamp", time.time()),
        "payload": raw,
    }


# ─────────────────────────────────────────────────────────────────────────────
# File Ingestion (JSONL / JSON)
# ─────────────────────────────────────────────────────────────────────────────

async def ingest_jsonl_file(filepath: str | Path) -> AsyncIterator[dict]:
    """
    Async generator – yields one record per line from a JSONL file.

    Usage::

        async for record in ingest_jsonl_file("data/events.jsonl"):
            process(record)
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Ingestion source not found: {path}")

    logger.info("📂 Ingesting JSONL file: {}", path)

    async with aiofiles.open(path, mode="r", encoding="utf-8") as fh:
        async for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                record = json.loads(line)
                yield _normalise_record(record)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed JSON line – {}: {}", exc, line[:120])


async def ingest_json_file(filepath: str | Path) -> AsyncIterator[dict]:
    """
    Async generator – ingests a JSON file that contains a top-level list of objects.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Ingestion source not found: {path}")

    logger.info("📂 Ingesting JSON file: {}", path)

    async with aiofiles.open(path, mode="r", encoding="utf-8") as fh:
        content = await fh.read()

    data = json.loads(content)
    if not isinstance(data, list):
        data = [data]

    for item in data:
        yield _normalise_record(item)


# ─────────────────────────────────────────────────────────────────────────────
# Directory Watcher (Pathway integration point)
# ─────────────────────────────────────────────────────────────────────────────

async def watch_directory(directory: str | None = None) -> AsyncIterator[dict]:
    """
    Continuously yields new JSONL records as files are dropped into *directory*.
    This is a lightweight polling watcher; in production use Pathway's built-in
    ``pw.io.fs.read`` connector for zero-overhead file streaming.
    """
    watch_dir = Path(directory or settings.data_watch_dir)
    watch_dir.mkdir(parents=True, exist_ok=True)

    seen: set[Path] = set()
    logger.info("👀 Watching directory for new files: {}", watch_dir)

    while True:
        for fpath in sorted(watch_dir.glob("*.jsonl")) + sorted(watch_dir.glob("*.json")):
            if fpath not in seen:
                seen.add(fpath)
                logger.info("🆕 New file detected: {}", fpath.name)
                if fpath.suffix == ".jsonl":
                    async for record in ingest_jsonl_file(fpath):
                        yield record
                else:
                    async for record in ingest_json_file(fpath):
                        yield record

        await asyncio.sleep(2)   # poll interval (seconds)


# ─────────────────────────────────────────────────────────────────────────────
# Kafka Consumer (async)
# ─────────────────────────────────────────────────────────────────────────────

async def ingest_kafka(
    topic: str | None = None,
    broker: str | None = None,
    group_id: str | None = None,
) -> AsyncIterator[dict]:
    """
    Async generator – consumes messages from a Kafka topic.

    Requires ``aiokafka`` to be installed (add to requirements.txt if using Kafka).
    Gracefully skips if aiokafka is not available (returns nothing).
    """
    try:
        from aiokafka import AIOKafkaConsumer  # type: ignore
    except ImportError:
        logger.warning("aiokafka not installed – Kafka ingestion disabled. Run: pip install aiokafka")
        return

    _topic = topic or settings.kafka_topic
    _broker = broker or settings.kafka_broker
    _group = group_id or settings.kafka_group_id

    logger.info("📡 Connecting to Kafka | broker={} topic={}", _broker, _topic)

    consumer = AIOKafkaConsumer(
        _topic,
        bootstrap_servers=_broker,
        group_id=_group,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
    )

    await consumer.start()
    logger.info("✅ Kafka consumer started on topic '{}'", _topic)

    try:
        async for msg in consumer:
            yield _normalise_record(msg.value)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: ingest from webhook payload (synchronous – called by FastAPI)
# ─────────────────────────────────────────────────────────────────────────────

def ingest_webhook_payload(payload: dict) -> dict:
    """
    Normalise a webhook payload dict received via the /events endpoint.
    Returns the normalised record ready for the pipeline.
    """
    return _normalise_record(payload)
