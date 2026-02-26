"""
GreenFlow AI – AI Decision Intelligence Engine
==============================================
Generates real-time actionable recommendations for smart city management 
using environmental analysis and LLM-powered insights.
"""

import os
import json
from typing import Dict, Any, List
from openai import OpenAI
from loguru import logger
from dotenv import load_dotenv

# Load environment
load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# 1. Decision Logic Constants
# ─────────────────────────────────────────────────────────────────────────────

ACTION_LEVELS = {
    "SAFE": "advisory",
    "MODERATE": "advisory",
    "HIGH": "warning",
    "CRITICAL": "emergency"
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. Recommendation Engine
# ─────────────────────────────────────────────────────────────────────────────

def generate_recommendation(context_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes environmental context and generates multi-modal recommendations.
    
    context_data = {
        "current_co2": float,
        "predicted_co2": float,
        "risk_level": str,
        "trend": str
    }
    """
    co2 = context_data.get("current_co2", 400.0)
    pred_co2 = context_data.get("predicted_co2", 400.0)
    risk = context_data.get("risk_level", "SAFE")
    trend = context_data.get("trend", "stable")

    level = ACTION_LEVELS.get(risk, "advisory")
    recommendations = []

    # ── Heuristic Action Selection ──

    # Traffic Management
    if risk in ["HIGH", "CRITICAL"] or (pred_co2 > 600 and trend == "increasing"):
        recommendations.append("Traffic Diversion: Reroute heavy vehicles from central districts.")
    
    # Ventilation & Industry
    if co2 > 500 or pred_co2 > 550:
        recommendations.append("HVAC Alert: Increase mechanical ventilation in public squares and schools.")
    
    # Public Advisory
    if risk == "MODERATE":
        recommendations.append("Public Advisory: Voluntary reduction of private vehicle usage suggested.")
    elif risk in ["HIGH", "CRITICAL"]:
        recommendations.append("Policy Suggestion: Implement temporary Green-Zone restrictions.")

    # Emergency Actions
    if risk == "CRITICAL":
        recommendations.append("Emergency Alert: Deploy mobile air purification units to high-density zones.")

    # ── LLM Explanation ──
    explanation = _get_llm_explanation(co2, pred_co2, risk, trend)

    return {
        "action_level": level,
        "recommendations": recommendations if recommendations else ["Maintain current sustainability protocols."],
        "explanation": explanation
    }

def _get_llm_explanation(co2: float, pred: float, risk: str, trend: str) -> str:
    """Uses OpenAI to generate a human-friendly narrative of the decision."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return f"System suggests actions based on {risk} status with {trend} CO2 trend ({co2}ppm -> {pred}ppm)."

    try:
        client = OpenAI(api_key=api_key)
        prompt = (
            f"You are a Smart City Decision Analyst. "
            f"Context: Current CO2 {co2}ppm, Predicted CO2 in 30m is {pred}ppm, "
            f"Current Risk Level: {risk}, Trend: {trend}. "
            f"In 2 sentences, explain why specific city management actions are needed."
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM Explanation failed: {e}")
        return f"Automated analysis indicates {risk} level due to {trend} CO2 levels reaching {pred}ppm."
