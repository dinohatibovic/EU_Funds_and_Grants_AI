# FinAssistBH — Architecture Blueprint

**Version:** 2.2.0 | **Owner:** Dino Hatibović | Tešanj, BiH

The system is organized into strictly separated layers. Each layer has its
own directory, its own dependencies, and can be tested/deployed in isolation.

## Layers

```
┌────────────────────────────────────────────────────────┐
│  Layer 4: FRONTEND (frontend/)                          │
│  Static HTML/CSS/JS — GitHub Pages                      │
│  index.html (chat) │ auth.html (JWT) │ pitch.html       │
└──────────────────────┬─────────────────────────────────┘
                       │ HTTPS / JSON (CORS whitelist)
┌──────────────────────▼─────────────────────────────────┐
│  Layer 3: BACKEND — API Gateway (backend/app/)          │
│  ├── api/       FastAPI routes (system, search, grants, │
│  │              auth, webhooks) + Pydantic schemas      │
│  ├── core/      config, database, security (JWT),       │
│  │              rate_limit                              │
│  ├── services/  ai.py — bridge to the AI layer          │
│  └── main.py    app factory, middleware, startup        │
└──────────────────────┬─────────────────────────────────┘
                       │ Python import (backend → ai_core)
┌──────────────────────▼─────────────────────────────────┐
│  Layer 2: AI CORE — Intelligence Stack (ai_core/)       │
│  ├── embeddings/    Gemini embedding-001 client         │
│  ├── vector_store/  ChromaDB persistent client          │
│  ├── rag_pipeline/  search, normalization, ingestion    │
│  │                  (JSON, web scraping, PDF, API)      │
│  └── agent/         EUFundsAgent — RAG + Gemini 2.5     │
│                     Flash generation (bs/en)            │
└──────────────────────┬─────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
  Google Gemini API            ChromaDB (disk)
  (embeddings + generation)    collection `eu_grants`

┌────────────────────────────────────────────────────────┐
│  Layer 5: INFRASTRUCTURE (infrastructure/)              │
│  render/ (production) │ k8s/ (optional) │               │
│  docker-compose.yml (local dev) │ scripts/              │
└────────────────────────────────────────────────────────┘
```

## Dependency matrix (who may import whom)

| Layer | may import | must NOT import |
|---|---|---|
| `frontend/` | — (HTTP only) | any Python |
| `backend/app/api/` | `backend/app/core`, `backend/app/services`, schemas | `ai_core` directly |
| `backend/app/services/` | `backend/app/core`, `ai_core` | `backend/app/api` |
| `backend/app/core/` | stdlib, external libraries | `ai_core`, `api`, `services` |
| `ai_core/*` | other `ai_core` modules | `backend`, `frontend` |
| `sdk/` | — (HTTP only) | internal modules |

Rule: **dependencies flow downward** (api → services → ai_core). The AI layer
does not know the backend exists — it can be used standalone (scripts,
notebooks, CLI).

## Data flow

1. **Ingestion:** `data/grants.json` → auto-ingest on startup (full refresh) →
   Gemini embeddings (batches of 10) → ChromaDB collection `eu_grants`.
2. **Search (`POST /search`):** query → embedding → ChromaDB top-N → raw
   results + metadata.
3. **AI answer (`POST /ai-answer`):** query → RAG context (top 5) → Gemini 2.5
   Flash prompt with BiH domain knowledge → structured answer + sources.

## Key decisions and constraints

- **ChromaDB local, not managed** — zero cost, sufficient below ~10K
  documents; the Render free-tier disk is ephemeral, so auto-ingest rebuilds
  the database on startup.
- **SQLite fallback for users** — the server boots even without a PostgreSQL
  connection; `DATABASE_URL` (Supabase) is recommended for production.
- **In-memory rate limiter** — fine for a single process; replace with Redis
  when scaling horizontally.
- **JWT HS256, 30 days** — `JWT_SECRET` must be a stable env variable in
  production.
- **Gemini model** — default `gemini-2.5-flash`, overridable via the
  `GEMINI_MODEL` env variable (the 2.0 model was discontinued).
