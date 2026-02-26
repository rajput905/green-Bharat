from fastapi import APIRouter
from loguru import logger

router = APIRouter()

@router.get("/prediction/co2")
async def get_prediction():
    """Returns the latest CO2 trend prediction."""
    logger.info("GET /prediction - Generating CO2 forecast")
    # Intelligent mock data as requested for production-ready baseline
    return {
        "current_co2": 430,
        "predicted_co2_30min": 445,
        "trend": "increasing",
        "confidence": 0.87
    }
