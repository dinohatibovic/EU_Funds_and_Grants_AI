# Render Deployment

The authoritative Render Blueprint is `/render.yaml` in the repository root.
This directory documents the verified production deployment contract.

## Production service

| Setting | Value |
|---|---|
| Service | `finassistbh-api` |
| Runtime | Python |
| Build | `pip install -r requirements.txt` |
| Start | `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/health` |
| Worker count | `WEB_CONCURRENCY=1` |
| Application version | `2.2.1` |

If the Render service was created manually rather than from the Blueprint,
the Dashboard configuration remains authoritative and must be kept aligned
with `/render.yaml`.

## Required environment variables

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Gemini embedding and generation API |
| `JWT_SECRET` | Yes | Stable JWT signing secret |
| `DATABASE_URL` | Production | PostgreSQL connection |
| `WEB_CONCURRENCY` | Yes | Keep at `1` for current process-local state |
| `GEMINI_MODEL` | Optional | Generation model, default `gemini-2.5-flash` |
| `DB_PATH` | Optional | SQLite fallback path |
| `CHROMA_DB_PATH` | Optional | ChromaDB persistence path |
| `RATE_LIMIT_REQUESTS` | Optional | Request limit |
| `RATE_LIMIT_WINDOW` | Optional | Rate-limit window |

Secrets must remain in Render Environment settings and must not be committed.

## Startup lifecycle

Production startup uses the FastAPI lifespan mechanism.

Startup performs:

```text
1. initialize PostgreSQL user storage
2. switch to SQLite only if database initialization fails
3. load the 30-grant cache
4. initialize Gemini and Chroma clients
5. generate three embedding batches of ten records
6. synchronize collection eu_grants
7. complete application startup
```

Embedding contract:

```text
Model:      gemini-embedding-001
Dimensions: 3072
```

Chroma contract:

```text
Collection: eu_grants
Documents:  30
```

## Production health verification

Run:

```bash
curl -fsS \
  --max-time 90 \
  https://eu-funds-and-grants-ai.onrender.com/health
```

Expected stable fields:

```text
status=healthy
version=2.2.1
git_commit=<currently deployed main commit>
chroma_collection=eu_grants
chroma_documents=30
database=connected
db_type=postgresql
ai_engine=ready
grants_total=30
grants_in_vector_db=30
```

The deployed `git_commit` changes after every successful post-release
documentation or code deployment. The immutable release tag `v2.2.1` remains
on release commit `f8355363ef9ea16ce8fd4a376c57fd6144511c33`.

## Automated verification

The Production Health Check workflow verifies:

- HTTP health availability
- application version
- deployed Git commit identity
- Chroma collection name
- indexed document count
- database status
- AI engine readiness
- loaded grant count

Authenticated smoke testing additionally verifies registration, JWT issuance,
`/auth/me`, `/search`, and `/ai-answer`.

## Free-instance limitations

- The service can sleep during inactivity.
- The first request after sleep can take 50 seconds or more.
- The filesystem is ephemeral.
- ChromaDB is rebuilt from `data/grants.json` during startup.
- PostgreSQL remains external and persistent.
- Local `users.db` is only a fallback and is not persistent on the free
  filesystem.

## Release artifact

```text
GitHub Release:
v2.2.1

Container:
ghcr.io/dinohatibovic/finassistbh-backend:2.2.1

Immutable manifest:
ghcr.io/dinohatibovic/finassistbh-backend@sha256:7878f5e101107423fedc37643461d7b34e5818ea7ab5737dff8c0020319a62e1
```

Use the versioned image or immutable digest for reproducible deployments.
