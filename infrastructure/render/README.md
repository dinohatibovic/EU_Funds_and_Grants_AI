# Render Deployment

Render Blueprint (`render.yaml`) **mora živjeti u root-u repozitorija** — Render
ga isključivo tamo traži. Zato je autoritativni fajl [`/render.yaml`](../../render.yaml),
a ovaj direktorij služi kao dokumentacija deployment sloja.

## Konfiguracija

| Postavka | Vrijednost |
|---|---|
| Service | `finassistbh-api` (web, Python runtime) |
| Build | `pip install -r requirements.txt` |
| Start | `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/health` |

## Environment varijable (Render Dashboard → Environment)

| Varijabla | Obavezna | Opis |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Google Gemini API ključ |
| `JWT_SECRET` | ✅ | Stabilan tajni ključ (inače se korisnici odjavljuju pri svakom restartu) |
| `DATABASE_URL` | ⬜ | PostgreSQL/Supabase connection string (bez njega → SQLite fallback) |
| `DB_PATH` | ⬜ | SQLite putanja (default `users.db`) |
| `CHROMA_DB_PATH` | ⬜ | Putanja ChromaDB store-a (default `vector_db/chroma_db_data`) |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW` | ⬜ | Rate limiting (default 30/60s) |

## Poznata ograničenja free tier-a

- **Cold start 50–75s** — frontend (`auth.html`) ima ugrađen progress UX za ovo.
- **Ephemeral disk** — `users.db` i ChromaDB se brišu pri restartu; auto-ingest
  na startupu ponovo puni vektorsku bazu iz `data/grants.json`.
