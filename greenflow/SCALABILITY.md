# GreenFlow AI: Scalability Architecture

This document provides a technical overview of how the GreenFlow AI system scales to handle massive real-time data loads, designed for the hackathon judges.

## 1. Real-Time Streaming (Pathway)
- **Pathway Engine**: Unlike traditional batch processors, Pathway maintains an incremental computation graph. This means it only processes *changes* (deltas), making it highly efficient as throughput increases.
- **Horizontal Scaling**: Pathway can be integrated with **Apache Kafka** or **Redpanda**. By partitioning Kafka topics, we can run multiple Pathway workers to process geographical data (e.g., North vs. South city data) in parallel.
- **Memory Efficiency**: The engine specifically optimizes stateful windows (like the 10-minute AQI average) by discarding old data points automatically, ensuring memory usage stays constant regardless of how long the system runs.

## 2. API Backend (FastAPI)
- **Async I/O**: Every endpoint in our FastAPI layer is `async`. This allows the server to handle thousands of concurrent requests while waiting for database or LLM responses without blocking the main thread.
- **Microservices**: By containerizing the API separately from the processing engine, we can scale the API independently using a load balancer (like Nginx or Kubernetes Service) to meet high dashboard traffic.

## 3. Persistent Storage (PostgreSQL)
- **Write-Optimized**: The Pathway engine uses high-performance bulk-write connectors to PostgreSQL.
- **Time-Series Scaling**: For production, we can swap standard PostgreSQL for **TimescaleDB** or use table partitioning by `timestamp` to ensure query speeds remain fast even with millions of rows.

## 4. AI & RAG (Retrieval Augmented Generation)
- **Vector Store**: Currently using ChromaDB/Pathway for simplified RAG. To scale to millions of documents, we can integrate **Pinecone** or **Milvus** for distributed vector search.
- **Hybrid Context**: Our custom RAG logic fetches only the "latest snapshot" for the LLM prompt, keeping prompt sizes small and token costs low while maintaining high accuracy.

## ⚖️ Scalability Summary
| Component | Scaling Strategy | Tooling |
| :--- | :--- | :--- |
| **Ingestion** | Parallel Partitioning | Kafka / Redpanda |
| **Logic** | Distributed Graph Processing | Pathway Workers |
| **API** | Replicated Pods | Docker / Kubernetes |
| **Storage** | Table Partitioning | PostgreSQL / TimescaleDB |
