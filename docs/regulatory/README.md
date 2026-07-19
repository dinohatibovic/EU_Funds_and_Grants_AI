# Regulatory framework — compliance and escalation

This directory tracks the regulatory compliance of the FinAssistBH platform.
**Status: framework in progress** — the documents below mark what is
implemented and what is on the roadmap. Nothing here is legal advice.

## GDPR / personal data protection

| Item | Status |
|---|---|
| Minimal data collection (email + password hash only) | ✅ implemented |
| Passwords never stored in plaintext (SHA256+salt) | ✅ implemented |
| `.env` secrets kept out of the repository | ✅ implemented |
| Right to erasure (delete-account endpoint) | 🔜 roadmap |
| DPAs (Data Processing Agreements) for Supabase/Render/Google | 🔜 roadmap |
| Privacy policy on the frontend | 🔜 roadmap |

## EU AI Act — AI system transparency

FinAssistBH is an informational RAG assistant (limited-risk category):

| Item | Status |
|---|---|
| Users clearly know they are talking to an AI system | ✅ (UI labeled as AI) |
| Answers cite sources (grant URLs) | ✅ implemented |
| Data reliability labels (✅/⚠️/❌, "unverified" status) | ✅ in grants.json |
| RAG query logging for audits (docs/forensics/) | 🔜 roadmap |
| Documented model provider (Google Gemini) and versions | ✅ in BLUEPRINT.md |

## Security incident reporting and escalation

1. **Critical vulnerabilities** — privately to the owner (contact in the root
   `SECURITY.md`).
2. **Other incidents** — GitHub issue via the `security_incident.md` template.
3. Dependency vulnerabilities are scanned automatically every week
   (`.github/workflows/security-audit.yml` — pip-audit, Bandit, gitleaks).

## Escalation contacts

```
Owner/DPO: Dino Hatibović — Tešanj, BiH — holdin.genesis@gmail.com
Regulator (BiH): Personal Data Protection Agency of BiH — azlp.ba
```
