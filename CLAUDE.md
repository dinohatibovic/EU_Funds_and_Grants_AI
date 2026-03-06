# CLAUDE.md — FinAssistBH kontekst za Claude Code

Ovaj fajl Claude Code automatski čita pri svakom pokretanju sesije.
Ne treba mu objašnjavati kontekst — sve je ovdje.

---

## Projekat

**FinAssistBH** — AI platforma za pronalazak i apliciranje na EU i BiH grantove.
Vlasnik: Dino Hatibović, Tešanj, ZDK, BiH.
Telefon: +387 62 564 303

Stack: Python 3.12 / FastAPI / Google Gemini / ChromaDB / HTML+Tailwind

---

## HITNI ROKOVI (ažuriraj po potrebi)

| Grant | Rok | Status |
|---|---|---|
| EU4CAET Energetika (GIZ/EU) | 30. mart 2026. | **AKTIVAN — ~24 dana** |
| Innovate Bosnia startupi (FIPA) | 31. mart 2026. | **AKTIVAN — ~25 dana** |
| FIPA podsticaji IT sektor | 15. april 2026. | Aktivan |
| Program Digitalna Evropa | 30. april 2026. | Aktivan |

---

## Lokalni grantovi — Tier 1 (ZDK / Tešanj)

```python
LOCAL_GRANTS = {
    "ZDK_fond": {
        "naziv": "Kantonalni fond za razvoj ZDK",
        "url": "https://zdk.ba/",
        "tip": "MSP, poljoprivreda, sport, kultura",
        "iznos": "do €50.000",
        "ko_aplicira": "Firme i udruženja registrovana u ZDK",
        "rok": "2026-10-15"
    },
    "RARS_RS": {
        "naziv": "Razvojno-poduzetnički centar Tešanj",
        "url": "https://rpc-tesanj.ba/",
        "tip": "Lokalni MSP poduzetnici",
        "iznos": "varijabilno",
        "ko_aplicira": "Preduzeća s područja Tešnja"
    }
}
```

---

## URL Monitor — lokalni izvori za `url_monitor.py`

```python
MONITOR_URLS_LOCAL = {
    # Tier 1 — Lokalni (Tešanj / ZDK)
    "ZDK_kanton":       "https://zdk.ba/",
    "RPC_Tesanj":       "https://rpc-tesanj.ba/",
    "Opcina_Tesanj":    "https://opcina-tesanj.ba/",

    # Tier 2 — Federalni
    "FIPA":             "https://fipa.gov.ba/",
    "FBiH_Vlada":       "https://www.fbihvlada.gov.ba/",
    "Fond_ZO_FBiH":     "https://fzofbih.org.ba/",
    "FZZZ":             "https://www.fzzz.ba/",

    # Tier 3 — EU / Međunarodni
    "EU_Delegacija_BiH":"https://europa.ba/",
    "GIZ_BiH":          "https://www.giz.de/en/worldwide/289.html",
    "USAID_BiH":        "https://www.usaid.gov/bosnia-and-herzegovina",
    "Interreg_IPA":     "https://www.interreg.eu/",
    "EU4CAET":          "https://eu4caet.eu/",
}
```

---

## Arhitektura

```
User → index.html (Tailwind dashboard)
     → main.py (FastAPI)
       → rag/pipeline.py
         → embeddings/embedding_client.py  (Gemini)
         → vector_db/chroma_client.py      (ChromaDB)
       → agent/agent.py (opciono, za chat)
         → agent/genai_client.py           (Gemini 2.0 Flash)

eu_funds_ai/ — napredni moduli (zasebni, nije u main.py):
  url_monitor.py       — scraping u pozadini
  eligibility_engine.py — da li firma ispunjava uvjete
  notification_system.py — email/SMS za rokove
  subscription_manager.py — BASIC/STANDARD/PREMIUM
  analytics_dashboard.py — Plotly izvještaji
  data_pipeline.py     — pipeline za kvalitet podataka
```

---

## Poznati bugovi (popravi kad dođeš)

1. `rag/pipeline.py:33` — poziva `embed_single()` ali metoda se zove `generate_embeddings()`
2. `api/server.py` — orphaned kod blok van funkcije (linija ~130)
3. `ingestion/web_scraper.py:61` — poziva `embed_single()` i `db.add()` (ispravno: `add_documents()`)
4. `agent/main_agent.py` — poziva `RAGPipeline.run()` (metoda se zove `.search()`)
5. `main.py:34` — `allow_origins=["*"]` zamijeni whitelist-om

---

## Fajlovi za brisanje (duplikati / dead code)

| Fajl | Zašto izbaciti |
|---|---|
| `ingest_sample.py` (root) | Duplikat od `ingestion/ingest_sample.py` |
| `newindex.html` | Zastarjela verzija, zamijenjena s `index.html` |
| `api/server.py` | Duplikat od `main.py` — koristi samo jedan |
| `project_report.json` | Prazan template, nikad popunjen |
| `frontend/index.html` | Minimalna verzija, zastarjela |

---

## Servisi koji nedostaju (TODO lista)

- [ ] `.env.example` fajl (GEMINI_API_KEY template)
- [ ] PostgreSQL ili Supabase (za persistence korisnika)
- [ ] Stripe integracija (pretplate)
- [ ] SMTP konfiguracija (notifikacije)
- [ ] Redis za caching API odgovora
- [ ] Integracijski testovi za RAG pipeline

---

## Prodaja chatbota — može!

Da — chatbot (AI agent) možeš prodavati kao SaaS. Model cijena je već definiran:
Starter €29/mj → Enterprise €799/mj. Ključne opcije:
1. **SaaS model** — pretplata, hosting na tvojem serveru
2. **White-label** — Agency plan, firma dobija chatbot pod svojim brendom
3. **API pristup** — developer plan, integracija u tuđe sisteme

Potrebno dodati: autentifikacija korisnika, Stripe, rate limiting po planu.
