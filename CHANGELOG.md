# Changelog

All notable changes to the FinAssistBH platform. The format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

### Changed
- Gemini generation model switched from the discontinued `gemini-2.0-flash`
  to `gemini-2.5-flash` (overridable via the `GEMINI_MODEL` env variable)
- LICENSE translated to English; contact changed from phone number to email
- Repository documentation translated to English (frontend stays Bosnian —
  product language)
- `.env.example` aligned with the actual config (`DATABASE_URL`,
  `CHROMA_DB_PATH`, `RATE_LIMIT_*`, `GEMINI_MODEL`); unused `SUPABASE_*`
  placeholders removed

### Fixed
- Removed duplicate grants from `data/grants.json` (Innovate Bosnia, FIPA IT,
  Environment Fund — 22 → 19 entries); duplicates were skewing RAG search
- `verify_sync.py` now derives the expected grant count from the local data
  file instead of a hardcoded value

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
