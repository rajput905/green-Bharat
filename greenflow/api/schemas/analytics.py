from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class AnalyticsBase(BaseModel):
    timestamp: float
    city: Optional[str]
    temp: Optional[float]
    humidity: Optional[float]
    aqi: Optional[int]
    avg_aqi_10m: Optional[float]
    risk_score: Optional[float]
    safety_level: Optional[str]

class AnalyticsResponse(AnalyticsBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class RiskScoreResponse(BaseModel):
    current_score: float
    safety_level: str
    timestamp: float

class PredictionResponse(BaseModel):
    timestamp: float
    actual_aqi: Optional[int]
    predicted_aqi: float
    delta: float

class CO2PredictionResponse(BaseModel):
    timestamp: float
    current_co2: float
    predicted_co2_30min: float
    trend: str
    confidence: float

class AIRecommendationResponse(BaseModel):
    action_level: str
    recommendations: List[str]
    explanation: str

class AlertResponse(BaseModel):
    timestamp: float
    risk_score: float
    alert_message: str
    severity: str

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    data_points: Optional[dict] = None
