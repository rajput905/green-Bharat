"""
GreenFlow AI – Query / RAG Route
==================================
Exposes the RAG engine via REST.  Accepts a natural-language question
and returns an AI-generated answer grounded in indexed documents.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import QueryLog, get_db
# rag_engine is now loaded lazily via get_rag_engine() inside routes

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, example="What is the current CO₂ level?")
    top_k: int = Field(4, ge=1, le=10, description="Number of context chunks to retrieve")


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    query: str
    latency_ms: float


class IndexRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Text to index into the vector store")
    metadata: dict = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=QueryResponse,
    summary="Ask the GreenFlow AI a question (RAG)",
)
async def query(
    req: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """
    Run a full RAG pipeline:
      1. Retrieve relevant chunks from ChromaDB
      2. Feed into OpenAI LLM with built-in context
      3. Return grounded answer
    """
    try:
        from rag.engine import get_rag_engine
        engine = get_rag_engine()
        result = await engine.query(req.question, top_k=req.top_k)
    except Exception as exc:
        logger.exception("RAG query failed: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM/RAG error: {exc}",
        )

    # Persist query log (best-effort)
    try:
        log = QueryLog(
            query_text=req.question,
            answer=result["answer"],
            latency_ms=result["latency_ms"],
        )
        db.add(log)
        await db.commit()
    except Exception as exc:
        logger.warning("Failed to persist query log: {}", exc)

    return QueryResponse(**result)


@router.post(
    "/index",
    status_code=status.HTTP_201_CREATED,
    summary="Index a document into the RAG vector store",
)
async def index_document(req: IndexRequest) -> dict:
    """
    Embed and store a document chunk so it can be retrieved in future queries.
    """
    try:
        from rag.engine import get_rag_engine
        engine = get_rag_engine()
        ids = engine.index_document(req.text, metadata=req.metadata)
    except Exception as exc:
        logger.exception("Indexing failed: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing error: {exc}",
        )
    return {"indexed_chunks": len(ids), "ids": ids}
