# EU Funds & Grants AI 🇪🇺🤖 — FinAssistBH

[![CI/CD Pipeline](https://img.shields.io/github/actions/workflow/status/dinohatibovic/EU_Funds_and_Grants_AI/ci-cd-pipeline.yml?branch=main&label=CI%2FCD)](https://github.com/dinohatibovic/EU_Funds_and_Grants_AI/actions)
[![Security Audit](https://img.shields.io/github/actions/workflow/status/dinohatibovic/EU_Funds_and_Grants_AI/security-audit.yml?branch=main&label=Security%20Audit)](https://github.com/dinohatibovic/EU_Funds_and_Grants_AI/actions)
[![Release](https://img.shields.io/github/v/release/dinohatibovic/EU_Funds_and_Grants_AI?label=Release&color=success)](https://github.com/dinohatibovic/EU_Funds_and_Grants_AI/releases)
[![Docker](https://img.shields.io/badge/GHCR-finassistbh--backend-2496ED?logo=docker&logoColor=white)](https://github.com/dinohatibovic/EU_Funds_and_Grants_AI/pkgs/container/finassistbh-backend)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Render](https://img.shields.io/badge/Render-Deployed-informational?logo=render)](https://render.com/)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](./LICENSE)
[![Sponsor](https://img.shields.io/badge/♥-Support_the_project-ea4aaa)](https://dinohatibovic.github.io/EU_Funds_and_Grants_AI/pitch.html)

A modular AI system with a **Retrieval-Augmented Generation (RAG)** architecture
for analyzing, indexing and intelligently searching EU and Bosnian grant &
funding programs — with a special focus on the **Zenica-Doboj Canton (ZDK) and
Tešanj**.

> Bosnia and Herzegovina uses less than 30% of the EU funds available to it.
> FinAssistBH is changing that.

**Live:** [Frontend (GitHub Pages)](https://dinohatibovic.github.io/EU_Funds_and_Grants_AI/) ·
[API (Render)](https://eu-funds-and-grants-ai.onrender.com/health)

---

## 🏗️ System architecture

The system is designed for maximum modularity and layer isolation:

- **AI Layer** (`ai_core/`) — RAG pipeline, Google Gemini embeddings
  (`gemini-embedding-001`), Gemini 2.5 Flash generation, ChromaDB vector
  store, ingestion (JSON / web scraping / PDF / API).
- **Backend** (`backend/`) — FastAPI API gateway: search, AI answers,
  grants REST, JWT auth, rate limiting, Stripe webhook.
- **Frontend** (`frontend/`) — static web app (chat, auth, investor pitch)
  hosted on GitHub Pages. *UI language: Bosnian (product language).*
- **Infrastructure** (`infrastructure/`) — Docker Compose for local dev,
  Render blueprint for production, optional Kubernetes manifests.

Full blueprint with the dependency matrix: [`docs/architecture/BLUEPRINT.md`](./docs/architecture/BLUEPRINT.md)

### Repository layout

```text
EU_Funds_and_Grants_AI/
├── .github/               # CI/CD workflows + issue/PR templates
├── ai_core/               # Layer 2: Core Intelligence Stack
│   ├── embeddings/        #   Google Gemini embedding client
│   ├── vector_store/      #   ChromaDB management
│   ├── rag_pipeline/      #   Search, normalization, ingestion
│   └── agent/             #   EUFundsAgent (RAG + Gemini, bs/en)
├── backend/               # Layer 3: API & Orchestration
│   └── app/
│       ├── api/           #   FastAPI routes (REST endpoints)
│       ├── core/          #   Config, DB, JWT, rate limiting
│       ├── services/      #   Bridge to the AI layer
│       └── main.py        #   Entry point
├── frontend/              # Layer 4: User Interface (GitHub Pages)
│   └── src/               #   index.html, auth.html, pitch.html
├── infrastructure/        # Layer 5: DevOps
│   ├── render/            #   Render deployment docs
│   ├── k8s/               #   Kubernetes manifests (optional)
│   ├── scripts/           #   verify_sync.py (prod ↔ code audit)
│   └── docker-compose.yml #   Local orchestration
├── docs/                  # Architecture, forensics, regulatory
├── data/grants.json       # Source of truth — 19 BiH/EU grants
├── sdk/                   # Public Python SDK for the API
├── tests/                 # backend_tests/ + ai_pipeline_tests/
├── Makefile               # make up / test / ingest ...
├── render.yaml            # Render blueprint (must stay in root)
└── README.md
```

---

## 🚀 Quick start (local environment)

### Prerequisites

- Docker + Docker Compose (or Python 3.12+ for a non-Docker setup)
- A [Gemini API key](https://aistudio.google.com/app/apikey)

### Install & run

1. **Clone the repository:**
   ```bash
   git clone https://github.com/dinohatibovic/EU_Funds_and_Grants_AI.git
   cd EU_Funds_and_Grants_AI
   ```

2. **Configure the environment** — copy the template and add your API keys:
   ```bash
   cp .env.example .env
   ```

3. **Run via Makefile:**
   ```bash
   make up        # Docker: backend on :8000, frontend on :3000
   # or without Docker:
   pip install -r requirements.txt
   make dev       # uvicorn backend.app.main:app --reload
   ```

   *API docs (Swagger): http://localhost:8000/docs*

4. **Tests:**
   ```bash
   pip install pytest httpx
   make test      # backend tests
   make ai-test   # AI pipeline tests
   ```

### Prebuilt Docker image (GitHub Packages)

Every release automatically publishes the backend image to GHCR:

```bash
docker pull ghcr.io/dinohatibovic/finassistbh-backend:latest
docker run --env-file .env -p 8000:8000 ghcr.io/dinohatibovic/finassistbh-backend:latest
```

New to the project? Start with [docs/onboarding.md](./docs/onboarding.md) —
from zero to a running system in 15 minutes.

---

## 🔌 API overview

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health` | GET | — | System status, grant counts, urgent deadlines |
| `/search` | POST | JWT | Semantic (vector) grant search |
| `/ai-answer` | POST | JWT | RAG + Gemini AI answer (Bosnian/English) |
| `/grants` | GET | — | Grant list (filters + pagination) |
| `/grants/local` | GET | — | ZDK/Tešanj priority calls |
| `/grants/urgent` | GET | — | Deadlines expiring within N days |
| `/auth/register` `/auth/login` | POST | — | JWT registration/login |
| `/ingest` | POST | JWT | Manual vector DB re-ingest |

Python SDK: [`sdk/client.py`](./sdk/client.py) —
`EUGrantsClient().login(email, pass)` → `client.query("SME incentives in ZDK")`

---

## 🛡️ Security & regulatory compliance

- **Automated audits:** weekly [security-audit workflow](./.github/workflows/security-audit.yml)
  — pip-audit (CVEs), Bandit (static analysis), gitleaks (secrets in code).
- **No secrets in the repo:** all keys live in environment variables; `.env`
  is gitignored.
- **Forensic transparency:** audits and system analyses are archived in
  [`docs/forensics/`](./docs/forensics/); production drift is checked by
  `infrastructure/scripts/verify_sync.py`.
- **EU AI Act & GDPR:** compliance status and escalation procedures are
  documented in [`docs/regulatory/`](./docs/regulatory/README.md) —
  AI answers always cite sources, and data entries carry reliability labels.
- Vulnerability reporting: [SECURITY.md](./SECURITY.md)

## 🛠️ CI/CD pipeline

GitHub Actions ([ci-cd-pipeline.yml](./.github/workflows/ci-cd-pipeline.yml)):

1. **Lint** — ruff static analysis (critical errors).
2. **Test** — isolated unit tests for the Backend and AI layers (external
   services mocked).
3. **Deploy backend** — automatic deploy to **Render** after green tests on
   `main` (deploy hook or Render auto-deploy).
4. **Deploy frontend** — `frontend/src/` to **GitHub Pages**
   (one-time setup: Settings → Pages → Source: *GitHub Actions*).

Releases: pushing a `v*` tag (or manually running the
[Release workflow](./.github/workflows/release.yml)) creates a GitHub Release
and publishes the Docker image to GHCR.

---

## 💰 Pricing (SaaS)

| Plan | Price | Audience |
|---|---|---|
| Starter | €29/mo | Small businesses, basic search |
| Pro | €149/mo | SMEs — notifications, AI matching |
| Agency | €299/mo | Consultants — white-label, API |
| Enterprise | €799/mo | Cantons, governments, corporations |

## 📞 Contact

**Dino Hatibović** — Tešanj, Zenica-Doboj Canton, Bosnia and Herzegovina
Email: holdin.genesis@gmail.com ·
[GitHub](https://github.com/dinohatibovic) ·
[LinkedIn](https://linkedin.com/in/dinohatibovic)

## 📄 License

Copyright © 2026 Dino Hatibović. All rights reserved.
Restricted access and distribution under the [proprietary license](./LICENSE).

---

*Built in Tešanj, BiH — for the EU market.*
