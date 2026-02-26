
"""
GreenFlow AI – RAG + OpenAI Chatbot Service
Fully working version
"""

import os
from typing import Optional
from openai import OpenAI
from loguru import logger
from rag.engine import get_rag_engine

class ChatbotService:
    def __init__(self, api_key: str | None = None, city_name: str = "New Delhi"):
        # Use provided key or fall back to environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.city_name = city_name
        self.engine = get_rag_engine()
        # Initialize client only if key is available
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    async def get_answer(self, query: str, latest_snapshot: Optional[dict] = None) -> str:
        """
        Try RAG first → if fails → fallback to OpenAI
        """
        try:
            # 🟢 TRY RAG ENGINE FIRST
            result = await self.engine.query(query)
            if result and "answer" in result:
                return result["answer"]
        except Exception as e:
            logger.error(f"RAG Engine failed: {e}")

        # 🔥 FALLBACK TO OPENAI (IMPORTANT)
        if not self.client:
             logger.warning("Chatbot service: OpenAI client not initialized (no API key).")
             return "AI temporarily unavailable. Check API key configuration."
             
        try:
            prompt = f"""
You are GreenFlow AI environmental assistant.

City: {self.city_name}
User question: {query}

Give short smart environmental recommendation and risk analysis.
"""
            if self.client:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=250,
                )
                return response.choices[0].message.content.strip()
            return "AI temporarily unavailable."
        except Exception as e:
            logger.error(f"OpenAI fallback failed: {e}")
            return f"I'm sorry, I encountered an issue while generating an AI answer: {str(e)}"