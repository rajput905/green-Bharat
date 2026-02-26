"""
GreenFlow AI – Retrieval-Augmented Generation (RAG) Engine
============================================================
Handles:
  1. Document embedding & indexing into ChromaDB
  2. Similarity search (retrieve top-k chunks)
  3. Prompt assembly and LLM call via OpenAI

The RAGEngine is designed to be instantiated once (singleton) and reused
across requests.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, cast

from sqlalchemy import text
from loguru import logger


from config import settings
from database.session import AsyncSessionFactory

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _doc_id(text: str) -> str:
    """Deterministic document ID from content hash."""
    # Use cast or explicit slice if linter is confused
    digest = hashlib.sha256(text.encode()).hexdigest()
    # Use loop to avoid subscript errors in this environment
    return "".join([c for i, c in enumerate(str(digest)) if i < 16])


def _chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> list[str]:
    """
    Sliding-window chunker.  Splits text into overlapping segments so long
    documents are fully captured in the vector store.
    """
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = "".join([c for i, c in enumerate(str(text)) if start <= i < end])
        chunks.append(str(chunk))
        start += max_chars - overlap
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# RAG Engine
# ─────────────────────────────────────────────────────────────────────────────

class RAGEngine:
    """
    Singleton RAG engine backed by ChromaDB for retrieval and
    OpenAI for generation.

    Typical usage::

        engine = RAGEngine()
        engine.index_document("Solar panel efficiency report…", metadata={"source": "sensor_42"})
        answer = await engine.query("What is the current CO₂ level?")
    """

    _instance: RAGEngine | None = None

    def __new__(cls) -> "RAGEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialised:
            return
        self._initialised = True
        self._ready = False

    def _lazy_init(self) -> None:
        if self._ready:
            return
        
        logger.info("🔧 Initialising RAGEngine (Lazy)…")

        # Lazy imports for heavy dependencies
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
        from langchain_core.tools import Tool

        # ── Vector store (ChromaDB HttpClient for remote / Client for local dev)
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self._chroma = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        except Exception:
            logger.warning("ChromaDB server not reachable – falling back to in-process store")
            import chromadb
            self._chroma = chromadb.Client()

        self._collection = self._chroma.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

        # ── Embeddings & LLM
        if settings.google_api_key:
            logger.info("Using Gemini for embeddings and LLM")
            self._embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=settings.google_api_key,
            )
            self._llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                temperature=settings.openai_temperature,
                google_api_key=settings.google_api_key,
            )
        else:
            logger.info("Using OpenAI for embeddings and LLM")
            self._embeddings = OpenAIEmbeddings(
                model=settings.openai_embedding_model,
                openai_api_key=settings.openai_api_key,
            )
            self._llm = ChatOpenAI(
                model=settings.openai_model,
                temperature=settings.openai_temperature,
                max_tokens=settings.openai_max_tokens,
                openai_api_key=settings.openai_api_key,
            )
        
        self._ready = True
        logger.info("✅ RAGEngine ready | collection={}", settings.chroma_collection)

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index_document(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """
        Embed *text* and upsert into the vector store.
        Returns the list of chunk IDs that were created/updated.
        """
        self._lazy_init()
        chunks = _chunk_text(text)
        ids = []

        for chunk in chunks:
            doc_id = _doc_id(chunk)
            embedding = self._embeddings.embed_query(chunk)
            meta = {"indexed_at": float(time.time())}
            if isinstance(metadata, dict):
                # Iterate keys explicitly to avoid .items() inference issues
                for k in metadata.keys():
                    meta[str(k)] = metadata[k]
            
            self._collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[meta],
            )
            ids.append(doc_id)

        logger.debug("📥 Indexed {} chunk(s) | ids={}", len(ids), ids)
        return ids

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 4) -> list[str]:
        """
        Embed *query* and return the top-k most similar document chunks.
        """
        self._lazy_init()
        q_embedding = self._embeddings.embed_query(query)
        results = self._collection.query(
            query_embeddings=[q_embedding],
            n_results=min(top_k, max(self._collection.count(), 1)),
        )
        docs: list[str] = results.get("documents", [[]])[0]
        query_snip = "".join([c for i, c in enumerate(str(query)) if i < 60])
        logger.debug("🔍 Retrieved {} chunks for query='{}'", len(docs), query_snip)
        return docs

    # ── Agentic Tools ─────────────────────────────────────────────────────────

    def _get_vector_tool(self) -> Tool:
        return Tool(
            name="Environmental_Knowledge_Base",
            func=lambda q: "\n".join(self.retrieve(q)),
            description="Search the environmental reports and sustainability documentation. Useful for general knowledge, ISO standards, and historical reports."
        )

    async def _query_live_db(self, query_str: str) -> str:
        """Execute a read-only SQL query against the analytics database."""
        # Simple heuristic to prevent destructive queries for safety
        if any(word in query_str.upper() for word in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER"]):
            return "Error: Only read-only queries are allowed."
        
        try:
            async with AsyncSessionFactory() as session:
                # Use SQL to get trends
                # Example: "Get the average risk score for the last 5 minutes"
                result = await session.execute(text(query_str))
                rows = result.all()
                return str([dict(r._mapping) for r in rows])
        except Exception as e:
            logger.error(f"SQL Tool Error: {e}")
            return f"Database Error: {str(e)}"
        
        return "No data found for this specific query."

    def _get_db_tool(self) -> Tool:
        return Tool(
            name="Live_Analytics_Database",
            func=self._query_live_db,
            description="Query the live PostgreSQL analytics database. Useful for real-time trends, average risk scores, and current environmental metrics. Use SQL SELECT statements. Tables: analytics_records, system_alerts."
        )

    # ── Generation (Agentic Loop) ─────────────────────────────────────────────

    async def query(self, user_query: str, top_k: int = 4) -> dict[str, Any]:
        """
        Execute an agentic reasoning loop to answer the user query.
        """
        self._lazy_init()
        t0 = time.perf_counter()


        # Lazy imports for agent
        try:
            from langchain.agents import AgentExecutor, create_openai_tools_agent
            from langchainhub import hub
        except ImportError:
            logger.error("LangChain Agent dependencies missing locally.")
            return {"answer": "Agent system unavailable locally. Please use Docker for full features.", "sources": [], "latency_ms": 0}

        # Step 1 – Create Agent
        tools = [self._get_vector_tool(), self._get_db_tool()]
        prompt = hub.pull("hwchase17/openai-tools-agent")
        
        agent = create_openai_tools_agent(self._llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        system_prompt = (
            "You are GreenFlow AI, an expert in environmental data analysis, "
            "carbon accounting, and sustainability intelligence. "
            "Answer the user's question using ONLY the provided context. "
            "If the context does not contain the answer, say so honestly."
        )

        # Gemini specific handling if needed (Gemini often uses 'chat-bison' or 'gemini-pro')
        # create_openai_tools_agent works with ChatGoogleGenerativeAI too if it supports tool calling
        try:
            response = await agent_executor.ainvoke({"input": user_query})
            answer = response["output"]
        except Exception as e:
            logger.error(f"Agent Execution Error: {e}")
            # Fallback to simple retrieval if agent loop fails
            fallback_chunks = self.retrieve(user_query, top_k=1)
            answer = f"Agent reasoning interrupted. Summary: {fallback_chunks[0] if fallback_chunks else 'No data found.'}"

        # Use format to avoid round() overload issues
        raw_latency = (time.perf_counter() - t0) * 1000
        latency_ms = float(f"{raw_latency:.1f}")
        logger.info("🤖 Agentic query completed | latency={}ms", latency_ms)

        return {
            "answer": answer,
            "sources": ["Live DB", "Knowledge Base"],
            "query": user_query,
            "latency_ms": latency_ms,
        }


_rag_engine: RAGEngine | None = None

def get_rag_engine() -> RAGEngine:
    """Return the RAG engine singleton, initialising on first call."""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
