"""
GreenFlow AI – What-If Simulation Router
==========================================
Exposes POST /api/v1/simulate for smart-city scenario analysis.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional
from loguru import logger

from database.session import get_db, AnalyticsRecord, CO2PredictionLog, EnvironmentalRisk
from features.simulation_engine import SimulationEngine, SimulationInput, simulation_engine

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class SimulateRequest(BaseModel):
    """
    What-If scenario inputs. All percentages are in range [0, 100].
    Omitting a lever is treated as 0% (no change).
    """
    traffic_reduction_pct: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Reduce road traffic volume by this percentage (0-100)."
    )
    ventilation_increase_pct: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Increase urban ventilation / air exchange rate by this percentage."
    )
    industry_reduction_pct: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Reduce industrial emissions by this percentage (0-100)."
    )

    # Optional manual baseline overrides
    baseline_co2:  Optional[float] = Field(None, gt=0, description="Override baseline CO₂ in ppm.")
    baseline_risk: Optional[float] = Field(None, ge=0, le=100, description="Override baseline risk score.")

    class Config:
        json_schema_extra = {
            "example": {
                "traffic_reduction_pct": 30,
                "ventilation_increase_pct": 20,
                "industry_reduction_pct": 15,
            }
        }


class SimulateResponse(BaseModel):
    """
    Simulation result - primary contract matching the required schema.
    """
    new_predicted_co2:  float
    new_risk_score:     float
    alert_level:        str
    impact_summary:     str

    # Extended breakdown (bonus fields)
    baseline_co2:            float
    baseline_risk:           float
    co2_reduction_ppm:       float
    co2_reduction_pct:       float
    risk_reduction:          float
    traffic_co2_saved:       float
    industry_co2_saved:      float
    ventilation_co2_diluted: float


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/", response_model=SimulateResponse, summary="Run a What-If simulation")
async def run_simulation(
    body: SimulateRequest,
    db: AsyncSession = Depends(get_db),
) -> SimulateResponse:
    """
    **What-If Simulation Engine**

    Accepts three city-level intervention levers and returns realistic
    projections of CO₂ concentration, risk score, and alert level.

    The engine:
    1. Fetches live baselines from the database (latest analytics record,
       CO₂ prediction, and risk assessment).
    2. Applies diminishing-returns emission models calibrated to IPCC AR6
       urban source shares.
    3. Returns a complete impact breakdown and natural-language summary.
    """
    logger.info(
        "🔧 Simulate request | traffic={:.0f}% ventil={:.0f}% industry={:.0f}%",
        body.traffic_reduction_pct,
        body.ventilation_increase_pct,
        body.industry_reduction_pct,
    )

    # ── Fetch live baselines from DB ─────────────────────────────────────────
    live_co2:  Optional[float] = None
    live_aqi:  Optional[float] = None
    live_risk: Optional[float] = None
    live_temp: Optional[float] = None

    try:
        # Latest analytics record  (has AQI, temp, risk_score)
        res = await db.execute(
            select(AnalyticsRecord)
            .order_by(desc(AnalyticsRecord.timestamp))
            .limit(1)
        )
        latest_rec = res.scalars().first()
        if latest_rec:
            live_aqi  = float(latest_rec.aqi)  if latest_rec.aqi  is not None else None
            live_temp = float(latest_rec.temp)  if latest_rec.temp is not None else None
            live_risk = float(latest_rec.risk_score) if latest_rec.risk_score is not None else None

        # Latest CO₂ prediction (most accurate CO₂ reading)
        res2 = await db.execute(
            select(CO2PredictionLog)
            .order_by(desc(CO2PredictionLog.timestamp))
            .limit(1)
        )
        latest_pred = res2.scalars().first()
        if latest_pred:
            live_co2 = float(latest_pred.current_co2)

        # Latest risk assessment (alternative risk source)
        if live_risk is None:
            res3 = await db.execute(
                select(EnvironmentalRisk)
                .order_by(desc(EnvironmentalRisk.timestamp))
                .limit(1)
            )
            latest_env_risk = res3.scalars().first()
            if latest_env_risk:
                live_risk = float(latest_env_risk.risk_score)

    except Exception as exc:
        logger.warning("DB fetch failed during simulation – using defaults. Error: {}", exc)

    # ── Build input model ────────────────────────────────────────────────────
    sim_input = SimulationInput(
        traffic_reduction_pct    = body.traffic_reduction_pct,
        ventilation_increase_pct = body.ventilation_increase_pct,
        industry_reduction_pct   = body.industry_reduction_pct,
        baseline_co2             = body.baseline_co2,
        baseline_risk            = body.baseline_risk,
    )

    # ── Run simulation ───────────────────────────────────────────────────────
    try:
        result = simulation_engine.simulate(
            inp       = sim_input,
            live_co2  = live_co2,
            live_aqi  = live_aqi,
            live_risk = live_risk,
            live_temp = live_temp,
        )
    except Exception as exc:
        logger.error("Simulation engine error: {}", exc)
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}")

    return SimulateResponse( # type: ignore
        new_predicted_co2        = result.new_predicted_co2,
        new_risk_score           = result.new_risk_score,
        alert_level              = result.alert_level,
        impact_summary           = result.impact_summary,
        baseline_co2             = result.baseline_co2,
        baseline_risk            = result.baseline_risk,
        co2_reduction_ppm        = result.co2_reduction_ppm,
        co2_reduction_pct        = result.co2_reduction_pct,
        risk_reduction           = result.risk_reduction,
        traffic_co2_saved        = result.traffic_co2_saved,
        industry_co2_saved       = result.industry_co2_saved,
        ventilation_co2_diluted  = result.ventilation_co2_diluted,
    )
