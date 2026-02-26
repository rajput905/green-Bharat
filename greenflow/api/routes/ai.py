
"""
GreenFlow AI – AI Recommendation Router
========================================
Provides endpoints for AI-driven environmental recommendations.
"""

import os
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from loguru import logger
from config import settings

router = APIRouter()

# OpenAI Client (Singleton for this module)
_client: OpenAI | None = None

def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
        if not api_key or "placeholder" in api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        _client = OpenAI(api_key=api_key)
    return _client

@router.get("/recommend", summary="Get AI-driven environmental recommendation")
async def ai_recommend():
    """
    Generates a smart recommendation for city authorities based on current conditions.
    """
    try:
        client = get_openai_client()
        prompt = """
        You are an environmental AI assistant expert.
        Current system status: CO2 rising, environmental risk is moderate.
        Provide a short, professional, and actionable environmental recommendation for a city authority.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )

        answer = response.choices[0].message.content
        return {"recommendation": answer}

    except Exception as e:
        logger.error(f"AI Recommendation Error: {e}")
        return {"recommendation": f"AI Intelligence Service Error: {str(e)}"}
