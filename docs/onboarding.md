# Onboarding — pokreni FinAssistBH za 15 minuta

Vodič za novog developera (ili tebe na novoj mašini).

## 1. Preduslovi (5 min)

- Python 3.12+ (ili Docker + Docker Compose)
- Git
- [Gemini API ključ](https://aistudio.google.com/app/apikey) — besplatan

## 2. Setup (5 min)

```bash
git clone https://github.com/dinohatibovic/EU_Funds_and_Grants_AI.git
cd EU_Funds_and_Grants_AI

cp .env.example .env
# → u .env unesi GEMINI_API_KEY (ostalo je opcionalno za lokalni rad)
```

**Opcija A — Docker (preporučeno):**
```bash
make up          # backend :8000 + frontend :3000
make logs        # prati backend logove
```

**Opcija B — bez Dockera:**
```bash
pip install -r requirements.txt
make dev         # uvicorn backend.app.main:app --reload
# frontend: otvori frontend/src/index.html u browseru
```

## 3. Provjera da sve radi (2 min)

```bash
curl http://localhost:8000/health
# očekuješ: "status": "healthy", "grants_total": 22
```

Swagger UI: http://localhost:8000/docs

## 4. Testovi (3 min)

```bash
pip install pytest httpx
make test        # backend (mockirani vanjski servisi — ne troši API kvotu)
make ai-test     # AI pipeline + integritet grants.json
make lint
```

## Gdje je šta — mentalna mapa

| Želim promijeniti... | Idem u... |
|---|---|
| API endpoint / rutu | `backend/app/api/` |
| Auth, rate limit, config | `backend/app/core/` |
| RAG pretragu / embeddinge | `ai_core/rag_pipeline/`, `ai_core/embeddings/` |
| AI prompt / ponašanje agenta | `ai_core/agent/agent.py` + `backend/app/api/search.py` |
| Podatke o grantovima | `data/grants.json` (pravila u `CLAUDE.md`!) |
| UI | `frontend/src/` |
| CI/CD | `.github/workflows/` |

Detaljna arhitektura: [architecture/BLUEPRINT.md](./architecture/BLUEPRINT.md)

## Česti problemi

- **`GEMINI_API_KEY not found`** → nisi kopirao `.env.example` u `.env` ili ključ fali
- **Server radi ali pretraga vraća 503** → AI klijenti se inicijalizuju ~10s nakon starta
- **Render produkcija spora prvi put** → free tier cold start (50–75s), normalno
