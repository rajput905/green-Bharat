
"""
GreenFlow AI – Simulated Background Worker
==========================================
Lightweight replacement for Pathway-based pipelines.
Simulates environmental data (AQI, CO2, Weather, Traffic) 
and populates the SQLite database for the dashboard.
"""
import sys
from pathlib import Path

# Add current directory to path to allow running from parent dir
curr_dir = Path(__file__).parent.absolute()
if str(curr_dir) not in sys.path:
    sys.path.insert(0, str(curr_dir))

import time
import random
import asyncio
from datetime import datetime
from loguru import logger
from sqlalchemy import select, desc

from database.session import (
    AsyncSessionFactory, 
    AnalyticsRecord, 
    SystemAlert, 
    CO2PredictionLog, 
    EnvironmentalRisk,
    init_db
)

# ── Config ──
CITY_NAME = "New Delhi"
SIMULATION_INTERVAL = 5.0  # seconds

# ── Simulation Logic ──

def compute_risk_score(aqi: int, vehicle_count: int, humidity: float) -> float:
    """Same formula as in analytics_pipeline.py."""
    normalized_traffic = vehicle_count / 10.0
    score = (aqi * 0.6) + (normalized_traffic * 0.3) + (humidity * 0.1)
    return min(max(score, 0), 100)

def categorize_safety(risk_score: float) -> str:
    if risk_score > 80: return "CRITICAL"
    if risk_score > 60: return "WARNING"
    if risk_score > 40: return "MODERATE"
    return "SAFE"

async def run_simulation():
    """Main simulation loop."""
    logger.info(f"🚀 Starting Simulated Background Worker for {CITY_NAME}")
    
    # Ensure DB is ready
    await init_db()

    iteration = 0
    while True:
        try:
            async with AsyncSessionFactory() as session:
                # 1. Generate Mock Data
                temp = round(random.uniform(18.0, 32.0), 1)
                humidity = round(random.uniform(40.0, 75.0), 1)
                
                # Occasionally spike AQI for testing alerts
                is_spike = (iteration % 10 == 0) and iteration > 0
                aqi = random.randint(150, 220) if is_spike else random.randint(40, 110)
                
                vehicle_count = random.randint(200, 800)
                speed = round(random.uniform(15.0, 65.0), 1)
                co2 = round(random.uniform(390.0, 460.0), 1)
                
                risk_score = compute_risk_score(aqi, vehicle_count, humidity)
                safety = categorize_safety(risk_score)
                ts = time.time()

                # 2. Record Analytics
                new_record = AnalyticsRecord(
                    timestamp=ts,
                    city=CITY_NAME,
                    temp=temp,
                    humidity=humidity,
                    aqi=aqi,
                    risk_score=round(risk_score, 1),
                    safety_level=safety
                )
                session.add(new_record)

                # 3. Record CO2 Prediction History (Simulated trend)
                trend = random.choice(["increasing", "stable", "decreasing"])
                prediction = CO2PredictionLog(
                    timestamp=ts,
                    current_co2=co2,
                    predicted_co2_30min=co2 + (5.0 if trend == "increasing" else -5.0 if trend == "decreasing" else 0.5),
                    trend=trend,
                    confidence=round(random.uniform(0.75, 0.95), 2)
                )
                session.add(prediction)

                # 4. Record Environmental Risk (History)
                risk_rec = EnvironmentalRisk(
                    timestamp=ts,
                    risk_score=round(risk_score, 1),
                    level=safety,
                    recommendation=f"Simulation update: {safety} protocol active."
                )
                session.add(risk_rec)

                # 5. Handle Alerts
                if safety in ["WARNING", "CRITICAL"]:
                    alert = SystemAlert(
                        timestamp=ts,
                        city=CITY_NAME,
                        alert_type="HIGH_POLLUTION" if aqi > 150 else "GENERAL_RISK",
                        message=f"System breach: {safety} risk detected (AQI: {aqi}, Score: {risk_score:.1f})",
                        severity=safety,
                        resolved=0
                    )
                    session.add(alert)
                    logger.warning(f"⚠️ ALERT TRIGGERED: {safety}")

                await session.commit()
                logger.info(f"✅ Data synced | AQI: {aqi} | Risk: {risk_score:.1f} ({safety})")

        except Exception as e:
            logger.error(f"Simulation Error: {e}")
        
        iteration += 1
        await asyncio.sleep(SIMULATION_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(run_simulation())
    except KeyboardInterrupt:
        logger.warning("Simulation worker stopped.")
