"""
GreenFlow AI – Advanced Analytics & Feature Engineering
======================================================
As an AI Data Scientist, this script extends the streaming pipeline with:
1. Stateful Rolling 10-minute AQI Average
2. Multi-factor Pollution Risk Scoring
3. Traffic Congestion & Health Safety Analytics
4. Predictive AQI Baseline
5. Real-time Threshold Alerting
"""

import os
import time
import json
import random
import pathway as pw # type: ignore
from loguru import logger
from dotenv import load_dotenv # type: ignore

from database.session import AnalyticsRecord, SystemAlert, CO2PredictionLog, EnvironmentalRisk # type: ignore
from features.prediction_engine import CO2Schema, build_co2_prediction_stream # type: ignore
from features.risk_engine import compute_risk_score as engine_compute_risk, classify_risk, record_risk # type: ignore

# Load environment variables
load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# 1. Schemas (Re-using from base for consistency)
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
# 2. Mock Data Generators (Same as base for standalone capability)
# ─────────────────────────────────────────────────────────────────────────────

def mock_weather_poller(city: str):
    return {"temp": round(random.uniform(15.0, 35.0), 1), "humidity": round(random.uniform(30.0, 80.0), 1), "city": city, "timestamp": time.time()} # type: ignore

def mock_aqi_poller(city: str):
    # Occasionally inject high AQI to trigger alerts
    is_spike = random.random() < 0.1
    aqi = random.randint(180, 250) if is_spike else random.randint(30, 150)
    return {"aqi": int(aqi), "primary_pollutant": str(random.choice(["PM2.5", "PM10", "NO2"])), "city": city, "timestamp": time.time()}

def traffic_generator(city: str):
    return {"vehicle_count": int(random.randint(100, 1000)), "avg_speed_kmh": round(random.uniform(10.0, 80.0), 1), "city": city, "timestamp": time.time()} # type: ignore

def mock_co2_poller(city: str):
    """Simulates a CO2 sensor reading (ppm)."""
    return {"co2": round(random.uniform(380.0, 450.0), 2), "city": city, "timestamp": time.time()} # type: ignore

# ─────────────────────────────────────────────────────────────────────────────
# 3. Analytics UDFs
# ─────────────────────────────────────────────────────────────────────────────

@pw.udf
def compute_risk_score(aqi: float, traffic_volume: float, humidity: float) -> float:
    """
    Formula: Risk Score = AQI * 0.6 + (Traffic/10) * 0.3 + Humidity * 0.1
    Scales everything to a roughly 0-150 range for alerting.
    """
    # Normalize traffic volume (0-1000) to a smaller scale
    normalized_traffic = traffic_volume / 10.0
    score = (aqi * 0.6) + (normalized_traffic * 0.3) + (humidity * 0.1)
    return min(max(score, 0), 100)

@pw.udf
def categorize_safety(risk_score: float) -> str:
    if risk_score > 80: return "CRITICAL"
    if risk_score > 60: return "WARNING"
    if risk_score > 40: return "MODERATE"
    return "SAFE"

@pw.udf
def compute_congestion_score(speed: float) -> float:
    # 80kmh = 0 score, 0kmh = 100 score
    score = 100 - (speed / 80.0 * 100)
    return max(min(score, 100), 0)

# ─────────────────────────────────────────────────────────────────────────────
# 4. Advanced Analytics Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_analytics_pipeline(city_name: str = "New Delhi"):
    logger.info(f"🧠 Starting Advanced AI Analytics Pipeline for {city_name}...")

    # ── Source Connectors ──
    weather = pw.io.g_gen.generate_stream(lambda: mock_weather_poller(city_name), interval_ms=5000, schema=WeatherSchema)
    aqi = pw.io.g_gen.generate_stream(lambda: mock_aqi_poller(city_name), interval_ms=5000, schema=AQISchema)
    traffic = pw.io.g_gen.generate_stream(lambda: traffic_generator(city_name), interval_ms=3000, schema=TrafficSchema)
    co2_stream = pw.io.g_gen.generate_stream(lambda: mock_co2_poller(city_name), interval_ms=5000, schema=CO2Schema)

    # ── Stateful Windowing: 10-Min Rolling AQI Average ──
    # We use a sliding window of 600 seconds
    aqi_window = aqi.window(
        pw.windows.sliding(duration=600, hop=30),
        instance=aqi.city
    ).reduce(
        avg_aqi=pw.reducers.avg(aqi.aqi),
        max_aqi=pw.reducers.max(aqi.aqi),
        # Simple Prediction: Current vs Avg diff
        pred_delta=aqi.aqi - pw.reducers.avg(aqi.aqi) 
    )

    # ── Fusion ──
    # Join traffic with latest context
    fused = traffic.asof_join(weather, traffic.timestamp, weather.timestamp) \
                   .asof_join(aqi, traffic.timestamp, aqi.timestamp) \
                   .asof_join(aqi_window, traffic.timestamp, aqi_window.end)

    # ── AI Feature Engineering ──
    analytics = fused.select(
        *pw.this,
        risk_score = compute_risk_score(pw.this.aqi, pw.this.vehicle_count, pw.this.humidity),
        congestion = compute_congestion_score(pw.this.avg_speed_kmh),
        # Simple AQI Prediction (Baseline Trend)
        predicted_aqi = pw.this.aqi + (pw.this.pred_delta * 0.5) 
    ).select(
        *pw.this,
        safety_level = categorize_safety(pw.this.risk_score)
    )

    # ── CO2 Prediction Engine ──
    co2_predictions = build_co2_prediction_stream(co2_stream)

    # ── Structured Output Table ──
    dashboard_table = analytics.select(
        timestamp = pw.this.timestamp,
        risk_score = pw.this.risk_score,
        safety = pw.this.safety_level,
        avg_aqi_10m = pw.this.avg_aqi,
        forecast_aqi = pw.this.predicted_aqi,
        congestion_pct = pw.this.congestion
    )

    # ── Real-Time Alerting ──
    alerts = analytics.filter(pw.this.risk_score > 80).select(
        msg = pw.apply(lambda r, s: f"🚨 ALERT: High Environmental Risk ({r:.1f})! Safety: {s}", 
                       pw.this.risk_score, pw.this.safety_level)
    )

    # ── Real-Time Environmental Risk Assessment ──
    @pw.udf
    def get_risk_assessment(co2: float, temp: float, carbon: float, speed: float) -> str:
        # speed < 30kmh counts as traffic impact
        traffic_impact = 1.0 if speed < 30 else 0.0
        score = engine_compute_risk(co2, temp, carbon, traffic_impact)
        assessment = classify_risk(score, co2, temp)
        # record for singleton API retrieval
        record_risk(assessment)
        return json.dumps(assessment)

    risk_stream = fused.select(
        timestamp = pw.this.timestamp,
        assessment_json = get_risk_assessment(
            pw.this.co2, 
            pw.this.temp, 
            # In our system, Carbon Score is derived from the high-res AQI & local traffic
            pw.this.aqi * 0.5, 
            pw.this.avg_speed_kmh
        )
    )

    # ── Sinks ──
    logger.info("📡 Analytics engine compiled. Printing live Dashboard & Alerts...")
    pw.io.debug.debug_print(dashboard_table, prefix="DASHBOARD: ")
    pw.io.debug.debug_print(alerts, prefix="[SYSTEM ALERT] ")
    pw.io.debug.debug_print(co2_predictions, prefix="📈 CO2 PREDICTION: ")
    pw.io.debug.debug_print(risk_stream, prefix="⚠️ RISK ASSESSMENT: ")

    # ── Database Sink (PostgreSQL) ──
    # Connect to the DB defined in .env
    db_url = os.getenv("DB_URL")
    if db_url:
        logger.info(f"🗄️ Initializing DB Sink to {db_url}")
        # Note: Tables are managed by the main FastAPI lifespan or manual init
        
        # Persist the primary analytics record
        pw.io.postgres.write(
            dashboard_table,
            postgres_url=db_url,
            table_name="analytics_records",
            primary_key=["timestamp"]
        )
        
        # Persist alerts
        pw.io.postgres.write(
            alerts,
            postgres_url=db_url,
            table_name="system_alerts",
            primary_key=["msg"] 
        )

        # Persist CO2 predictions
        pw.io.postgres.write(
            co2_predictions,
            postgres_url=db_url,
            table_name="co2_prediction_history",
            primary_key=["timestamp"]
        )

        # Persist Environmental Risk
        pw.io.postgres.write(
            risk_stream.select(
                timestamp = pw.this.timestamp,
                risk_score = pw.apply(lambda j: json.loads(j)["risk_score"], pw.this.assessment_json),
                level = pw.apply(lambda j: json.loads(j)["level"], pw.this.assessment_json),
                recommendation = pw.apply(lambda j: json.loads(j)["recommendation"], pw.this.assessment_json)
            ),
            postgres_url=db_url,
            table_name="environmental_risks",
            primary_key=["timestamp"]
        )

    pw.run()

if __name__ == "__main__":
    import asyncio
    from database.session import init_db
    try:
        # Ensure database tables exist before starting the pipeline
        asyncio.run(init_db())
        run_analytics_pipeline()
    except KeyboardInterrupt:
        logger.warning("Analytics pipeline stopped.")
