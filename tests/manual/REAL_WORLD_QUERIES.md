# FinAssistBH Manual Benchmark

Datum: 2026-08-24

## JWT/Auth

PASS

- register radi
- login radi
- auth/me radi

---

## Digitalizacija firme u ZDK

Query:

grant za digitalizaciju firme u ZDK

Expected:

- ZEDA
- FMRPO
- Digital Europe

Actual:

- ZDK fond
- Digital Europe
- ZEDA
- FMRPO

Status:

PASS (partial)

---

## Poljoprivreda BiH

Query:

Poticaji za poljoprivredu u BiH

Expected:

- FMPVS
- EU4AGRI

Actual:

- ZDK fond
- FMPVS
- EU4AGRI

Status:

NEEDS TUNING

---

## Deployment

Commit:

db8abc8

Message:

fix: rerank grant search results by quality

Status:

LIVE on Render

---

## Dataset

Current grants:

19

Recommendation:

Expand grants dataset to 100+

Add:

- verified_score
- source_priority
- automated ingestion
