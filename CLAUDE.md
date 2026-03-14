# CLAUDE.md — FinAssistBH Lokalni Pozivi
# Dino Hatibović | Tešanj, BiH | Mart 2026.
#
# SVRHA: Ovaj fajl Claude Code čita automatski.
# Sadrži sve lokalne i regionalne pozive za grantove
# koje bot treba znati i koje url_monitor.py treba pratiti.

---

## PROJEKAT

- Naziv: EU_Funds_and_Grants_AI (FinAssistBH)
- Stack: FastAPI + ChromaDB + Google Gemini Embeddings + RAG
- Frontend: https://dinohatibovic.github.io/EU_Funds_and_Grants_AI/
- OS: Ubuntu 24.04.1 LTS (WSL2) | Python 3.12.3

---

## TIER 1 — LOKALNI POZIVI (Tešanj + ZDK Kanton)

### Općina Tešanj
```
URL:      https://www.tesanj.ba/
Odjel:    Odjel za privredu i lokalni razvoj
Tel:      +387 32 650 100
Fokus:    Poticaji za polj., obrt, malo poduzetništvo
Scraping: /javni-pozivi/ ili /aktuelnosti/
```

### ZDK — Zeničko-dobojski kanton
```
URL:      https://zdk.ba/ministarstva/ministarstvo-za-privredu
Fokus:    Kantonalni poticaji za poljoprivredu i privredu
Scraping: pratiti /aktuelnosti/ i /javni-pozivi/
Napomena: ⭐ Prioritet — Tešanj je u ZDK
```

### ZEDA — Zenička razvojna agencija
```
URL:      https://zeda.ba/javni-pozivi/
Fokus:    Agregira ZDK pozive, refundacija troškova,
          poticaji za konkurentnost MSP
Scraping: Strukturiran HTML, relativno lak za parse
Tel:      +387 32 449 400 (Privredna komora ZDK)
```

### Privredna komora ZDK
```
URL:      https://pkzdk.ba/
Fokus:    Obavještenja o federalnim i kantonalnim natječajima
Tel:      +387 32 449 400
```

---

## TIER 2 — FEDERALNI POZIVI (FBiH)

### Federalno ministarstvo poljoprivrede, vodoprivrede i šumarstva
```
URL:      https://fmpvs.gov.ba/
API:      Nema — scraping stranice
Fokus:    Program novčanih podrški u polj. i ruralnom razvoju
          (Nacrt za 2026. u javnoj raspravi feb. 2026.)
Email:    info@fmpvs.gov.ba
Tel:      +387 33 726 550
Adresa:   Hamdije Čemerlića 2, 71000 Sarajevo
```

### FMRPO — Fed. ministarstvo razvoja, poduzetništva i obrta
```
URL:      https://fmrpo.gov.ba/
Pozivi:   https://javnipozivi.fmrpo.gov.ba/        ← PRIORITET
Fokus:    Grant sredstva 28 mil. KM (2026.)
          - Poticaj novoosnovanim subjektima
          - Razvoj obrta i srodnih djelatnosti
          - Jačanje konkurentnosti MSP
          - Start-up ekosistem
          - Poduzetničke zone
Info dan: Organizovan u Zenici (Priv. komora ZDK)
```

### Federalni zavod za zapošljavanje
```
URL:      https://www.fzzz.ba/
Fokus:    Sufinansiranje zapošljavanja, "Prvo radno iskustvo"
          Država plaća doprinose 12 mj. za nove radnike
```

### Fond za zaštitu okoliša FBiH
```
URL:      https://fzofbih.org.ba/
Fokus:    Energetska efikasnost, solarni paneli,
          obnovljiva energija za javne i privatne subjekte
```

### Federalni javni pozivi — agregator
```
URL:      https://javnipozivi.gov.ba
Fokus:    Svi otvoreni FBiH pozivi, dugme "Otvoren"
Scraping: Strukturiran HTML, visok prioritet
```

---

## TIER 3 — EU I MEĐUNARODNI POZIVI

### EU4Agri — Podrška poljoprivredi BiH
```
Pozivi:   https://javnipoziv.undp.ba         ← Prijave ovdje
Vijesti:  https://eu4agri.ba
Fokus:    Ruralni razvoj, mehanizacija, prerada
          voća/povrća, certifikacija
Iznosi:   30.000 KM do 200.000 KM po projektu
Impl.:    UNDP BiH u saradnji s EU
```

### UNDP BiH
```
URL:      https://www.ba.undp.org/
Pozivi:   https://javnipoziv.undp.ba
Fokus:    Poljoprivreda, ruralni razvoj, okoliš
```

### EU4CAET — Energetska efikasnost
```
URL:      https://eu4caet.ba/
Iznos:    99.999 EUR – 170.000 EUR po projektu
Pokriće:  50% – 80% troškova
Rok:      30. mart 2026. do 16:00h  ← HITNO
Fokus:    Solarni PV, biomasa, toplotne pumpe
Impl.:    GIZ BiH
```

### FIPA — Agencija za strane investicije
```
URL:      https://fipa.gov.ba/
Fokus:    Poticaji do 150.000 KM za IT i industriju
```

### DEI BiH — Direktorat za evropske integracije
```
URL:      https://www.dei.gov.ba/en/eu-programmes
Fokus:    EU programi specifični za BiH
Scraping: Laravel/PHP backend
```

### eufondovikonkursi.com — Regionalni agregator
```
URL:      https://www.eufondovikonkursi.com/
Filter:   ?country=bih&sector=agriculture
Fokus:    BiH, Srbija, MK, CG — svi sektori
Scraping: Moguć, strukturiran HTML
```

---

## AKTIVNI LOKALNI GRANTOVI — Mart 2026.

```python
LOCAL_GRANTS = [
    {
        "title":    "FMRPO Grant Sredstva 2026 — Novo poduzetništvo",
        "category": "Federalni",
        "budget":   "28.000.000 KM (ukupni fond)",
        "deadline": "2026-04-30",   # okvirno, pratiti javnipozivi.fmrpo.gov.ba
        "relevance":"Visoka",
        "url":      "https://javnipozivi.fmrpo.gov.ba/",
        "note":     "Uključuje: novo poduzetništvo, obrti, MSP, start-upi",
    },
    {
        "title":    "EU4CAET Grant — Energetska efikasnost",
        "category": "EU/GIZ",
        "budget":   "99.999 EUR – 170.000 EUR",
        "deadline": "2026-03-30",   # ⚠️ HITNO — za 24 dana
        "relevance":"Visoka",
        "url":      "https://eu4caet.ba/",
        "note":     "Pokriva 50–80% troškova. Solarni, biomasa, toplotne pumpe.",
    },
    {
        "title":    "EU4Agri — Ruralni razvoj i poljoprivreda",
        "category": "EU/UNDP",
        "budget":   "30.000 KM – 200.000 KM",
        "deadline": "Varijabilno — pratiti javnipoziv.undp.ba",
        "relevance":"Visoka",
        "url":      "https://javnipoziv.undp.ba",
        "note":     "Mehanizacija, prerada, certifikacija. Fokus: ZDK i FBiH.",
    },
    {
        "title":    "FBiH Program novčanih podrški u poljoprivredi 2026",
        "category": "Federalni",
        "budget":   "Varijabilno — budžet u pripremi",
        "deadline": "Q2 2026 — pratiti fmpvs.gov.ba",
        "relevance":"Visoka",
        "url":      "https://fmpvs.gov.ba/",
        "note":     "Nacrt programa bio u javnoj raspravi feb. 2026.",
    },
    {
        "title":    "ZEDA — Refundacija troškova konkurentnosti",
        "category": "Kantonalni (ZDK)",
        "budget":   "Do 50% refundacija",
        "deadline": "Varijabilno — pratiti zeda.ba",
        "relevance":"Visoka",
        "url":      "https://zeda.ba/javni-pozivi/",
        "note":     "Direktno relevantno za Tešanj (ZDK kanton).",
    },
    {
        "title":    "Fond za zaštitu okoliša FBiH",
        "category": "Specijalni (FBiH)",
        "budget":   "Varijabilno",
        "deadline": "2026-06-15",
        "relevance":"Srednja",
        "url":      "https://fzofbih.org.ba/",
        "note":     "Solarni paneli, energetska sanacija, biomasa.",
    },
    {
        "title":    "Innovate Bosnia — Grantovi za startupe",
        "category": "Nacionalni",
        "budget":   "50.000 KM max",
        "deadline": "2026-03-31",   # ⚠️ HITNO — za 25 dana
        "relevance":"Visoka",
        "url":      "https://javnipozivi.fmrpo.gov.ba/",
        "note":     "Tech startupe, digitalni proizvodi.",
    },
    {
        "title":    "FIPA Poticaji — IT sektor",
        "category": "Nacionalni",
        "budget":   "150.000 KM max",
        "deadline": "2026-04-15",
        "relevance":"Srednja",
        "url":      "https://fipa.gov.ba/",
        "note":     "Za investicije u IT sektor u BiH.",
    },
]
```

---

## URL_MONITOR.PY — Stranice za praćenje

```python
# Dodaj ove URL-ove u url_monitor.py → LOKALNE STRANICE sekcija

MONITOR_URLS_LOCAL = {
    # --- ZDK / Tešanj ---
    "tesanj_opcina":     "https://www.tesanj.ba/",
    "zdk_privreda":      "https://zdk.ba/ministarstva/ministarstvo-za-privredu",
    "zeda_pozivi":       "https://zeda.ba/javni-pozivi/",      # ⭐ PRIORITET

    # --- Federalni ---
    "fmrpo_pozivi":      "https://javnipozivi.fmrpo.gov.ba/",  # ⭐ PRIORITET
    "fmpvs_polj":        "https://fmpvs.gov.ba/",
    "fbih_javni_pozivi": "https://javnipozivi.gov.ba",
    "fzzz":              "https://www.fzzz.ba/",
    "fzofbih":           "https://fzofbih.org.ba/",

    # --- EU / Međunarodni ---
    "eu4agri":           "https://eu4agri.ba",
    "undp_pozivi":       "https://javnipoziv.undp.ba",
    "eu4caet":           "https://eu4caet.ba/",
    "dei_bih":           "https://www.dei.gov.ba/en/eu-programmes",
    "fipa":              "https://fipa.gov.ba/",

    # --- Agregatori ---
    "eufondovi":         "https://www.eufondovikonkursi.com/",
    "webalkans_bih":     "https://webalkans.eu/en/country/bosnia-and-herzegovina/",
}
```

---

## PRAVILA ZA BOTA

1. Svaki grant mora imati: naziv, iznos, rok, URL izvor, nivo pouzdanosti.
2. Nikad ne navoditi rokove bez provjere datuma.
3. BiH je kandidat za EU — NIJE punopravna članica.
4. GIZ je implementator (ne finansijer) — izvor je EU.
5. Lokalni pozivi (ZDK/Tešanj) imaju prioritet za korisnike iz tog kantona.
6. Oznake pouzdanosti: ✅ VISOKA | ⚠️ SREDNJA | ❌ NEPOTVRĐENO

---

## KONTAKTI — Brza referenca

```
Federalno ministarstvo poljoprivrede:
  📧 info@fmpvs.gov.ba
  ☎️ +387 33 726 550

Privredna komora ZDK (Zenica):
  ☎️ +387 32 449 400

Općina Tešanj:
  🌐 www.tesanj.ba
  ☎️ +387 32 650 100

UNDP BiH pozivi:
  🌐 javnipoziv.undp.ba

FMRPO grant pozivi:
  🌐 javnipozivi.fmrpo.gov.ba
```

---

## Poznati bugovi (popravi kad dođeš)

1. `ingestion/ingest_sample.py:138` — kolekcija je `"grants"` umjesto `"eu_grants"`
2. `main.py:34` — `allow_origins=["*"]` zamijeni whitelist-om

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
