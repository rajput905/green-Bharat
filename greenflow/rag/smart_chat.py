"""
GreenFlow AI – Smart Chat Reasoning Engine
===========================================
Enhanced RAG system that integrates:
1. Real-time telemetry (Live Data)
2. CO2 Forecasting (Prediction Engine)
3. Multi-modal Risk Assessment (Risk Engine)
4. Environmental Policy Documents (Vector Store)
"""

import os
import time
from typing import Dict, Any, List, Optional
from openai import OpenAI
import google.generativeai as genai
from loguru import logger
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import AsyncSessionFactory, AnalyticsRecord, CO2PredictionLog, EnvironmentalRisk
# rag_engine is now loaded lazily via get_rag_engine() inside methods

class SmartContextBuilder:
    """Consolidates live, predicted, and risk data into a single context."""
    
    @staticmethod
    async def get_live_context() -> Dict[str, Any]:
        """Fetches latest metrics across all engines."""
        results: Dict[str, Any] = {"telemetry": None, "prediction": None, "risk": None}
        try:
            async with AsyncSessionFactory() as session:
                # 1. Latest Analytics
                res_a = await session.execute(select(AnalyticsRecord).order_by(desc(AnalyticsRecord.timestamp)).limit(1))
                results["telemetry"] = res_a.scalars().first()
                
                # 2. Latest Prediction
                res_p = await session.execute(select(CO2PredictionLog).order_by(desc(CO2PredictionLog.timestamp)).limit(1))
                results["prediction"] = res_p.scalars().first()
                
                # 3. Latest Risk
                res_r = await session.execute(select(EnvironmentalRisk).order_by(desc(EnvironmentalRisk.id)).limit(1))
                results["risk"] = res_r.scalars().first()
        except Exception as e:
            logger.error(f"Context Builder Error: {e}")
            
        return results

class DataSummaryGenerator:
    """Formats raw database records into human-readable data summaries for the LLM."""
    
    @staticmethod
    def generate_summary(context: Dict[str, Any]) -> str:
        t = context.get("telemetry")
        p = context.get("prediction")
        r = context.get("risk")
        
        summary = "CURRENT ENVIRONMENTAL STATE:\n"
        if t:
            summary += f"- CO2 Level: {t.co2 if hasattr(t, 'co2') else t.aqi}ppm (AQI proxy)\n"
            summary += f"- Humidity: {t.humidity}%\n"
            summary += f"- Traffic Speed: {t.avg_speed_kmh if hasattr(t, 'avg_speed_kmh') else 'N/A'}km/h\n"
        
        summary += "\nFORECASTS & TRENDS:\n"
        if p:
            summary += f"- 30m Prediction: {p.predicted_co2_30min:.1f}ppm\n"
            summary += f"- Trend: {p.trend} (Confidence: {p.confidence:.2f})\n"
        
        summary += "\nRISK ASSESSMENT:\n"
        if r:
            summary += f"- Risk Level: {r.level} (Score: {r.risk_score})\n"
            summary += f"- Recommendation: {r.recommendation}\n"
            
        return summary

class SmartChatEngine:
    """Orchestrates RAG retrieval and real-time data reasoning."""

    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.google_key = os.getenv("GOOGLE_API_KEY")
        
        self.openai_client = OpenAI(api_key=self.openai_key) if self.openai_key else None
        
        if self.google_key:
            genai.configure(api_key=self.google_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.gemini_model = None

    async def ask(self, query: str) -> str:
        """Main entry point for intelligent chat reasoning."""
        # 1. Retrieve Policy Data (RAG)
        from rag.engine import get_rag_engine
        engine = get_rag_engine()
        policy_docs = engine.retrieve(query, top_k=3)
        context_docs = "\n\n".join(policy_docs)

        # 2. Retrieve Live/Predicted Data
        data_context = await SmartContextBuilder.get_live_context()
        data_summary = DataSummaryGenerator.generate_summary(data_context)

        # 3. Construct System Prompt
        system_prompt = f"""
You are the GreenFlow AI Smart Assistant. You specialize in real-time environmental reasoning.

{data_summary}

ENVIRONMENTAL POLICIES & KNOWLEDGE:
{context_docs}

INSTRUCTIONS:
- Use THE DATA SUMMARIES to explain "why" or "what will happen".
- Use THE POLICIES for regulatory context or standard procedures.
- If data is missing or stable, report it accurately.
- Keep answers professional, data-backed, and concise (max 3-4 sentences).
"""

        # 4. Execute Query (Prefer Gemini if available, fallback to OpenAI)
        try:
            if self.google_key and self.gemini_model:
                logger.info("Using Gemini for smart chat reasoning")
                response = self.gemini_model.generate_content(
                    f"{system_prompt}\n\nUser Question: {query}"
                )
                return response.text.strip()
            
            elif self.openai_client:
                logger.info("Using OpenAI for smart chat reasoning")
                response = self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.3
                )
                return response.choices[0].message.content.strip()
            
            else:
                return "AI provider not configured. Please check your GOOGLE_API_KEY or OPENAI_API_KEY."

        except Exception as e:
            logger.error(f"Smart Chat Error: {e}")
            return f"I'm sorry, I encountered an error while analyzing the data: {str(e)}"

# Singleton instance
smart_chat = SmartChatEngine()
