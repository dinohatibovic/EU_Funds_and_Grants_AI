# FinAssistBH Architecture Blueprint

**Version:** 2.2.1
**Owner:** Dino Hatibović
**Production status:** Live

## System overview

FinAssistBH is organized into isolated application layers with explicit
dependency boundaries.

```text
Frontend
  |
  | HTTPS and JSON
  v
FastAPI backend
  |
  +--> authentication and PostgreSQL
  |
  +--> AI service bridge
          |
          +--> Gemini embeddings
          +--> ChromaDB retrieval
          +--> deterministic reranking
          +--> Gemini answer generation
```

## Layer 4: Frontend

Location:

```text
frontend/src/
```

Responsibilities:

- static GitHub Pages user interface
- registration and login
- JWT token use
- search requests
- AI-answer requests
- cold-start progress handling

The frontend communicates with the backend only through HTTP.

## Layer 3: Backend and orchestration

Location:

```text
backend/app/
```

Structure:

```text
api/       FastAPI routes and Pydantic schemas
core/      configuration, database, JWT, rate limiting
services/  bridge to the AI layer
main.py    application lifecycle and router registration
```

Production lifecycle uses:

```text
FastAPI(lifespan=lifespan)
```

The lifespan startup sequence is:

```text
init_user_db
load_grants_cache
init_ai_clients
auto_ingest_grants
```

If the configured production database cannot be initialized, startup switches
to the SQLite fallback before continuing.

## Layer 2: AI core

Location:

```text
ai_core/
```

Responsibilities:

- Gemini embedding generation
- ChromaDB management
- ingestion normalization
- RAG retrieval
- metadata-aware reranking
- answer generation

Embedding contract:

```text
Model:      gemini-embedding-001
Dimensions: 3072
Batch size: 10
```

Vector-store contract:

```text
Collection: eu_grants
Documents:  30 in the verified v2.2.1 dataset
```

## Layer 1: Data

Source of truth:

```text
data/grants.json
```

The v2.2.1 baseline contains 30 unique structured grant records.

Each Chroma record uses a stable grant identifier and structured metadata for
retrieval and reranking.

The synchronization strategy is failure-safe:

1. generate embeddings
2. upsert current records
3. verify successful writes
4. delete stale records only after successful synchronization

## Layer 5: Infrastructure

Location:

```text
infrastructure/
```

Components:

```text
render/              production deployment documentation
docker-compose.yml   local orchestration
k8s/                 optional Kubernetes manifests
scripts/             deployment and synchronization utilities
```

The authoritative Render Blueprint remains at:

```text
/render.yaml
```

## Dependency matrix

| Layer | May depend on | Must not depend on |
|---|---|---|
| `frontend/` | backend HTTP API | Python internals |
| `backend/app/api/` | core, services, schemas | `ai_core` directly |
| `backend/app/services/` | core, `ai_core` | API route modules |
| `backend/app/core/` | standard library, external packages | API and AI layers |
| `ai_core/` | other AI-core modules | backend and frontend |
| `sdk/` | public HTTP API | internal application modules |

Dependencies flow from API to services to AI core. The AI layer can be used
without importing the FastAPI backend.

## Search data flow

```text
POST /search
  -> JWT validation
  -> Gemini query embedding
  -> ChromaDB candidate retrieval
  -> metadata-aware reranking
  -> requested result limit
  -> SearchResponse
```

The current search pipeline retrieves a larger candidate set before applying
deterministic quality-aware reranking.

## AI-answer data flow

```text
POST /ai-answer
  -> JWT validation
  -> query embedding
  -> ChromaDB candidate retrieval
  -> rerank to top five
  -> build grant context
  -> Gemini 2.5 Flash generation
  -> answer plus sources
```

## Production health contract

The health endpoint exposes:

```text
version
git_commit
chroma_collection
chroma_documents
database
db_type
ai_engine
grants_total
grants_in_vector_db
```

This allows the Production Health Check workflow to confirm that the deployed
commit and runtime data match the intended release.

## Key operational constraints

- Render free instances can sleep during inactivity.
- Cold starts can exceed 50 seconds.
- ChromaDB storage is ephemeral on the current Render plan.
- Automatic startup synchronization rebuilds the vector collection.
- PostgreSQL is used for production users.
- SQLite remains a failure fallback.
- `WEB_CONCURRENCY=1` avoids inconsistent process-local state.
- The current in-memory rate limiter is not intended for horizontal scaling.
- `JWT_SECRET` must remain stable across restarts.

## Verified v2.2.1 baseline

```text
Release commit:       f8355363ef9ea16ce8fd4a376c57fd6144511c33
Grant records:        30
Embedding dimensions: 3072
Chroma documents:     30
Automated tests:      87
```

Search benchmark:

```text
Full HitRate@5:       0.8667
Full MRR@10:          0.7622
Full NDCG@10:         0.6293

Evaluable HitRate@5:  0.9286
Evaluable MRR@10:     0.8167
Evaluable NDCG@10:    0.6573
```

## Planned evolution

- verified dataset expansion
- stronger behavior-lock tests around search
- retrieval and reranking module decomposition
- SBOM and provenance attestations
- optional Redis-backed rate limiting
- local LLM, LangChain, LangGraph, and local RAG experimentation outside the
  production release path
