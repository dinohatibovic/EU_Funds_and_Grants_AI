# EU Funds & Grants AI  
Modularni AI sistem za grantove, fondove, finansijske analize i RAG pretragu.
# EU Funds & Grants AI

EU Funds & Grants AI is a modular, retrieval-augmented, agent-based system designed to ingest, normalize, index, and query information about EU funds and grant opportunities.

The system is built to be:
- Modular and extensible
- Audit-friendly and transparent
- Ready for API, SDK, CLI, and UI integrations
- Suitable for grants, research, and production deployments

---

## 1. High-level architecture

The system is organized into several logical layers:

1. **Ingestion Layer**  
   - Scrapes, loads, or fetches raw data from web pages, PDFs, and APIs.
   - Produces canonical JSON structures for downstream processing.

2. **Preprocessing & Normalization**  
   - Cleans and standardizes raw text and metadata.
   - Normalizes dates, currencies, and text fields.

3. **Embedding & Vectorization**  
   - Uses SentenceTransformer models to convert text into dense vector embeddings.
   - Centralized in a single `EmbeddingClient` class.

4. **Vector Database & Indexing**  
   - Stores embeddings and metadata in ChromaDB.
   - Supports similarity search and filtered retrieval.

5. **RAG Pipeline**  
   - Combines vector search with contextual answer generation.
   - Provides a high-level `RAGPipeline` interface.

6. **Agent Orchestrator**  
   - Coordinates multi-step workflows and reasoning.
   - Wraps the RAG pipeline into higher-level tasks.

7. **SDK Layer**  
   - Exposes a simple, stable interface for external applications.
   - Intended for use by other services, CLIs, or UIs.

8. **Utilities & Logging**  
   - Provides logging and shared helpers.

---

## 2. Project structure

```text
EU_Funds_and_Grants_AI/
│
├── README.md
├── .env
├── __init__.py
│
├── ingestion/
│   ├── __init__.py
│   ├── web_scraper.py
│   ├── pdf_loader.py
│   └── api_loader.py
│
├── preprocessing/
│   ├── __init__.py
│   └── normalizer.py
│
├── embeddings/
│   ├── __init__.py
│   └── embedding_client.py
│
├── vector_db/
│   ├── __init__.py
│   └── chroma_client.py
│
├── rag/
│   ├── __init__.py
│   └── pipeline.py
│
├── agent/
│   ├── __init__.py
│   └── main_agent.py
│
├── sdk/
│   ├── __init__.py
│   └── client.py
│
└── utils/
    ├── __init__.py
    └── logger.py

