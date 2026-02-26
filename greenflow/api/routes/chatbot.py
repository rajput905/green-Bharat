from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import os

from database.session import get_db, AnalyticsRecord
from api.schemas.analytics import ChatRequest, ChatResponse
from rag.smart_chat import smart_chat

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """
    POST /chat - Interact with the AI using real-time and predictive reasoning.
    The AI uses live sensor data, CO2 predictions, and risk assessments.
    """
    answer = await smart_chat.ask(request.query)
    return ChatResponse(answer=answer)
