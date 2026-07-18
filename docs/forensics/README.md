# Forenzički logovi i sistemske analize

Ovaj direktorij čuva artefakte tehničkih revizija sistema — trajni zapis za
audit trail, odvojeno od koda.

## Šta ide ovdje

- Izvještaji revizija koda i arhitekture (datirani, immutable)
- Analize incidenata (postmortem dokumenti)
- Rezultati `infrastructure/scripts/verify_sync.py` audita
  (route parity, data drift, security headers)
- Snapshot analize performansi i sigurnosnih skenova

## Konvencija imenovanja

```
YYYY-MM-DD_<tip>_<kratki-opis>.md
npr. 2026-07-12_audit_repo-restructure.md
```

## Napomena o runtime logovima

Aplikacijski runtime logovi (uvicorn/FastAPI) se NE commituju ovdje — oni žive
u hosting platformi (Render Logs). Ovdje idu samo analizirani, sažeti nalazi.
Automatsko logovanje svih RAG upita u ovaj direktorij je na roadmapi
(vidi docs/regulatory/README.md — EU AI Act transparentnost).
