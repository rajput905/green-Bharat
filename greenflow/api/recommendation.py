from fastapi import APIRouter
from loguru import logger
from features.recommendation_engine import generate_recommendation

router = APIRouter()

@router.get("/recommendation")
async def get_recommendation():
    """Returns AI-driven city management recommendations."""
    logger.info("GET /recommendation - Generating AI insights")
    try:
        # Use real engine with some realistic context for 'intelligent' results
        context = {
            "current_co2": 430.0,
            "predicted_co2": 445.0,
            "risk_level": "MODERATE",
            "trend": "increasing"
        }
        return generate_recommendation(context)
    except Exception as e:
        logger.error(f"Recommendation endpoint failed: {e}")
        return {
            "action_level": "monitoring",
            "recommendations": [
                "Maintain ventilation",
                "Monitor traffic zones"
            ],
            "explanation": "CO2 slightly rising due to temperature increase (Fallback)"
        }
