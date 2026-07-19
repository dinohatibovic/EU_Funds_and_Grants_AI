# Onboarding — run FinAssistBH in 15 minutes

A guide for a new developer (or yourself on a new machine).

## 1. Prerequisites (5 min)

- Python 3.12+ (or Docker + Docker Compose)
- Git
- A [Gemini API key](https://aistudio.google.com/app/apikey) — free

## 2. Setup (5 min)

```bash
git clone https://github.com/dinohatibovic/EU_Funds_and_Grants_AI.git
cd EU_Funds_and_Grants_AI

cp .env.example .env
# → put your GEMINI_API_KEY into .env (everything else is optional locally)
```

**Option A — Docker (recommended):**
```bash
make up          # backend :8000 + frontend :3000
make logs        # follow backend logs
```

**Option B — without Docker:**
```bash
pip install -r requirements.txt
make dev         # uvicorn backend.app.main:app --reload
# frontend: open frontend/src/index.html in a browser
```

## 3. Verify everything works (2 min)

```bash
curl http://localhost:8000/health
# expect: "status": "healthy", "grants_total": 19
```

Swagger UI: http://localhost:8000/docs

## 4. Tests (3 min)

```bash
pip install pytest httpx
make test        # backend (external services mocked — no API quota used)
make ai-test     # AI pipeline + grants.json integrity
make lint
```

## Where things live — a mental map

| I want to change... | Go to... |
|---|---|
| An API endpoint / route | `backend/app/api/` |
| Auth, rate limiting, config | `backend/app/core/` |
| RAG search / embeddings | `ai_core/rag_pipeline/`, `ai_core/embeddings/` |
| The AI prompt / agent behavior | `ai_core/agent/agent.py` + `backend/app/api/search.py` |
| Grant data | `data/grants.json` (rules in `CLAUDE.md`!) |
| The UI | `frontend/src/` |
| CI/CD | `.github/workflows/` |

Detailed architecture: [architecture/BLUEPRINT.md](./architecture/BLUEPRINT.md)

## Common problems

- **`GEMINI_API_KEY not found`** → you did not copy `.env.example` to `.env`, or the key is missing
- **Server runs but search returns 503** → AI clients initialize ~10s after startup
- **Render production slow on first hit** → free-tier cold start (50–75s), normal
