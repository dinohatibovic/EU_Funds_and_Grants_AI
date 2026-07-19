# Forensic logs and system analyses

This directory stores artifacts of technical system audits — a durable audit
trail kept separate from the code.

## What belongs here

- Code and architecture audit reports (dated, immutable)
- Incident analyses (postmortem documents)
- Results of `infrastructure/scripts/verify_sync.py` audits
  (route parity, data drift, security headers)
- Performance snapshots and security scan results

## Naming convention

```
YYYY-MM-DD_<type>_<short-description>.md
e.g. 2026-07-12_audit_repo-restructure.md
```

## A note on runtime logs

Application runtime logs (uvicorn/FastAPI) are NOT committed here — they live
in the hosting platform (Render Logs). Only analyzed, summarized findings go
here. Automatic logging of all RAG queries into this directory is on the
roadmap (see docs/regulatory/README.md — EU AI Act transparency).
