# Security Policy

## Podržane verzije

| Verzija | Podržana |
| ------- | -------- |
| 2.2.x   | ✅ |
| < 2.2   | ❌ |

## Prijava ranjivosti

**Kritične ranjivosti** (pristup podacima korisnika, API ključevima, auth bypass)
prijavi **privatno** — ne otvaraj javni issue:

```
Dino Hatibović — vlasnik projekta
Tešanj, Zeničko-dobojski kanton, BiH
Telefon: +387 62 564 303
GitHub: @dinohatibovic (Private Vulnerability Reporting / DM)
```

**Ostale sigurnosne probleme** prijavi kroz GitHub issue šablon
[`security_incident.md`](.github/ISSUE_TEMPLATE/security_incident.md).

Očekivani odgovor: potvrda prijema u roku 72h; status update sedmično dok se
ranjivost ne riješi ili odbaci s obrazloženjem.

## Automatizovane provjere

- `security-audit.yml` workflow: **pip-audit** (CVE u zavisnostima, sedmično),
  **Bandit** (statička analiza), **gitleaks** (hardkodirane tajne).
- Tajne se drže isključivo u env varijablama (`.env` je u `.gitignore`).

## Poznata sigurnosna ograničenja (roadmap)

- Password hashing je SHA256+salt — planirana migracija na bcrypt/argon2.
- Rate limiter je in-memory (per-proces) — Redis planiran za skaliranje.
