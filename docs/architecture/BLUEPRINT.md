# FinAssistBH — Arhitekturni Blueprint

**Verzija:** 2.2.0 | **Vlasnik:** Dino Hatibović | Tešanj, BiH

Sistem je organizovan u strogo odvojene slojeve. Svaki sloj ima vlastiti
direktorij, vlastite zavisnosti i može se testirati/deployati izolovano.

## Slojevi

```
┌────────────────────────────────────────────────────────┐
│  Layer 4: FRONTEND (frontend/)                          │
│  Statični HTML/CSS/JS — GitHub Pages                    │
│  index.html (chat) │ auth.html (JWT) │ pitch.html       │
└──────────────────────┬─────────────────────────────────┘
                       │ HTTPS / JSON (CORS whitelist)
┌──────────────────────▼─────────────────────────────────┐
│  Layer 3: BACKEND — API Gateway (backend/app/)          │
│  ├── api/       FastAPI rute (system, search, grants,   │
│  │              auth, webhooks) + Pydantic šeme         │
│  ├── core/      config, database, security (JWT),       │
│  │              rate_limit                              │
│  ├── services/  ai.py — most prema AI sloju             │
│  └── main.py    app factory, middleware, startup        │
└──────────────────────┬─────────────────────────────────┘
                       │ Python import (backend → ai_core)
┌──────────────────────▼─────────────────────────────────┐
│  Layer 2: AI CORE — Intelligence Stack (ai_core/)       │
│  ├── embeddings/    Gemini embedding-001 klijent        │
│  ├── vector_store/  ChromaDB perzistentni klijent       │
│  ├── rag_pipeline/  pretraga, normalizacija, ingestion  │
│  │                  (JSON, web scraping, PDF, API)      │
│  └── agent/         EUFundsAgent — RAG + Gemini 2.0     │
│                     Flash generacija (bs/en)            │
└──────────────────────┬─────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
  Google Gemini API            ChromaDB (disk)
  (embeddings + generacija)    kolekcija `eu_grants`

┌────────────────────────────────────────────────────────┐
│  Layer 5: INFRASTRUCTURE (infrastructure/)              │
│  render/ (produkcija) │ k8s/ (opcionalno) │             │
│  docker-compose.yml (lokalni razvoj) │ scripts/         │
└────────────────────────────────────────────────────────┘
```

## Matrica zavisnosti (ko smije importovati koga)

| Sloj | smije importovati | NE smije importovati |
|---|---|---|
| `frontend/` | — (HTTP only) | bilo šta Python |
| `backend/app/api/` | `backend/app/core`, `backend/app/services`, šeme | `ai_core` direktno |
| `backend/app/services/` | `backend/app/core`, `ai_core` | `backend/app/api` |
| `backend/app/core/` | stdlib, vanjske biblioteke | `ai_core`, `api`, `services` |
| `ai_core/*` | drugi `ai_core` moduli | `backend`, `frontend` |
| `sdk/` | — (HTTP only) | interne module |

Pravilo: **zavisnosti teku prema dolje** (api → services → ai_core). AI sloj ne
zna da backend postoji — može se koristiti samostalno (skripte, notebook, CLI).

## Tok podataka

1. **Ingestion:** `data/grants.json` → auto-ingest pri startupu (full refresh) →
   Gemini embeddings (batch po 10) → ChromaDB kolekcija `eu_grants`.
2. **Pretraga (`POST /search`):** upit → embedding → ChromaDB top-N → sirovi
   rezultati + metadata.
3. **AI odgovor (`POST /ai-answer`):** upit → RAG kontekst (top 5) → Gemini 2.0
   Flash prompt s BiH domenskim znanjem → strukturirani odgovor + izvori.

## Ključne odluke i ograničenja

- **ChromaDB lokalno, ne managed** — trošak 0, dovoljno za <10K dokumenata;
  na Render free tier disk je ephemeral pa auto-ingest rekonstruiše bazu.
- **SQLite fallback za korisnike** — server se podiže i bez PostgreSQL veze;
  `DATABASE_URL` (Supabase) je preporučen za produkciju.
- **In-memory rate limiter** — dovoljan za jedan proces; kod horizontalnog
  skaliranja zamijeniti Redis-om.
- **JWT HS256, 30 dana** — `JWT_SECRET` mora biti stabilan env var u produkciji.
