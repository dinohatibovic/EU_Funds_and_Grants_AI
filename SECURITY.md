# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 2.2.x   | ✅ |
| < 2.2   | ❌ |

## Reporting a vulnerability

**Critical vulnerabilities** (access to user data, API keys, auth bypass)
must be reported **privately** — do not open a public issue:

```
Dino Hatibović — project owner
Tešanj, Zenica-Doboj Canton, Bosnia and Herzegovina
Email: holdin.genesis@gmail.com
GitHub: @dinohatibovic (Private Vulnerability Reporting / DM)
```

**Other security issues** can be reported through the GitHub issue template
[`security_incident.md`](.github/ISSUE_TEMPLATE/security_incident.md).

Expected response: acknowledgement within 72 hours; weekly status updates
until the vulnerability is resolved or declined with an explanation.

## Automated checks

- `security-audit.yml` workflow: **pip-audit** (dependency CVEs, weekly),
  **Bandit** (static analysis), **gitleaks** (hardcoded secrets).
- Secrets are kept exclusively in environment variables (`.env` is gitignored).

## Known security limitations (roadmap)

- Password hashing is SHA256+salt — migration to bcrypt/argon2 is planned.
- The rate limiter is in-memory (per process) — Redis is planned for scaling.

## Temporary dependency-audit exceptions

The security workflow contains documented temporary exceptions for known
advisories affecting the pinned ChromaDB release.

These exceptions:

- apply only to explicitly listed advisory identifiers;
- do not disable `pip-audit` for other dependencies;
- must be reviewed whenever ChromaDB is upgraded;
- must be removed when a compatible patched release becomes available.

The authoritative exception list and rationale are maintained in
`.github/workflows/security-audit.yml`.
