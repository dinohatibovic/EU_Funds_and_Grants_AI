# Render Deployment

The Render Blueprint (`render.yaml`) **must live in the repository root** —
Render only looks for it there. The authoritative file is therefore
[`/render.yaml`](../../render.yaml); this directory documents the deployment
layer.

## Configuration

| Setting | Value |
|---|---|
| Service | `finassistbh-api` (web, Python runtime) |
| Build | `pip install -r requirements.txt` |
| Start | `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/health` |

> ⚠️ If the service was created manually (not via the Blueprint), `render.yaml`
> is ignored — the Start Command must be updated by hand in the Render
> Dashboard → Settings whenever it changes.

## Environment variables (Render Dashboard → Environment)

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `JWT_SECRET` | ✅ | Stable secret (otherwise users get logged out on every restart) |
| `GEMINI_MODEL` | ⬜ | Generation model (default `gemini-2.5-flash`) |
| `DATABASE_URL` | ⬜ | PostgreSQL/Supabase connection string (SQLite fallback without it) |
| `DB_PATH` | ⬜ | SQLite path (default `users.db`) |
| `CHROMA_DB_PATH` | ⬜ | ChromaDB store path (default `vector_db/chroma_db_data`) |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW` | ⬜ | Rate limiting (default 30/60s) |

## Known free-tier limitations

- **Cold start 50–75s** — the frontend (`auth.html`) has a built-in progress
  UX for this.
- **Ephemeral disk** — `users.db` and ChromaDB are wiped on restart; startup
  auto-ingest repopulates the vector DB from `data/grants.json`.
