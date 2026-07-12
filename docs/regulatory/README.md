# Regulatorni okvir — usklađenost i eskalacija

Ovaj direktorij prati regulatornu usklađenost FinAssistBH platforme.
**Status: okvir u pripremi** — dokumenti ispod označavaju šta je implementirano,
a šta je na roadmapi. Ništa ovdje nije pravni savjet.

## GDPR / Zaštita ličnih podataka

| Stavka | Status |
|---|---|
| Minimalna kolekcija podataka (samo email + hash lozinke) | ✅ implementirano |
| Lozinke se nikad ne čuvaju u plaintextu (SHA256+salt) | ✅ implementirano |
| `.env` tajne van repozitorija | ✅ implementirano |
| Pravo na brisanje (delete account endpoint) | 🔜 roadmap |
| DPA (Data Processing Agreement) za Supabase/Render/Google | 🔜 roadmap |
| Politika privatnosti na frontendu | 🔜 roadmap |

## EU AI Act — transparentnost AI sistema

FinAssistBH je informativni RAG asistent (limited-risk kategorija):

| Stavka | Status |
|---|---|
| Korisniku je jasno da razgovara s AI sistemom | ✅ (UI označen kao AI) |
| Odgovori navode izvore (URL grantova) | ✅ implementirano |
| Oznake pouzdanosti podataka (✅/⚠️/❌, status "neprovjereno") | ✅ u grants.json |
| Logovanje RAG upita za audit (docs/forensics/) | 🔜 roadmap |
| Dokumentovan model provider (Google Gemini) i verzije | ✅ u BLUEPRINT.md |

## Prijava i eskalacija sigurnosnih incidenata

1. **Kritične ranjivosti** — privatno vlasniku (kontakt u root `SECURITY.md`).
2. **Ostali incidenti** — GitHub issue kroz šablon `security_incident.md`.
3. Ranjivosti zavisnosti se automatski skeniraju sedmično
   (`.github/workflows/security-audit.yml` — pip-audit, Bandit, gitleaks).

## Eskalacijski kontakti

```
Vlasnik/DPO: Dino Hatibović — Tešanj, BiH — +387 62 564 303
Regulator (BiH): Agencija za zaštitu ličnih podataka BiH — azlp.ba
```
