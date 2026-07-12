# EU Funds & Grants AI 🇪🇺🤖 — FinAssistBH

[![CI/CD Pipeline](https://img.shields.io/github/actions/workflow/status/dinohatibovic/EU_Funds_and_Grants_AI/ci-cd-pipeline.yml?branch=main&label=CI%2FCD)](https://github.com/dinohatibovic/EU_Funds_and_Grants_AI/actions)
[![Security Audit](https://img.shields.io/github/actions/workflow/status/dinohatibovic/EU_Funds_and_Grants_AI/security-audit.yml?branch=main&label=Security%20Audit)](https://github.com/dinohatibovic/EU_Funds_and_Grants_AI/actions)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Render](https://img.shields.io/badge/Render-Deployed-informational?logo=render)](https://render.com/)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](./LICENSE)

Modularni AI sistem s **Retrieval-Augmented Generation (RAG)** arhitekturom za
analizu, indeksiranje i pametno pretraživanje EU i BiH fondova i grantova —
s posebnim fokusom na **ZDK kanton i Tešanj**.

> Bosna i Hercegovina koristi manje od 30% dostupnih EU sredstava.
> FinAssistBH to mijenja.

**Live:** [Frontend (GitHub Pages)](https://dinohatibovic.github.io/EU_Funds_and_Grants_AI/) ·
[API (Render)](https://eu-funds-and-grants-ai.onrender.com/health)

---

## 🏗️ Arhitektura sistema

Sistem je dizajniran s maksimalnim fokusom na modularnost i izolaciju slojeva:

- **AI Layer** (`ai_core/`) — RAG pipeline, Google Gemini embeddings
  (`gemini-embedding-001`), Gemini 2.0 Flash generacija, ChromaDB vektorska
  pohrana, ingestion (JSON / web scraping / PDF / API).
- **Backend** (`backend/`) — FastAPI API gateway: pretraga, AI odgovori,
  grants REST, JWT auth, rate limiting, Stripe webhook.
- **Frontend** (`frontend/`) — statična web aplikacija (chat, auth, investor
  pitch) hostana na GitHub Pages.
- **Infrastructure** (`infrastructure/`) — Docker Compose za lokalni razvoj,
  Render blueprint za produkciju, opcionalni Kubernetes manifesti.

Detaljan blueprint s matricom zavisnosti: [`docs/architecture/BLUEPRINT.md`](./docs/architecture/BLUEPRINT.md)

### Struktura repozitorija

```text
EU_Funds_and_Grants_AI/
├── .github/               # CI/CD workflows + issue šabloni
├── ai_core/               # Layer 2: Core Intelligence Stack
│   ├── embeddings/        #   Google Gemini embedding klijent
│   ├── vector_store/      #   ChromaDB menadžment
│   ├── rag_pipeline/      #   Pretraga, normalizacija, ingestion
│   └── agent/             #   EUFundsAgent (RAG + Gemini, bs/en)
├── backend/               # Layer 3: API & Orchestration
│   └── app/
│       ├── api/           #   FastAPI rute (REST endpoints)
│       ├── core/          #   Config, DB, JWT, rate limiting
│       ├── services/      #   Most prema AI sloju
│       └── main.py        #   Entry point
├── frontend/              # Layer 4: User Interface (GitHub Pages)
│   └── src/               #   index.html, auth.html, pitch.html
├── infrastructure/        # Layer 5: DevOps
│   ├── render/            #   Render deployment dokumentacija
│   ├── k8s/               #   Kubernetes manifesti (opcionalno)
│   ├── scripts/           #   verify_sync.py (produkcija ↔ kod audit)
│   └── docker-compose.yml #   Lokalno orkestriranje
├── docs/                  # Arhitektura, forenzika, regulatorni okvir
├── data/grants.json       # Izvor istine — 22 BiH/EU granta
├── sdk/                   # Javni Python SDK za API
├── tests/                 # backend_tests/ + ai_pipeline_tests/
├── Makefile               # make up / test / ingest ...
├── render.yaml            # Render blueprint (mora biti u root-u)
└── README.md
```

---

## 🚀 Brzi start (lokalno okruženje)

### Preduslovi

- Docker + Docker Compose (ili Python 3.12+ za razvoj bez Dockera)
- [Gemini API ključ](https://aistudio.google.com/app/apikey)

### Instalacija i pokretanje

1. **Kloniranje repozitorija:**
   ```bash
   git clone https://github.com/dinohatibovic/EU_Funds_and_Grants_AI.git
   cd EU_Funds_and_Grants_AI
   ```

2. **Konfiguracija okruženja** — kopiraj šablon i unesi API ključeve:
   ```bash
   cp .env.example .env
   ```

3. **Pokretanje putem Makefile-a:**
   ```bash
   make up        # Docker: backend na :8000, frontend na :3000
   # ili bez Dockera:
   pip install -r requirements.txt
   make dev       # uvicorn backend.app.main:app --reload
   ```

   *API dokumentacija (Swagger): http://localhost:8000/docs*

4. **Testovi:**
   ```bash
   pip install pytest httpx
   make test      # backend testovi
   make ai-test   # AI pipeline testovi
   ```

---

## 🔌 API pregled

| Endpoint | Metoda | Auth | Opis |
|---|---|---|---|
| `/health` | GET | — | Status sistema, broj grantova, hitni rokovi |
| `/search` | POST | JWT | Semantička (vektorska) pretraga grantova |
| `/ai-answer` | POST | JWT | RAG + Gemini AI odgovor (bosanski/engleski) |
| `/grants` | GET | — | Lista grantova (filteri + paginacija) |
| `/grants/local` | GET | — | ZDK/Tešanj prioritetni pozivi |
| `/grants/urgent` | GET | — | Rokovi koji ističu unutar N dana |
| `/auth/register` `/auth/login` | POST | — | JWT registracija/prijava |
| `/ingest` | POST | JWT | Manualni re-ingest vektorske baze |

Python SDK: [`sdk/client.py`](./sdk/client.py) —
`EUGrantsClient().login(email, pass)` → `client.query("poticaji za MSP u ZDK")`

---

## 🛡️ Sigurnost i regulatorna usklađenost

- **Automatizovani audit:** sedmični [security-audit workflow](./.github/workflows/security-audit.yml)
  — pip-audit (CVE), Bandit (statička analiza), gitleaks (tajne u kodu).
- **Bez tajni u repou:** svi ključevi u env varijablama; `.env` u `.gitignore`.
- **Forenzička transparentnost:** revizije i sistemske analize se arhiviraju u
  [`docs/forensics/`](./docs/forensics/); produkcijski drift se provjerava
  skriptom `infrastructure/scripts/verify_sync.py`.
- **EU AI Act & GDPR:** status usklađenosti i eskalacijske procedure su
  dokumentovani u [`docs/regulatory/`](./docs/regulatory/README.md) —
  AI odgovori uvijek navode izvore, a podaci nose oznake pouzdanosti.
- Prijava ranjivosti: [SECURITY.md](./SECURITY.md)

## 🛠️ CI/CD Pipeline

GitHub Actions ([ci-cd-pipeline.yml](./.github/workflows/ci-cd-pipeline.yml)):

1. **Lint** — ruff statička analiza (kritične greške).
2. **Test** — izolovani unit testovi za Backend i AI slojeve (mockirani vanjski servisi).
3. **Deploy backend** — automatski deploy na **Render** nakon zelenih testova
   na `main` (deploy hook ili Render auto-deploy).
4. **Deploy frontend** — `frontend/src/` na **GitHub Pages**
   (jednokratno: Settings → Pages → Source: *GitHub Actions*).

---

## 💰 Model cijena (SaaS)

| Plan | Cijena | Za koga |
|---|---|---|
| Starter | €29/mj | Mala preduzeća, osnovna pretraga |
| Pro | €149/mj | MSP — notifikacije, AI matching |
| Agency | €299/mj | Konzultanti — white-label, API |
| Enterprise | €799/mj | Kantoni, vlade, korporacije |

## 📞 Kontakt

**Dino Hatibović** — Tešanj, Zeničko-dobojski kanton, BiH
Telefon: +387 62 564 303 ·
[GitHub](https://github.com/dinohatibovic) ·
[LinkedIn](https://linkedin.com/in/dinohatibovic)

## 📄 Licenca

Copyright © 2026 Dino Hatibović. Sva prava zadržana.
Ograničen pristup i distribucija u skladu s [vlasničkom licencom](./LICENSE).

---

*Razvijeno u Tešnju, BiH — za EU tržište.*
