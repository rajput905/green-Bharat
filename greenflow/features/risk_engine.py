"""
GreenFlow AI – Environmental Risk Scoring Engine
================================================
Calculates streaming risk scores based on multiple environmental factors.
"""

import time
from typing import Dict, Any

from loguru import logger

# ─────────────────────────────────────────────────────────────────────────────
# 1. Risk Formula Constants
# ─────────────────────────────────────────────────────────────────────────────

# Weights (must sum to 1.0)
WEIGHT_CO2 = 0.5
WEIGHT_TEMP = 0.2
WEIGHT_CARBON = 0.2
WEIGHT_TRAFFIC = 0.1

# Normalization baselines
BASE_CO2 = 400.0   # Standard background CO2
MAX_CO2 = 1000.0   # High risk threshold

BASE_TEMP = 25.0   # Comfortable temp
MAX_TEMP = 45.0    # Extreme heat threshold

# ─────────────────────────────────────────────────────────────────────────────
# 2. Risk Calculation & Classification
# ─────────────────────────────────────────────────────────────────────────────

def compute_risk_score(co2: float, temp: float, carbon_score: float, traffic_impact: float = 0.0) -> float:
    """
    Computes a risk score from 0-100 based on environmental inputs.
    """
    # Normalize inputs (0-1)
    # CO2: 400->0, 1000->1
    n_co2 = max(0.0, min(1.0, (co2 - BASE_CO2) / (MAX_CO2 - BASE_CO2)))
    
    # Temp: 25->0, 45->1
    n_temp = max(0.0, min(1.0, (temp - BASE_TEMP) / (MAX_TEMP - BASE_TEMP)))
    
    # Carbon Score (already 0-100 in our system, normalize to 0-1)
    n_carbon = carbon_score / 100.0
    
    # Traffic Impact (0-1)
    n_traffic = max(0.0, min(1.0, traffic_impact))

    # Weighted Sum
    total_risk = (
        (n_co2 * WEIGHT_CO2) +
        (n_temp * WEIGHT_TEMP) +
        (n_carbon * WEIGHT_CARBON) +
        (n_traffic * WEIGHT_TRAFFIC)
    ) * 100.0

    # Use float formatting to avoid round() overload confusion
    final_score = float(max(0.0, min(100.0, total_risk)))
    return float(f"{final_score:.2f}")

def classify_risk(score: float, co2: float, temp: float) -> Dict[str, Any]:
    """
    Classifies risk score and provides contextual recommendations.
    """
    if score <= 30:
        level = "SAFE"
        rec = "Air quality is excellent. Ideal conditions for outdoor activities and natural ventilation."
    elif score <= 60:
        level = "MODERATE"
        rec = "Moderate risk detected. Sensitive individuals should limit prolonged outdoor exertion."
    elif score <= 80:
        level = "HIGH"
        rec = "Significant environmental stress. Close windows, activate air filtration, and reduce energy consumption."
    else:
        level = "CRITICAL"
        rec = "Hazardous conditions! Evacuate non-essential personnel, activate emergency HVAC protocols, and seek filtered environments."

    # Contextual override/addition for extreme heat or CO2
    if temp > 40.0:
        rec += " Extreme heat alert: Ensure hydration and active cooling."
    if co2 > 800.0:
        rec += " High CO2 alert: Increase mechanical ventilation immediately."

    return {
        "risk_score": score,
        "level": level,
        "recommendation": rec
    }

# ─────────────────────────────────────────────────────────────────────────────
# 3. Singleton State (For API retrieval of latest scores)
# ─────────────────────────────────────────────────────────────────────────────

# In a real distributed system, this would be in Redis or the DB.
# For this requirement, we keep a small in-memory buffer of the last 100 scores.
_risk_history = []

def record_risk(risk_data: Dict[str, Any]):
    """Stores the latest risk assessment and maintains the buffer."""
    _risk_history.append(risk_data)
    if len(_risk_history) > 100:
        _risk_history.pop(0)

def get_latest_risk() -> Dict[str, Any]:
    """Retrieves the absolute latest risk score."""
    if not _risk_history:
        return {
            "risk_score": 0.0,
            "level": "SAFE",
            "recommendation": "Initializing sensor network... Data incoming."
        }
    return _risk_history[-1]
