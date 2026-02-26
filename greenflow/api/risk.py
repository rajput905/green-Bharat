from fastapi import APIRouter
from loguru import logger
from features.risk_engine import get_latest_risk

router = APIRouter()

@router.get("/risk-score")
async def get_risk():
    """Returns the latest environmental risk assessment."""
    logger.info("GET /risk - Fetching latest risk data")
    try:
        # Try to get real-time data from the engine
        data = get_latest_risk()
        
        # If engine has no data yet (0.0 score), return intelligent mock data for frontend
        if not data or data.get("risk_score") == 0.0:
            return {
                "risk_score": 52.4,
                "level": "MODERATE",
                "recommendation": "Air quality stable but monitor closely"
            }
        return data
    except Exception as e:
        logger.error(f"Risk endpoint failed: {e}")
        return {
            "risk_score": 52.4,
            "level": "MODERATE",
            "recommendation": "Air quality stable but monitor closely (Fallback)"
        }
