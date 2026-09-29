# FinAssistBH
### AI asistent za EU i domaće grantove u Bosni i Hercegovini

BiH koristi manje od 30% raspoloživih EU sredstava. FinAssistBH pomaže firmama,
obrtnicima i konsultantima da **pronađu pravi javni poziv** — na bosanskom,
sa izvorom, bez izmišljenih rokova i budžeta.

Fokus: Zenica-Doboj kanton i Tešanj, zatim FBiH i EU programi dostupni BiH.

[![CI/CD](https://img.shields.io/github/actions/workflow/status/dinohatibovic/EU_Funds_and_Grants_AI/ci-cd-pipeline.yml?branch=main&label=CI%2FCD)](https://github.com/dinohatibovic/EU_Funds_and_Grants_AI/actions)
[![Release](https://img.shields.io/github/v/release/dinohatibovic/EU_Funds_and_Grants_AI)](https://github.com/dinohatibovic/EU_Funds_and_Grants_AI/releases)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](./LICENSE)

**Live:** [Aplikacija](https://dinohatibovic.github.io/EU_Funds_and_Grants_AI/) ·
[API health](https://eu-funds-and-grants-ai.onrender.com/health) ·
[Pitch](https://dinohatibovic.github.io/EU_Funds_and_Grants_AI/pitch.html)

Demo: 3 AI upita bez registracije. Render free instanca može spavati; prvi
poziv traje do ~60 sekundi.

---

## Za koga

| Korisnik | Šta dobija danas |
|---|---|
| MSP, obrt, startup | Prirodni upit → rangirani grantovi + izvori |
| Konsultant | Brza pretraga i grounding umjesto ručnog kopanja portala |
| Općina / razvojna agencija | Lokalni i kantonalni pozivi uz EU programe |

BiH je **kandidat za EU**, nije članica. Platforma to ne zamagljuje.

## Šta radi sada

```text
Upit na bosanskom
  → hybrid pretraga (BM25 + dense + RRF)
  → reranking
  → strukturirani rezultati i URL izvori
  → AI odgovor samo nad verificiranim podacima
```

AI **ne smije** izmišljati rok, budžet, uslove ni URL. Ako podatak nije
potvrđen, kaže da nije potvrđen. Polje `next_expected` nije aktivni deadline.

Sljedeći proizvodni sloj (nije u ovom releaseu): profil firme, matching,
alerti, dokumentacija prijave, praćenje statusa.

## Produkcijski ugovor

| | |
|---|---|
| Release linija | `2.2.x` (`v2.2.1`) |
| Dataset | 30 strukturiranih grantova, `data/grants.json` |
| Vektori | ChromaDB `eu_grants`, Gemini `gemini-embedding-001` (3072 dim) |
| Generisanje | Gemini 2.5 Flash |
| Baza korisnika | PostgreSQL (SQLite fallback) |
| Frontend | statički HTML, GitHub Pages, UI na bosanskom |
| Backend | FastAPI na Renderu |

Trenutni runtime čitaj sa [`/health`](https://eu-funds-and-grants-ai.onrender.com/health)
(`version`, `git_commit`, `chroma_documents`, `database`, `ai_engine`).
Ne tvrdi SHA iz README-ja ako health kaže drugačije.

P1 search baseline (15 upita, v2.2.1):

```text
HitRate@5  0.8667
MRR@10     0.7622
NDCG@10    0.6293
```

Rupa u datasetu: `zapošljavanje mladih u FBiH` nema potvrđen relevantan
dokument — to je coverage gap, ne izmišljen hit.

Lokalni testovi (pre-push, 29.9.2026): 191. Release `v2.2.1` je imao 87.

Prije ranking/RAG PR-a:

```bash
make lint && make test && make ai-test && make benchmark-test
```

## Arhitektura

```text
GitHub Pages  →  FastAPI  →  PostgreSQL
                    │
                    └→  ai_core
                          BM25 + Chroma + RRF + rerank + Gemini
```

| Sloj | Put | Odgovornost |
|---|---|---|
| UI | `frontend/src/` | prijava, demo, chat, pitch |
| API | `backend/app/` | JWT, grantovi, search, AI, Stripe webhook |
| AI | `ai_core/` | embeddings, Chroma, RAG, grounding |
| Podaci | `data/grants.json` | jedini izvor istine za grantove |
| Ops | `infrastructure/`, `render.yaml` | Docker, Render, health |

Slojevi su namjerno odvojeni: frontend ne uvozi Python, `ai_core` ne uvozi FastAPI.

```text
EU_Funds_and_Grants_AI/
├── ai_core/            embeddings, vector_store, rag_pipeline, agent
├── backend/app/        api/, core/, services/, main.py
├── frontend/src/       index.html, auth.html, pitch.html
├── data/grants.json    30 grantova
├── docs/               blueprint, onboarding, regulatory
├── infrastructure/     docker-compose, render, k8s, scripts
├── sdk/                Python klijent
├── tests/              backend_tests/ + ai_pipeline_tests/
├── Makefile
└── render.yaml
```

Blueprint: [`docs/architecture/BLUEPRINT.md`](docs/architecture/BLUEPRINT.md)

## API

| Endpoint | Auth | Namjena |
|---|---|---|
| `GET /health` | — | status, SHA, Chroma, DB |
| `GET /grants` | — | lista + filteri |
| `GET /grants/local` | — | ZDK / Tešanj |
| `GET /grants/urgent` | — | bliski rokovi |
| `POST /auth/register` `POST /auth/login` | — | JWT |
| `POST /search` | JWT | hybrid pretraga |
| `POST /ai-answer` | JWT | RAG odgovor (bs/en) |
| `POST /demo/ai-answer` | — | 3 guest upita |
| `POST /ingest` | JWT | ručni re-ingest |

SDK: [`sdk/client.py`](sdk/client.py)

## Pokretanje

Treba Python 3.12+ (ili Docker) i [Gemini API key](https://aistudio.google.com/app/apikey).

```bash
git clone https://github.com/dinohatibovic/EU_Funds_and_Grants_AI.git
cd EU_Funds_and_Grants_AI
cp .env.example .env
make up          # backend :8000, frontend :3000
# ili: pip install -r requirements.txt && make dev
```

```bash
make lint && make test && make ai-test
```

Onboarding: [`docs/onboarding.md`](docs/onboarding.md)

Prebuilt image:

```bash
docker pull ghcr.io/dinohatibovic/finassistbh-backend:2.2.1
```

## Izvori grantova

Prioritet: Općina Tešanj, ZDK, ZEDA, FMRPO, FBiH javni pozivi, DEI BiH,
Funding & Tenders / SEDIA, IPA, WBIF. TED je javna nabavka, ne grant katalog.

Svaki zapis treba: naziv, iznos ako je poznat, rok ili `null`, URL, nivo
pouzdanosti. Nepoznat rok ostaje nepoznat.

## Ograničenja (namjerno vidljiva)

- 30 grantova — proizvodni katalog, ne cijeli EU space
- Render free: cold start, Chroma se gradi na startupu
- Rate limit je in-memory, jedan worker (`WEB_CONCURRENCY=1`)
- Stripe pretplate i SMTP alerti još nisu produkcijski tok
- AI odgovor je informativan, nije pravni savjet ni prijava na fond

## Komercijalna licenca

Kod je proprietary. Pregled u ovom repou je dozvoljen u edukativne svrhe.
Komercijalna upotreba: [LICENSE](LICENSE).

| Plan | Cijena |
|---|---|
| Starter | €29 / mj |
| Pro | €149 / mj |
| Agency | €299 / mj |
| Enterprise | €799 / mj |

## Kontakt

**Dino Hatibović** — Tešanj, Zeničko-dobojski kanton, BiH
holdin.genesis@gmail.com · [GitHub](https://github.com/dinohatibovic) ·
[LinkedIn](https://linkedin.com/in/dinohatibovic)

Copyright © 2026 Dino Hatibović. Sva prava zadržana.

*Građeno u Tešnju, za firme koje ostavljaju EU novac na stolu.*
