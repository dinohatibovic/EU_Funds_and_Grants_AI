# FinAssistBH Project Report

## Verified baseline

| Field | Verified value |
|---|---|
| Product | EU Funds & Grants AI, FinAssistBH |
| Production release | `v2.2.1` |
| Release commit | `f8355363ef9ea16ce8fd4a376c57fd6144511c33` |
| Post-release documentation main | `585a02cf11c8ca497461e207b1885415ada67d95` |
| Production API | `https://eu-funds-and-grants-ai.onrender.com` |
| Grant records | 30 |
| ChromaDB collection | `eu_grants` |
| ChromaDB documents | 30 |
| Embedding model | `gemini-embedding-001` |
| Embedding dimensions | 3072 |
| Generation model | `gemini-2.5-flash` |
| Automated tests | 87 |
| Database | PostgreSQL in production with SQLite fallback |
| Backend lifecycle | FastAPI lifespan context manager |

## Product purpose

FinAssistBH is a production RAG application for discovering EU, Bosnian,
federal, cantonal, and local funding programs. The platform focuses on Bosnia
and Herzegovina, with priority coverage for the Zenica-Doboj Canton and
Tešanj.

The product combines:

- a structured grant dataset
- Gemini embeddings
- ChromaDB semantic retrieval
- deterministic metadata-aware reranking
- Gemini answer generation
- JWT-protected user flows
- a FastAPI backend
- a static GitHub Pages frontend
- automated production health verification

## Production architecture

```text
User
  |
  v
GitHub Pages frontend
  |
  v
Render FastAPI backend
  |
  +--> PostgreSQL user database
  |
  +--> Gemini embedding and generation APIs
  |
  +--> ChromaDB collection eu_grants
          |
          +--> 30 structured grant documents
```

The backend starts through a FastAPI lifespan context manager. Startup:

1. initializes the user database
2. falls back to SQLite if the configured database is unavailable
3. loads the grant cache
4. initializes AI clients
5. synchronizes the grant dataset with ChromaDB
6. completes application startup

The production process uses one worker through `WEB_CONCURRENCY=1`.

## Data and retrieval contracts

The source dataset is `data/grants.json` and contains 30 unique grant records.

The embedding contract is:

```text
Model:      gemini-embedding-001
Dimensions: 3072
Batch size: 10
```

The production dataset is embedded in three batches of ten records.

The vector-store contract is:

```text
Collection: eu_grants
Documents:  30
```

Dataset synchronization follows a failure-safe order. New records are embedded
and upserted before stale records are removed, so a failed embedding or write
operation does not delete the existing production collection.

## API user flows

Public endpoints include:

```text
GET  /health
GET  /grants
GET  /grants/local
GET  /grants/urgent
POST /auth/register
POST /auth/login
GET  /auth/me
```

JWT-protected endpoints include:

```text
POST /search
POST /ai-answer
POST /ingest
```

The production authenticated smoke test verified:

- registration returns HTTP 200
- JWT issuance succeeds
- `/auth/me` confirms the token identity
- `/search` returns HTTP 200 and five results
- `/ai-answer` returns HTTP 200 and five sources
- unauthenticated `/search` returns HTTP 401
- unauthenticated `/ai-answer` returns HTTP 401

The observed authenticated smoke run returned:

```text
Search processing time:     0.350 seconds
AI-answer processing time:  9.028 seconds
AI-answer size:             2674 characters
AI-answer source count:     5
```

These values describe one verified smoke run and are not latency guarantees.

## Production health contract

The public health endpoint exposes:

```text
status
version
git_commit
chroma_collection
chroma_documents
database
db_type
ai_engine
grants_total
grants_in_vector_db
grants_urgent_30d
timestamp
```

The verified v2.2.1 release reported:

```text
status:               healthy
version:              2.2.1
release commit:       f8355363ef9ea16ce8fd4a376c57fd6144511c33
chroma_collection:    eu_grants
chroma_documents:     30
database:             connected
db_type:              postgresql
ai_engine:            ready
grants_total:         30
grants_in_vector_db:  30
```

After the post-release documentation merge, production correctly reported the
new `main` commit while retaining application version `2.2.1`.

## Search evaluation

The benchmark contains 15 representative production queries and 53 graded
query-document judgments. Binary relevance uses threshold 2.

Full product-level baseline across all 15 queries:

```text
HitRate@5: 0.8667
MRR@10:    0.7622
NDCG@10:   0.6293
```

Sensitivity baseline across 14 evaluable queries:

```text
HitRate@5: 0.9286
MRR@10:    0.8167
NDCG@10:   0.6573
```

Production processing time across the 15 benchmark search requests:

```text
Mean:               0.2423 seconds
Median:             0.2421 seconds
Minimum:            0.2171 seconds
Maximum:            0.2699 seconds
P95 nearest rank:   0.2699 seconds
```

Query 13, `zapošljavanje mladih u FBiH`, has no confirmed binary-relevant
document in the current 30-grant dataset. It remains included in the full
product score as a dataset coverage failure and is excluded only from the
14-query ranking sensitivity view.

Query 14, `energetska efikasnost MSP`, misses HitRate@5 and places the first
binary-relevant result at rank 10. This is the clearest current ranking
improvement target.

## Test and delivery evidence

The verified local suite contains 87 tests.

Focused coverage includes:

- backend API behavior
- authentication
- FastAPI lifespan startup ordering
- PostgreSQL-to-SQLite fallback
- failure-safe AI startup
- health release metadata
- Chroma collection contracts
- Chroma write contracts
- benchmark metric calculations
- grant data integrity

The release delivery chain is:

```text
main release commit
  -> annotated v2.2.1 tag
  -> GitHub Release
  -> GHCR container build
  -> tags 2.2.1 and latest
  -> production health verification
```

The release workflow, CI/CD workflow, Security Audit, GitHub Pages deployment,
and Production Health Check completed successfully.

## Container artifact

Versioned image:

```text
ghcr.io/dinohatibovic/finassistbh-backend:2.2.1
```

Current release image:

```text
ghcr.io/dinohatibovic/finassistbh-backend:latest
```

Immutable manifest:

```text
ghcr.io/dinohatibovic/finassistbh-backend@sha256:7878f5e101107423fedc37643461d7b34e5818ea7ab5737dff8c0020319a62e1
```

The public registry returned HTTP 200 for the versioned manifest. GHCR package
metadata confirmed that `2.2.1` and `latest` reference the published release
record.

## Known limitations

- The Render free instance can sleep while inactive, causing a cold start of
  approximately 50 seconds or more.
- ChromaDB data on the free ephemeral filesystem is rebuilt from the source
  dataset during startup.
- The current dataset has no confirmed youth-employment funding record for
  Query 13.
- Query 14 requires further retrieval and reranking work.
- The rate limiter is in memory and is appropriate only for a single-process
  deployment.
- JWT uses HS256 and requires a stable production `JWT_SECRET`.
- SBOM and container provenance attestations are not yet part of the release
  workflow.

## Next development priorities

1. Expand the dataset with verified programs for uncovered user needs.
2. Repeat the production benchmark after dataset changes.
3. Add behavior-lock tests for `backend/app/api/search.py`.
4. Decompose retrieval, reranking, and answer-generation logic in isolated
   pull requests.
5. Add container SBOM and provenance attestations.
6. Keep local LLM, LangChain, LangGraph, and local RAG experimentation
   separate from the stable production release path.

## Evidence links

- Release: `https://github.com/dinohatibovic/EU_Funds_and_Grants_AI/releases/tag/v2.2.1`
- Production health: `https://eu-funds-and-grants-ai.onrender.com/health`
- GHCR package: `https://github.com/dinohatibovic/EU_Funds_and_Grants_AI/pkgs/container/finassistbh-backend`
- Changelog: `../CHANGELOG.md`
- Architecture blueprint: `architecture/BLUEPRINT.md`
- Deployment checklist: `DEPLOYMENT_CHECKLIST.md`
