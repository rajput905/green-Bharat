"""
GreenFlow AI – Real-Time Environmental Data Pipeline
=====================================================
As a Real-Time Data Engineer, this script implements a high-performance 
Pathway streaming pipeline that fuses data from three main sources:
1. Weather API (Polling)
2. AQI API (Polling)
3. Simulated Traffic Data (Every 3 seconds)

Features:
- Incremental stream processing
- Robust joining on timestamps
- Cleaning of invalid/missing values
- Real-time logging to console
"""

import os
import time
import json
import random
import asyncio
from datetime import datetime
from typing import Any

import pathway as pw
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "INSERT_API_KEY")
AQI_API_KEY = os.getenv("AQI_API_KEY", "INSERT_API_KEY")

# ─────────────────────────────────────────────────────────────────────────────
# 1. Schemas
# ─────────────────────────────────────────────────────────────────────────────

class WeatherSchema(pw.Schema):
    temp: float
    humidity: float
    city: str
    timestamp: float

class AQISchema(pw.Schema):
    aqi: int
    primary_pollutant: str
    city: str
    timestamp: float

class TrafficSchema(pw.Schema):
    vehicle_count: int
    avg_speed_kmh: float
    city: str
    timestamp: float

# ─────────────────────────────────────────────────────────────────────────────
# 2. Simulated Connectors (Mocking APIs for demonstration)
# ─────────────────────────────────────────────────────────────────────────────

def mock_weather_poller(city: str):
    """Simulates a Weather API response."""
    # In production, use pw.io.http.rest_poller
    return {
        "temp": round(random.uniform(15.0, 35.0), 2), # type: ignore
        "humidity": round(random.uniform(30.0, 80.0), 2), # type: ignore
        "city": city,
        "timestamp": time.time()
    }

def mock_aqi_poller(city: str):
    """Simulates an AQI API response."""
    return {
        "aqi": random.randint(30, 150),
        "primary_pollutant": random.choice(["PM2.5", "PM10", "NO2", "O3"]),
        "city": city,
        "timestamp": time.time()
    }

def traffic_generator(city: str):
    """Generates simulated traffic data every 3 seconds."""
    return {
        "vehicle_count": random.randint(100, 1000),
        "avg_speed_kmh": round(random.uniform(20.0, 80.0), 1), # type: ignore
        "city": city,
        "timestamp": time.time()
    }

# ─────────────────────────────────────────────────────────────────────────────
# 3. Pipeline Definition
# ─────────────────────────────────────────────────────────────────────────────

def run_environment_pipeline(city_name: str = "New Delhi"):
    """
    Main Pathway pipeline logic.
    """
    logger.info(f"🚀 Initializing Real-Time Environmental Pipeline for {city_name}...")

    # ── Source 1: Weather (Polling every 5s) ──
    weather_stream = pw.io.g_gen.generate_stream(
        lambda: mock_weather_poller(city_name),
        interval_ms=5000,
        schema=WeatherSchema
    )

    # ── Source 2: AQI (Polling every 5s) ──
    aqi_stream = pw.io.g_gen.generate_stream(
        lambda: mock_aqi_poller(city_name),
        interval_ms=5000,
        schema=AQISchema
    )

    # ── Source 3: Traffic (Polling every 3s) ──
    traffic_stream = pw.io.g_gen.generate_stream(
        lambda: traffic_generator(city_name),
        interval_ms=3000,
        schema=TrafficSchema
    )

    # ── Transformation: Clean & Enrich ──
    # Handle missing or invalid values (e.g., negative AQI or extreme temps)
    weather_cleaned = weather_stream.filter(
        (pw.this.temp > -50) & (pw.this.temp < 60)
    )

    aqi_cleaned = aqi_stream.filter(
        (pw.this.aqi >= 0) & (pw.this.aqi <= 500)
    )

    # ── Merging Streams (Join by Timestamp) ──
    # Note: In real-time streaming, we often use asof_join or window-based joins.
    # Here we'll use a simple Union and Reduce or just print them as they come.
    # For a unified AI feature vector, we wait for all signals.
    
    # Enrich traffic with weather context using ASOF join (closest timestamp)
    unified_stream = traffic_stream.asof_join(
        weather_cleaned,
        pw.this.timestamp,
        weather_cleaned.timestamp
    ).asof_join(
        aqi_cleaned,
        pw.this.timestamp,
        aqi_cleaned.timestamp
    )

    # final enrichment
    final_output = unified_stream.select(
        *pw.this,
        status = pw.if_else(pw.this.aqi > 100, "Unhealthy", "Good"),
        congestion_level = pw.if_else(pw.this.avg_speed_kmh < 30, "High", "Low"),
        feature_vector = pw.apply(
            lambda t, h, a, v, s: json.dumps([t, h, a, v, s]),
            pw.this.temp, pw.this.humidity, pw.this.aqi, pw.this.vehicle_count, pw.this.avg_speed_kmh
        )
    )

    # ── Live Console Sink ──
    # This prints updates every time a row is processed
    pw.io.debug.debug_print(final_output)

    # ── Run the graph ──
    logger.info("📡 Pipeline is live! Press Ctrl+C to stop.")
    pw.run()

# ─────────────────────────────────────────────────────────────────────────────
# 4. Instructions
# ─────────────────────────────────────────────────────────────────────────────
"""
HOW TO RUN:
1. Ensure you have Pathway installed: 'pip install pathway-framework'
2. Set your environment variables (optional for mock mode):
   export WEATHER_API_KEY="your_key"
   export AQI_API_KEY="your_key"
3. Run the script:
   python realtime_pipeline.py

TIPS:
- This script uses 'pw.io.g_gen' for simulation.
- In a production environment with real REST APIs, replace 'mock' with 'pw.io.http.rest_poller'.
- The asof_join ensures that every traffic event has the latest weather/AQI context without waiting for clock sync.
"""

if __name__ == "__main__":
    try:
        run_environment_pipeline()
    except KeyboardInterrupt:
        logger.warning("Pipeline stopped by user.")
