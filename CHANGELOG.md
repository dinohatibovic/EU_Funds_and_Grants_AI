# Changelog

All notable changes to the FinAssistBH platform. The format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

## [2.2.1] — 2026-08-25

### Added

- Expanded the production grant dataset to 30 structured records.
- Added shared release metadata to the public health endpoint:
  `version`, `git_commit`, `chroma_collection` and `chroma_documents`.
- Added deterministic Chroma collection and write lifecycle contract tests.
- Added automated production health verification after deployment.
- Added versioned relevance judgments and production search benchmark
  evidence for 15 representative grant queries.
- Added FastAPI lifespan behavior tests for startup ordering, database
  fallback and failure-safe AI initialization.

### Changed

- Centralized the Gemini embedding model contract.
- Standardized Gemini embeddings at 3072 dimensions.
- Centralized the ChromaDB collection contract as `eu_grants`.
- Unified structured metadata and embedding text generation across primary
  grant ingestion paths.
- Migrated FastAPI startup initialization from the deprecated
  `@app.on_event("startup")` mechanism to the lifespan context manager.
- Updated the application version contract to `2.2.1`.
- Improved quality-aware reranking for grant search results.

### Fixed

- Made production ChromaDB dataset synchronization failure-safe by upserting
  the new dataset before deleting stale records.
- Prevented failed embedding or upsert operations from deleting the existing
  production collection.
- Removed the FastAPI `on_event` deprecation warning.
- Preserved database fallback, grants cache loading, AI client initialization
  and ChromaDB auto-ingestion during the lifespan migration.

### Production validation

- Production release commit:
  `f8355363ef9ea16ce8fd4a376c57fd6144511c33`.
- Public health endpoint reports version `2.2.1` and the matching Git commit.
- PostgreSQL connection reports `connected`.
- AI engine reports `ready`.
- ChromaDB collection `eu_grants` reports 30 documents.
- Three Gemini embedding batches of 10 records completed successfully.
- Embedding vectors use 3072 dimensions.
- Full automated test suite: 87 passing tests.
- GitHub Release and GHCR image published with tags `2.2.1` and `latest`.

### Search benchmark

Full 15-query production baseline:

- HitRate@5: `0.8667`
- MRR@10: `0.7622`
- NDCG@10: `0.6293`

Fourteen evaluable queries, excluding one documented dataset coverage gap:

- HitRate@5: `0.9286`
- MRR@10: `0.8167`
- NDCG@10: `0.6573`

Production processing time across 15 search requests:

- Mean: `0.2423` seconds
- Median: `0.2421` seconds
- Minimum: `0.2171` seconds
- Maximum: `0.2699` seconds
- P95 nearest rank: `0.2699` seconds

### Known limitations

- The benchmark query `zapošljavanje mladih u FBiH` is recorded as a dataset
  coverage gap because the current judgment set has no document with binary
  relevance grade `>= 2`.
- The Render free instance can sleep during inactivity, so the first request
  after an idle period can have substantially higher latency.

## [2.2.0] — 2026-07-19

### Added
- **Enterprise layered repository structure**: `ai_core/` (AI layer),
  `backend/app/` (api/core/services), `frontend/src/`, `infrastructure/`, `docs/`
- CI/CD pipeline (GitHub Actions): lint → tests → Render deploy → GitHub Pages deploy
- Security Audit workflow: pip-audit, Bandit, gitleaks (weekly + on push)
- Release workflow: a git tag automatically creates a GitHub Release +
  publishes the Docker image to GHCR
- Docker Compose for local development, Kubernetes manifests (optional)
- Makefile (`make up/dev/test/ai-test/lint/ingest`)
- Dependabot, issue/PR templates, FUNDING, CONTRIBUTING, onboarding docs
- Architecture blueprint with a dependency matrix (`docs/architecture/BLUEPRINT.md`)
- Regulatory framework — GDPR / EU AI Act status (`docs/regulatory/`)
- Tests: 31 (backend + AI pipeline + data integrity)

### Fixed
- SDK (`sdk/client.py`): `/search` requires JWT — added `login()` and the
  Authorization header
- `web_scraper.py`: ChromaDB does not accept `None` metadata (deadline falls
  back to `""`)
- `api_loader.py`: added a timeout to HTTP calls
- Bandit B608 false positives annotated (parameterized queries)
- `.gitignore` cleaned up (duplicates, wrong `embeddings/` ignore)

### Changed
- Entry point: `uvicorn main:app` → `uvicorn backend.app.main:app`
- ChromaDB path configurable via `CHROMA_DB_PATH`
- `data/grants.json`: unverified entries explicitly labeled, expired
  deadlines → `null`

## [2.1.0] — 2026-06

### Added
- `/ai-answer` endpoint (RAG + Gemini generation, bs/en)
- `/grants`, `/grants/local`, `/grants/urgent` REST endpoints
- Rate limiting (30 req/60s per IP), email validation, JWT auth
- Graceful DB fallback (PostgreSQL → SQLite) on startup
- CORS whitelist for production

## [2.0.0] — 2026-03

### Added
- First production version: FastAPI + ChromaDB + Gemini embeddings (RAG)
- Frontend (chat, auth, investor pitch) on GitHub Pages
- Deployment to Render.com with grant auto-ingest on startup
