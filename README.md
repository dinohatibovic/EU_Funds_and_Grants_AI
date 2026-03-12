# FinAssistBH — AI platforma za EU grantove u BiH

![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)

**FinAssistBH** je AI alat koji agregira sve EU i domaće BiH fondove na jednom mjestu, te pomaže firmama, NVO-ima i privatnim osobama da pronađu i apliciraju za grantove koji odgovaraju njihovom profilu.

> Bosna i Hercegovina koristi manje od 30% dostupnih EU sredstava. FinAssistBH to mijenja.

---

## Šta platforma radi

- **AI pretraga grantova** — upišeš opis firme/projekta, sistem pronađe relevantne fondove
- **Vođenje kompletne projektne dokumentacije** — od prijave do izvještaja
- **Monitoring 32+ izvora** u realnom vremenu (EU portali, FBiH, ZDK, FIPA, GIZ, USAID...)
- **Dashboard** s rokovima, budžetima i relevantnošću po kategoriji
- **Pitch za investitore** s modelom cijena (Starter / Pro / Agency / Enterprise)

---

## Tehnički stack

| Sloj | Tehnologija |
|---|---|
| Backend | Python 3.12, FastAPI |
| AI / Embeddings | Google Gemini 2.0 Flash + `gemini-embedding-001` |
| Vector DB | ChromaDB (lokalno, perzistentno) |
| Frontend | HTML + Tailwind CSS + Chart.js |
| Deployment | Docker, Render / Heroku |

---

## Pokretanje lokalno

```bash
# 1. Kloniraj repo
git clone https://github.com/dinohatibovic/EU_Funds_and_Grants_AI
cd EU_Funds_and_Grants_AI

# 2. Instaliraj zavisnosti
pip install -r requirements.txt

# 3. Postavi API ključ
cp .env.example .env
# Unesi GEMINI_API_KEY u .env

# 4. Učitaj podatke u vector bazu
python ingestion/ingest_sample.py
python ingestion/ingest_real_data.py

# 5. Pokreni server
uvicorn main:app --reload
```

Frontend: otvori `index.html` u browseru.

---

## Struktura projekta

```
EU_Funds_and_Grants_AI/
├── main.py                    ← FastAPI server (entry point)
├── index.html                 ← Glavni dashboard
├── pitch.html                 ← Stranica za investitore
├── data/grants.json           ← 14 verificiranih grantova
├── agent/                     ← AI agent (RAG + Gemini)
├── rag/                       ← RAG pipeline
├── embeddings/                ← Gemini embedding klijent
├── vector_db/                 ← ChromaDB klijent
├── ingestion/                 ← Učitavanje podataka
├── eu_funds_ai/               ← Napredni moduli
│   ├── url_monitor.py         ← Scraping 15+ BiH/EU izvora
│   ├── eligibility_engine.py  ← Procjena podobnosti
│   ├── notification_system.py ← Email/SMS upozorenja za rokove
│   ├── subscription_manager.py← Upravljanje pretplatama
│   ├── analytics_dashboard.py ← Izvještaji i vizualizacije
│   └── data_pipeline.py       ← Procesiranje podataka
└── tests/                     ← Unit testovi
```

---

## Model cijena

| Plan | Cijena | Za koga |
|---|---|---|
| Starter | €29/mj | Mala preduzeća, osnovna pretraga |
| Pro | €149/mj | MSP, notifikacije, AI matching |
| Agency | €299/mj | Konzultanti, white-label |
| Enterprise | €799/mj | Kantoni, vlade, korporacije |

---

## Kontakt

**Dino Hatibović** — Tešanj, Zeničko-dobojski kanton, BiH
Telefon: +387 62 564 303
GitHub: [github.com/dinohatibovic](https://github.com/dinohatibovic)
LinkedIn: [linkedin.com/in/dinohatibovic](https://linkedin.com/in/dinohatibovic)

---

*Razvijeno u Tešnju, BiH — za EU tržište.*
