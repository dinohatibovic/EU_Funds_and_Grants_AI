# Changelog

Sve značajne izmjene FinAssistBH platforme. Format prati
[Keep a Changelog](https://keepachangelog.com/), verzije prate [SemVer](https://semver.org/).

## [2.2.0] — 2026-07-19

### Dodano
- **Enterprise slojevita struktura repozitorija**: `ai_core/` (AI sloj),
  `backend/app/` (api/core/services), `frontend/src/`, `infrastructure/`, `docs/`
- CI/CD pipeline (GitHub Actions): lint → testovi → Render deploy → GitHub Pages deploy
- Security Audit workflow: pip-audit, Bandit, gitleaks (sedmično + na push)
- Release workflow: automatski GitHub Release + Docker image na GHCR pri git tagu
- Docker Compose za lokalni razvoj, Kubernetes manifesti (opcionalno)
- Makefile (`make up/dev/test/ai-test/lint/ingest`)
- Dependabot, issue/PR šabloni, FUNDING, CONTRIBUTING, onboarding dokumentacija
- Arhitekturni blueprint s matricom zavisnosti (`docs/architecture/BLUEPRINT.md`)
- Regulatorni okvir — GDPR / EU AI Act status (`docs/regulatory/`)
- Testovi: 31 (backend + AI pipeline + integritet podataka)

### Popravljeno
- SDK (`sdk/client.py`): `/search` zahtijeva JWT — dodan `login()` i Authorization header
- `web_scraper.py`: ChromaDB ne prima `None` metadata (deadline fallback na `""`)
- `api_loader.py`: dodan timeout na HTTP pozive
- Bandit B608 lažne uzbune označene (parametrizovani upiti)
- `.gitignore` očišćen (duplikati, pogrešan ignore `embeddings/`)

### Promijenjeno
- Entry point: `uvicorn main:app` → `uvicorn backend.app.main:app`
- ChromaDB putanja konfigurabilna preko `CHROMA_DB_PATH`
- `data/grants.json`: neprovjereni unosi eksplicitno označeni, istekli rokovi → `null`

## [2.1.0] — 2026-06

### Dodano
- `/ai-answer` endpoint (RAG + Gemini 2.0 Flash generacija, bs/en)
- `/grants`, `/grants/local`, `/grants/urgent` REST endpointi
- Rate limiting (30 req/60s po IP), email validacija, JWT auth
- Graceful DB fallback (PostgreSQL → SQLite) na startupu
- CORS whitelist za produkciju

## [2.0.0] — 2026-03

### Dodano
- Prva produkcijska verzija: FastAPI + ChromaDB + Gemini embeddings (RAG)
- Frontend (chat, auth, investor pitch) na GitHub Pages
- Deployment na Render.com s auto-ingest grantova pri startu
